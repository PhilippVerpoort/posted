from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
import pint_pandas
from sigfig import round


class AbstractCalcRoutine(ABC):
    def __init__(self, df: pd.DataFrame):
        self._df = df

    @property
    @abstractmethod
    def part(self):
        pass

    def calc(self, unit: None | str = None, raise_missing: bool = True):
        if self._df.columns.nlevels > 1:
            grouped = self._df.groupby(by=[c for c in self._df.columns.names if c != 'type'], axis=1)

            newCols = []
            missingCols = []
            for idx, group in grouped:
                old = group.droplevel(level=[l for l in group.columns.names if l != 'type'], axis=1)
                new, missing = self._calc(old)

                if missing:
                    if raise_missing:
                        raise Exception(f"Missing data for calculations: " + ' '.join([f"No {', '.join(val)} for {key}." for key, val in missing.items()]))
                    else:
                        missingCols.extend(missing)

                multiColProd = list([[x] for x in idx])
                multiColProd.insert(group.columns.names.index('type'), new.columns)
                new.columns = pd.MultiIndex.from_product(multiColProd)
                new.columns.names = group.columns.names

                newCols.append(new)
            result = pd.concat(newCols, axis=1)
        else:
            result, missingCols = self._calc(self._df)

        # reduce units
        result = result.apply(lambda col: col.pint.to(unit) if unit is not None else col.pint.to_reduced_units())

        # round values
        roundVec = np.vectorize(lambda scalar: round(scalar, sigfigs=4, warn=False) if scalar==scalar else scalar)
        for colName in result.columns:
            result[colName] = pint_pandas.PintArray(roundVec(result[colName].values.quantity.m), dtype=result[colName].dtype)

        # return
        return result, missingCols

    @abstractmethod
    def _calc(cls, df: pd.DataFrame) -> (pd.DataFrame, dict):
        pass

    def _has(self, required: list, df: pd.DataFrame, missing: dict):
        if required[0] not in df:
            missing[required[0]] = True
            return False
        else:
            m = [c for c in required[1:] if c not in df]
            if m:
                missing[required[0]] = m
                return False
            else:
                return True
