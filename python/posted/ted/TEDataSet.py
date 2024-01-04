import copy
import re
import warnings
from pathlib import Path
from typing import Optional, Literal

import numpy as np
import pandas as pd
from sigfig import round

from posted.config import default_period
from posted.path import databases
from posted.ted.Mask import Mask
from posted.ted.TEBase import TEBase, read_fields, read_masks
from posted.ted.TEDataFile import TEDataFile
from posted.ted.failures import TEMappingFailure
from posted.units.units import unit_convert, ureg


# get list of TEDs potentially containing variable
def collect_files(parent_variable: str, include_databases: Optional[list[str]] = None):
    if not parent_variable:
        raise Exception('Variable may not me empty.')

    # check that the requested database to include can be found
    if include_databases is not None:
        for database_id in include_databases:
            if not (database_id in databases and databases[database_id].exists()):
                raise Exception(f"Could not find database '{database_id}'.")

    ret = []
    for database_id, database_path in databases.items():
        # skip ted paths not requested to include
        if include_databases is not None and database_id not in include_databases: continue

        # find top-level file and directory
        top_path = '/'.join(parent_variable.split('|'))
        top_file = database_path / 'teds' / (top_path + '.csv')
        top_directory = database_path / 'teds' / top_path

        # add top-level file if it exists
        if top_file.exists() and top_file.is_file():
            ret.append((parent_variable, database_id))

        # add all files contained in top-level directory
        if top_directory.exists() and top_directory.is_dir():
            for sub_file in top_directory.rglob('*.csv'):
                sub_variable = parent_variable + '|' + sub_file.relative_to(top_directory).name.rstrip('.csv')
                ret.append((sub_variable, database_id))

        # loop over levels
        levels = parent_variable.split('|')
        for l in range(0, len(levels)):
            # find top-level file and directory
            top_path = '/'.join(levels[:l])
            parent_file = database_path / 'teds' / (top_path + '.csv')

            # add parent file if it exists
            if parent_file.exists() and parent_file.is_file():
                parent_variable = '|'.join(levels[:l])
                ret.append((parent_variable, database_id))

    return ret


# normalise units
def normalise_units(df: pd.DataFrame, level: Literal['reported', 'reference'], var_units: dict[str, str],
                    var_flow_ids: dict[str, str]):
    level_variable = f"{level}_variable"
    df_tmp = pd.concat([
        df,
        df.apply(
            lambda row: var_units[f"{row['parent_variable']}|{row[level_variable]}"]
            if isinstance(row[level_variable], str) else np.nan,
            axis=1,
        )
        .to_frame('target_unit'),
        df.apply(
            lambda row: var_flow_ids[f"{row['parent_variable']}|{row[level_variable]}"]
            if isinstance(row[level_variable], str) else np.nan,
            axis=1,
        )
        .to_frame('target_flow_id'),
    ], axis=1)

    df_tmp[f"{level}_value"] *= df_tmp.apply(
        lambda row: unit_convert(row[f"{level}_unit"], row['target_unit'], row['target_flow_id'])
        if not np.isnan(row[f"{level}_value"]) else 1.0,
        axis=1,
    )
    df_tmp[f"{level}_unit"] = df_tmp['target_unit']

    return df_tmp.drop(columns=['target_unit', 'target_flow_id'])


# normalise values
def normalise_values(df: pd.DataFrame):
    reported_value_new = df.apply(
        lambda row:
            row['reported_value'] / row['reference_value']
            if not pd.isnull(row['reference_value']) else
            row['reported_value'],
        axis=1,
    )
    reference_value_new = df.apply(
        lambda row:
            1.0
            if not pd.isnull(row['reference_value']) else
            np.nan,
        axis=1,
    )

    return df.assign(reported_value=reported_value_new, reference_value=reference_value_new)


