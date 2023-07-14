from typing import Callable

import numpy as np
import pandas as pd


MaskCondition = str | dict | Callable

def applyCond(df: pd.DataFrame, cond: MaskCondition):
    if isinstance(cond, str):
        return df.eval(cond)
    elif isinstance(cond, dict):
        cond = ' & '.join([f"{key}=='{val}'" for key, val in cond.items()])
        return df.eval(cond)
    elif isinstance(cond, Callable):
        return df.apply(cond)

class Mask:
    def __init__(self,
                 when: MaskCondition | list[MaskCondition] = None,
                 use: MaskCondition | list[MaskCondition] = None,
                 weight: None | float | list[float] = None,
                 other: float = np.nan):
        # set fields from constructor arguments
        self._when: list[MaskCondition] = [] if when is None else when if isinstance(when, list) else [when]
        self._use: list[MaskCondition] = [] if use is None else use if isinstance(use, list) else [use]
        self._weight: list[float] = weight if isinstance(weight, list) or weight is None else [weight]
        self._other = other

        # perform consistency checks on fields
        if use and weight is not None and len(use) != len(weight):
            raise Exception(f"Must provide same length of 'use' conditions as 'weight' values.")

        # set default weight to 1 if not set otherwise
        if use and self._weight is None:
            self._weight = len(self._use) * [1.0]

    # check if a mask matches a dataframe (all 'when' conditions match across all rows)
    def matches(self, df: pd.DataFrame):
        for w in self._when:
            if not applyCond(df, w).all():
                return False
        return True

    # return a dataframe with weights applied
    def applyWeights(self, df: pd.DataFrame):
        # set default weight for all rows
        ret = df.assign(weight=self._other)

        # apply weights where the use condition matches
        for u, w in zip(self._use, self._weight):
            ret.loc[applyCond(df, u), 'weight'] = w

        # drop all rows with weights equal to nan
        ret.dropna(subset='weight', inplace=True)

        # apply weight
        ret['value'] *= ret['weight']
        ret.drop(columns='weight', inplace=True)

        # return
        return ret
