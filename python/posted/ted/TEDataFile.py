import warnings
from typing import Optional
import copy
from pathlib import Path

import numpy as np
import pandas as pd

from posted.config import base_format, base_dtypes, variables
from posted.path import databases
from posted.ted.TEBase import TEBase
from posted.ted.inconsistencies import check_row_consistency


def expand_cases(row: pd.Series, main_variable: str) -> pd.DataFrame:
    variable = main_variable + '|' + row['variable']
    var_specs = variables[variable]

    rows = [row]
    if 'case_fields' in var_specs:
        for case_field_id, case_field_options in var_specs['case_fields'].items():
            new_rows = []
            for row in rows:
                if case_field_id not in row or row[case_field_id] == '*':
                    for option in case_field_options:
                        new_row = row.copy()
                        new_row.loc[case_field_id] = option
                        new_rows.append(new_row)
                else:
                    new_rows.append(row)
            rows = new_rows
    return pd.DataFrame(data=rows)

def combine_variable(row: pd.Series, main_variable: str) -> str:
    variable = main_variable + '|' + row['variable']
    var_specs = variables[variable]

    return ' '.join([main_variable] + row[list(var_specs['case_fields'].keys())].tolist()) + '|' + row['variable']


class TEDataFile(TEBase):
    # initialise
    def __init__(self,
                 main_variable: str,
                 database_id: str = 'public',
                 file_path: Optional[Path] = None,
                 data: Optional[pd.DataFrame] = None,
                 ):
        TEBase.__init__(self, main_variable)

        # initialise object fields
        self._df: None | pd.DataFrame = data
        self._inconsistencies: dict = {}
        self._file_path: None | Path = (
            None if data is not None else
            file_path if file_path is not None else
            databases[database_id] / 'teds' / ('/'.join(self._main_variable.split('|')) + '.csv')
        )

    @property
    def file_path(self) -> Path:
        return self._file_path

    @file_path.setter
    def file_path(self, file_path: Path):
        self._file_path = file_path

    # load TEDataFile (only if it has not been read yet)
    def load(self):
        if self._df is None:
            self.read()
        else:
            warnings.warn('TEDataFile is already loaded. Please execute .read() if you want to load from file again.')

        return self

    # read TEDataFile from CSV file
    def read(self):
        if self._file_path is None:
            raise Exception('Cannot read from file, as this TEDataFile object has been created from a dataframe.')

        # read CSV file
        self._df = pd.read_csv(
            self._file_path,
            sep=',',
            quotechar='"',
            encoding='utf-8',
        )

        # adjust row index to start at 1 instead of 0
        self._df.index += 1

        # create data format and dtypes from base format
        data_format_cols = list(base_format.keys())
        data_format_cols = [c for c in self._df.columns if c not in data_format_cols] + data_format_cols
        data_dtypes = copy.deepcopy(base_dtypes)
        for c in data_format_cols:
            if c not in data_dtypes:
                data_dtypes[c] = 'category'

        # insert missing columns and reorder via reindexing and update dtypes
        df_new = self._df.reindex(columns=data_format_cols)
        for col, dtype in data_dtypes.items():
            if col in self._df:
                continue
            df_new[col] = df_new[col].astype(dtype)
            df_new[col] = np.nan
        self._df = df_new

    # write TEDataFile to CSV file
    def write(self):
        if self._file_path is None:
            raise Exception('Cannot write to file, as this TEDataFile object has been created from a dataframe. Please '
                            'first set a file path on this object.')

        self._df.to_csv(
            self._file_path,
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )

    # access dataframe
    @property
    def data(self) -> pd.DataFrame:
        return self._df

    # get data
    def get_inconsistencies(self) -> dict:
        return self._inconsistencies

    # check that TEDataFile is consistent
    def check(self, raise_exception: bool = True):
        self._inconsistencies = {}

        # check row consistency for each row individually
        for row_id in self._df.index:
            self.check_row(row_id, raise_exception=raise_exception)

    # check that row in TEDataFile is consistent
    def check_row(self, row_id: int, raise_exception: bool = True):
        row = self._df.loc[row_id]
        self._inconsistencies[row_id] = check_row_consistency(
            main_variable=self._main_variable,
            row=row,
            row_id=row_id,
            file_path=self._file_path,
            raise_exception=raise_exception,
        )

    def expand_data(self) -> pd.DataFrame:
        data = self._df

        # expand case fields
        data = pd.concat([expand_cases(row, self._main_variable) for _, row in data.iterrows()]).reset_index(drop=True)

        # combine variable identifiers
        data['variable'] = data.apply(lambda row: combine_variable(row, self._main_variable), axis=1)

        # drop fields that are not in the base format
        data = data.filter(list(base_format.keys()))

        return data
