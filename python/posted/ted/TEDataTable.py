import numpy as np
import pandas as pd
import pint_pandas
from sigfig import round

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine
from posted.config.config import techClasses
from posted.units.units import ureg, convUnit


class TEDataTable:
    # initialise
    def __init__(self, data: pd.DataFrame, refQuantity: ureg.Quantity, refFlow: None | str, name: None | str):
        self._df: pd.DataFrame = data
        self._refQuantity: ureg.Quantity = refQuantity
        self._refFlow: str = refFlow
        self._name: None | str = name


    # access dataframe
    @property
    def data(self) -> pd.DataFrame:
        return self._df


    # access reference flowtype
    @property
    def refFlow(self) -> str:
        return self._refFlow


    # access reference flow dimension
    @property
    def refQuantity(self) -> ureg.Quantity:
        return self._refQuantity


    # access name
    @property
    def name(self) -> None | str:
        return self._name


    # set name
    def setName(self, name: str):
        self._name = name


    # entry types with assuming a reference
    @property
    def refTypes(self):
        entryTypes = techClasses['conversion']['entry_types']
        return [typeid for typeid in entryTypes if 'ref_dim' in entryTypes[typeid]]


    # rescale content of table to new reference quantity
    def rescale(self, refQuantityNew: ureg.Quantity, inplace: bool = False):
        factor = refQuantityNew.m \
               / self._refQuantity.m \
               * convUnit(str(self._refQuantity.u), str(refQuantityNew.m), self._refFlow)

        colsRef = [c for c in self.data.columns if c in self.refTypes]

        if inplace:
            self._refQuantity = refQuantityNew
            self._df[colsRef] *= factor
            return self
        else:
            dfNew = self._df.copy()
            dfNew[colsRef] *= factor
            return TEDataTable(
                dfNew,
                refQuantityNew,
                self._refFlow,
                self._name,
            )


    # calculate levelised cost of X
    def calc(self, routine: AbstractCalcRoutine, unit: None | str = None) -> pd.DataFrame:
        # call calc routine
        results = routine.calc(self._df)

        # add multicolumn layer names
        results.columns.names = self._df.columns.names

        # adjust units
        results = results.apply(lambda col: col.pint.to(unit) if unit is not None else col.pint.to_reduced_units())

        # round values
        roundVec = np.vectorize(lambda scalar: round(scalar, sigfigs=4, warn=False) if scalar==scalar else scalar)
        for colName in results.columns:
            results[colName] = pint_pandas.PintArray(roundVec(results[colName].values.quantity.m), dtype=results[colName].dtype)

        # return
        return results
