from re import sub

import pandas as pd

from units import Q

from ....map_variables import AbstractVariableMapper


class FixedOPEXSpecificMapper(AbstractVariableMapper):
    def _prepare_warnings(self) -> dict[str, str]:
        return {"no_ocf": "Cannot map `OPEX Fixed Specific` to `OPEX Fixed`, because `OCF` not found."}

    def _condition(self, selected: pd.DataFrame) -> pd.Series:
        return selected["variable"] == "OPEX Fixed Specific"

    def _prepare_units(self) -> None:
        if "OCF" not in self._units:
            return
        if "OPEX Fixed" not in self._units:
            self._units["OPEX Fixed"] = self._units["OPEX Fixed Specific"] + "/year"
        self._conv_factor = (
            (Q(self._units["OPEX Fixed Specific"] + "/year") / Q(self._units["OCF"]))
            .to(self._units["OPEX Fixed"]).m
        )

    def _map(self,
            group: pd.DataFrame,
            cond: pd.Series) -> pd.DataFrame:
        cond_ocf = group["variable"] == "OCF"
        if not cond_ocf.any():
            self._add_warning("no_ocf", cond)
            return group

        row_ocf = cond_ocf.idxmax()
        ocf_value = group.loc[row_ocf, "value"]
        ref_var = group.loc[cond, "reference_variable"].iloc[0]

        new_ref_var = sub('^(Input|Output)', r'\1 Capacity', ref_var)
        if new_ref_var not in self._units:
            self._units[new_ref_var] = self._units[ref_var] + "/year"

        ref_conv_factor = (
            (Q(self._units[ref_var] + "/year"))
            .to(self._units[new_ref_var]).m
        )

        group.loc[cond, "variable"] = "OPEX Fixed"
        group.loc[cond, "reference_variable"] = new_ref_var
        group.loc[cond, "value"] *= self._conv_factor / ref_conv_factor / ocf_value

        return group
