import copy
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from posted.config import variables, base_format, base_dtypes
from posted.fields import CustomFieldDefinition, AbstractFieldDefinition
from posted.masking import Mask
from posted.path import databases
from posted.read import read_yml_file
from posted.units import unit_allowed


def read_fields(variable: str):
    ret: list[CustomFieldDefinition] = []

    for database_id in databases:
        fpath = databases[database_id] / 'fields' / ('/'.join(variable.split('|')) + '.yml')
        if fpath.exists():
            if not fpath.is_file():
                raise Exception(f"Expected YAML file, but not a file: {fpath}")
            ret += [
                CustomFieldDefinition(field_id, **field_specs)
                for field_id, field_specs in read_yml_file(fpath).items()
            ]

    return ret


def read_masks(variable: str):
    ret: list[Mask] = []

    for database_id in databases:
        fpath = databases[database_id] / 'masks' / ('/'.join(variable.split('|')) + '.yml')
        if fpath.exists():
            if not fpath.is_file():
                raise Exception(f"Expected YAML file, but not a file: {fpath}")

            ret += [
                Mask(**mask_specs)
                for mask_specs in read_yml_file(fpath)
            ]

    return ret


class TEBase:
    # initialise
    def __init__(self, parent_variable: str):
        # set variable from function argument
        self._parent_variable: str = parent_variable

        # set technology specifications
        self._var_specs: dict = {key: val for key, val in variables.items() if key.startswith(self._parent_variable)}

    @property
    def parent_variable(self) -> str:
        return self._parent_variable


class TEDF(TEBase):
    # initialise
    def __init__(self,
                 parent_variable: str,
                 database_id: str = 'public',
                 file_path: Optional[Path] = None,
                 data: Optional[pd.DataFrame] = None,
                 ):
        TEBase.__init__(self, parent_variable)

        # initialise object fields
        self._df: None | pd.DataFrame = data
        self._inconsistencies: dict = {}
        self._file_path: None | Path = (
            None if data is not None else
            file_path if file_path is not None else
            databases[database_id] / 'tedfs' / ('/'.join(self._parent_variable.split('|')) + '.csv')
        )
        self._fields: list[AbstractFieldDefinition] = read_fields(self._parent_variable)

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
        print(data_format_cols)
        # insert missing columns and reorder via reindexing and update dtypes
        df_new = self._df.reindex(columns=data_format_cols)
        print(self._df.columns)
        print(df_new.columns)
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
            parent_variable=self._parent_variable,
            fields=self._fields,
            row=row,
            row_id=row_id,
            file_path=self._file_path,
            raise_exception=raise_exception,
        )


class TEDFInconsistencyException(Exception):
    """Exception raised for inconsistencies in TEDFs.

    Attributes:
        message -- message explaining the inconsistency
        row_id -- row where the inconsistency occurs
        col_id -- column where the inconsistency occurs
        file_path -- path to the file where the inconsistency occurs
    """
    def __init__(self, message: str = "Inconsistency detected", row_id: None | int = None,
                 col_id: None | str = None, file_path: None | Path = None):
        self.message: str = message
        self.row_id: None | int = row_id
        self.col_id: None | str = col_id
        self.file_path: None | Path = file_path

        # add tokens at the end of the error message
        message_tokens = []
        if file_path is not None:
            message_tokens.append(f"file \"{file_path}\"")
        if row_id is not None:
            message_tokens.append(f"line {row_id}")
        if col_id is not None:
            message_tokens.append(f"in column \"{col_id}\"")

        # compose error message from tokens
        exception_message: str = message
        if message_tokens:
            exception_message += f"\n    " + (", ".join(message_tokens)).capitalize()

        super().__init__(exception_message)


# create a new inconsistency object based on function arguments and either raise or return. returning will typically
# occur in file-editing mode in the GUI, whereas raising will happen in active usage and testing.
def new_inconsistency(raise_exception: bool, **kwargs) -> TEDFInconsistencyException:
    exception = TEDFInconsistencyException(**kwargs)
    if raise_exception:
        raise exception
    else:
        return exception


