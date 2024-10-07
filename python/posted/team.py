import re
import warnings
from abc import abstractmethod
from itertools import product
from typing import Optional, Callable, TypeAlias, Tuple

import numpy as np
import pandas as pd
import pint
import pint_pandas
from pint.errors import DimensionalityError
from numpy.linalg import solve
from pandas.core.groupby import DataFrameGroupBy

from posted.units import ureg, unit_convert, Q, U

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
def annuity_factor(ir: Q, bl: Q):
    try:
        ir = ir.to('dimensionless').m
        bl = bl.to('a').m
    except DimensionalityError:
        return np.nan

    return ir * (1 + ir) ** bl / ((1 + ir) ** bl - 1) / Q('1 a')


# define abstract manipulation class
class AbstractManipulation:
    @abstractmethod
    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    def _varsplit(self,
                  df: pd.DataFrame,
                  cmd: Optional[str] = None,
                  regex: Optional[str] = None) -> pd.DataFrame:
        # Check that precisely one of the two arguments (cmd and regex)
        # is provided.
        if cmd is not None and regex is not None:
            raise Exception('Only one of the two arguments may be provided: '
                            'cmd or regex.')
        if cmd is None and regex is None:
            raise Exception('Either a command or a regex string must be '
                            'provided.')

        # Determine regex from cmd if necessary.
        if regex is None:
            regex = '^' + r'\|'.join([
                rf'(?P<{t[1:]}>[^|]*)' if t[0] == '?' else
                rf'(?P<{t[1:]}>.*)' if t[0] == '*' else
                re.escape(t)
                for t in cmd.split('|')
            ]) + '$'

        # Extract new columns from existing.
        cols_extracted = df.columns.str.extract(regex)
        df_new = df[df.columns[cols_extracted.notnull().all(axis=1)]]
        df_new.columns = (
            pd.MultiIndex.from_frame(cols_extracted.dropna())
            if len(cols_extracted.columns) > 1 else
            cols_extracted.dropna().iloc[:, 0]
        )

        # Return new dataframe.
        return df_new


