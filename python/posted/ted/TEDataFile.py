from pathlib import Path

import pandas as pd

from posted.path import pathOfTEDFile
from posted.ted.TEBase import TEBase
from posted.ted.inconsistencies import checkRowConsistency


class TEDataFile(TEBase):
    # initialise
    def __init__(self, tid: str, path: None|Path = None):
        TEBase.__init__(self, tid)

        # initialise object fields
        self._path: Path = path or pathOfTEDFile(self._tid)
        self._df: None | pd.DataFrame = None
        self._inconsistencies: dict = {}


    # load TEDataFile (only if it has not been read yet)
    def load(self):
        if self._df is None:
            self.read()


    # read TEDataFile from CSV file
    def read(self):
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

        # insert missing columns and reorder via reindexing
        self._df = self._df.reindex(columns=dataFormatColIDs)


    # write TEDataFile to CSV file
    def write(self):
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
        return self._df


    # get data
    def getInconsistencies(self) -> dict:
        return self._inconsistencies


    # check that TEDataFile is consistent
    def check(self, re: bool = True):
        self._inconsistencies = {}

        # check row consistency for each row individually
        for rowID in self._df.index:
            self.checkRow(rowID, re=re)


    # check that row in TEDataFile is consistent
    def checkRow(self, rowID: int, re: bool = True):
        row = self._df.loc[rowID]
        self._inconsistencies[rowID] = checkRowConsistency(self._tid, row, re=re, rowID=rowID, filePath=self._path)