class TEDataSet(TEBase):
    _df: None | pd.DataFrame

    # initialise
    def __init__(self,
                 parent_variable: str,
                 include_databases: Optional[list[str] | tuple[str]] = None,
                 file_paths: Optional[list[Path]] = None,
                 check_inconsistencies: bool = False,
                 data: Optional[pd.DataFrame] = None,
                 normalise: bool = False,
                 ):
        TEBase.__init__(self, parent_variable)

        self._fields: dict = {}
        self._masks: list = []

        if data is not None:
            self._df = data
        else:
            # initialise object fields
            self._df = None

            # read TEDataFiles and combine into dataset
            include_databases = list(include_databases) if include_databases is not None else list(databases.keys())
            self._df = self._load_files(include_databases, file_paths or [], check_inconsistencies)

            # normalise units and reference value unless told to skip
            if normalise:
                self.normalise()


    # load TEDatFiles and compile into dataset
    def _load_files(self, include_databases: list[str], file_paths: list[Path], check_inconsistencies: bool):
        files: list[TEDataFile] = []

        # collect TEDataFiles and append to list
        collected_files = collect_files(parent_variable=self._parent_variable, include_databases=include_databases)
        for file_variable, file_database_id in collected_files:
            files.append(TEDataFile(parent_variable=file_variable, database_id=file_database_id))
        for file_path in file_paths:
            files.append(TEDataFile(parent_variable=self._parent_variable, file_path=file_path))

        # raise exception if no TEDataFiles can be loaded
        if not files:
            raise Exception(f"No TEDataFiles to load for variable '{self._parent_variable}'.")

        # get fields and masks from files
        files_vars: set[str] = {f.parent_variable for f in files}
        for v in files_vars:
            if v in self._fields:
                raise Exception(f"Cannot load TEDataFiles with equally named fields: '{v}'")
            self._fields |= read_fields(v)
            self._masks += read_masks(v)

        # load all TEDataFiles: load from file, check for inconsistencies (if requested), expand cases and variables
        file_dfs: list[pd.DataFrame] = []
        for f in files:
            # load
            f.load()

            # check for inconsistencies
            if check_inconsistencies:
                f.check()

            # obtain dataframe and insert column parent_variable
            df_tmp = f.data.copy()
            df_tmp.insert(0, 'parent_variable', f.parent_variable)

            # append to dataframe list
            file_dfs.append(df_tmp)

        # compile dataset from the dataframes loaded from the individual files
        data = pd.concat(file_dfs)

        # query relevant variables
        data = data.query(f"parent_variable=='{self._parent_variable}'")

        # return
        return data

    # normalise reference values, reference units, and reported units
    def _normalise(self, override: Optional[dict[str, str]], split_off_units: bool):
        if override is None:
            override = {}

        # get overridden var specs
        var_flow_ids = {
            var_name: var_specs['flow_id'] if 'flow_id' in var_specs else np.nan
            for var_name, var_specs in self._var_specs.items()
        }
        var_units = {
            var_name: var_specs['default_unit']
            for var_name, var_specs in self._var_specs.items()
        } | override

        # normalise reference units, normalise reference values, and normalise reported units
        df_tmp = self._df \
            .pipe(normalise_units, level='reference', var_units=var_units, var_flow_ids=var_flow_ids) \
            .pipe(normalise_values) \
            .pipe(normalise_units, level='reported', var_units=var_units, var_flow_ids=var_flow_ids)

        # split off units if requested
        if split_off_units:
            return df_tmp.drop(columns=['reported_unit', 'reference_unit']), var_units
        else:
            return df_tmp

    def normalise(self, override: Optional[dict[str, str]] = None, inplace: bool = False):
        df_tmp = self._normalise(override, split_off_units=False)

        if inplace:
            self._df = df_tmp
            return
        else:
            new_self = copy.copy(self)
            new_self.set_data(df_tmp)
            return new_self

    # access dataframe
    @property
    def data(self):
        return self._df

    def set_data(self, df: pd.DataFrame):
        self._df = df

    # query data
    def query(self, *args, **kwargs):
        return TEDataSet(
            parent_variable=self._parent_variable,
            data=self._df.query(*args, **kwargs),
        )

    def prepare(self,
                override: Optional[dict[str, str]] = None,
                **kwargs):
        selection, var_units_final = self._prepare(override, **kwargs)
        selection.insert(selection.columns.tolist().index('value'), 'unit', np.nan)
        selection['unit'] = selection['variable'].map(var_units_final)
        return selection

    # prepare data for selection
    def _prepare(self,
                 override: Optional[dict[str, str]],
                 **kwargs):

        # normalise before selection; the resulting dataframe is the starting point
        selection, var_units = self._normalise(override, split_off_units=True)

        # drop reference value field
        selection.drop(columns=['reference_value'], inplace=True)
        selection.rename(columns={'reported_value': 'value'}, inplace=True)

        # add parent variable
        selection['reported_variable'] = selection['parent_variable'] + '|' + selection['reported_variable']
        selection['reference_variable'] = selection['parent_variable'] + '|' + selection['reference_variable']
        selection.drop(columns=['parent_variable'], inplace=True)

        # drop columns that are not used (at the moment)
        selection.drop(
            columns=['region', 'reported_unc', 'comment', 'source_detail'] +
                    [c for c in self._fields if self._fields[c]['type'] == 'comment'],
            inplace=True,
        )

        # expand source field
        all_sources = [v for v in selection['source'].unique() if v != '*']
        selection = pd.concat([
            selection[selection['source'] != '*'],
            selection[selection['source'] == '*']
            .drop(columns=['source'])
            .merge(pd.DataFrame.from_dict({'source': all_sources}), how='cross'),
        ])

        # expand all case fields
        expand_cols = {}
        for idx_name, col_specs in self._fields.items():
            if col_specs['type'] != 'cases':
                continue
            if (idx_name not in kwargs or kwargs[idx_name] is None):
                if col_specs['coded']:
                    expand_cols[idx_name] = list(col_specs['codes'].keys())
                else:
                    expand_cols[idx_name] = [v for v in selection[idx_name].unique() if v != '*']
            elif idx_name in kwargs and kwargs[idx_name] is not None and isinstance(kwargs[idx_name], str):
                expand_cols[idx_name] = [kwargs[idx_name]]
            elif idx_name in kwargs and kwargs[idx_name] is not None and isinstance(kwargs[idx_name], list):
                expand_cols[idx_name] = kwargs[idx_name]
        selection = self._expand_fields(selection, expand_cols)

        # insert missing periods
        selection = self._insert_missing_periods(selection)

        # select/interpolate periods
        if 'period' not in kwargs or kwargs['period'] is None:
            period = default_period
        else:
            period = kwargs['period']
        if isinstance(period, int) | isinstance(period, float):
            period = [period]
        selection = self._select_periods(selection, period)

        # apply mappings
        selection = self._apply_mappings(selection, var_units)

        # add unit column, drop reference variable, reorder columns, sort rows
        def combine_units(numerator: str, denominator: str):
            ret = ureg(f"{numerator}/({denominator})").u
            if not ret.dimensionless:
                return str(ret)
            else:
                return (f"{numerator}/({denominator})"
                        if '/' in denominator else
                        f"{numerator}/{denominator}")
        selection_units = selection.apply(
            lambda row: {
                'variable': row['reported_variable'],
                'unit': combine_units(
                    var_units[row['reported_variable']].split(';')[0],
                    var_units[row['reference_variable']].split(';')[0]
                ) if isinstance(row['reference_variable'], str) else
                var_units[row['reported_variable']].split(';')[0],
            },
            axis=1,
            result_type='expand',
        ).set_index('variable').drop_duplicates()['unit']
        if not selection_units.index.is_unique:
            raise Exception('Multiple combined units per reported variable found.')
        var_units_final = selection_units.to_dict()
        selection.drop(columns=['reference_variable'], inplace=True)
        selection.rename(columns={'reported_variable': 'variable'}, inplace=True)
        cols_sorted = [
            c for c in (list(self._fields.keys()) + ['source', 'variable', 'period', 'unit', 'value'])
            if c in selection.columns
        ]
        selection = selection[cols_sorted]
        selection = selection \
            .sort_values(by=[c for c in cols_sorted if c not in ('unit', 'value')]) \
            .reset_index(drop=True)

        return selection, var_units_final

    # select data
    def select(self,
               agg: Optional[list[str]] = None,
               masks: Optional[list[Mask]] = None,
               masks_database: bool = True,
               override: Optional[dict[str, str]] = None,
               **kwargs):
        # prepare selection
        selection, var_units_final = self._prepare(override, split_off_units=True, **kwargs)

        # compile all masks into list
        masks = masks if masks is not None else []
        if masks_database:
            masks += [Mask(**mask_dict) for mask_dict in self._masks]

        # aggregation
        selection = self._aggregate(selection, agg, masks)

        # round values
        selection = selection.apply(lambda col: col.apply(
            lambda cell: cell if not isinstance(cell, float) or np.isnan(cell) else round(cell, sigfigs=4, warn=False)
        ))

        # add units
        selection.insert(selection.columns.tolist().index('value'), 'unit', np.nan)
        selection['unit'] = selection['variable'].map(var_units_final)

        # return dataframe
        return selection

    # insert missing periods
    def _insert_missing_periods(self, selection: pd.DataFrame) -> pd.DataFrame:
        # TODO: insert year of publication instead of current year
        selection = selection.fillna({'period': 2023})

        # return
        return selection

    def _aggregate(self, selection: pd.DataFrame, agg: list, masks: list[Mask]) -> pd.DataFrame:
        # aggregate
        if agg is None:
            agg = [
                field_name
                for field_name, field_specs in self._fields.items()
                if field_specs['type'] == 'components'
            ] + ['source']

        # aggregate over component fields
        group_cols = [
            c for c in selection.columns
            if c != 'value' and (c not in agg or c not in self._fields or self._fields[c]['type'] != 'components')
        ]
        selection = selection \
            .groupby(group_cols, dropna=False) \
            .agg({'value': 'sum'}) \
            .reset_index()

        # aggregate over cases fields
        group_cols = [
            c for c in selection.columns
            if c != 'value' and c not in agg
        ]
        ret = []
        for keys, rows in selection.groupby(group_cols, dropna=False):
            # set default weights to 1.0
            rows = rows.assign(weight=1.0)

            # update weights by applying masks
            for mask in masks:
                if mask.matches(rows):
                    rows['weight'] *= mask.get_weights(rows)

            # drop all rows with weights equal to nan
            rows.dropna(subset='weight', inplace=True)

            if not rows.empty:
                # aggregate with weights
                out = rows \
                    .groupby(group_cols, dropna=False) \
                    .apply(lambda cols: pd.Series({
                        'value': np.average(cols['value'], weights=cols['weight']),
                    }))

                # add to return list
                ret.append(out)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index()

    # apply mappings between entry types
    def _apply_mappings(self, selection: pd.DataFrame, var_units: dict) -> pd.DataFrame:
        # list of columns to group by
        group_cols = [c for c in self._fields if self._fields[c]['type'] != 'comment'] + \
                     ['period', 'source']

        # perform groupby and do not drop NA values
        grouped = selection.groupby(group_cols, dropna=False)

        # create return list
        ret = []

        # loop over groups
        for keys, ids in grouped.groups.items():
            # get rows in group
            rows = selection.loc[ids, [c for c in selection if c not in group_cols]].copy()

            # 1. convert FLH to OCF
            cond = rows['reported_variable'].str.endswith('|FLH')
            if cond.any():
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: unit_convert(var_units[row['reported_variable']], 'a'),
                    axis=1,
                )
                rows.loc[cond, 'reported_variable'] = rows.loc[cond, 'reported_variable'] \
                    .str.replace('|FLH', '|OCF', regex=False)

            # 2. convert FOPEX Relative to FOPEX
            cond = rows['reported_variable'].str.endswith('|FOPEX Relative')
            if cond.any():
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: unit_convert(
                        var_units[row['reported_variable'].replace('|FOPEX Relative', '|CAPEX')] + '/a',
                        var_units[row['reported_variable'].replace('|FOPEX Relative', '|FOPEX')]
                    ) * (rows.query(
                        f"reported_variable=='{row['reported_variable'].replace('|FOPEX Relative', '|CAPEX')}'"
                    ).pipe(
                        lambda df: df['value'].iloc[0] if not df.empty else np.nan,
                    )),
                    axis=1,
                )
                rows.loc[cond, 'reported_variable'] = rows.loc[cond, 'reported_variable'] \
                    .str.replace('|FOPEX Relative', '|FOPEX')
                rows.loc[cond, 'reference_variable'] = rows.loc[cond].apply(
                    lambda row: rows.query(
                        f"reported_variable=='{row['reported_variable'].replace('|FOPEX', '|CAPEX')}'"
                    ).pipe(
                        lambda df: df['reference_variable'].iloc[0] if not df.empty else np.nan,
                    ),
                    axis=1,
                )
                if (cond & rows['value'].isnull()).any():
                    warnings.warn(TEMappingFailure(
                        selection.loc[ids].loc[cond & rows['value'].isnull()],
                        'No CAPEX value matching a FOPEX Relative value found.',
                    ))

            # 3. convert FOPEX Specific to FOPEX
            cond = rows['reported_variable'].str.endswith('|FOPEX Specific')
            if cond.any():
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: unit_convert(
                        var_units[row['reported_variable']] + '/a',
                        var_units[row['reported_variable'].replace('|FOPEX Specific', '|FOPEX')]
                    ) / unit_convert(
                        var_units[row['reference_variable']] + '/a',
                        var_units[re.sub(r'(Input|Output)', r'\1 Capacity', row['reference_variable'])],
                        self._var_specs[row['reference_variable']]['flow_id'],
                    ) * (rows.query(
                        f"reported_variable=='{row['reported_variable'].replace('|FOPEX Specific', '|OCF')}'"
                    ).pipe(
                        lambda df: df['value'].iloc[0] if not df.empty else np.nan,
                    )),
                    axis=1,
                )
                rows.loc[cond, 'reported_variable'] = rows.loc[cond, 'reported_variable'] \
                    .str.replace('|FOPEX Specific', '|FOPEX')
                rows.loc[cond, 'reference_variable'] = rows.loc[cond, 'reference_variable'].apply(
                    lambda cell: re.sub(r'(Input|Output)', r'\1 Capacity', cell),
                )
                if (cond & rows['value'].isnull()).any():
                    warnings.warn(TEMappingFailure(
                        selection.loc[ids].loc[cond & rows['value'].isnull()],
                        'No OCF value matching a FOPEX Specific value found.',
                    ))

            # 4. convert efficiencies (Output over Input) to demands (Input over Output)
            cond = (rows['reported_variable'].str.contains(r'\|Output(?: Capacity)?\|') &
                    rows['reference_variable'].str.contains(r'\|Input(?: Capacity)?\|'))
            if cond.any():
                rows.loc[cond, 'value'] = 1.0 / rows.loc[cond, 'value']
                rows.loc[cond, 'reported_variable_new'] = rows.loc[cond, 'reference_variable']
                rows.loc[cond, 'reference_variable'] = rows.loc[cond, 'reported_variable']
                rows.loc[cond, 'reported_variable'] = rows.loc[cond, 'reported_variable_new']
                rows.drop(columns=['reported_variable_new'], inplace=True)

            # 5. convert all references to primary output
            cond = ((rows['reference_variable'].str.contains(r'\|Output(?: Capacity)?\|') |
                    rows['reference_variable'].str.contains(r'\|Input(?: Capacity)?\|')) &
                    rows['reported_variable'].map(lambda var: 'default_reference' in self._var_specs[var]) &
                    (rows['reported_variable'].map(
                        lambda var: self._var_specs[var]['default_reference']
                        if 'default_reference' in self._var_specs[var] else np.nan
                    ) != rows['reference_variable']))
            if cond.any():
                regex_find = r'\|(Input|Output)(?: Capacity)?\|'
                regex_repl = r'|\1|'
                rows.loc[cond, 'reference_variable_new'] = rows.loc[cond, 'reported_variable'].map(
                    lambda var: self._var_specs[var]['default_reference'],
                )
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: rows.query(
                        f"reported_variable=='{re.sub(regex_find, regex_repl, row['reference_variable'])}' & "
                        f"reference_variable=='{re.sub(regex_find, regex_repl, row['reference_variable_new'])}'"
                    ).pipe(
                        lambda df: df['value'].iloc[0] if not df.empty else np.nan,
                    ),
                    axis=1,
                )
                rows.loc[cond, 'reference_variable'] = rows.loc[cond, 'reference_variable_new']
                rows.drop(columns=['reference_variable_new'], inplace=True)
                if (cond & rows['value'].isnull()).any():
                    warnings.warn(TEMappingFailure(
                        selection.loc[ids].loc[cond & rows['value'].isnull()],
                        'No appropriate mapping found to convert row reference to primary output.',
                    ))

            # set missing columns from group
            rows[group_cols] = keys

            # add to return list
            ret.append(rows)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True)

    # expand based on subtechs, modes, and period
    def _expand_fields(self, selection: pd.DataFrame, expand_cols: dict) -> pd.DataFrame:
        # loop over affected columns
        for field_id, field_vals in expand_cols.items():
            if '*' in field_vals:
                raise Exception(f"Asterisk may not be among expand values for column '{field_id}': {field_vals}")
            if self._fields[field_id]['type'] == 'cases':
                selection = pd.concat([
                        selection[selection[field_id].isin(field_vals)],
                        selection[selection[field_id] == '*']
                        .drop(columns=[field_id])
                        .merge(pd.DataFrame.from_dict({field_id: field_vals}), how='cross'),
                    ])
            elif self._fields[field_id]['type'] == 'components':
                selection = selection.query(f"{field_id}.isin({field_vals})")

        # return
        return selection.reset_index(drop=True)

    # group by identifying columns and select periods/generate time series
    def _select_periods(self, selection: pd.DataFrame, period: float | list | np.ndarray) -> pd.DataFrame:
        # expands asterisk values
        selection = pd.concat([
                selection[selection['period'] != '*'],
                selection[selection['period'] == '*']
                .drop(columns=['period'])
                .merge(pd.DataFrame.from_dict({'period': period}), how='cross'),
            ]).astype({'period': 'float'})

        # get list of groupable columns
        group_cols = [c for c in self._fields if self._fields[c]['type'] != 'comment'] + \
                     ['reported_variable', 'reference_variable', 'source']

        # perform groupby and do not drop NA values
        grouped = selection.groupby(group_cols, dropna=False)

        # create return list
        ret = []

        # loop over groups
        for keys, rows in grouped:
            # get rows in group
            rows = rows[['period', 'value']]

            # get a list of periods that exist
            periods_exist = rows['period'].unique()

            # create dataframe containing rows for all requested periods
            req_rows = pd.DataFrame.from_dict({
                'period': period,
                'period_upper': [min([ip for ip in periods_exist if ip >= p], default=np.nan) for p in period],
                'period_lower': [max([ip for ip in periods_exist if ip <= p], default=np.nan) for p in period],
            })

            # set missing columns from group
            req_rows[group_cols] = keys

            # check case
            cond_match = req_rows['period'].isin(periods_exist)
            cond_extrapolate = (req_rows['period_upper'].isna() | req_rows['period_lower'].isna())

            # match
            rows_match = req_rows.loc[cond_match] \
                .merge(rows, on='period')

            # extrapolate
            rows_extrapolate = req_rows.loc[~cond_match & cond_extrapolate] \
                .assign(period_combined=lambda x: np.where(x.notna()['period_upper'], x['period_upper'], x['period_lower'])) \
                .merge(rows.rename(columns={'period': 'period_combined'}), on='period_combined')

            # interpolate
            rows_interpolate = req_rows.loc[~cond_match & ~cond_extrapolate] \
                .merge(rows.rename(columns={c: f"{c}_upper" for c in rows.columns}), on='period_upper') \
                .merge(rows.rename(columns={c: f"{c}_lower" for c in rows.columns}), on='period_lower') \
                .assign(value=lambda row: row['value_lower'] + (row['period_upper'] - row['period']) /
                       (row['period_upper'] - row['period_lower']) * (row['value_upper'] - row['value_lower']))

            # combine into one dataframe and drop unused columns
            rows_append = pd.concat([rows_match, rows_extrapolate, rows_interpolate]) \
                .drop(columns=['period_upper', 'period_lower', 'period_combined', 'value_upper', 'value_lower'])

            # add to return list
            ret.append(rows_append)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True)
