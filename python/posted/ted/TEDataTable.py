import pandas as pd

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine
from posted.config.config import techClasses
from posted.units.units import ureg, convUnit


allowedKeepTokens = ['', 'off', 'value', 'assump']


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


    def assume(self, assump: pd.DataFrame | dict, inplace: bool = False):
        if isinstance(assump, pd.DataFrame):
            # ensure all indexes have names
            if any(n is None and assump.index.get_level_values(n).nunique() > 1 for n in assump.index.names):
                raise Exception(f"Assumption indexes need to have names or contain only one value. Found index: {assump.index}")

            # add part 'assump' as top column level if not present
            if 'part' in assump.columns.names:
                parts = assump.index.unique(level='part')
                if len(parts) > 1 or 'assump' not in parts:
                    raise Exception(f"Assumption columns should either not contain the part level or only contain part 'assump'. Found: {parts}")
            else:
                assump = pd.concat([assump], keys=['assump'], names=['part'], axis=1)

            # reorder column levels
            assump = assump.reorder_levels(self._df.columns.names, axis=1)

            # drop existing assumptions that will be overwritten
            dfNew = self._df.drop(columns=[c for c in self._df if c in assump.columns])

            # determine indexes
            leftIndexes = self._df.index.names
            rightIndexes = assump.index.names
            commonIndexes = [n for n in leftIndexes if n in rightIndexes]
            allIndexes = list(set(leftIndexes+rightIndexes))

            # merge datatable with assumptions
            mergeMode = dict(on=commonIndexes, how='outer') if commonIndexes else dict(how='cross')
            dfNew = pd.merge(dfNew.reset_index(), assump.reset_index(), **mergeMode).set_index(allIndexes)
        elif isinstance(assump, dict):
            dfNew = self._df if inplace else self._df.copy()
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

        # update existing instance (inplace) or return new datatable (not inplace)
        if inplace:
            self._df = dfNew
        else:
            return TEDataTable(
                data=dfNew,
                refQuantity=self.refQuantity,
                refFlow=self.refFlow,
                name=self.name,
            )


    # calculate levelised cost of X
    def calc(self, *routines, assump: None | pd.DataFrame | dict = None, unit: None | str = None,
             keep: str = 'off', inplace: bool = False) -> 'TEDataTable':
        # add assumptions to dataframe if provided
        if assump is not None:
            r = self.assume(assump=assump, inplace=inplace)
            df = self._df if inplace else r.data
        else:
            df = self._df

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
