import re
import warnings
from abc import abstractmethod
from typing import Optional, Callable, TypeAlias, Tuple

import numpy as np
import pandas as pd
import pint
from pint.errors import DimensionalityError
from numpy.linalg import solve
from pandas.core.groupby import DataFrameGroupBy

from posted.units import ureg


try:
    import igraph
    from igraph import Graph, Layout

    HAS_IGRAPH: bool = True
except ImportError:
    igraph = None

    class Graph:
        pass

    class Layout:
        pass

    HAS_IGRAPH: bool = False


# calculate annuity factor
def _annuity_factor(ir: ureg.Quantity, n: ureg.Quantity):
    try:
        n = n.to('a').m
        ir = ir.to('dimensionless').m
    except DimensionalityError:
        return np.nan

    return ir * (1 + ir) ** n / ((1 + ir) ** n - 1) / ureg('a')


# abstract analysis or manipulation
class AbstractAnalysisOrManipulation:
    @abstractmethod
    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        pass


# pandas dataframe accessor for groupby and perform methods
@pd.api.extensions.register_dataframe_accessor("team")
class TEAMAccessor:
    def __init__(self, df: pd.DataFrame):
        self._df = df
        self._fields = [c for c in self._df if c not in ('variable', 'unit', 'value')]
        for c in ('variable', 'unit', 'value'):
            if c not in df:
                raise AttributeError('Can only use .team accessor with team-like dataframes that contain at least the'
                                     'variable, unit, and value columns.')

    @property
    def fields(self):
        return self._fields

    # for grouping rows by fields (region, period, other...), including an `explode` statement for `nan` entries
    def groupby_fields(self, **kwargs) -> DataFrameGroupBy:
        if 'by' in kwargs:
            raise Exception("The 'by' argument is determined by team, you cannot provide it manually.")

        df = self._df
        for field in self._fields:
            df = df \
                .assign(**{field: lambda df: df[field].apply(
                    lambda cell: df[field].dropna().unique().tolist() if pd.isnull(cell) else cell
                )}) \
                .explode(field)
        return df.groupby(by=self._fields, **kwargs)

    # for performing analyses
    def perform(self, *aoms: AbstractAnalysisOrManipulation, dropna: bool = False, only_new: bool = False):
        # prepare data in dataframe format for manipulation
        df = self.groupby_fields(group_keys=False).apply(
            lambda rows: rows.pivot(
                index=rows.team.fields,
                columns='variable',
                values=['unit', 'value'],
            ),
        ).apply(
            func=lambda rows: {
                var: rows['value', var] * ureg(rows['unit', var] if pd.notnull(rows['unit', var]) else '')
                for var in rows.index.unique(level='variable')
            },
            axis=1,
            result_type='expand',
        ).rename_axis('variable', axis=1)

        # perform analysis or manipulation and bring rows back to original long dataframe format
        ret = [
            df.apply(lambda row: aom.perform(row), axis=1).rename_axis('variable', axis=1).stack().apply(
                lambda cell: pd.Series({'unit': str(cell.u), 'value': cell.m})
            ).reset_index()
            for aom in aoms
        ]

        if dropna:
            for new_rows in ret:
                new_rows.dropna(subset=['unit', 'value'], inplace=True)

        if not only_new:
            ret = [self._df] + ret

        return pd.concat(ret).reset_index(drop=True)


# types that a variable assignment can take: it can be an int, float, string, or a function to be called
VariableAssignment: TypeAlias = int | float | str | Callable


# generic manipulation for calculating variables
class CalcVariable(AbstractAnalysisOrManipulation):
    _assignments: dict[str, VariableAssignment]
    _unit: Optional[str | pint.Unit]

    def __init__(self, unit: Optional[str | pint.Unit] = None, **assignments: VariableAssignment):
        self._assignments = assignments
        self._unit = unit

        # check all supplied arguments are either functions or allowed values (int, float, string)
        for variable, assigned in self._assignments.items():
            if not (isinstance(assigned, int | float | str) or callable(assigned)):
                raise Exception(f"Assignments must be int, float, string, or callable, but found: {type(assigned)}")

        # check unit has correct format if supplied
        if not (unit is None or
                (isinstance(unit, str) and ureg.Unit(unit)) or
                (isinstance(unit, ureg.Unit) and id(unit._REGISTRY) == id(ureg))):
            raise Exception('Argument unit must be a valid posted unit.')

    def perform(self, row: pd.Series) -> pd.Series:
        return pd.Series({
            variable: assigned(row) if callable(assigned) else assigned
            for variable, assigned in self._assignments.items()
        })


