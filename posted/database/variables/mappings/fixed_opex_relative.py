import pandas as pd

from units import Q

from ....map_variables import AbstractVariableMapper


class FixedOPEXRelativeMapper(AbstractVariableMapper):
    def _prepare_warnings(self) -> dict[str, str]:
        return {
            "no_capex": "Cannot map `OPEX Fixed Relative` to `OPEX Fixed`, "
                        "because `CAPEX` not found.",
        }

    def _prepare_units(self) -> None:
        if "CAPEX" not in self._units:
            return
        if "OPEX Fixed" not in self._units:
            self._units["OPEX Fixed"] = self._units["CAPEX"] + "/year"
        self._conv_factor = (
            (
                Q(self._units["OPEX Fixed Relative"])
                * Q(self._units["CAPEX"] + "/year")
            )
            .to(self._units["OPEX Fixed"])
            .m
        )

    def _condition(self, selected: pd.DataFrame) -> pd.Series:
        return selected["variable"] == "OPEX Fixed Relative"

    def _map(self, group: pd.DataFrame, cond: pd.Series) -> pd.DataFrame:
        cond_capex = group["variable"] == "CAPEX"
        if not cond_capex.any():
            self._add_warning("no_capex", cond)
            return group

        row_capex = cond_capex.idxmax()
        capex_value = group.loc[row_capex, "value"]
        ref_var = group.loc[row_capex, "reference_variable"]

        group.loc[cond, "variable"] = "OPEX Fixed"
        group.loc[cond, "reference_variable"] = ref_var
        group.loc[cond, "value"] *= capex_value * self._conv_factor

        return group
