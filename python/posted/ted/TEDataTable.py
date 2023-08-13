import pandas as pd
import pint

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine
from posted.config.config import techClasses
from posted.units.units import ureg, convUnit
from posted.utils import utils


allowedKeepTokens = ['', 'off', 'value', 'assump']

class TEDataTable:
    # initialise
    def __init__(self, data: pd.DataFrame, refQuantity: ureg.Quantity, refFlow: None | str, name: None | str):
        self._df: pd.DataFrame = data
        self._refQuantity: ureg.Quantity = refQuantity
        self._refFlow: str = refFlow
        self._name: None | str = name


    # get and set dataframe and define property data
    def get_data(self) -> pd.DataFrame:
        return self._df
    def set_data(self, data: pd.DataFrame):
        self._df = data
    data = property(get_data, set_data)


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


    def assume(self, assump: pd.DataFrame | dict):
        if isinstance(assump, pd.DataFrame):
            # ensure all indexes have names
            if any((n is None and assump.index.get_level_values(n).nunique() > 1) for n in assump.index.names):
                raise Exception(f"Assumption indexes need to have names or contain only one value. Found index: {assump.index}")

            # add part 'assump' as top column level if not present
            if 'part' in assump.columns.names:
                parts = assump.index.unique(level='part')
                if len(parts) > 1 or 'assump' not in parts:
                    raise Exception(f"Assumption columns should either not contain the part level or only contain part 'assump'. Found: {parts}")
            else:
                assump = pd.concat([assump], keys=['assump'], names=['part'], axis=1)

            # stack column levels not present in assumptions
            stackLevels = [n for n in self._df.columns.names if n not in assump.columns.names]
            if stackLevels:
                dfNew = self._df.stack(stackLevels)
                while None in dfNew.index.names:
                    dfNew = dfNew.droplevel(None)
            else:
                dfNew = self._df

            # reorder column levels
            assump = assump.reorder_levels(dfNew.columns.names, axis=1)

            # drop existing assumptions that will be overwritten
            dfNew = dfNew.drop(columns=[c for c in self._df if c in assump.columns])

            # merge datatable with assumptions
            dfNew = utils.fullMerge(dfNew, assump)

            # unstack stacked columns levels
            if stackLevels:
                dfNew = dfNew.unstack(stackLevels, fill_value=0.0)
                if isinstance(dfNew, pd.Series):
                    dfNew = dfNew.to_frame().T
        elif isinstance(assump, dict):
            dfNew = self._df.copy()
            tlev = dfNew['value'].columns.names.index('type')
            for col in assump:
                if dfNew['value'].columns.nlevels > 1:
                    cols = [list(c) for c in dfNew['value'].columns.unique().to_list()]
                    for c in cols:
                        c[tlev] = col
                    cols = list(set(tuple(['assump'] + c) for c in cols))
                    dfNew[cols] = assump[col]
                else:
                    dfNew['assump', col] = assump[col]
        else:
            raise Exception(f"Assumptions have to be of type pd.DataFrame or dict. Received: {type(assump)}")

        # fix pint unit types in dataframe
        for col in dfNew:
            dfNew[col] = dfNew[col].astype(f"pint[{dfNew[col].iloc[0].u if isinstance(dfNew[col].iloc[0], pint.Quantity) else 'dimensionless'}]")

        # update existing instance (inplace) or return new datatable (not inplace)
        return TEDataTable(
            data=dfNew,
            refQuantity=self.refQuantity,
            refFlow=self.refFlow,
            name=self.name,
        )


    # calculate levelised cost of X
    def calc(self, *routines, unit: None | str = None, keep: str = 'off', inplace: bool = False) -> 'TEDataTable':
        df = self._df if inplace else self._df.copy()

        # combine values and assumptions into dataframe for calculations and override values with assumptions
        calcCols = [('assump', *c) if isinstance(c, tuple) else ('assump', c) for c in df['assump']] \
                 + [('value', *c) if isinstance(c, tuple) else ('value', c) for c in df['value'] if c not in df['assump']]
        dfCalc = df[calcCols].droplevel(level='part', axis=1)

        # loop over routines provided
        results = []
        keepValues = []
        for routine in routines:
            if not issubclass(routine, AbstractCalcRoutine):
                raise Exception('All calc routines provided have to be subclass of AbstractCalcRoutine.')
            result, missingCols = routine(dfCalc).calc(unit=unit, raise_missing=False)
            results.append(
                pd.concat([result], keys=[routine.part], names=['part'], axis=1)
            )

        # combine results with existing dataframe
        dfNew = pd.concat([self._df if inplace else self._df.copy()] + results, axis=1)

        # keep columns
        keepTokens = keep.split('+')
        if not all(t in allowedKeepTokens for t in keepTokens):
            raise Exception(f"Keyword keep has to be a string containing a '+' separated list of keep tokens."
                            f"Allowed tokens: {allowedKeepTokens}. Found: {keepTokens}")
        if 'value' not in keepTokens:
            dfNew = dfNew.loc[:, dfNew.columns.get_level_values('part') !='value']
        if 'assump' not in keepTokens:
            dfNew = dfNew.loc[:, dfNew.columns.get_level_values('part') !='assump']

        # return
        if inplace:
            self._df = dfNew
        else:
            return TEDataTable(
                data=dfNew,
                refQuantity=self.refQuantity,
                refFlow=self.refFlow,
                name=self.name,
            )