# building value chains
class BuildValueChain(AbstractAnalysisOrManipulation):
    _name: str
    _proc_graph: dict[str, dict[str, list[str]]]

    def __init__(self,
                 name: str,
                 demand: dict[str, dict[str, pint.Quantity]],
                 process_diagram: Optional[str] = None,
                 process_tree: Optional[dict[str, dict[str, list[str]]]] = None,):
        if process_diagram is None and process_tree is None:
            raise Exception('Either the process_diagram or the process_tree argument must be provided.')
        if process_diagram is not None and process_tree is not None:
            raise Exception('The process_diagram and process_tree arguments cannot both be provided.')

        self._name = name
        self._demand = demand
        self._proc_graph = self._read_diagram(process_diagram) if process_diagram is not None else process_tree
        self._flows = list({
            flow
            for proc_edges in self._proc_graph.values()
            for flow in proc_edges
        })

    # get name of value chain
    @property
    def name(self) -> str:
        return self._name

    # get process graph as property
    @property
    def proc_graph(self) -> dict[str, dict[str, list[str]]]:
        return self._proc_graph

    # get process graph as igraph object for plotting
    def igraph(self) -> Tuple[Graph, Layout]:
        if not HAS_IGRAPH:
            raise ImportError("Need to install the `igraph` package first. Please run `pip install igraph` or `poetry "
                              "add igraph`.")

        procs = list(self._proc_graph.keys())
        graph = igraph.Graph(
            n=len(procs),
            edges=[
                (procs.index(p1), procs.index(p2))
                for p1 in procs
                for flow, procs2 in self._proc_graph[p1].items()
                for p2 in procs2
            ],
        )
        graph.vs['name'] = procs
        graph.es['name'] = [flow for p1 in procs for flow in self._proc_graph[p1]]

        layout = graph.layout_reingold_tilford(root=[len(graph.vs) - 1])
        layout.rotate(angle=90)

        return graph, layout

    # reduce a single subdiagram
    @staticmethod
    def _reduce_subdiagram(subdiagram: str) -> tuple[str, str, str]:
        processes = []
        for token in subdiagram.split('=>'):
            components = token.split('->')
            if len(components) == 1:
                processes.append((token.strip(' '), None))
            elif len(components) == 2:
                processes.append((components[0].strip(' '), components[1].strip(' ')))
            else:
                raise Exception(f"Too many consecutive `->` in diagram.")

        for i in range(len(processes)):
            proc, flow = processes[i]
            proc2 = processes[i + 1][0] if i + 1 < len(processes) else None
            if flow is None and i + 1 < len(processes):
                raise Exception(f"Flow must be provided for processes feeding into downstream processes: {subdiagram}")
            yield proc, flow, proc2

    # read the full diagram
    @staticmethod
    def _read_diagram(diagram: str) -> dict[str, dict[str, list[str]]]:
        out = {}
        for diagram in diagram.split(';'):
            for proc, flow, proc2 in BuildValueChain._reduce_subdiagram(diagram):
                if flow is None:
                    continue
                if proc in out:
                    if flow in out[proc]:
                        if proc2 is not None:
                            out[proc][flow].append(proc2)
                    else:
                        out[proc] |= {flow: ([proc2] if proc2 is not None else [])}
                else:
                    out[proc] = {flow: ([proc2] if proc2 is not None else [])}
                if proc2 is not None and proc2 not in out:
                    out[proc2] = {}

        return out

    # perform analysis by computing functional units from technosphere matrix
    def perform(self, row: pd.Series) -> pd.Series:
        # obtain technosphere matrix (tsm)
        tsm = np.array([
            [
                + row[f"Tech|{proc1}|Output|{flow}"].m
                if proc1 == proc2 else
                - row[f"Tech|{proc2}|Input|{flow}"].to(row[f"Tech|{proc1}|Output|{flow}"].u).m
                if proc2 in proc1_flow_targets else
                0.0
                for proc2 in self._proc_graph
            ]
            for proc1 in self._proc_graph
            for flow, proc1_flow_targets in self._proc_graph[proc1].items()
        ])

        # obtain demand
        d = np.array([
            self._demand[proc1][flow].to(row[f"Tech|{proc1}|Output|{flow}"].u).m
            if proc1 in self._demand and flow in self._demand[proc1] else
            0.0
            for proc1 in self._proc_graph
            for flow, proc1_flow_targets in self._proc_graph[proc1].items()
        ])

        # calculate functional units from technosphere matrix and demand
        func_units = solve(tsm, d)

        return pd.Series({
            f"Value Chain|{self._name}|Functional Units|{proc}": func_units[i] * ureg('')
            for i, proc in enumerate(list(self._proc_graph.keys()))
        } | {
            f"Value Chain|{self._name}|Demand|{proc}|{flow}": self._demand[proc][flow]
            for proc in self._demand
            for flow in self._demand[proc]
        })


