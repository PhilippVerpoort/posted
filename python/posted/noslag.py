import re
import warnings
from pathlib import Path
from typing import Optional, Literal

import numpy as np
import pandas as pd
from sigfig import round

from posted.config import variables
from posted.settings import default_periods
from posted.columns import AbstractFieldDefinition, CustomFieldDefinition, read_fields, AbstractColumnDefinition, base_columns
from posted.path import databases
from posted.masking import Mask, read_masks
from posted.tedf import TEBase, TEDF
from posted.units import unit_convert, ureg


# get list of TEDFs potentially containing variable
def collect_files(parent_variable: str, include_databases: Optional[list[str]] = None):
    '''Takes a parent variable and optional list of databases to include,
    checks for their existence, and collects files and directories based on the parent variable.

    Parameters
    ----------
    parent_variable : str
        Variable to collect files on
    include_databases : Optional[list[str]]
        List of Database IDs to collect files from

    Returns
    -------
        list[tuple]
            List of tuples containing the parent variable and the
        database ID for each file found in the specified directories.

    '''
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

def normalise_units(df: pd.DataFrame, level: Literal['reported', 'reference'], var_units: dict[str, str],
                       var_flow_ids: dict[str, str]):
    '''
    Takes a DataFrame with reported or reference data, along with
    dictionaries mapping variable units and flow IDs, and normalizes the units of the variables in the
    DataFrame based on the provided mappings.

    Parameters
    ----------
        df : pd.DataFrame
            Dataframe to be normalised
        level : Literal['reported', 'reference']
            Specifies whether the data should be normalised on the reported or reference values
        var_units : dict[str, str]
            Dictionary that maps a combination of parent variable and variable
            to its corresponding unit. The keys in the dictionary are in the format "{parent_variable}|{variable}",
            and the values are the units associated with that variable.
        var_flow_ids : dict[str, str]
            Dictionary that maps a combination of parent variable and variable to a
            specific flow ID. This flow ID is used for unit conversion in the `normalise_units` function.

    Returns
    -------
        pd.DataFrame
            Normalised dataframe

    '''

    prefix = '' if level == 'reported' else 'reference_'
    var_col_id = prefix + 'variable'
    value_col_id = prefix + 'value'
    unit_col_id = prefix + 'unit'
    df_tmp = pd.concat([
        df,
        df.apply(
            lambda row: var_units[f"{row['parent_variable']}|{row[var_col_id]}"]
            if isinstance(row[var_col_id], str) else np.nan,
            axis=1,
        )
        .to_frame('target_unit'),
        df.apply(
            lambda row: var_flow_ids[f"{row['parent_variable']}|{row[var_col_id]}"]
            if isinstance(row[var_col_id], str) else np.nan,
            axis=1,
        )
        .to_frame('target_flow_id'),
    ], axis=1)

    # Apply unit conversion
    conv_factor = df_tmp.apply(
        lambda row: unit_convert(row[unit_col_id], row['target_unit'], row['target_flow_id'])
        if not np.isnan(row[value_col_id]) else 1.0,
        axis=1,
    )

    # Update value column with conversion factor
    df_tmp[value_col_id] *= conv_factor

    # If level is 'reported', update uncertainty column with conversion factor
    if level == 'reported':
        df_tmp['uncertainty'] *= conv_factor

    # Uupdate unit columns
    df_tmp[unit_col_id] = df_tmp['target_unit']

    # Drop unneccessary columns and return
    return df_tmp.drop(columns=['target_unit', 'target_flow_id'])



