import re
import warnings
from abc import abstractmethod
from typing import Optional, Callable, TypeAlias, Tuple

import numpy as np
import pandas as pd
import pint
import pint_pandas
from pint.errors import DimensionalityError
from numpy.linalg import solve
from pandas.core.groupby import DataFrameGroupBy

from posted.units import ureg, unit_convert


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


# set the unit registry for pint_pandas
pint_pandas.PintType.ureg = ureg


# calculate annuity factor
def annuity_factor(ir: ureg.Quantity, n: ureg.Quantity):
    try:
        ir = ir.to('dimensionless').m
        n = n.to('a').m
    except DimensionalityError:
        return np.nan

    return ir * (1 + ir) ** n / ((1 + ir) ** n - 1) / ureg('a')


# define abstract manipulation class
class AbstractManipulation:
    @abstractmethod
    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        pass


# pandas dataframe accessor for groupby and perform methods
@pd.api.extensions.register_dataframe_accessor('team')
class TEAMAccessor:
    def __init__(self, df: pd.DataFrame):
        # check that column axis has only one level
        if df.columns.nlevels > 1:
            raise ValueError('Can only use .team accessor with team-like dataframes that contain only one column '
                             'layer.')

        # check that at least variable, unit, and value are among the columns
        if not all(c in df for c in ('variable', 'unit', 'value')):
            raise ValueError('Can only use .team accessor with team-like dataframes that contain at least the variable, '
                             'unit, and value columns.')

        # store arguments
        self._df = df
        self._fields = [c for c in self._df if c not in ('variable', 'unit', 'value')]

    @property
    def fields(self):
        return self._fields

    # explode rows with nan entries
    def explode(self, fields: Optional[str | list[str]] = None) -> pd.DataFrame:
        df = self._df
        fields = self._fields if fields is None else [fields] if isinstance(fields, str) else fields
        for field in fields:
            df = df \
                .assign(**{field: lambda df: df[field].apply(
                    lambda cell: df[field].dropna().unique().tolist() if pd.isnull(cell) else cell
                )}) \
                .explode(field)

        return df.reset_index(drop=True)

    # for grouping rows by fields (region, period, other...), including an `explode` statement for `nan` entries
    def groupby_fields(self, **kwargs) -> DataFrameGroupBy:
        if 'by' in kwargs:
            raise Exception("The 'by' argument is determined by team, you cannot provide it manually.")
        return self.explode().groupby(by=self._fields, **kwargs)

    # pivot posted-formatted dataframe from long to wide (variables as columns)
    def pivot_wide(self):
        ret = self.explode().pivot(
            index=self._fields,
            columns=['variable', 'unit'],
            values='value',
        )
        if ret.columns.get_level_values(level='unit').isna().any():
            raise Exception('Unit column may not contain NaN entries. Please use "dimensionless" or "No Unit" if the '
                            'variable has no unit.')
        return ret.pint.quantify()

    # for performing analyses
    def perform(self, *manipulations: AbstractManipulation, dropna: bool = False, only_new: bool = False):
        # pivot dataframe before manipulation
        df_pivot = self.pivot_wide()

        # perform analysis or manipulation and bring rows back to original long dataframe format
        for manipulation in manipulations:
            original_index = df_pivot.index
            df_pivot = manipulation.perform(df_pivot)
            if not df_pivot.index.equals(original_index):
                raise Exception('Manipulation may not change the index.')

        # ensure that the axis label still exists before melt
        df_pivot.rename_axis('variable', axis=1, inplace=True)

        # pivot back
        ret = df_pivot \
            .pint.dequantify() \
            .melt(ignore_index=False) \
            .reset_index()

        # drop rows with na entries in unit or value columns
        if dropna:
            ret.dropna(subset=['unit', 'value'], inplace=True)

        # keep only new variables
        if only_new:
            ret = ret.loc[~ret['variable'].isin(self._df['variable'].unique())]

        # return
        return ret.reset_index(drop=True)

    # for splitting variable components into separate columns
    def varsplit(self, cmd: Optional[str] = None, regex: Optional[str] = None,
                 new_variable: Optional[str | bool] = True, keep_unmatched: bool = False):
        # check that precisely one of the two arguments (cmd and regex) is provided
        if cmd is not None and regex is not None:
            raise Exception('Only one of the two arguments may be provided: cmd or regex.')
        if cmd is None and regex is None:
            raise Exception('Either a command or a regex string must be provided.')

        # determine regex from cmd if necessary
        if regex is None:
            regex = '^' + r'\|'.join([rf'(?P<{t[1:]}>[^|]*)' if t[0] == '?' else t for t in cmd.split('|')]) + '$'

        # determine value of new variable column from arguments
        if new_variable is False:
            new_variable = None
        elif new_variable is True:
            if cmd is None:
                warnings.warn("The variable cannot be set automatically when using a custom regex.")
                new_variable = None
            else:
                new_variable = '|'.join([t for t in cmd.split('|') if t[0] != '?'])

        # create dataframe to be returned by applying regex to variable column and dropping unmatched rows
        ret = self._df['variable'].str.extract(regex)

        # assign new variable column and drop if all are nan
        cond = ret.notnull().any(axis=1)
        ret['variable'] = self._df['variable']
        ret.loc[cond, 'variable'] = new_variable or np.nan

        # drop unmatched rows if requested
        if not keep_unmatched:
            ret.dropna(inplace=True)

        # drop variable column if all nan
        if ret['variable'].isnull().all():
            ret.drop(columns='variable', inplace=True)

        # combine with original dataframe and return
        return ret.combine_first(self._df.loc[ret.index].drop(columns='variable'))


    # convert units
    def unit_convert(self, to: str | pint.Unit | dict[str, str | pint.Unit], flow_id: Optional[str] = None):
        return self._df.assign(
                unit_to=to if not isinstance(to, dict) else self._df.apply(
                    lambda row: to[row['variable']] if row['variable'] in to else row['unit'], axis=1,
                ),
                value=lambda df: df.apply(
                    lambda row: row['value'] * unit_convert(row['unit'], row['unit_to'], flow_id=flow_id), axis=1,
                ),
            ) \
            .drop(columns='unit') \
            .rename(columns={'unit_to': 'unit'})


