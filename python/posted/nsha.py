import re
import warnings
from pathlib import Path
from typing import Optional, Literal

import numpy as np
import pandas as pd
from sigfig import round

from posted.config import default_periods
from posted.fields import AbstractFieldDefinition, SourceFieldDefinition, PeriodFieldDefinition, CustomFieldDefinition
from posted.path import databases
from posted.masking import Mask
from posted.tedf import TEBase, read_fields, read_masks, TEDF
from posted.units import unit_convert, ureg


# get list of TEDFs potentially containing variable
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
        top_file = database_path / 'tedfs' / (top_path + '.csv')
        top_directory = database_path / 'tedfs' / top_path

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
            parent_file = database_path / 'tedfs' / (top_path + '.csv')

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


class HarmoniseMappingFailure(Warning):
    """Warning raised for rows in TEDataSets where mappings fail.

    Attributes:
        row_data -- the data of the row that causes the failure
        message -- explanation of the error
    """
    def __init__(self, row_data: pd.DataFrame, message: str = "Failure when selecting from dataset."):
        # save constructor arguments as public fields
        self.row_data: pd.DataFrame = row_data
        self.message: str = message

        # compose warning message
        warning_message: str = message + f"\n{row_data}"

        # call super constructor
        super().__init__(warning_message)


