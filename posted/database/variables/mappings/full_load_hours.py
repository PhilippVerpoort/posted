import pandas as pd

from units import Q

from ....map_variables import AbstractVariableMapper


class FullLoadHoursMapper(AbstractVariableMapper):
    _conv_factor: float

    def _prepare_units(self) -> None:
        if "FLH" not in self._units:
            return
        if "OCF" not in self._units:
            self._units["OCF"] = "dimensionless"
        self._conv_factor = (
            (Q(self._units["FLH"]) / Q("year")).to(self._units["OCF"]).m
        )

    def _condition(self, selected: pd.DataFrame) -> pd.Series:
        return selected["variable"] == "FLH"

    def _map(self, group: pd.DataFrame, cond: pd.Series) -> pd.DataFrame:
        group.loc[cond, "variable"] = "OCF"
        group.loc[cond, "value"] *= self._conv_factor

        return group
