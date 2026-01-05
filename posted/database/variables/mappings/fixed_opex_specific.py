from re import sub

import pandas as pd

from cet_units import Q

from posted.noslag.mapping import AbstractVariableGroupMapper


class FixedOPEXSpecificMapper(AbstractVariableGroupMapper):
    _warning_types = {
        "no_ocf": "No entry for `OCF` found when mapping `OPEX Fixed Specific` "
                  "to `OPEX Fixed`. Assuming OCF of 100%.",
        "multi": "Multiple `OCF` entries for one case. Assuming OCF of 100%."
    }

    def _condition(self) -> pd.Series:
        return self._df["variable"] == "OPEX Fixed Specific"

    def _prepare_units(self) -> None:
        # Derive a suitable unit if none is given.
        if "OPEX Fixed" not in self._units:
            self._units["OPEX Fixed"] = (
                self._units["OPEX Fixed Specific"] + "/year"
            )

        # Determine conversion factor from old to new unit.
        self._conv_factor = (
            Q(self._units["OPEX Fixed Specific"] + "/year")
            .to(self._units["OPEX Fixed"])
            .m
        )

        # Account for unit of OCF if it exists.
        if "OCF" in self._units:
            self._conv_factor_ocf = Q(self._units["OCF"]).to("dimensionless")

    def _map(self, group: pd.DataFrame, group_cond: pd.Series) -> pd.DataFrame:
        # Determine if OCF variable is present.
        cond_ocf = group["variable"] == "OCF"
        nr = cond_ocf.sum()

        if nr != 1:
            # If too few or too many entries for OCF found, warn and use 100%.
            self._add_warning("multi" if nr else "no_ocf", group_cond)
            ocf_value = 1.0
        else:
            # Otherwise use OCF value and unit.
            row_ocf = cond_ocf.idxmax()
            ocf_value = group.loc[row_ocf, "value"] * self._conv_factor_ocf

        # Determine new reference variable and corresponding conversion factor.
        ref_var = group.loc[group_cond, "reference_variable"].iloc[0]

        new_ref_var = sub("^(Input|Output)", r"\1 Capacity", ref_var)
        if new_ref_var not in self._units:
            self._units[new_ref_var] = self._units[ref_var] + "/year"

        ref_conv_factor = (
            Q(self._units[ref_var] + "/year")
            .to(self._units[new_ref_var])
            .m
        )

        # Apply all.
        group.loc[group_cond, "variable"] = "OPEX Fixed"
        group.loc[group_cond, "reference_variable"] = new_ref_var
        group.loc[group_cond, "value"] *= (
            self._conv_factor / ref_conv_factor / ocf_value
        )

        return group
