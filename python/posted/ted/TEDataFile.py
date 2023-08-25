from pathlib import Path

import numpy as np
import pandas as pd

from posted.path import pathOfTEDFile
from posted.ted.TEBase import TEBase
from posted.ted.inconsistencies import checkRowConsistency

class TEDataFile(TEBase):
    """ The base class for all TE data file classes.

    This abstract class defines the basic structure of a TE data file class.
    This includes tid, data format, technology specifications, and dtype mapping.
    It also is a subclass fo TEBase.

    Attributes
    ----------
    _tid : str
        The technology ID.
    _tspecs : dict
        The technology specifications.
    _dataFormat : dict
        The data format.
    _caseFields : list
        The case fields.
    _dtypeMapping : None | dict
        The dtype mapping.
    _path : Path
        The path to the data file.
    _df : None | pd.DataFrame
        The data frame.
    _inconsistencies : dict
        The inconsistencies.

    Methods
    -------
    __init__(tid: str)
        Create a TEDataFile object.
    load()
        Checks if the data has been read in, if not reads the data.
    read()
        Reads the data from the data file.
        Checks if the data file contains no unknown columns.
        Inserts missing columns, reorders via reindexing and updates dtypes.
    write()
        Writes the data back to the data file.
    data
        Get the data.
    getInconsistencies()
        Get the inconsistencies.
    check(re: bool = True)
        Check the data for inconsistencies.
    checkRow(rowID: int, re: bool = True)
        Check the consistency of a single row.
    """
    # initialise
    def __init__(self, tid: str, path: None|Path = None):
        """ Create a TEDataFile object.
        
        Parameters
        ----------
        tid : str
            The technology ID.
        path : None | Path
            The path to the data file.
        """
        TEBase.__init__(self, tid)

        # initialise object fields
        self._path: Path = path or pathOfTEDFile(self._tid)
        self._df: None | pd.DataFrame = None
        self._inconsistencies: dict = {}


    # load TEDataFile (only if it has not been read yet)
    def load(self):
        """ Checks if the data has been read in, if not reads the data.

        Returns
        -------
        self
        """
        if self._df is None:
            self.read()


    # read TEDataFile from CSV file
    def read(self):
        """ Reads the data from the data file.
        Checks if the data file contains no unknown columns.
        Inserts missing columns, reorders via reindexing and updates dtypes.

        Returns
        -------
        None
        """
        # read CSV file
        self._df = pd.read_csv(
            self._path,
            dtype=self._getDtypeMapping(),
            sep=',',
            quotechar='"',
            encoding='utf-8',
        )

        # adjust row index to start at 1 instead of 0
        self._df.index += 1

        # make sure the file contains no unknown columns
        dataFormatColIDs = list(self._dataFormat.keys())
        for colID in self._df.columns:
            if colID not in dataFormatColIDs:
                raise Exception(f"Unknown column '{colID}' in file \"{self._path}\".")

        # insert missing columns and reorder via reindexing and update dtypes
        dfNew = self._df.reindex(columns=dataFormatColIDs)
        for col, dtype in self._getDtypeMapping().items():
            if col in self._df:
                continue
            dfNew[col] = dfNew[col].astype(dtype)
            dfNew[col] = np.nan
        self._df = dfNew


    # write TEDataFile to CSV file
    def write(self):
        """ Writes the data back to the data file.

        Returns
        -------
        None
        """
        self._df.to_csv(
            self._path,
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )


    # access dataframe
    @property
    def data(self) -> pd.DataFrame:
        """ Get the data.

        Returns
        -------
        pd.DataFrame
            The data frame.
        """
        return self._df


    # get data
    def getInconsistencies(self) -> dict:
        """ Get the inconsistencies.

        Returns
        -------
        dict
            The inconsistencies.
        """
        return self._inconsistencies


    # check that TEDataFile is consistent
    def check(self, re: bool = True):
        """ Check the data for inconsistencies.

        Parameters
        ----------
        re : bool, optional
            If TRUE, inconsistencies are checked, by default True

        Returns
        -------
        None
        """
        self._inconsistencies = {}

        # check row consistency for each row individually
        for rowID in self._df.index:
            self.checkRow(rowID, re=re)


    # check that row in TEDataFile is consistent
    def checkRow(self, rowID: int, re: bool = True):
        """ Check the consistency of a single row.

        Parameters
        ----------
        rowID : int
            The row ID
        re : bool, optional
            If TRUE, inconsistencies are checked, by default True

        Returns
        -------
        None
        """
        row = self._df.loc[rowID]
        self._inconsistencies[rowID] = checkRowConsistency(self._tid, row, re=re, rowID=rowID, filePath=self._path)