def normalise_values(df: pd.DataFrame):
    '''Takes a DataFrame as input, normalizes the 'value' and 'uncertainty'
    columns by the reference value, and updates the 'reference_value' column accordingly.

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe to be normalised

    Returns
    -------
        pd.DataFrame
            Returns a modified DataFrame where the 'value' column has been
            divided by the 'reference_value' column (or 1.0 if 'reference_value' is null), the 'uncertainty'
            column has been divided by the 'reference_value' column, and the 'reference_value' column has been
            replaced with 1.0 if it was not null, otherwise

    '''
    # Calculate reference value
    reference_value =  df.apply(
        lambda row:
            row['reference_value']
            if not pd.isnull(row['reference_value']) else
            1.0,
        axis=1,
    )
    # Calculate new value, reference value and uncertainty
    value_new = df['value'] / reference_value
    uncertainty_new = df['uncertainty'] / reference_value
    reference_value_new = df.apply(
        lambda row:
            1.0
            if not pd.isnull(row['reference_value']) else
            np.nan,
        axis=1,
    )
    # Assign new values to dataframe and return
    return df.assign(value=value_new, uncertainty=uncertainty_new, reference_value=reference_value_new)


class HarmoniseMappingFailure(Warning):
    """Warning raised for rows in TEDataSets where mappings fail.

    Parameters
    ----------
        row_data: pd.DataFrame
            Contains the Data on the rows to map
        message: str, optional
            Contains the message of the failure

    Attributes
    ----------
        row_data
            the data of the row that causes the failure
        message
            explanation of the error
    """
    def __init__(self, row_data: pd.DataFrame, message: str = "Failure when selecting from dataset."):
        '''Save constructor arguments as public fields, compose warning message, call super constructor'''
        # save constructor arguments as public fields
        self.row_data: pd.DataFrame = row_data
        self.message: str = message

        # compose warning message
        warning_message: str = message + f"\n{row_data}"

        # call super constructor
        super().__init__(warning_message)



def combine_units(numerator: str, denominator: str):
    '''Combine fraction of two units into updated unit string

    Parameters
    ----------
        numerator: str
            numerator of the fraction
        denominator: str
            denominator of the fraction

    Returns
    -------
        str
            updated unit string after simplification
    '''


    ret = ureg(f"{numerator}/({denominator})").u
    # chekc if ret is dimensionless, if not return ret, else return the explicit quotient
    if not ret.dimensionless:
        return str(ret)
    else:
        return (f"{numerator}/({denominator})"
                if '/' in denominator else
                f"{numerator}/{denominator}")


