import pandas as pd

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
    def calc(self, *routines, unit: None | str = None, keep: str = 'off') -> 'TEDataTable':
        # determine if the data table has different parts (values, costs, ghgis, etc)
        hasParts: bool = (self._df.columns.names[0] == 'part')

        # loop over routines provided
        results = {}
        keepCols = []
        for routine in routines:
            if not isinstance(routine, AbstractCalcRoutine):
                raise Exception('All calc routines provided have to be subclass of AbstractCalcRoutine.')
            df = self._df['value'] if hasParts else self._df
            result, missingCols = routine.calc(
                df=df,
                unit=unit,
                raise_missing=(keep!='missing'),
            )
            results[routine.part] = result
            keepCols.extend(missingCols)

        # keep columns
        if keep == 'off':
            data = None
        elif keep in ['missing', 'all']:
            if hasParts:
                data = self._df
            else:
                data = pd.concat([self._df], keys=['value'], names=['part'], axis=1)
            if keep=='missing':
                data = data[[(('value',) + c) for c in keepCols]]
        else:
            raise Exception(f"Illegal value for argument keep: {keep}")
        for part, result in results.items():
            add = pd.concat([result], keys=[part], names=['part'], axis=1)
            if data is None:
                data = add
            else:
                data = data.merge(add, left_index=True, right_index=True)

        # return
        return TEDataTable(
            data=data,
            refQuantity=self.refQuantity,
            refFlow=self.refFlow,
            name=self.name,
        )
