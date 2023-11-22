import warnings
import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sigfig import round

from posted.path import databases
from posted.ted.TEBase import TEBase
from posted.ted.TEDataFile import TEDataFile
from posted.units.units import unit_convert, ureg


# get list of TEDs potentially containing variable
def collect_files(main_variable: str, include_databases: Optional[list[str]] = None):
    if not main_variable:
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
        top_path = '/'.join(main_variable.split('|'))
        top_file = database_path / 'teds' / (top_path + '.csv')
        top_directory = database_path / 'teds' / top_path

        # add top-level file if it exists
        if top_file.exists() and top_file.is_file():
            ret.append((main_variable, database_id))

        # add all files contained in top-level directory
        if top_directory.exists() and top_directory.is_dir():
            for sub_file in top_directory.rglob('*.csv'):
                sub_variable = main_variable + '|' + sub_file.relative_to(top_directory).name.rstrip('.csv')
                ret.append((sub_variable, database_id))

        # loop over levels
        levels = main_variable.split('|')
        for l in range(0, len(levels)):
            # find top-level file and directory
            top_path = '/'.join(levels[:l])
            parent_file = database_path / 'teds' / (top_path + '.csv')

            # add parent file if it exists
            if parent_file.exists() and parent_file.is_file():
                parent_variable = '|'.join(levels[:l])
                ret.append((parent_variable, database_id))

    return ret


class TEDataSet(TEBase):
    _df: None | pd.DataFrame

    # initialise
    def __init__(self,
                 main_variable: str,
                 include_databases: Optional[list[str] | tuple[str]] = None,
                 file_paths: Optional[list[Path]] = None,
                 check_inconsistencies: bool = False,
                 data: Optional[pd.DataFrame] = None,
                 skip_normalise: bool = False,
                 ):
        TEBase.__init__(self, main_variable)

        if data is not None:
            self._df = data
        else:
            # initialise object fields
            self._df = None

            # read TEDataFiles and combine into dataset
            include_databases = list(include_databases) if include_databases is not None else list(databases.keys())
            self._df = self._load_files(include_databases, file_paths or [], check_inconsistencies)

            # normalise units and reference value unless told to skip
            if not skip_normalise:
                self.normalise()

    # load TEDatFiles and compile into dataset
    def _load_files(self, include_databases: list[str], file_paths: list[Path], check_inconsistencies: bool):
        files: list[TEDataFile] = []

        # collect TEDataFiles and append to list
        collected_files = collect_files(main_variable=self._main_variable, include_databases=include_databases)
        for file_variable, file_database_id in collected_files:
            files.append(TEDataFile(main_variable=file_variable, database_id=file_database_id))
        for file_path in file_paths:
            files.append(TEDataFile(main_variable=self._main_variable, file_path=file_path))

        # raise exception if no TEDataFiles can be loaded
        if not files:
            raise Exception(f"No TEDataFiles to load for variable '{self._main_variable}'.")

        # load all TEDataFiles: load from file, check for inconsistencies (if requested), expand cases and variables
        file_dfs: list[pd.DataFrame] = []
        for f in files:
            # load
            f.load()

            # check for inconsistencies
            if check_inconsistencies:
                f.check()

            # expand data from DataFile and append to dataframe list
            file_dfs.append(f.expand_data())

        # compile dataset from the dataframes loaded from the individual files
        data = pd.concat(file_dfs)

        # query relevant variables
        data = data.query(f"variable.str.startswith('{self._main_variable}')")

        # return
        return data

    # normalise reference values, reference units, and reported units
    def normalise(self, override: Optional[dict] = None):
        # normalise reference units
        self.normalise_reference_units(override)

        # normalise reference values
        self.normalise_reference_values()

        # normalise reported units
        self.normalise_reported_units(override)

    # normalise reference units
    def normalise_reference_units(self, override: Optional[dict] = None):
        if override is None:
            override = {}

        df_help = pd.concat([
            self._df,
            self._df.apply(lambda row: self._var_specs[row['variable']] | override, axis=1, result_type="expand")
        ], axis=1)

        self._df['reference_value'] *= df_help.apply(
            lambda row: unit_convert(row['reference_unit'], row['reference_unit_default'], row['reference_flow_id'])
            if not np.isnan(row['reference_value']) else 1.0,
            axis=1,
        )
        self._df['reference_unit'] = df_help['reference_unit_default']

    # normalise reference values
    def normalise_reference_values(self):
        self._df['reported_value'] /= self._df.apply(
            lambda row: row['reference_value']
            if not np.isnan(row['reference_value']) else 1.0,
            axis=1,
        )
        self._df['reference_value'] = self._df.apply(
            lambda row: 1.0
            if not np.isnan(row['reference_value']) else np.nan,
            axis=1,
        )

    # normalise reported units
    def normalise_reported_units(self, override: Optional[dict] = None):
        if override is None:
            override = {}

        df_help = pd.concat([
            self._df,
            self._df.apply(lambda row: self._var_specs[row['variable']] | override, axis=1, result_type="expand")
        ], axis=1)

        self._df['reported_value'] *= df_help.apply(
            lambda row: unit_convert(row['reported_unit'], row['reported_unit_default'], row['reported_flow_id'])
            if not np.isnan(row['reported_value']) else 1.0,
            axis=1,
        )
        self._df['reported_unit'] = df_help['reported_unit_default']

    # access dataframe
    @property
    def data(self):
        return self._df

    # query data
    def query(self, *args, **kwargs):
        return TEDataSet(
            main_variable=self._main_variable,
            data=self._df.query(*args, **kwargs),
        )