def check_row_consistency(parent_variable: str, fields: list[AbstractFieldDefinition], row: pd.Series, row_id: int,
                          file_path: Path, raise_exception: bool) -> list[TEDFInconsistencyException]:
    ikwargs = {'row_id': row_id, 'file_path': file_path, 'raise_exception': raise_exception}
    ret = []

    # check whether fields are among those defined in the technology specs
    for col_id in (c for c in row.index if c not in base_format):
        if not any(col_id == field.id for field in fields):
            ret.append(new_inconsistency(
                message=f"Invalid field ID: {col_id}.", col_id=col_id, **ikwargs,
            ))
        else:
            cell = row[col_id]
            field = next(field for field in fields if field.id == col_id)
            if field.type == 'comment':
                continue
            if field.type == 'cases' and cell == '#':
                ret.append(new_inconsistency(
                    message=f"Case fields may not contain hash keys.", col_id=col_id, **ikwargs,
                ))
            if field.type == 'components' and cell == '*':
                ret.append(new_inconsistency(
                    message=f"Component fields may not contain asterisks.", col_id=col_id, **ikwargs,
                ))
            if pd.isnull(cell) or (field.is_coded and not field.is_allowed(cell)):
                ret.append(new_inconsistency(
                    message=f"Invalid field value '{cell}'.", col_id=col_id, **ikwargs,
                ))

    # period may not be empty
    if pd.isnull(row['period']):
        ret.append(new_inconsistency(
            message=f"Period cell is empty.", col_id='period', **ikwargs,
        ))
    elif (not isinstance(row['period'], float) and
          not isinstance(row['period'], int) and
          not (isinstance(row['period'], str) and (is_float(row['period']) or row['period'] == '*'))):
        ret.append(new_inconsistency(
            message=f"Period is not a valid entry: {row['period']}", col_id='period', **ikwargs,
        ))

    # variable may not be empty
    reported_subvariable = row['reported_variable']
    reference_subvariable = row['reference_variable']
    if not isinstance(reported_subvariable, str):
        ret.append(new_inconsistency(message=f"Empty reported variable.", col_id='reported_variable', **ikwargs))
        return ret

    # if the variable is not empty, check whether variable is among the allowed variables
    reported_variable = f"{parent_variable}|{reported_subvariable}"
    reference_variable = f"{parent_variable}|{reference_subvariable}"
    if reported_variable not in variables:
        ret.append(new_inconsistency(
            message=f"Invalid reported variable '{reported_variable}'.", col_id='reported_variable', **ikwargs,
        ))
        return ret
    if reference_variable not in variables and 'default_reference' in variables[reported_variable]:
        ret.append(new_inconsistency(
            message=f"Invalid reference variable '{reference_variable}'.", col_id='reference_variable', **ikwargs,
        ))
        return ret

    # check that reported and reference units match variable definition
    for level, variable in [('reported', reported_variable),
                            ('reference', reference_variable),]:
        if not isinstance(reference_subvariable, str):
            continue
        var_specs = variables[variable]
        col_id = f"{level}_unit"
        unit = row[col_id]
        if 'dimension' not in var_specs:
            if unit is not np.nan:
                ret.append(new_inconsistency(
                    message=f"Unexpected unit '{unit}' for {col_id}.", col_id=col_id, **ikwargs,
                ))
            continue
        dimension = var_specs['dimension']

        flow_id = var_specs['flow_id'] if 'flow_id' in var_specs else None
        allowed, message = unit_allowed(unit=unit, flow_id=flow_id, dimension=dimension)
        if not allowed:
            ret.append(new_inconsistency(message=message, col_id=col_id, **ikwargs))

    return ret


def is_float(string: str) -> bool:
    try:
        float(string)
        return True
    except ValueError:
        return False


tedf = TEDF("tech|ELH2")
tedf.load()
print(tedf._df)