# pandas dataframe accessor for groupby and perform methods
@pd.api.extensions.register_dataframe_accessor('team')
class TEAMAccessor:
    def __init__(self, df: pd.DataFrame):
        # Check that column axis has only one level.
        if df.columns.nlevels > 1:
            raise ValueError('Can only use .team accessor with team-like '
                             'dataframes that contain only one column layer.')

        # Check that at least variable, unit, and value are among the columns.
        if not all(c in df for c in ('variable', 'unit', 'value')):
            raise ValueError('Can only use .team accessor with team-like '
                             'dataframes that contain at least the variable, '
                             'unit, and value columns.')

        # Check that there are no nans among variable, unit, and value columns.
        for c in ('variable', 'unit', 'value'):
            if df[c].isnull().any():
                ex_msg = ('Can only use .team accessor with team-like '
                          'dataframes in which there are no nan entries in '
                          'the variable, unit, and value columns.')
                if c == 'unit':
                    ex_msg += (' Please use "dimensionless" or "No Unit" if '
                               'the variable has no unit.')
                raise ValueError(ex_msg)

        # Warn if 'unfielded' column exists.
        if 'unfielded' in df.columns:
            warnings.warn("Having a column named 'unfielded' in the dataframe "
                          "may result in unexpected behaviour.")

        # Store arguments as member fields.
        self._df = df
        self._fields = [
            c for c in self._df
            if c not in ('variable', 'unit', 'value')
        ]

    @property
    def fields(self):
        return self._fields

    def explode(self,
                fields: Optional[str | list[str]] = None) -> pd.DataFrame:
        """
        Explode rows with nan entries.

        Parameters
        ----------
        fields : str | list[str] | None
            The list of fields to explode.

        Returns
        -------
            pd.DataFrame
                The dataframe with nan entries in the respective fields
                exploded.
        """
        df = self._df
        fields = (
            self._fields if fields is None else [fields]
            if isinstance(fields, str) else fields
        )
        for field in fields:
            explodable = pd.Series(
                index=df.index,
                data=len(df)*[df[field].dropna().unique().tolist()],
            )
            df = (
                df
                .assign(**{field: df[field].fillna(explodable)})
                .explode(field)
            )

        return df.reset_index(drop=True)

    def groupby_fields(self, **kwargs) -> DataFrameGroupBy:
        """
        Group by field columns (region, period, other...). Fields with
        rows that contain nan entries will be 'exploded' first.

        Parameters
        ----------
        kwargs
            Passed on to pd.DataFrame.groupby.

        Returns
        -------
            pd.DataFrameGroupBy
                The grouped dataframe rows.
        """
        if 'by' in kwargs:
            raise Exception("The 'by' argument is determined by team, you "
                            "cannot provide it manually.")
        return self.explode().groupby(by=self._fields, **kwargs)

    def pivot_wide(self):
        """
        Pivot dataframe wide, such that column names are variables.

        Returns
        -------
            pd.DataFrame
                The original dataframe in pivot mode.
        """
        ret = self.explode()

        # Create dummy field if non exists.
        if not self._fields:
            ret = ret.assign(unfielded=0)
            fields = self._fields + ['unfielded']
        else:
            fields = self._fields

        # Pivot dataframe.
        ret = ret.pivot(
            index=fields,
            columns=['variable', 'unit'],
            values='value',
        )

        # Raise exception if duplicate cases exist.
        if ret.index.has_duplicates:
            raise ValueError('Performed pivot_wide on dataframe with '
                             'duplicate cases. Each variable should only be '
                             'defined once for each combination of field '
                             'values.')

        return ret.pint.quantify()

    # for performing analyses
    def perform(self,
                *manipulations: AbstractManipulation,
                dropna: bool = True,
                only_new: bool = False):
        """
        Perform manipulation(s).

        Parameters
        ----------
        manipulations : AbstractManipulation
            The manipulations to apply to the dataframe.
        dropna : bool
            Whether to drop nan rows at the end.
        only_new : bool
            Whether to only keep new variables.

        Returns
        -------
            pd.DataFrame
                The dataframe that underwent the manipulation(s).
        """
        # Pivot dataframe before manipulation.
        df_pivot = self.pivot_wide()

        # Create list of column groups of variables and units.
        col_groups = (
            pd.Series(df_pivot.columns)
            .reset_index()
            .groupby('variable')
            .groups
        )

        # Raise exception in case of duplicate variables with different units.
        for col_name in col_groups:
            df_pivot_sub = df_pivot[col_name]
            if isinstance(df_pivot_sub, pd.Series):
                continue
            duplicate_indexes = (df_pivot_sub.notnull().sum(axis=1) > 1)
            if duplicate_indexes.any():
                warnings.warn(f"Duplicate units in variable '{col_name}' for "
                              f"fields: {df_pivot.index[duplicate_indexes]}")

        # Loop over groups.
        df_pivot_list = []
        for col_ids in product(*col_groups.values()):
            df_pivot_group = df_pivot.iloc[:, list(col_ids)].dropna(how='all')

            # Perform analysis or manipulation and bring rows back to
            # original long dataframe format.
            for manipulation in manipulations:
                original_index = df_pivot_group.index
                df_pivot_group = manipulation.perform(df_pivot_group)
                if not isinstance(df_pivot_group, pd.DataFrame):
                    raise Exception('Manipulation must return a dataframe.')
                if not df_pivot_group.index.equals(original_index):
                    raise Exception('Manipulation may not change the index.')

            # Ensure that the axis label still exists before melt.
            df_pivot_group.rename_axis('variable', axis=1, inplace=True)

            # Pivot back and append.
            df_pivot_list.append(
                df_pivot_group
                    .pint.dequantify()
                    .melt(ignore_index=False)
                    .reset_index()
            )

        # Combine groups into single dataframe.
        ret = pd.concat(df_pivot_list)

        # Drop rows with nan entries in unit or value columns.
        if dropna:
            ret.dropna(subset='value', inplace=True)

        # Drop duplicates arising from multiple var-unit groups.
        ret.drop_duplicates(inplace=True)

        # Raise exception if index has duplicates after the above.
        duplicates = ret.duplicated(subset=self._fields + ['variable'])
        if duplicates.any():
            duplicate_labels = ret.loc[duplicates, self._fields + ['variable']]
            raise Exception(f"Internal error: variables should only exist "
                            f"once per case: {duplicate_labels}")

        # Keep only new variables if requested.
        if only_new:
            ret = ret.loc[~ret['variable'].isin(self._df['variable'].unique())]

        # Drop column called 'unfielded' if it exists.
        if 'unfielded' in ret.columns:
            ret = ret.drop(columns='unfielded')

        # Return dataframe.
        return ret.reset_index(drop=True)

    def varsplit(self,
                 cmd: Optional[str] = None,
                 regex: Optional[str] = None,
                 target: str = 'variable',
                 new: Optional[str | bool] = True,
                 keep_unmatched: bool = False) -> pd.DataFrame:
        """
        Split variable components separated by pipe characters into
        separate columns. The pattern must either be provided as
        `cmd` or as `regex`.

        Parameters
        ----------
        cmd : str
            A command to interpret into a regex.
        regex : str
            A direct regex.
        target : str
            (Optional) The name of the column where the new
            variable will be stored.
        new : str
            (Optional) The new variable name.
        keep_unmatched : bool
            Whether or not to keep unmatched rows.

        Returns
        -------
            pd.DataFrame
                The dataframe that contains the new split variables.
        """
        # Check that precisely one of the two arguments (either `cmd`
        # or `regex`) is provided.
        if cmd is not None and regex is not None:
            raise Exception('Only one of the two arguments may be provided: '
                            'cmd or regex.')
        if cmd is None and regex is None:
            raise Exception('Either a command or a regex string must be '
                            'provided.')

        # Check that target is in columns of dataframe.
        if target not in self._df.columns:
            raise Exception(f"Could not find column of name '{target}' in "
                            f"dataframe.")

        # Determine regex from cmd if necessary.
        if regex is None:
            regex = '^' + r'\|'.join([
                rf'(?P<{t[1:]}>[^|]*)' if t[0] == '?' else
                rf'(?P<{t[1:]}>.*)' if t[0] == '*' else
                re.escape(t)
                for t in cmd.split('|')
            ]) + '$'

        # Determine value of new variable column from arguments.
        if new is False:
            new = None
        elif new is True:
            if cmd is None:
                new = None
            else:
                new = '|'.join([
                    t for t in cmd.split('|')
                    if t[0] not in ('?', '*')
                ])

        # Create dataframe to be returned by applying regex to variable
        # column and dropping unmatched rows.
        matched = self._df[target].str.extract(regex)

        # Drop unmatched rows if requested.
        is_unmatched = matched.isna().any(axis=1)
        matched = matched.drop(index=matched.loc[is_unmatched].index)

        # Assign new variable column and drop if all are nan.
        if target not in matched:
            cond = matched.notnull().any(axis=1)
            matched[target] = self._df[target]
            matched.loc[cond, target] = new or np.nan
            if new is None:
                warnings.warn('New target column could not be set '
                              'automatically.')

        # Drop variable column if all nan.
        if matched[target].isnull().all():
            matched.drop(columns=target, inplace=True)

        # Combine with original dataframe.
        if keep_unmatched:
            df_combine = self._df.assign(**{
                target: lambda df: df[target].where(is_unmatched)
            })
        else:
            df_combine = self._df.loc[matched.index].drop(columns=target)
        ret = matched.combine_first(df_combine)

        # Sort columns.
        order = matched.columns.tolist() + self._df.columns.tolist()
        ret.sort_index(
            key=lambda cols: [order.index(c) for c in cols],
            axis=1,
            inplace=True,
        )

        # Return dataframe.
        return ret

    def varcombine(self,
                   cmd: str | Callable,
                   keep_cols: bool = False,
                   target: str = 'variable') -> pd.DataFrame:
        """
        Combine columns into new variable (or other column).

        Parameters
        ----------
        cmd : str | Callable
            How the new variable (or other column) should be assembled.
        keep_cols : bool
            Whether to keep the used columns.
        target : str
            (Optional) The name of the target column. By default, this
            will be called `variable`.

        Returns
        -------
            pd.DataFrame
                The updated dataframe.
        """
        ret = self._df.assign(**{
            target: self._df.apply(lambda row:
                cmd.format(**row) if isinstance(cmd, str) else cmd(row),
            axis=1),
        })
        return ret if keep_cols else ret.filter([
            col for col in ret
            if col == target or
               (isinstance(cmd, Callable) or f"{{{col}}}" not in cmd)
        ])

    def unit_convert(self,
                     to: str | pint.Unit | dict[str, str | pint.Unit],

                     flow_id: Optional[str] = None):
        """
        Convert units in dataframe.

        Parameters
        ----------
        to : str | pint.Unit | dict[str, str | pint.Unit]
            The unit to convert to. This is either one unit for all rows
            or a dict that maps variables to units.
        flow_id : str
            (Optional) The flow ID for converting flow units.

        Returns
        -------
            pd.DataFrame
                The dataframe with updated units.
        """

        return self._df.assign(
            unit_to=to if not isinstance(to, dict) else self._df.apply(
                lambda row: (
                    to[row['variable']]
                    if row['variable'] in to else
                    row['unit']
                ), axis=1,
            ),
            value=lambda df: df.apply(
                lambda row: row['value'] * unit_convert(
                    row['unit'], row['unit_to'], flow_id=flow_id),
                    axis=1,
            ),
        ) \
            .drop(columns='unit') \
            .rename(columns={'unit_to': 'unit'})