class NSHADataSet(TEBase):
    _df: None | pd.DataFrame
    _fields: list[AbstractFieldDefinition]
    _masks: list[Mask]

    # initialise
    def __init__(self,
                 parent_variable: str,
                 include_databases: Optional[list[str] | tuple[str]] = None,
                 file_paths: Optional[list[Path]] = None,
                 check_inconsistencies: bool = False,
                 data: Optional[pd.DataFrame] = None,
                 ):
        TEBase.__init__(self, parent_variable)

        # initialise fields
        self._df = None
        self._fields = []
        self._masks = []

        if data is not None:
            self._df = data
        else:
            # read TEDataFiles and combine into dataset
            include_databases = list(include_databases) if include_databases is not None else list(databases.keys())
            self._df = self._load_files(include_databases, file_paths or [], check_inconsistencies)

    # access dataframe
    @property
    def data(self):
        return self._df

    def set_data(self, df: pd.DataFrame):
        self._df = df

    # load TEDFs and compile into NSHADataSet
    def _load_files(self, include_databases: list[str], file_paths: list[Path], check_inconsistencies: bool):
        files: list[TEDF] = []

        # collect TEDF and append to list
        collected_files = collect_files(parent_variable=self._parent_variable, include_databases=include_databases)
        for file_variable, file_database_id in collected_files:
            files.append(TEDF(parent_variable=file_variable, database_id=file_database_id))
        for file_path in file_paths:
            files.append(TEDF(parent_variable=self._parent_variable, file_path=file_path))

        # raise exception if no TEDF can be loaded
        if not files:
            raise Exception(f"No TEDF to load for variable '{self._parent_variable}'.")

        # get fields and masks from files
        files_vars: set[str] = {f.parent_variable for f in files}
        for v in files_vars:
            self._fields += read_fields(v)
            self._masks += read_masks(v)
        self._fields += [SourceFieldDefinition(), PeriodFieldDefinition()]
        field_ids = [field.id for field in self._fields]
        if len(field_ids) > len(set(field_ids)):
            raise Exception(f"Cannot load TEDFs due to multiple fields defined with equal name: {field_ids}")

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
    def normalise(self, override: Optional[dict[str, str]] = None, inplace: bool = False) -> pd.DataFrame:
        normalised, _ = self._normalise(override)

        if inplace:
            self._df = normalised
            return
        else:
            return normalised

    def _normalise(self, override: Optional[dict[str, str]]) -> tuple[pd.DataFrame, dict[str, str]]:
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
        normalised = self._df \
            .pipe(normalise_units, level='reference', var_units=var_units, var_flow_ids=var_flow_ids) \
            .pipe(normalise_values) \
            .pipe(normalise_units, level='reported', var_units=var_units, var_flow_ids=var_flow_ids)

        # return dataframe and variable units
        return normalised, var_units

    # prepare data for selection
    def select(self,
               override: Optional[dict[str, str]] = None,
               drop_singular_fields: bool = True,
               **field_vals_select) -> pd.DataFrame:
        selected, var_units_final = self._select(override, drop_singular_fields, **field_vals_select)
        selected[['reported_unit', 'reference_unit']] = (selected[['reported_variable', 'reference_variable']]
                                                         .apply(lambda col: col.map(var_units_final)))

        return selected

    def _select(self,
                override: Optional[dict[str, str]],
                drop_singular_fields: bool,
                **field_vals_select) -> tuple[pd.DataFrame, dict[str, str]] :
        # normalise before selection; the resulting dataframe is the starting point
        selected, var_units = self._normalise(override)
        selected.drop(columns=['reported_unit', 'reference_value', 'reference_unit'], inplace=True)
        selected.rename(columns={'reported_value': 'value'}, inplace=True)

        # add parent variable
        selected['reported_variable'] = selected['parent_variable'] + '|' + selected['reported_variable']
        selected['reference_variable'] = selected['parent_variable'] + '|' + selected['reference_variable']
        selected.drop(columns=['parent_variable'], inplace=True)

        # drop columns that are not used (at the moment)
        selected.drop(
            columns=['region', 'reported_unc', 'comment', 'source_detail'] +
                    [field.id for field in self._fields if field.type == 'comment'],
            inplace=True,
        )

        # raise exception if fields listed in arguments that are unknown
        for field_id in field_vals_select:
            if not any(field_id == field.id for field in self._fields):
                raise Exception(f"Field '{field_id}' does not exist and cannot be used for selection.")
            if next(field for field in self._fields if field_id == field.id).type == 'comment':
                raise Exception(f"Cannot select by comment field: {field_id}")

        # select and expand fields
        for field in self._fields:
            if field.type == 'comment':
                continue
            if field.id not in field_vals_select or field_vals_select[field.id] is None:
                if field.is_coded:
                    field_vals = field.codes
                elif field.id == 'period':
                    field_vals = default_periods
                else:
                    field_vals = [v for v in selected[field.id].unique() if v != '*']
            else:
                field_vals = field_vals_select[field.id]
                # ensure that field values is a list of elements (not tuple, not single value)
                if isinstance(field_vals, tuple):
                    field_vals = list(field_vals)
                elif not isinstance(field_vals, list):
                    field_vals = [field_vals]
                # check that every element is a suitable value
                if any(not isinstance(v, field.allowed_types) for v in field_vals):
                    raise Exception(f"Selected value(s) for field '{field.id}' must be type: {field.allowed_types}")
                elif '*' in field_vals:
                    raise Exception(f"Selected value(s) for field '{field.id}' must not be the asterisk."
                                    f"Omit the '{field.id}' argument to select all.")
            selected = field.select_and_expand(selected, field_vals)

        # drop fields with only one value if specified in method argument
        if drop_singular_fields:
            selected.drop(columns=[
                field.id for field in self._fields
                if isinstance(field, CustomFieldDefinition) and
                   field.type != 'comment' and
                   selected[field.id].nunique() < 2
            ])

        return selected, var_units

    def harmonise(self,
                  override: Optional[dict[str, str]] = None,
                  drop_singular_fields: bool = True,
                  **field_vals_select) -> pd.DataFrame:
        harmonised, var_units_final = self._harmonise(override, drop_singular_fields, **field_vals_select)
        harmonised.insert(harmonised.columns.tolist().index('value'), 'unit', np.nan)
        harmonised['unit'] = harmonised['variable'].map(var_units_final)

        return harmonised

    def _harmonise(self,
                   override: Optional[dict[str, str]],
                   drop_singular_fields,
                   **field_vals_select) -> tuple[pd.DataFrame, dict[str, str]]:
        selected, var_units = self._select(override, drop_singular_fields, **field_vals_select)

        # apply mappings
        selected = self._apply_mappings(selected, var_units)

        # add unit column, drop reference variable, reorder columns, sort rows
        def combine_units(numerator: str, denominator: str):
            ret = ureg(f"{numerator}/({denominator})").u
            if not ret.dimensionless:
                return str(ret)
            else:
                return (f"{numerator}/({denominator})"
                        if '/' in denominator else
                        f"{numerator}/{denominator}")
        selection_units = selected.apply(
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
        selected.drop(columns=['reference_variable'], inplace=True)
        selected.rename(columns={'reported_variable': 'variable'}, inplace=True)
        custom_fields = [field.id for field in self._fields if isinstance(field, CustomFieldDefinition)]
        cols_sorted = [
            c for c in (custom_fields + ['source', 'variable', 'period', 'unit', 'value'])
            if c in selected.columns
        ]
        selected = selected[cols_sorted]
        selected = selected \
            .sort_values(by=[c for c in cols_sorted if c in selected and c not in ('unit', 'value')]) \
            .reset_index(drop=True)

        return selected, var_units_final

    # apply mappings between entry types
    def _apply_mappings(self, selection: pd.DataFrame, var_units: dict) -> pd.DataFrame:
        # list of columns to group by
        group_cols = [
            c for c in selection.columns
            if c not in ['reported_variable', 'reference_variable', 'value']
        ]

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
                    warnings.warn(HarmoniseMappingFailure(
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
                    warnings.warn(HarmoniseMappingFailure(
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
                    warnings.warn(HarmoniseMappingFailure(
                        selection.loc[ids].loc[cond & rows['value'].isnull()],
                        'No appropriate mapping found to convert row reference to primary output.',
                    ))

            # set missing columns from group
            rows[group_cols] = keys

            # add to return list
            ret.append(rows)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True)

    # select data
    def aggregate(self,
                  override: Optional[dict[str, str]] = None,
                  drop_singular_fields: bool = True,
                  agg: Optional[str | list[str] | tuple[str]] = None,
                  masks: Optional[list[Mask]] = None,
                  masks_database: bool = True,
                  **field_vals_select) -> pd.DataFrame:
        # get selection
        harmonised, var_units_final = self._harmonise(override, drop_singular_fields, **field_vals_select)

        # compile masks from databases and function argument into one list
        if masks is not None and any(not isinstance(m, Mask) for m in masks):
            raise Exception("Function argument 'masks' must contain a list of posted.masking.Mask objects.")
        masks = (self._masks if masks_database else []) + (masks or [])

        # aggregation
        component_fields = [
            field.id for field in self._fields
            if field.type == 'components'
        ]
        if agg is None:
            agg = component_fields + ['source']
        else:
            if isinstance(agg, tuple):
                agg = list(agg)
            elif not isinstance(agg, list):
                agg = [agg]
            for a in agg:
                if not isinstance(a, str):
                    raise Exception(f"Field ID in argument 'agg' must be a string but found: {a}")
                if not any(a == field.id for field in self._fields):
                    raise Exception(f"Field ID in argument 'agg' is not a valid field: {a}")

        # aggregate over component fields
        group_cols = [
            c for c in harmonised.columns
            if not (c == 'value' or (c in agg and c in component_fields))
        ]
        aggregated = harmonised \
            .groupby(group_cols, dropna=False) \
            .agg({'value': 'sum'}) \
            .reset_index()

        # aggregate over cases fields
        group_cols = [
            c for c in aggregated.columns
            if not (c == 'value' or c in agg)
        ]
        ret = []
        for keys, rows in aggregated.groupby(group_cols, dropna=False):
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

        # convert return list to dataframe and reset index
        aggregated = pd.concat(ret).reset_index()

        # round values
        aggregated['value'] = aggregated['value'].apply(
            lambda cell: cell if pd.isnull(cell) else round(cell, sigfigs=4, warn=False)
        )

        # add units
        aggregated.insert(aggregated.columns.tolist().index('value'), 'unit', np.nan)
        aggregated['unit'] = aggregated['variable'].map(var_units_final)

        # return dataframe
        return aggregated
