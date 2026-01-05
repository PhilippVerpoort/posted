import pandas as pd

from cet_units import Q

from posted.noslag.mapping import AbstractVariableMapper


class FullLoadHoursMapper(AbstractVariableMapper):
    def _condition(self) -> pd.Series:
        return self._df["variable"] == "FLH"

    def _prepare_units(self) -> None:
        if "OCF" not in self._units:
            self._units["OCF"] = "dimensionless"
        self._conv_factor: float = (
            (Q(self._units["FLH"]) / Q("year")).to(self._units["OCF"]).m
        )

    def _map(self, df: pd.DataFrame, cond: pd.Series) -> pd.DataFrame:
        df.loc[cond, "variable"] = "OCF"
        df.loc[cond, "value"] *= self._conv_factor

        return df