# new variable can be calculated through expression assignments or
# keyword assignments expression assignments are of form
# "`a` = `b` + `c`" and are based on the pandas eval functionality
# keyword assignment must be int, float, string, or a function to
# be called to assign to the variable defined as key
ExprAssignment: TypeAlias = str
KeywordAssignment: TypeAlias = int | float | str | Callable


# Generic manipulation for calculating variables.
class CalcVariable(AbstractManipulation):
    _expr_assignments: tuple[ExprAssignment]
    _kw_assignments: dict[str, KeywordAssignment]

    def __init__(self,
                 *expr_assignments: ExprAssignment,
                 **kw_assignments: KeywordAssignment):
        self._expr_assignments = expr_assignments
        self._kw_assignments = kw_assignments

        # check all supplied arguments are valid
        for expr_assignment in self._expr_assignments:
            if not isinstance(expr_assignment, str):
                raise Exception(f"Expression assignments must be of type str, "
                                f"but found: {type(expr_assignment)}")
        for kw_assignment in self._kw_assignments.values():
            if not (isinstance(kw_assignment, int | float | str) or
                    callable(kw_assignment)):
                raise Exception(f"Keyword assignments must be of type int, "
                                f"float, string, or callable, but found: "
                                f"{type(kw_assignment)}")

    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        for expr_assignment in self._expr_assignments:
            df.eval(expr_assignment, inplace=True, engine='python')
        df = df.assign(**self._kw_assignments)
        return df


