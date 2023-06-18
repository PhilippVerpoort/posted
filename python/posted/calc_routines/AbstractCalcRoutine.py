from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
import pint_pandas
from sigfig import round

from posted.calc_routines.MissingAssumptionsException import MissingAssumptionsException


class AbstractCalcRoutine(ABC):
    def __init__(self, part: str):
        self._part = part

    @property
    def part(self):
        return self._part

    @abstractmethod
    def _calcColumn(self, oldType: str, oldCol: pd.Series):
        pass


    def calc(self, df: pd.DataFrame, unit: None | str = None, raise_missing: bool = True):
        # determin the type column level
        typeLevel = df.columns.names.index('type')

        # loop over columns in dataframe values
        newColumns = []
        missingCols = []
        for colIndex in df:
            oldType = colIndex[typeLevel] if isinstance(colIndex, tuple) else colIndex
            oldCol = df[colIndex]

            try:
                r = self._calcColumn(oldType, oldCol)
                if r is None:
                    continue
                else:
                    newType, newCol = r
            except MissingAssumptionsException as ex:
                if raise_missing:
                    raise ex
                missingCols.append(colIndex)
                continue

            # update column name
            if isinstance(colIndex, tuple):
                newColIndex = list(colIndex)
                newColIndex[typeLevel] = newType
                newCol.name = tuple(newColIndex)
            else:
                newCol.name = newType

            # append to list of new columns
            newColumns.append(newCol)

        result = pd.concat(newColumns, axis=1)

        # add multicolumn layer names
        result.columns.names = df.columns.names

        # reduce units
        result = result.apply(lambda col: col.pint.to(unit) if unit is not None else col.pint.to_reduced_units())

        # round values
        roundVec = np.vectorize(lambda scalar: round(scalar, sigfigs=4, warn=False) if scalar==scalar else scalar)
        for colName in result.columns:
            result[colName] = pint_pandas.PintArray(roundVec(result[colName].values.quantity.m), dtype=result[colName].dtype)

        # return
        return result, missingCols
