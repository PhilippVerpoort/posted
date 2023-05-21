import copy
from pathlib import Path

import pandas as pd

from src.python.path import pathOfTEDFile
from src.python.config.config import flowTypes, techs, mapColnamesDtypes
from src.python.ted.inconsistencies import checkRowConsistency


class TEDataFile:
    # initialise
    def __init__(self, tid: str, path: None|Path = None):
        self._tid: str = tid
        self._tspecs: dict = copy.deepcopy(techs[tid])
        self._path: Path = path or pathOfTEDFile(self._tid)
        self._data: None | pd.DataFrame = None
        self._inconsistencies: dict = {}


    # load TEDataFile (only if it has not been read yet)
    def load(self):
        if self._data is None:
            self.read()


    # read TEDataFile from CSV file
    def read(self):
        # read CSV file
        self._data = pd.read_csv(
            self._path,
            dtype=mapColnamesDtypes,
            sep=',',
            quotechar='"',
            encoding='utf-8',
        )

        # adjust row index to start at 1 instead of 0
        self._data.index += 1

        # make sure the file contains no unknown columns
        dataFormatColIDs = list(mapColnamesDtypes.keys())
        for colID in self._data.columns:
            if colID not in dataFormatColIDs:
                raise Exception(f"Unknown column '{colID}' in file \"{self._path}\".")

        # insert missing columns and reorder via reindexing
        self._data = self._data.reindex(columns=dataFormatColIDs)


    # write TEDataFile to CSV file
    def write(self):
        self._data.to_csv(
            self._path,
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )


    # get data
    def getData(self) -> pd.DataFrame:
        return self._data


    # get data
    def getInconsistencies(self) -> dict:
        return self._inconsistencies


    # check that TEDataFile is consistent
    def check(self, re: bool = True):
        self._inconsistencies = {}

        # check row consistency for each row individually
        for rowID in self._data.index:
            self.checkRow(rowID, re=re)


    # check that row in TEDataFile is consistent
    def checkRow(self, rowID: int, re: bool = True):
        row = self._data.loc[rowID]
        self._inconsistencies[rowID] = checkRowConsistency(self._tid, row, re=re, rowID=rowID, filePath=self._path)
