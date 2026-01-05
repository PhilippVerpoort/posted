import pandas as pd

from cet_units import Q

from posted.noslag.mapping import AbstractVariableGroupMapper


class FixedOPEXRelativeMapper(AbstractVariableGroupMapper):
    _warning_types = {
        "no_capex": "Cannot map `OPEX Fixed Relative` to `OPEX Fixed`, "
                    "because `CAPEX` not found.",
    }

    def _condition(self) -> pd.Series:
        return self._df["variable"] == "OPEX Fixed Relative"

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

    def _map(self, group: pd.DataFrame, cond_group: pd.Series) -> pd.DataFrame:
        cond_capex = group["variable"] == "CAPEX"
        if not cond_capex.any():
            self._add_warning("no_capex", cond_group)
            return group

        row_capex = cond_capex.idxmax()
        capex_value = group.loc[row_capex, "value"]
        ref_var = group.loc[row_capex, "reference_variable"]

        group.loc[cond_group, "variable"] = "OPEX Fixed"
        group.loc[cond_group, "reference_variable"] = ref_var
        group.loc[cond_group, "value"] *= capex_value * self._conv_factor

        return group