# building process chains
class ProcessChain(AbstractManipulation):
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
            raise Exception('Either the process_diagram or the process_tree '
                            'argument must be provided.')
        if process_diagram is not None and process_tree is not None:
            raise Exception('The process_diagram and process_tree arguments '
                            'cannot both be provided.')

        self._name = name
        self._demand = demand
        self._sc_demand = sc_demand
        self._proc_graph = (
            self._read_diagram(process_diagram)
            if process_diagram is not None else
            process_tree
        )
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
            raise ImportError("Need to install the `igraph` package first. "
                              "Please run `pip install igraph` or `poetry add "
                              "igraph`.")

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
        graph.es['name'] = [
            flow
            for p1 in procs
            for flow in self._proc_graph[p1]
        ]

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
                processes.append((components[0].strip(' '),
                                  components[1].strip(' '),))
            else:
                raise Exception(f"Too many consecutive `->` in diagram.")

        for i in range(len(processes)):
            proc, flow = processes[i]
            proc2 = processes[i + 1][0] if i + 1 < len(processes) else None
            if flow is None and i + 1 < len(processes):
                raise Exception(f"Flow must be provided for processes feeding "
                                f"into downstream processes: {subdiagram}")
            yield proc, flow, proc2

    # read the full diagram
    @staticmethod
    def _read_diagram(diagram: str) -> dict[str, dict[str, list[str]]]:
        out = {}
        for diagram in diagram.split(';'):
            for proc, flow, proc2 in ProcessChain._reduce_subdiagram(diagram):
                if flow is None:
                    continue
                if proc in out:
                    if flow in out[proc]:
                        if proc2 is not None:
                            out[proc][flow].append(proc2)
                    else:
                        out[proc] |= {
                            flow: ([proc2] if proc2 is not None else [])
                        }
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
                - row[f"Tech|{proc2}|Input|{flow}"] \
                    .to(row[f"Tech|{proc1}|Output|{flow}"].u).m
                if proc2 in proc1_flow_targets else
                0.0
                for proc2 in self._proc_graph
            ]
            for proc1 in self._proc_graph
            for flow, proc1_flow_targets in self._proc_graph[proc1].items()
        ])

        # obtain demand
        d = np.array([
            self._demand[proc1][flow]
                .to(row[f"Tech|{proc1}|Output|{flow}"].u).m
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
                    self._sc_demand[proc1][flow].to(
                        row[f"Tech|{proc1}|Output|{flow}"].u).m
                    for proc1 in self._sc_demand
                    for flow in self._sc_demand[proc1]
                ]
            ])

        # calculate functional units from technosphere matrix and demand
        func_units = solve(tsm, d)

        return pd.Series({
            f"Process Chain|{self._name}|Functional Unit|{proc}": func_units[i] * U('')
            for i, proc in enumerate(list(self._proc_graph.keys()))
        } | ({
            f"Process Chain|{self._name}|Demand|{proc}|{flow}": self._demand[proc][flow]
            for proc in self._demand
            for flow in self._demand[proc]
        } if self._demand is not None else {}) | ({
            f"Process Chain|{self._name}|SC Demand|{proc}|{flow}": self._sc_demand[proc][flow]
            for proc in self._sc_demand
            for flow in self._sc_demand[proc]
        } if self._sc_demand is not None else {}))


