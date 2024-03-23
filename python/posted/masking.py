from typing import Callable

import numpy as np
import pandas as pd

from posted.path import databases
from posted.read import read_yml_file


MaskCondition = str | dict | Callable


def apply_cond(df: pd.DataFrame, cond: MaskCondition):
    if isinstance(cond, str):
        return df.eval(cond)
    elif isinstance(cond, dict):
        cond = ' & '.join([f"{key}=='{val}'" for key, val in cond.items()])
        return df.eval(cond)
    elif isinstance(cond, Callable):
        return df.apply(cond)


class Mask:
    def __init__(self,
                 where: MaskCondition | list[MaskCondition] = None,
                 use: MaskCondition | list[MaskCondition] = None,
                 weight: None | float | str | list[float | str] = None,
                 other: float = np.nan,
                 comment: str = ''):
        # set fields from constructor arguments
        self._where: list[MaskCondition] = [] if where is None else where if isinstance(where, list) else [where]
        self._use: list[MaskCondition] = [] if use is None else use if isinstance(use, list) else [use]
        self._weight: list[float] = (
            None
            if weight is None else
            [float(w) for w in weight]
            if isinstance(weight, list) else
            [float(weight)]
        )
        self._other: float = other
        self._comment: str = comment

        # perform consistency checks on fields
        if self._use and self._weight and len(self._use) != len(self._weight):
            raise Exception(f"Must provide same length of 'use' conditions as 'weight' values.")

        # set default weight to 1 if not set otherwise
        if not self._weight:
            self._weight = len(self._use) * [1.0]

    # check if a mask matches a dataframe (all 'when' conditions match across all rows)
    def matches(self, df: pd.DataFrame):
        for w in self._where:
            if not apply_cond(df, w).all():
                return False
        return True

    # return a dataframe with weights applied
    def get_weights(self, df: pd.DataFrame):
        ret = pd.Series(index=df.index, data=np.nan)

        # apply weights where the use condition matches
        for u, w in zip(self._use, self._weight):
            ret.loc[apply_cond(df, u)] = w

        # return
        return ret


def read_masks(variable: str):
    ret: list[Mask] = []

    for database_id in databases:
        fpath = databases[database_id] / 'masks' / ('/'.join(variable.split('|')) + '.yml')
        if fpath.exists():
            if not fpath.is_file():
                raise Exception(f"Expected YAML file, but not a file: {fpath}")

            ret += [
                Mask(**mask_specs)
                for mask_specs in read_yml_file(fpath)
            ]

    return ret
