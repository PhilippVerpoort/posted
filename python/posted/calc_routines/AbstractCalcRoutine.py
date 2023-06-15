from abc import ABC, abstractmethod

import pandas as pd


class AbstractCalcRoutine(ABC):
    @abstractmethod
    def _calcColumn(self, oldType: str, oldCol: pd.Series):
        pass


    def calc(self, df: pd.DataFrame):
        newColumns = []

        typeLevel = df.columns.names.index('type')

        for colIndex in df:
            oldType = colIndex[typeLevel] if isinstance(colIndex, tuple) else colIndex
            oldCol = df[colIndex]

            newType, newCol = self._calcColumn(oldType, oldCol)
            if newType is None: continue

            # update column name
            if isinstance(colIndex, tuple):
                newColIndex = list(colIndex)
                newColIndex[typeLevel] = newType
                newCol.name = tuple(newColIndex)
            else:
                newCol.name = newType

            # append to list of new columns
            newColumns.append(newCol)

        # return
        return pd.concat(newColumns, axis=1)