# new variable can be calculated through expression assignments or keyword assignments
# expression assignments are of form "`a` = `b` + `c`" and are based on the pandas eval functionality
# keyword assignment must be int, float, string, or a function to be called to assign to the variable defined as key
ExprAssignment: TypeAlias = str
KeywordAssignment: TypeAlias = int | float | str | Callable


# generic manipulation for calculating variables
class CalcVariable(AbstractManipulation):
    _expr_assignments: tuple[ExprAssignment]
    _kw_assignments: dict[str, KeywordAssignment]

    def __init__(self, *expr_assignments: ExprAssignment, **kw_assignments: KeywordAssignment):
        self._expr_assignments = expr_assignments
        self._kw_assignments = kw_assignments

        # check all supplied arguments are valid
        for expr_assignment in self._expr_assignments:
            if not isinstance(expr_assignment, str):
                raise Exception(f"Expression assignments must be of type str, but found: {type(expr_assignment)}")
        for kw_assignment in self._kw_assignments.values():
            if not (isinstance(kw_assignment, int | float | str) or callable(kw_assignment)):
                raise Exception(f"Keyword assignments must be of type int, float, string, or callable, but found: "
                                f"{type(kw_assignment)}")

    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        for expr_assignment in self._expr_assignments:
            df.eval(expr_assignment, inplace=True, engine='python')
        df = df.assign(**self._kw_assignments)
        return df


# calculate levelised cost of X
class LCOX(AbstractManipulation):
    _name: str
    _reference: str
    _process: str
    _interest_rate: Optional[float]
    _book_lifetime: Optional[float]

    def __init__(self, name: str, process: str, reference: str,
                 interest_rate: Optional[float] = None, book_lifetime: Optional[float] = None):
        self._name = name
        self._reference = reference
        self._process = process
        self._interest_rate = interest_rate * ureg('') if isinstance(interest_rate, int | float) else interest_rate
        self._book_lifetime = book_lifetime * ureg('a') if isinstance(book_lifetime, int | float) else book_lifetime

    # perform
    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        # calculate levelised cost, prepend "LCOX|{name}|" before column names, and divide by reference
        ret = self.calc_cost(df) \
            .rename(columns=lambda col_name: f"LCOX|{self._name}|{col_name}") \
            .apply(lambda col: col / df[f"Tech|{self._process}|{self._reference}"])
        return pd.concat([df, ret], axis=1)

    # calc levelised cost
    def calc_cost(self, df: pd.DataFrame) -> pd.DataFrame:
        tech = self._varsplit(df, f"Tech|{self._process}|?variable")
        prices = self._varsplit(df, 'Price|?io')
        iocaps = self._varsplit(df, regex=fr"Tech\|{self._process}\|((?:Input|Output) Capacity\|.*)")
        ios = self._varsplit(df, regex=fr"Tech\|{self._process}\|((?:Input|Output)\|.*)")

        # determine reference capacity and reference of that reference capacity for CAPEX and OPEX Fixed
        if any(c in tech for c in ('CAPEX', 'OPEX Fixed')):
            try:
                cap = iocaps.iloc[:, 0]
                capref = ios[re.sub(r'(Input|Output) Capacity', r'\1', cap.name)]
            except IndexError:
                warnings.warn('Could not find a reference capacity for CAPEX and OPEX columns.')
                cap = capref = None
            except KeyError:
                warnings.warn('Could not find reference matching the reference capacity.')
                capref = None
        else:
            cap = capref = None

        ret = pd.DataFrame(index=df.index)

        # calc capital cost and fixed OM cost
        if cap is not None and capref is not None:
            OCF = tech['OCF'] if 'OCF' in tech else 1.0

            if 'CAPEX' in tech:
                ANF = annuity_factor(self._interest_rate, self._book_lifetime)
                ret['Capital'] = ANF * tech['CAPEX'] / OCF / cap * capref

            if 'OPEX Fixed' in tech:
                ret['OM Fixed'] = tech['OPEX Fixed'] / OCF / cap * capref

        # calc var OM cost
        if 'OPEX Variable' in tech:
            ret['OM Variable'] = tech['OPEX Variable']

        # calc input cost
        for io in ios:
            if io == self._reference:
                continue
            io_type, io_flow = io.split('|', 2)
            if io_flow not in prices:
                warnings.warn(
                    f"'{io}' is ignored in LCOX, because it is neither the reference nor an associated price is given.")
                continue
            # inputs are counted as costs, outputs are counted as revenues
            sign = +1 if io_type == 'Input' else -1
            ret[f"{io_type} Cost|{io_flow}"] = sign * ios[io] * prices[io_flow]

        return ret