class DataSet(TEBase):
    '''Class to store, normalise, select and aggregate DataSets



    Attributes
    ----------
        data
    '''
    _df: None | pd.DataFrame
    _columns: dict[str, AbstractColumnDefinition]
    _fields: dict[str, AbstractFieldDefinition]
    _masks: list[Mask]

    # initialise
    def __init__(self,
                 parent_variable: str,
                 include_databases: Optional[list[str] | tuple[str]] = None,
                 file_paths: Optional[list[Path]] = None,
                 check_inconsistencies: bool = False,
                 data: Optional[pd.DataFrame] = None,
                 ):
        '''Initialise parent class and fields, load data from specified databases and files

        Parameters
        ----------
        parent_variable: str
            Variable to collect Data on
        include_databases: Optional[list|str] | tuple[str]], optional
            Databases to load from
        file_paths: Optional[list[path]], optional
            Paths to load data from
        check_inconsistencies: bool, optional
            Wether to check for inconsistencies
        data: Optional[pd.DataFrame], optional
            Specific data to include in the dataset

        '''
        TEBase.__init__(self, parent_variable)

        # initialise fields
        self._df = None
        self._columns = base_columns
        self._fields = {
            col_id: field
            for col_id, field in self._columns.items()
            if isinstance(field, AbstractFieldDefinition)
        }
        self._masks = []

        # Load data if provided, otherwise load from TEDataFiles
        if data is not None:
            self._df = data
        else:
            # read TEDataFiles and combine into dataset
            include_databases = list(include_databases) if include_databases is not None else list(databases.keys())
            self._df = self._load_files(include_databases, file_paths or [], check_inconsistencies)


    @property
    def data(self):
        '''Get or set dataframe'''
        return self._df

    def set_data(self, df: pd.DataFrame):
        self._df = df


    def _load_files(self, include_databases: list[str], file_paths: list[Path], check_inconsistencies: bool):
        # Load TEDFs and compile into NSHADataSet

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

        # get fields and masks from databases
        files_vars: set[str] = {f.parent_variable for f in files}
        for v in files_vars:
            new_fields, new_comments = read_fields(v)
            for col_id in new_fields | new_comments:
                if col_id in self._columns:
                    raise Exception(f"Cannot load TEDFs due to multiple columns with same ID defined: {col_id}")
            self._fields = new_fields | self._fields
            self._columns = new_fields | self._columns | new_comments
            self._masks += read_masks(v)

        # load all TEDFs: load from file, check for inconsistencies (if requested), expand cases and variables
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

        # drop entries with unknown variables and warn
        for var_type in ('variable', 'reference_variable'):
            cond = (data[var_type].notnull() &
                    data.apply(lambda row: f"{row['parent_variable']}|{row[var_type]}" not in self._var_specs, axis=1))
            if cond.any():
                warnings.warn(f"Unknown {var_type}, so dropping rows:\n{data.loc[cond, var_type]}")
                data = data.loc[~cond].reset_index(drop=True)

        # return
        return data


    def normalise(self, override: Optional[dict[str, str]] = None, inplace: bool = False) -> pd.DataFrame | None:
        '''
        normalise data: default reference units, reference value equal to 1.0, default reported units

        Parameters
        ----------
        override: Optional[dict[str,str]], optional
            Dictionary with key, value pairs of variables to override
        inplace: bool, optional
            Wether to do the normalisation in place

        Returns
        -------
        pd.DataFrame
            if inplace is false, returns normalised dataframe'''
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

        # return normalised data and variable units
        return normalised, var_units

    # prepare data for selection
    def select(self,
               override: Optional[dict[str, str]] = None,
               drop_singular_fields: bool = True,
               extrapolate_period: bool = True,
               **field_vals_select) -> pd.DataFrame:
        '''Select desired data from the dataframe

        Parameters
        ----------
        override: Optional[dict[str, str]]
            Dictionary with key, value paris of variables to override
        drop_singular_fields: bool, optional
            If True, drop custom fields with only one value
        extrapolate_period: bool, optional
            If True, extrapolate values by extrapolation, if no value for this period is given
        **field_vals_select
            IDs of values to select

        Returns
        -------
        pd.DataFrame
            DataFrame with selected Values
            '''
        selected, var_units, var_references = self._select(
            override,
            drop_singular_fields,
            extrapolate_period,
            **field_vals_select,
        )
        selected.insert(selected.columns.tolist().index('variable'), 'reference_variable', np.nan)
        selected['reference_variable'] = selected['variable'].map(var_references)
        return self._cleanup(selected, var_units)

    def _select(self,
                override: Optional[dict[str, str]],
                drop_singular_fields: bool,
                extrapolate_period: bool,
                **field_vals_select) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
        # start from normalised data
        normalised, var_units = self._normalise(override)
        selected = normalised

        # drop unit columns and reference value column
        selected.drop(columns=['unit', 'reference_unit', 'reference_value'], inplace=True)

        # drop columns containing comments and uncertainty field (which is currently unsupported)
        selected.drop(
            columns=['uncertainty'] + [
                col_id for col_id, field in self._columns.items()
                if field.col_type == 'comment'
            ],
            inplace=True,
        )

        # add parent variable as prefix to other variable columns
        selected['variable'] = selected['parent_variable'] + '|' + selected['variable']
        selected['reference_variable'] = selected['parent_variable'] + '|' + selected['reference_variable']
        selected.drop(columns=['parent_variable'], inplace=True)

        # raise exception if fields listed in arguments that are unknown
        for field_id in field_vals_select:
            if not any(field_id == col_id for col_id in self._fields):
                raise Exception(f"Field '{field_id}' does not exist and cannot be used for selection.")

        # order fields for selection: period must be expanded last due to the interpolation
        fields_select = ({col_id: self._fields[col_id] for col_id in field_vals_select} |
                         {col_id: field for col_id, field in self._fields.items() if col_id != 'period' and col_id not in field_vals_select} |
                         {'period': self._fields['period']})

        # select and expand fields
        for col_id, field in fields_select.items():
            field_vals = field_vals_select[col_id] if col_id in field_vals_select else None
            selected = field.select_and_expand(selected, col_id, field_vals, extrapolate_period=extrapolate_period)

        # drop custom fields with only one value if specified in method argument
        if drop_singular_fields:
            selected.drop(columns=[
                col_id for col_id, field in self._fields.items()
                if isinstance(field, CustomFieldDefinition) and selected[col_id].nunique() < 2
            ], inplace=True)

        # apply mappings
        selected = self._apply_mappings(selected, var_units)

        # drop rows with failed mappings
        selected.dropna(subset='value', inplace=True)

        # get map of variable references
        var_references = selected \
            .filter(['variable', 'reference_variable']) \
            .drop_duplicates() \
            .set_index('variable')['reference_variable']

        # Check for multiple reference variables per reported variable
        if not var_references.index.is_unique:
            raise Exception(f"Multiple reference variables per reported variable found: {var_references}")
        var_references = var_references.to_dict()

        # Remove 'reference_variable column
        selected.drop(columns=['reference_variable'], inplace=True)

        # strip off unit variants
        var_units = {
            variable: unit.split(';')[0]
            for variable, unit in var_units.items()
        }

        # return
        return selected, var_units, var_references


    def _apply_mappings(self, expanded: pd.DataFrame, var_units: dict) -> pd.DataFrame:
        # apply mappings between entry types
        # list of columns to group by
        group_cols = [
            c for c in expanded.columns
            if c not in ['variable', 'reference_variable', 'value']
        ]

        # perform groupby and do not drop NA values
        grouped = expanded.groupby(group_cols, dropna=False)

        # create return list
        ret = []

        # loop over groups
        for keys, ids in grouped.groups.items():
            # get rows in group
            rows = expanded.loc[ids, [c for c in expanded if c not in group_cols]].copy()

            # 1. convert FLH to OCF
            cond = rows['variable'].str.endswith('|FLH')
            if cond.any():

                # Multiply 'value' by conversion factor
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: unit_convert(var_units[row['variable']], 'a'),
                    axis=1,
                )

                # Replace '|FLH' with '|OCF‘ in 'variable'
                rows.loc[cond, 'variable'] = rows.loc[cond, 'variable'] \
                    .str.replace('|FLH', '|OCF', regex=False)

            # 2. convert OPEX Fixed Relative to OPEX Fixed
            cond = rows['variable'].str.endswith('|OPEX Fixed Relative')
            if cond.any():

                # Define a function to calculate the conversion factor
                def calculate_conversion(row):
                    conversion_factor = unit_convert(var_units[row['variable']], 'dimensionless') * unit_convert(
                        var_units[row['variable'].replace('|OPEX Fixed Relative', '|CAPEX')] + '/a',
                        var_units[row['variable'].replace('|OPEX Fixed Relative', '|OPEX Fixed')]
                    ) * (rows.query(
                        f"variable=='{row['variable'].replace('|OPEX Fixed Relative', '|CAPEX')}'"
                    ).pipe(
                        lambda df: df['value'].iloc[0] if not df.empty else np.nan,
                    ))
                    return conversion_factor

                # Calcualte the conversion factor and update 'value' for rows satisfying the condition
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: calculate_conversion(row),
                    axis=1,
                )

                # Replace '|OPEX Fixed Relative' with '|OPEX FIXED' in 'variable'
                rows.loc[cond, 'variable'] = rows.loc[cond, 'variable'] \
                    .str.replace('|OPEX Fixed Relative', '|OPEX Fixed')

                # Assign 'reference_variable' based on modified 'variable'
                rows.loc[cond, 'reference_variable'] = rows.loc[cond].apply(
                    lambda row: rows.query(
                        f"variable=='{row['variable'].replace('|OPEX Fixed', '|CAPEX')}'"
                    ).pipe(
                        lambda df: df['reference_variable'].iloc[0] if not df.empty else np.nan,
                    ),
                    axis=1,
                )

                # Check if there are rows with null 'value' after the operation
                if (cond & rows['value'].isnull()).any():
                    warnings.warn(HarmoniseMappingFailure(
                        expanded.loc[ids].loc[cond & rows['value'].isnull()],
                        'No CAPEX value matching a OPEX Fixed Relative value found.',
                    ))

            # 3. convert OPEX Fixed Specific to OPEX Fixed
            cond = rows['variable'].str.endswith('|OPEX Fixed Specific')
            if cond.any():

                # Define a function to calculate the conversion factor
                def calculate_conversion(row):
                    conversion_factor = unit_convert(
                        var_units[row['variable']] + '/a',
                        var_units[row['variable'].replace('|OPEX Fixed Specific', '|OPEX Fixed')]
                    ) / unit_convert(
                        var_units[row['reference_variable']] + '/a',
                        var_units[re.sub(r'(Input|Output)', r'\1 Capacity', row['reference_variable'])],
                        self._var_specs[row['reference_variable']]['flow_id'] if 'flow_id' in self._var_specs[row['reference_variable']] else np.nan,
                    ) * unit_convert(
                        var_units[row['variable'].replace('|OPEX Fixed Specific', '|OCF')],
                        'dimensionless'
                    ) * (rows.query(
                        f"variable=='{row['variable'].replace('|OPEX Fixed Specific', '|OCF')}'"
                    ).pipe(
                        lambda df: df['value'].iloc[0] if not df.empty else np.nan,
                    ))
                    return conversion_factor

                # Calculate the conversion factor and update 'value' for rows satisfying the condition
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: calculate_conversion(row),
                    axis=1,
                )

                # replace '|OPEX Fixed Specific' with '|OPEX Fixed' in 'variable'
                rows.loc[cond, 'variable'] = rows.loc[cond, 'variable'] \
                    .str.replace('|OPEX Fixed Specific', '|OPEX Fixed')

                # Assign 'reference_variable by replacing 'Input' or 'Output' with 'Input Capacity' or 'Output Capacity'
                rows.loc[cond, 'reference_variable'] = rows.loc[cond, 'reference_variable'].apply(
                    lambda cell: re.sub(r'(Input|Output)', r'\1 Capacity', cell),
                )

                # Check if there are any rows with null 'value' after the opera
                if (cond & rows['value'].isnull()).any():
                    warnings.warn(HarmoniseMappingFailure(
                        expanded.loc[ids].loc[cond & rows['value'].isnull()],
                        'No OCF value matching a OPEX Fixed Specific value found.',
                    ))

            # 4. convert efficiencies (Output over Input) to demands (Input over Output)
            cond = (rows['variable'].str.contains(r'\|Output(?: Capacity)?\|') &
                    (rows['reference_variable'].str.contains(r'\|Input(?: Capacity)?\|')
                    if rows['reference_variable'].notnull().any() else False))
            if cond.any():
                rows.loc[cond, 'value'] = 1.0 / rows.loc[cond, 'value']
                rows.loc[cond, 'variable_new'] = rows.loc[cond, 'reference_variable']
                rows.loc[cond, 'reference_variable'] = rows.loc[cond, 'variable']
                rows.loc[cond, 'variable'] = rows.loc[cond, 'variable_new']
                rows.drop(columns=['variable_new'], inplace=True)

            # 5. convert all references to primary output
            cond = (((rows['reference_variable'].str.contains(r'\|Output(?: Capacity)?\|') |
                    rows['reference_variable'].str.contains(r'\|Input(?: Capacity)?\|'))
                    if rows['reference_variable'].notnull().any() else False) &
                    rows['variable'].map(lambda var: 'default_reference' in self._var_specs[var]) &
                    (rows['variable'].map(
                        lambda var: self._var_specs[var]['default_reference']
                        if 'default_reference' in self._var_specs[var] else np.nan
                    ) != rows['reference_variable']))
            if cond.any():
                regex_find = r'\|(Input|Output)(?: Capacity)?\|'
                regex_repl = r'|\1|'
                rows.loc[cond, 'reference_variable_new'] = rows.loc[cond, 'variable'].map(
                    lambda var: self._var_specs[var]['default_reference'],
                )

                # Define function to calculate the conversion factor
                def calculate_conversion(row):
                    conversion_factor =  unit_convert(
                        ('a*' if 'Capacity' in row['reference_variable'] else '') + var_units[row['reference_variable_new']],
                        var_units[re.sub(regex_find, regex_repl, row['reference_variable_new'])],
                        row['reference_variable_new'].split('|')[-1]
                    ) / unit_convert(
                        ('a*' if 'Capacity' in row['reference_variable'] else '') + var_units[row['reference_variable']],
                        var_units[re.sub(regex_find, regex_repl, row['reference_variable'])],
                        row['reference_variable'].split('|')[-1]
                    ) * rows.query(
                        f"variable=='{re.sub(regex_find, regex_repl, row['reference_variable'])}' & "
                        f"reference_variable=='{re.sub(regex_find, regex_repl, row['reference_variable_new'])}'"
                    ).pipe(
                        lambda df: df['value'].iloc[0] if not df.empty else np.nan,
                    )
                    return conversion_factor

                # Calculate the conversion factor and update 'value' for rows satisfying the condition
                rows.loc[cond, 'value'] *= rows.loc[cond].apply(
                    lambda row: calculate_conversion(row),
                    axis=1,
                )
                rows.loc[cond, 'reference_variable'] = rows.loc[cond, 'reference_variable_new']
                rows.drop(columns=['reference_variable_new'], inplace=True)
                if (cond & rows['value'].isnull()).any():
                    warnings.warn(HarmoniseMappingFailure(
                        expanded.loc[ids].loc[cond & rows['value'].isnull()],
                        'No appropriate mapping found to convert row reference to primary output.',
                    ))

            # set missing columns from group
            rows[group_cols] = keys

            # add to return list
            ret.append(rows)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True) if ret else expanded.iloc[[]]

    # select data
    def aggregate(self, override: Optional[dict[str, str]] = None,
                  drop_singular_fields: bool = True,
                  extrapolate_period: bool = True,
                  agg: Optional[str | list[str] | tuple[str]] = None,
                  masks: Optional[list[Mask]] = None,
                  masks_database: bool = True,
                  **field_vals_select) -> pd.DataFrame:
        '''Aggregates data based on specified parameters, applies masks,
        and cleans up the resulting DataFrame.

        Parameters
        ----------
        override: Optional[dict[str, str]]
            Dictionary with key, value paris of variables to override
        drop_singular_fields: bool, optional
            If True, drop custom fields with only one value
        extrapolate_period: bool, optional
            If True, extrapolate values by extrapolation, if no value for this period is given
        agg : Optional[str | list[str] | tuple[str]]
            Specifies which fields to aggregate over.
        masks : Optional[list[Mask]]
            Specifies a list of Mask objects that will be applied to the data during aggregation.
            These masks can be used to filter or weight the
            data based on certain conditions defined in the Mask objects.
        masks_database : bool, optional
            Determines whether to include masks from databases in the aggregation process.
            If set to `True`, masks from databases will be included along with any masks provided as function arguments.
            If set to `False`, only the masks provided as function argruments will be applied

        Returns
        -------
        pd.DataFrame
            The `aggregate` method returns a pandas DataFrame that has been cleaned up and aggregated based
            on the specified parameters and input data. The method performs aggregation over component
            fields and cases fields, applies weights based on masks, drops rows with NaN weights, aggregates
            with weights, inserts reference variables, sorts columns and rows, rounds values, and inserts
            units before returning the final cleaned and aggregated DataFrame.

        '''

        # get selection
        selected, var_units, var_references = self._select(override,
                                                           extrapolate_period,
                                                           drop_singular_fields,
                                                           **field_vals_select)

        # compile masks from databases and function argument into one list
        if masks is not None and any(not isinstance(m, Mask) for m in masks):
            raise Exception("Function argument 'masks' must contain a list of posted.masking.Mask objects.")
        masks = (self._masks if masks_database else []) + (masks or [])

        # aggregation
        component_fields = [
            col_id for col_id, field in self._fields.items()
            if field.field_type == 'component'
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
                if not any(a == col_id for col_id in self._fields):
                    raise Exception(f"Field ID in argument 'agg' is not a valid field: {a}")

        # aggregate over component fields
        group_cols = [
            c for c in selected.columns
            if not (c == 'value' or (c in agg and c in component_fields))
        ]
        aggregated = selected \
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
                    .groupby(group_cols, dropna=False)[['value', 'weight']] \
                    .apply(lambda cols: pd.Series({
                        'value': np.average(cols['value'], weights=cols['weight']),
                    }))

                # add to return list
                ret.append(out)
        aggregated = pd.concat(ret).reset_index()

        # insert reference variables
        var_ref_unique = {
            var_references[var]
            for var in aggregated['variable'].unique()
            if not pd.isnull(var_references[var])
        }
        agg_append = []
        for ref_var in var_ref_unique:
            agg_append.append(pd.DataFrame({
                'variable': [ref_var],
                'value': [1.0],
            } | {
                col_id: ['*']
                for col_id, field in self._fields.items() if col_id in aggregated
            }))
        if agg_append:
            agg_append = pd.concat(agg_append).reset_index(drop=True)
            for col_id, field in self._fields.items():
                if col_id not in aggregated:
                    continue
                agg_append = field.select_and_expand(agg_append, col_id, aggregated[col_id].unique().tolist())
        else:
            agg_append = None

        # convert return list to dataframe, reset index, and clean up
        return self._cleanup(pd.concat([aggregated, agg_append]), var_units)

    # clean up: sort columns and rows, round values, insert units
    def _cleanup(self, df: pd.DataFrame, var_units: dict[str, str]) -> pd.DataFrame:
        # sort columns and rows
        cols_sorted = (
            [col_id for col_id, field in self._fields.items() if isinstance(field, CustomFieldDefinition)] +
            ['source', 'variable', 'reference_variable', 'region', 'period', 'value']
        )
        cols_sorted = [c for c in cols_sorted if c in df.columns]
        df = df[cols_sorted]
        df = df \
            .sort_values(by=[c for c in cols_sorted if c in df and c != 'value']) \
            .reset_index(drop=True)

        # round values
        df['value'] = df['value'].apply(
            lambda cell: cell if pd.isnull(cell) else round(cell, sigfigs=4, warn=False)
        )

        # insert column containing units
        df.insert(df.columns.tolist().index('value'), 'unit', np.nan)
        if 'reference_variable' in df:
            df['unit'] = df.apply(
                lambda row: combine_units(var_units[row['variable']], var_units[row['reference_variable']])
                            if not pd.isnull(row['reference_variable']) else
                            var_units[row['variable']],
                axis=1,
            )
        else:
            df['unit'] = df['variable'].map(var_units)

        return df
