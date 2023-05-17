from pathlib import Path

import numpy as np
import pandas as pd
from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.python.read.read_config import techs, dataFormat, mapColnamesDtypes, flowTypes, techClasses
from src.python.ted.TEDataFile import TEDataFile


class PGTableModel(QtCore.QAbstractTableModel):
    def __init__(self, tid: str, path: Path, parent=None, *args):
        # call super constructor
        super(PGTableModel, self).__init__(parent, *args)

        # add local variables
        self._tid: str = tid
        self._path: Path = path
        self._dataFile: TEDataFile = TEDataFile(tid, path)
        self._viewConsistency: bool = True
        self._viewColumns: dict = {colID: True for colID in dataFormat}
        self._colIDList = list(self._viewColumns.keys())

        # add local triggers
        self.dataChanged.connect(self._updateCheck)


    # load data
    def load(self):
        # read in TEDataFile
        self._dataFile.read()

        # initially check
        self._initCheck()

        # emit layout changed trigger
        self.layoutChanged.emit()


    # save data
    def save(self):
        # write TEDataFile to CSV text file
        self._dataFile.write()


    # get data from TEDataFile object
    @property
    def _data(self) -> pd.DataFrame:
        return self._dataFile.getData()


    # get inconsistencies from TEDataFile object
    @property
    def _incons(self) -> dict:
        return self._dataFile.getInconsistencies()


    # initially check
    def _initCheck(self):
        # check for inconsistencies without raising exceptions
        try:
            self._dataFile.check(re=False)
        except:
            pass


    # update consistency checks after data changed
    def _updateCheck(self, topLeft, bottomRight):
        for index in range(topLeft.row(), bottomRight.row()+1, 1):
            rowID = self._data.index[index]
            try:
                self._dataFile.checkRow(rowID, re=False)
            except:
                pass


    # toggle view of cell consistency
    def toggleViewConsistency(self):
        self._viewConsistency = not self._viewConsistency


    # toggle view of column
    def toggleViewColumn(self, colID):
        self._viewColumns[colID] = not self._viewColumns[colID]
        self._colIDList = list(colID for colID in dataFormat if self._viewColumns[colID])
        self.layoutChanged.emit()


    # abstract method implementations
    def data(self, index, role):
        rowID, colID = self._getIndices(index)

        if (role == Qt.DisplayRole) | (role == Qt.EditRole):
            cell = self._data.loc[rowID, colID]
            return cell if cell is not np.nan else ''
        elif role == Qt.ForegroundRole:
            return QColor(Qt.black) if self._isEditable(colID) else QColor(Qt.gray)
        elif role == Qt.BackgroundRole:
            if not self._isEditable(colID):
                return QColor(239, 239, 239)
            elif self._viewConsistency and self._checkValue(rowID, colID):
                return QColor(255, 239, 239)
            else:
                return QColor(Qt.white)
        # elif role == Qt.ToolTipRole:
        #     if self._viewConsistency:
        #         check = self._checkValue(rowID, colID)
        #         if check is not None:
        #             return check



    def rowCount(self, index):
        return len(self._data) if self._data is not None else 0


    def columnCount(self, index):
        return sum(1 for colID in dataFormat if self._viewColumns[colID])


    def headerData(self, index, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            colID = self._colIDList[index]
            return dataFormat[colID]['name']
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self._data.iloc[index].index


    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.EditRole:
            return False

        if value == '':
            value = np.nan

        rowID, colID = self._getIndices(index)
        dtype = mapColnamesDtypes[colID]
        if dtype == 'category':
            if value not in self._data[colID].cat.categories and value is not np.nan:
                self._data[colID] = self._data[colID].cat.add_categories([value])
            self._data.loc[rowID, colID] = value
            self._data[colID] = self._data[colID].cat.remove_unused_categories()
        elif dtype == 'float':
            self._data.loc[rowID, colID] = float(value)
        elif dtype == 'str':
            self._data.loc[rowID, colID] = value
        else:
            raise Exception(f"Unknown dtype {dtype}.")

        self.dataChanged.emit(index, index)

        return False


    def flags(self, index):
        rowID, colID = self._getIndices(index)

        if self._isEditable(colID):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable


    def _getIndices(self, index):
        rowID = self._data.index[index.row()]
        colID = self._colIDList[index.column()]

        return rowID, colID


    def _isEditable(self, colID):
        if colID == 'subtech' and 'subtechs' not in techs[self._tid]:
            return False
        if colID == 'mode' and 'modes' not in techs[self._tid]:
            return False
        return True


    def _checkValue(self, rowID: int, colID: str):
        if (rowID not in self._incons) or not self._incons[rowID]:
            return None

        for ex in self._incons[rowID]:
            if ex.colID is None or ex.colID == colID:
                return ex.message