# building value chains
class BuildValueChain(AbstractManipulation):
    _name: str
    _demand: dict[str, dict[str, pint.Quantity]]
    _sc_demand: dict[str, dict[str, pint.Quantity]] | None
    _proc_graph: dict[str, dict[str, list[str]]] | None

    def __init__(self,
                 name: str,
                 demand: dict[str, dict[str, pint.Quantity]],
                 process_diagram: Optional[str] = None,
                 process_tree: Optional[dict[str, dict[str, list[str]]]] = None,
                 sc_demand: Optional[dict[str, dict[str, pint.Quantity]]] = None,
                 ):
        if process_diagram is None and process_tree is None:
            raise Exception('Either the process_diagram or the process_tree argument must be provided.')
        if process_diagram is not None and process_tree is not None:
            raise Exception('The process_diagram and process_tree arguments cannot both be provided.')

        self._name = name
        self._demand = demand
        self._sc_demand = sc_demand
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

    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.apply(self._perform_row, axis=1).combine_first(df)

    # perform analysis by computing functional units from technosphere matrix
    def _perform_row(self, row: pd.Series) -> pd.Series:
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

        # add supply-chain demand
        if self._sc_demand is not None:
            tsm = np.concatenate([
                tsm,
                [
                    [
                        row[f"Tech|{proc1}|Output|{flow}"].m
                        if proc1 == proc2 else
                        0.0
                        for proc2 in self._proc_graph
                    ]
                    for proc1 in self._sc_demand
                    for flow in self._sc_demand[proc1]
                ]
            ])
            d = np.concatenate([
                d,
                [
                    self._sc_demand[proc1][flow].to(row[f"Tech|{proc1}|Output|{flow}"].u).m
                    for proc1 in self._sc_demand
                    for flow in self._sc_demand[proc1]
                ]
            ])

        # calculate functional units from technosphere matrix and demand
        func_units = solve(tsm, d)

        return pd.Series({
            f"Value Chain|{self._name}|Functional Units|{proc}": func_units[i] * ureg('')
            for i, proc in enumerate(list(self._proc_graph.keys()))
        } | ({
            f"Value Chain|{self._name}|Demand|{proc}|{flow}": self._demand[proc][flow]
            for proc in self._demand
            for flow in self._demand[proc]
        } if self._demand is not None else {}) | ({
            f"Value Chain|{self._name}|SC Demand|{proc}|{flow}": self._sc_demand[proc][flow]
            for proc in self._sc_demand
            for flow in self._sc_demand[proc]
        } if self._sc_demand is not None else {}))


class LCOXAnalysis(AbstractManipulation):
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

    # perform
    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.apply(self._perform_row, axis=1).combine_first(df)

    # perform LCOX calculation for every value chain
    def _perform_row(self, row: pd.Series) -> pd.Series:
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
        reference = self._reference
        if reference is None:
            try:
                reference = next(var for var in row.index if var.startswith(f"Value Chain|{vc}|Demand|"))
            except StopIteration:
                try:
                    reference = next(var for var in row.index if var.startswith(f"Value Chain|{vc}|SC Demand|"))
                except StopIteration:
                    raise Exception('The LCOX Analysis requires a reference (demand or supply-chain demand provided as '
                                    'either argument or one of the dataframe variables).')

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
                        ret['OM Fixed'] = row_proc['OPEX Fixed'] / reference_capacity * reference

                    if 'CAPEX' in row_proc:
                        if all(v in row_proc for v in ('Interest Rate', 'Book Lifetime')):
                            ANF = annuity_factor(row_proc['Interest Rate'], row_proc['Book Lifetime'])
                            ret['Capital'] = ANF * row_proc['CAPEX'] / reference_capacity * reference
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
