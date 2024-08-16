import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from posted.config import variables
from posted.columns import AbstractFieldDefinition, base_columns, AbstractColumnDefinition, read_fields
from posted.path import databases
from posted.units import unit_allowed


class TEDFInconsistencyException(Exception):
    """
    Exception raised for inconsistencies in TEDFs.

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

        # Add tokens at the end of the error message.
        message_tokens = []
        if file_path is not None:
            message_tokens.append(f"file \"{file_path}\"")
        if row_id is not None:
            message_tokens.append(f"line {row_id}")
        if col_id is not None:
            message_tokens.append(f"in column \"{col_id}\"")

        # Compose error message from tokens.
        exception_message: str = message
        if message_tokens:
            exception_message += (
                f"\n    " + (", ".join(message_tokens)).capitalize()
            )

        super().__init__(exception_message)


def new_inconsistency(raise_exception: bool, **kwargs) -> TEDFInconsistencyException:
    """
    Create new inconsistency object based on kwqargs

    Parameters
    ----------

    """
    exception = TEDFInconsistencyException(**kwargs)
    if raise_exception:
        raise exception
    else:
        return exception


class TEBase:
    """
    Base class for techno-economic data/

    Parameters
    ----------
    parent_variable: str
        Variable from which Data should be collected
    """
    # initialise

    def __init__(self, parent_variable: str):
        """ Set parent variable and technology specifications
        (var_specs) from input"""
        self._parent_variable: str = parent_variable
        self._var_specs: dict = {
            key: val for key, val in variables.items()
            if key.startswith(self._parent_variable)
        }

    @property
    def parent_variable(self) -> str:
        """Get parent variable"""
        return self._parent_variable


class TEDF(TEBase):
    """
    Class to handle Techno-Economic Data Files (TEDFs).

    Parameters
    ----------
    parent_variable: str
        Variable from which Data should be collected
    database_id: str, default: public
        Database from which to load data
    file_path: Path, optional
        File Path from which to load file
    data: pd.DataFrame, optional
        Specific Technoeconomic data

    Methods
    ----------
    load
        Load TEDF if it has not been read yet.
    read
        Read TEDF from CSV file.
    write
        Write TEDF to CSV file.
    check
        Check if TEDF is consistent.
    check_row
        Check that row in TEDF is consistent and return all
        inconsistencies found for row.
    """
    # Typed declarations.
    _df: None | pd.DataFrame
    _inconsistencies: dict
    _file_path: None | Path
    _fields: dict[str, AbstractFieldDefinition]
    _columns: dict[str, AbstractColumnDefinition]

    def __init__(self,
                 parent_variable: str,
                 database_id: str = 'public',
                 file_path: Optional[Path] = None,
                 data: Optional[pd.DataFrame] = None,
                 ):
        """ Initialise parent class and object fields"""
        TEBase.__init__(self, parent_variable)

        self._df = data
        self._inconsistencies = {}
        self._file_path = (
            None if data is not None else
            file_path if file_path is not None else
            (databases[database_id] / 'tedfs' /
                ('/'.join(self._parent_variable.split('|')) + '.csv'))
        )
        self._fields, comments = read_fields(self._parent_variable)
        self._columns = self._fields | base_columns | comments

    @property
    def file_path(self) -> Path:
        """ Get or set the file path"""
        return self._file_path

    @file_path.setter
    def file_path(self, file_path: Path):
        self._file_path = file_path

    def load(self):
        """
        load TEDF (only if it has not been read yet)

        Warns
        ----------
        warning
            Warns if TEDF is already loaded
        Returns
        --------
            TEDF
                Returns the TEDF object it is called on
        """
        if self._df is None:
            self.read()
        else:
            warnings.warn('TEDF is already loaded. Please execute .read() if '
                          'you want to load from file again.')

        return self

    def read(self):
        """
        read TEDF from CSV file

        Raises
        ------
        Exception
            If there is no file path from which to read
        """

        if self._file_path is None:
            raise Exception('Cannot read from file, as this TEDF object has '
                            'been created from a dataframe.')

        # Read CSV file.
        self._df = pd.read_csv(
            self._file_path,
            sep=',',
            quotechar='"',
            encoding='utf-8',
        )

        # Check column IDs match base columns and fields.
        if not all(c in self._columns for c in self._df.columns):
            raise Exception(f"Column IDs used in CSV file do not match "
                            f"columns definition: {self._df.columns.tolist()}")

        # Adjust row index to start at 1 instead of 0.
        self._df.index += 1

        # Insert missing columns and reorder via reindexing, then
        # update dtypes.
        df_new = self._df.reindex(columns=list(self._columns.keys()))
        for col_id, col in self._columns.items():
            if col_id in self._df:
                continue
            df_new[col_id] = df_new[col_id].astype(col.dtype)
            df_new[col_id] = col.default
        self._df = df_new

    def write(self):
        """
        Write TEDF to CSV file

        Raises
        ------
        Exception
            If there is no file path that specifies where to write
        """
        if self._file_path is None:
            raise Exception('Cannot write to file, as this TEDataFile object '
                            'has been created from a dataframe. Please first '
                            'set a file path on this object.')

        self._df.to_csv(
            self._file_path,
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )

    @property
    def data(self) -> pd.DataFrame:
        """Get data, i.e. access dataframe"""
        return self._df

    @property
    def inconsistencies(self) -> dict[int, TEDFInconsistencyException]:
        """Get inconsistencies"""
        return self._inconsistencies

    def check(self, raise_exception: bool = True):
        """
        Check that TEDF is consistent and add inconsistencies to internal parameter

        Parameters
        ----------
        raise_exception: bool, default: True
            If exception is to be raised
        """
        self._inconsistencies = {}

        # check row consistency for each row individually
        for row_id in self._df.index:
            self._inconsistencies[row_id] = self.check_row(
                row_id=row_id,
                raise_exception=raise_exception,
            )

    def check_row(self, row_id: int, raise_exception: bool) -> list[TEDFInconsistencyException]:
        """
        Check that row in TEDF is consistent and return all inconsistencies found for row

        Parameters
        ----------
        row_id: int
            Index of the row to check
        raise_exception: bool
            If exception is to be raised

        Returns
        -------
            list
                List of inconsistencies
        """
        row = self._df.loc[row_id]
        ikwargs = {
            'row_id': row_id,
            'file_path': self._file_path,
            'raise_exception': raise_exception,
        }
        ret = []

        # Check whether fields are among those defined in the technology specs.
        for col_id, col in self._columns.items():
            cell = row[col_id]
            if col.col_type == 'variable':
                cell = cell if pd.isnull(
                    cell) else self.parent_variable + '|' + cell
            if not col.is_allowed(cell):
                ret.append(new_inconsistency(
                    message=f"Invalid cell for column of type '{col.col_type}': {cell}", col_id=col_id, **ikwargs,
                ))

        # Check that reported and reference units match variable definition.
        for col_prefix in ['', 'reference_']:
            raw_variable = row[col_prefix + 'variable']
            col_id = col_prefix + 'unit'
            unit = row[col_id]
            if pd.isnull(raw_variable) and pd.isnull(unit):
                continue
            if pd.isnull(raw_variable) or pd.isnull(unit):
                ret.append(new_inconsistency(
                    message=f"Variable and unit must either both be set or "
                            f"both be unset': {raw_variable} -- {unit}",
                    col_id=col_id,
                    **ikwargs,
                ))
            variable = self.parent_variable + '|' + raw_variable
            var_specs = variables[variable]
            if 'dimension' not in var_specs:
                if unit is not np.nan:
                    ret.append(new_inconsistency(
                        message=f"Unexpected unit '{unit}' for {col_id}.",
                        col_id=col_id,
                        **ikwargs,
                    ))
                continue
            dimension = var_specs['dimension']

            flow_id = var_specs['flow_id'] if 'flow_id' in var_specs else None
            allowed, message = unit_allowed(
                unit=unit,
                flow_id=flow_id,
                dimension=dimension,
            )
            if not allowed:
                ret.append(new_inconsistency(
                    message=message,
                    col_id=col_id,
                    **ikwargs,
                ))

        return ret