class LCOXAnalysis(AbstractAnalysisOrManipulation):
    _reference: Optional[str]
    _value_chains: Optional[list[str]]
    _interest_rate: Optional[float]
    _book_lifetime: Optional[float]

    def __init__(self, value_chains: Optional[list[str]] = None, reference: Optional[str] = None,
                 interest_rate: Optional[float] = None, book_lifetime: Optional[float] = None):
        self._reference = reference
        self._value_chains = value_chains
        self._interest_rate = interest_rate * ureg('') if isinstance(interest_rate, int | float) else interest_rate
        self._book_lifetime = book_lifetime * ureg('a') if isinstance(book_lifetime, int | float) else book_lifetime

    # perform LCOX calculation for every value chain
    def perform(self, row: pd.Series) -> pd.Series:
        value_chains: list[str] = self._value_chains or list({
            var.split('|')[1]
            for var in row.index
            if var.startswith('Value Chain|')
        })

        return pd.Series({
            variable: value.to_base_units()
            for vc in value_chains
            for variable, value in self._calc(vc, row).items()
        })

    # calculate LCOX for one value chain
    def _calc(self, vc: str, row: pd.Series) -> dict[str, pint.Quantity]:
        reference = self._reference or next(var for var in row.index if var.startswith(f"Value Chain|{vc}|Demand|"))

        ret = {}
        for func_unit_tech, func_unit in row[row.index.str.startswith(f"Value Chain|{vc}|Functional Units|")].items():
            proc_id = func_unit_tech.split('|')[-1]
            row_proc = {
                key.removeprefix(f"Tech|{proc_id}|"): value
                for key, value in row.items()
                if key.startswith(f"Tech|{proc_id}|")
            }

            if 'CAPEX' in row_proc:
                if 'Interest Rate' not in row_proc:
                    if f"Techno-economic Assumptions|Interest Rate|{proc_id}" in row:
                        row_proc['Interest Rate'] = row[f"Techno-economic Assumptions|Interest Rate|{proc_id}"]
                    elif f"Techno-economic Assumptions|Interest Rate" in row:
                        row_proc['Interest Rate'] = row[f"Techno-economic Assumptions|Interest Rate"]
                    elif self._interest_rate is not None:
                        row_proc['Interest Rate'] = self._interest_rate

                    if f"Techno-economic Assumptions|Book Lifetime|{proc_id}" in row:
                        row_proc['Book Lifetime'] = row[f"Techno-economic Assumptions|Book Lifetime|{proc_id}"]
                    elif f"Techno-economic Assumptions|Book Lifetime" in row:
                        row_proc['Book Lifetime'] = row[f"Techno-economic Assumptions|Book Lifetime"]
                    elif self._book_lifetime is not None:
                        row_proc['Book Lifetime'] = self._book_lifetime
                    elif 'Lifetime' in row:
                        row_proc['Book Lifetime'] = row['Lifetime']

            for var_io_type, sign in [('Input', +1), ('Output', -1)]:
                for var_io in [v for v in row_proc if v.startswith(f"{var_io_type}|")]:
                    flow_io = var_io.split('|')[1]
                    if f"Price|{flow_io}|{proc_id}" in row:
                        row_proc[f"Price|{flow_io}"] = row[f"Price|{flow_io}|{proc_id}"]
                    elif f"Price|{flow_io}" in row:
                        row_proc[f"Price|{flow_io}"] = row[f"Price|{flow_io}"]

            for component, value in self._calc_proc(row_proc).items():
                ret[f"{proc_id}|{component}"] = value

        return {f"Value Chain|{vc}|LCOX|{k}": v / row[reference] for k, v in ret.items()}

    # calculate LCOX for a single process in a value chain
    def _calc_proc(self, row_proc: dict):
        ret = {}

        if 'CAPEX' in row_proc or 'OPEX Fixed' in row_proc:
            try:
                reference_capacity_var = next(
                    v for v in row_proc
                    if v.startswith('Input Capacity|') or v.startswith('Output Capacity|')
                )
                reference_capacity = row_proc[reference_capacity_var]
            except StopIteration:
                warnings.warn(f"No reference capacity found but CAPEX and/or OPEX Fixed variables provided for.")
                reference_capacity = np.nan

            if not pd.isnull(reference_capacity):
                try:
                    reference = row_proc[re.sub(r'(Input|Output) Capacity', r'\1', reference_capacity_var)]
                except KeyError:
                    warnings.warn(f"No reference input/output found matching the reference capacity.")
                    reference = np.nan

                if not pd.isnull(reference):
                    if 'OPEX Fixed' in row_proc:
                        ret['OM Cost'] = row_proc['OPEX Fixed'] / reference_capacity * reference

                    if 'CAPEX' in row_proc:
                        if all(v in row_proc for v in ('Interest Rate', 'Book Lifetime')):
                            ANF = _annuity_factor(row_proc['Interest Rate'], row_proc['Book Lifetime'])
                            ret['Capital Cost'] = ANF * row_proc['CAPEX'] / reference_capacity * reference
                        else:
                            warnings.warn(f"Annuity factor could not be determined.")

        for var_io_type, sign in [('Input', +1), ('Output', -1)]:
            for var_io in [v for v in row_proc if v.startswith(f"{var_io_type}|")]:
                flow_io = var_io.split('|')[1]
                var_io_price = f"Price|{flow_io}"
                if var_io_price in row_proc:
                    ret[f"{var_io_type} Cost"] = sign * row_proc[var_io_price] * row_proc[var_io]
                elif var_io_type == 'Input':
                    warnings.warn(f"Price not found corresponding to Input: {var_io}")

        return ret
