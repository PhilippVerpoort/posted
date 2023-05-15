from pathlib import Path

import numpy as np
import pandas as pd
from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.python.read.file_read import readTEDFile, saveTEDFile
from src.python.read.read_config import techs, dataFormat, mapColnamesDtypes, flowTypes, techClasses


class PGTableModel(QtCore.QAbstractTableModel):
    def __init__(self, tid: str, path: Path, parent=None, *args):
        # call super constructor
        super(PGTableModel, self).__init__(parent, *args)

        # add local variables
        self._tid: str = tid
        self._path: Path = path
        self._data: None | pd.DataFrame = None
        self._viewConsistency: bool = True
        self._viewColumns: dict = {colID: True for colID in dataFormat}
        self._colIDList = list(self._viewColumns.keys())


    # load data
    def load(self):
        self._data = readTEDFile(self._path, mapColnamesDtypes)
        self.layoutChanged.emit()


    # save data
    def save(self):
        saveTEDFile(self._path, self._data)


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
            value = self._data.loc[rowID, colID]
            return value if value is not np.nan else ''
        elif role == Qt.ForegroundRole:
            return QColor(Qt.black) if self._isEditable(colID) else QColor(Qt.gray)
        elif role == Qt.BackgroundRole:
            if not self._isEditable(colID):
                return QColor(239, 239, 239)
            elif self._viewConsistency and not self._checkValue(rowID, colID):
                return QColor(255, 239, 239)
            else:
                return QColor(Qt.white)


    def rowCount(self, index):
        return len(self._data) if self._data is not None else 0


    def columnCount(self, index):
        return sum(1 for colID in dataFormat if self._viewColumns[colID])


    def headerData(self, index, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            colID = self._colIDList[index]
            return dataFormat[colID]['name']
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return f"{index+1}"


    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.EditRole:
            return False

        if value == '':
            value = np.nan

        row, colID = self._getIndices(index)
        dtype = mapColnamesDtypes[colID]
        if dtype == 'category':
            if value not in self._data[colID].cat.categories:
                self._data[colID] = self._data[colID].cat.add_categories([value])
            self._data.loc[row, colID] = value
            self._data[colID] = self._data[colID].cat.remove_unused_categories()
        elif dtype == 'float':
            self._data.loc[row, colID] = float(value)
        elif dtype == 'str':
            self._data.loc[row, colID] = value
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
        rowID = index.row()
        colID = self._colIDList[index.column()]

        return rowID, colID


    def _isEditable(self, colID):
        if colID == 'subtech' and 'subtechs' not in techs[self._tid]:
            return False
        if colID == 'mode' and 'modes' not in techs[self._tid]:
            return False
        return True


    def _checkValue(self, rowID: int, colID: str):
        val = self._data.loc[rowID, colID]

        # type should be an allowed value specified in the respective technology class specs
        if colID == 'type' and val not in techClasses[techs[self._tid]['class']]['entry_types']:
            return False

        # subtech and mode should be an allowed value specified in the respective technology specs
        if val is not np.nan:
            if colID == 'subtech':
                if val not in techs[self._tid]['subtechs']:
                    return False

            if colID == 'mode':
                if val not in techs[self._tid]['modes']:
                    return False

        # flow type should be a valid flowid for energy and feedstock demand types or otherwise empty
        if colID == 'flow_type':
            if self._data.loc[rowID, 'type'] in ['energy_dem', 'feedstock_dem']:
                if val not in flowTypes:
                    return False
            else:
                if val is not np.nan:
                    return False

        return True