# calculate levelised cost of X
class LCOX(AbstractManipulation):
    """
    Calculate levelised cost of X (LCOX).
    """
    _name: str
    _reference: str
    _process: str
    _interest_rate: Optional[float]
    _book_lifetime: Optional[float]

    def __init__(self,
                 reference: str,
                 process: Optional[str] = None,
                 process_chain: Optional[str] = None,
                 name: Optional[str] = None,
                 interest_rate: Optional[float] = None,
                 book_lifetime: Optional[float] = None):
        if process is None and process_chain is None:
            raise Exception('Either process or vc must be provided as an '
                            'argument.')
        elif process is not None and process_chain is not None:
            raise Exception('Only one of process and vc must be provided as an '
                            'argument.')

        self._reference = reference
        self._process = process
        self._process_chain = process_chain
        self._name = name if name is not None else process if process is not None else process_chain
        self._interest_rate = (
            interest_rate * U('')
            if isinstance(interest_rate, int | float) else
            interest_rate
        )
        self._book_lifetime = (
            book_lifetime * U('a')
            if isinstance(book_lifetime, int | float) else
            book_lifetime
        )

    # perform
    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._process is not None:
            # calculate levelised cost of process, prepend "LCOX|{name}|" before variable names, and divide by reference
            ret = self.calc_cost(df, self._process) \
                .rename(columns=lambda col_name: f"LCOX|{self._name}|{col_name}") \
                .apply(lambda col: col / df[f"Tech|{self._process}|{self._reference}"])
            return pd.concat([df, ret], axis=1)
        else:
            # get functional units
            func_units = self._varsplit(df, f"Process Chain|"
                                            f"{self._process_chain}|"
                                            f"Functional Unit|?process"
            )
            if func_units.empty:
                raise Exception(f"Process chain '{self._process_chain}' could "
                                f"not be found. Make sure you performed the "
                                f"process chain manipulation on the dataframe "
                                f"first to determine the functional units and "
                                f"make sure the spelling of the process chain "
                                f"is correct.")
            # loop over processes in process chain
            ret_list = []
            for process in func_units.columns:
                # calculate levelised cost of process, prepend
                # "LCOX|{name}|{process}|" before variable names, divide
                # by reference, and multiply by functional unit
                ret = self.calc_cost(df, process) \
                    .rename(columns=lambda var: f"LCOX|{self._name}|"
                                                f"{process}|{var}") \
                    .apply(lambda col: col / df[f"Tech|{self._reference}"] * func_units[process])
                ret_list.append(ret)
            return pd.concat([df] + ret_list, axis=1)

    # calc levelised cost
    def calc_cost(self, df: pd.DataFrame, process: str) -> pd.DataFrame:
        tech = self._varsplit(df, f"Tech|{process}|?variable")
        prices = self._varsplit(df, 'Price|?io')
        iocaps = self._varsplit(df, regex=fr"Tech\|{re.escape(process)}\|"
                                          fr"((?:Input|Output) Capacity\|.*)",
        )
        ios = self._varsplit(df, regex=fr"Tech\|{re.escape(process)}\|"
                                       fr"((?:Input|Output)\|.*)",
        )

        # determine reference capacity and reference of that reference capacity for CAPEX and OPEX Fixed
        if any(c in tech for c in ('CAPEX', 'OPEX Fixed')):
            try:
                cap = iocaps.iloc[:, 0]
                c = re.sub(r'(Input|Output) Capacity', r'\1', cap.name)
                capref = ios[c]
            except IndexError:
                warnings.warn('Could not find a reference capacity for CAPEX '
                              'and OPEX columns.')
                cap = capref = None
            except KeyError:
                warnings.warn('Could not find reference matching the reference '
                              'capacity.')
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
        unused = []
        for io in ios:
            if io == self._reference:
                continue
            io_type, io_flow = io.split('|', 2)
            if io_flow not in prices:
                unused.append(io)
                continue
            # inputs are counted as costs, outputs are counted as revenues
            sign = +1 if io_type == 'Input' else -1
            c = (f"{io_type} {'Cost' if io_type == 'Input' else 'Revenue'}|"
                 f"{io_flow}")
            ret[c] = sign * ios[io] * prices[io_flow]

        # warn about unused variables
        if unused:
            warnings.warn(f"The following inputs/outputs are not used in "
                          f"LCOX, because they are neither the reference "
                          f"nor is an associated price given: "
                          f"{', '.join(unused)}")

        return ret


class FSCP(AbstractManipulation):
    """
    Calculate fuel-switching carbon price (FSCP).
    """
    _fuels: tuple[str]

    def __init__(self, *fuels: str):
        self._fuels = fuels

    def perform(self, df: pd.DataFrame) -> pd.DataFrame:
        for id_x, fuel_x in enumerate(self._fuels):
            for id_y, fuel_y in enumerate(self._fuels):
                if id_x < id_y:
                    df[f"FSCP|{fuel_x} to {fuel_y}"] = (
                        (df[f"Cost|{fuel_y}"] - df[f"Cost|{fuel_x}"])
                      / (df[f"GHGI|{fuel_x}"] - df[f"GHGI|{fuel_y}"])
                    )

        return df
