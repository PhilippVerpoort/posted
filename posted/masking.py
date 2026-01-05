from typing import Callable

import numpy as np
import pandas as pd


MaskCondition = str | dict | Callable


def apply_cond(df: pd.DataFrame, cond: MaskCondition):
    """
    Takes a pandas DataFrame and a condition, which can be a string,
    dictionary, or callable, and applies the condition to the DataFrame
    using `eval` or `apply` accordingly.

    Parameters
    ----------
    df : pd.DataFrame
        A pandas DataFrame containing the data on which the condition
        will be applied.
    cond : MaskCondition
        The condition to be applied on the dataframe. Can be either a
        string, a dictionary, or a callable function.

    Returns
    -------
        pd.DataFrame
            Dataframe evaluated at the mask condition
    """
    if isinstance(cond, str):
        return df.eval(cond)
    elif isinstance(cond, dict):
        cond = " & ".join([f"{key}=='{val}'" for key, val in cond.items()])
        return df.eval(cond)
    elif isinstance(cond, Callable):
        return df.apply(cond)


class Mask:
    """
    Class to define masks with conditions and weights to apply to
    DataFiles

    Parameters
    ----------
    where: MaskCondition | list[MaskCondition], optional
        Where the mask should be applied
    use:  MaskCondition | list[MaskCondition], optional
        Condition on where to use the masks
    weight: None | float | str | list[float | str], optional
        Weights to apply
    other: float, optional

    comment: str, optional
            Comment
    """

    def __init__(
        self,
        where: MaskCondition | list[MaskCondition] = None,
        use: MaskCondition | list[MaskCondition] = None,
        weight: None | float | str | list[float | str] = None,
        other: float = np.nan,
        comment: str = "",
    ):
        """Set fields from constructor arguments, perform consistency
        checks on fields, set default weight to 1 if not set
        otherwise"""
        self._where: list[MaskCondition] = (
            []
            if where is None
            else where
            if isinstance(where, list)
            else [where]
        )
        self._use: list[MaskCondition] = (
            [] if use is None else use if isinstance(use, list) else [use]
        )
        self._weight: list[float] = (
            None
            if weight is None
            else [float(w) for w in weight]
            if isinstance(weight, list)
            else [float(weight)]
        )
        self._other: float = other
        self._comment: str = comment

        # perform consistency checks on fields
        if self._use and self._weight and len(self._use) != len(self._weight):
            raise Exception(
                f"Must provide same length of 'use' conditions as "
                f"'weight' values."
            )

        # set default weight to 1 if not set otherwise
        if not self._weight:
            self._weight = len(self._use) * [1.0]

    def matches(self, df: pd.DataFrame):
        """
        Check if a mask matches a dataframe (all 'where' conditions match
        across all rows)

        Parameters
        ----------
        df: pd.Dataframe
            Dataframe to check for matches
        Returns
        -------
            bool
                If the mask matches the dataframe
        """
        for w in self._where:
            if not apply_cond(df, w).all():
                return False
        return True

    def get_weights(self, df: pd.DataFrame):
        """
        Apply weights to the dataframe

        Parameters
        ----------
        df: pd.Dataframe
            Dataframe to apply weights on

        Returns
        -------
            pd.DataFrame
                Dataframe with applied weights
        """
        ret = pd.Series(index=df.index, data=self._other)

        # apply weights where the use condition matches
        for u, w in zip(self._use, self._weight):
            ret.loc[apply_cond(df, u)] = w

        return ret
