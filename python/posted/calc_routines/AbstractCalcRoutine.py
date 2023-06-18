from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
import pint_pandas
from sigfig import round


class AbstractCalcRoutine(ABC):
    @abstractmethod
    def _calcColumn(self, oldType: str, oldCol: pd.Series):
        pass


    def calc(self, df: pd.DataFrame, unit: None | str = None):
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

        results = pd.concat(newColumns, axis=1)

        # add multicolumn layer names
        results.columns.names = df.columns.names

        # reduce units
        results = results.apply(lambda col: col.pint.to(unit) if unit is not None else col.pint.to_reduced_units())

        # round values
        roundVec = np.vectorize(lambda scalar: round(scalar, sigfigs=4, warn=False) if scalar==scalar else scalar)
        for colName in results.columns:
            results[colName] = pint_pandas.PintArray(roundVec(results[colName].values.quantity.m), dtype=results[colName].dtype)

        # return
        return results
