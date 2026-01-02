from re import sub

import numpy as np
import pandas as pd
from numpy.linalg import solve

from units import Q, U

from ....map_variables import AbstractVariableMapper


class ActivitiesMapper(AbstractVariableMapper):
    def _prepare_warnings(self) -> dict[str, str]:
        return {
            "activities": "Cannot align activities on reference: " + self._reference_activity,
            "capacities": "Cannot align capacities on reference: " + self._reference_capacity,
            "tot_cap": "Cannot align total capacities on reference: " + self._reference_capacity,
        }

    def _prepare_units(self) -> None:
        if not (self._cond_capacity_change | self._cond_tot_capacity_change).any():
            return
        self._ref_cap_activity = sub(r"(Input|Output) Capacity", r"\1", self._reference_capacity)
        if self._ref_cap_activity not in self._units:
            return
        if self._reference_capacity not in self._units:
            self._units[self._reference_capacity] = self._units[self._ref_cap_activity] + "/year"

        self._conv_factor_cap = (Q(self._units[self._ref_cap_activity] + "/year")).to(self._units[self._reference_capacity]).m

    def _condition(self, selected: pd.DataFrame) -> pd.Series:
        self._cond_activity = pd.concat([
            selected["variable"].str.match(pattern)
            for pattern in self._activities
        ], axis=1).any(axis=1)
        self._cond_activity_change = (
            self._cond_activity &
            (selected["reference_variable"] != self._reference_activity)
        )

        self._cond_capacity = pd.concat([
            selected["variable"].str.match(pattern)
            for pattern in self._capacities
        ], axis=1).any(axis=1)
        self._cond_capacity_change = (
            self._cond_capacity &
            (selected["reference_variable"] != self._reference_capacity)
        )

        self._cond_tot_capacity = selected["variable"].str.match(r"Total (Input|Output) Capacity\|")
        self._cond_tot_capacity_change = (
            self._cond_tot_capacity &
            (selected["variable"] != ("Total " + self._reference_capacity))
        )

        return (
            self._cond_activity_change | self._cond_capacity_change | self._cond_tot_capacity_change
        )

    def _map(self,
             group: pd.DataFrame,
             cond: pd.Series) -> pd.DataFrame:

        cond_activity = self._cond_activity.loc[group.index]
        cond_capacity_change = self._cond_capacity_change.loc[group.index]
        cond_tot_capacity_change = self._cond_tot_capacity_change.loc[group.index]

        if not cond_activity.any():
            if cond_capacity_change.any():
                self._add_warning("capacities", cond_capacity_change)
            group.loc[cond, "value"] = np.nan
            return group

        df = group.loc[cond_activity]

        # All unique variables.
        cols = pd.concat([df["variable"], df["reference_variable"]]).unique()

        # Initialise matrix with zeroes.
        matrix = pd.DataFrame(0.0, index=df.index, columns=cols)

        # Fill values from activities.
        matrix.values[np.arange(len(df)), matrix.columns.get_indexer(df["variable"])] = -1.0
        matrix.values[np.arange(len(df)), matrix.columns.get_indexer(df["reference_variable"])] = df["value"].values

        # Add last row and inhomogeneity, which enforce that the reference activity equals to 1.0.
        last_row = pd.Series(0.0, index=cols)
        last_row[self._reference_activity] = 1.0
        inh = np.zeros(len(df)+1)
        inh[-1] = 1.0

        try:
            # Try to solve the linear system to give harmonised activities.
            harmonised_activities = solve(np.vstack([matrix, last_row]), inh)
        except:
            harmonised_activities = None
            self._add_warning("activities", cond)
            group.loc[cond_activity, "value"] = np.nan
        else:
            group.loc[cond_activity, "variable"] = df["variable"].where(df["variable"] != self._reference_activity, df["reference_variable"])
            group.loc[cond_activity, "reference_variable"] = self._reference_activity
            group.loc[cond_activity, "value"] = harmonised_activities[matrix.columns.get_indexer(group.loc[cond_activity, "variable"])]

        if cond_capacity_change.any() or cond_tot_capacity_change.any():
            if harmonised_activities is None or self._ref_cap_activity != self._reference_activity:
                last_row = pd.Series(0.0, index=cols)
                last_row[self._ref_cap_activity] = 1.0

                try:
                    harmonised_activities = solve(np.vstack([matrix, last_row]), inh)
                except:
                    cond_cap = cond_capacity_change | cond_tot_capacity_change
                    self._add_warning("capacities", cond_cap)
                    group.loc[cond_cap, "value"] = np.nan
                    return group

            if cond_capacity_change.any():
                cap_vars = group.loc[cond_capacity_change, "reference_variable"].rename("to")
                act_vars = cap_vars.str.replace(r"(Input|Output) Capacity", r"\1", regex=True).rename("from")
                a = harmonised_activities[matrix.columns.get_indexer(act_vars)]
                b = (
                    pd.concat([act_vars, cap_vars], axis=1)
                    .apply(lambda row: Q(self._units[row["from"]] + "/year").to(self._units[row["to"]]).m, axis=1)
                )
                c = self._conv_factor_cap
                group.loc[cond_capacity_change, "value"] /= a * b / c
                group.loc[cond_capacity_change, "reference_variable"] = self._reference_capacity

            if cond_tot_capacity_change.any():
                cap_vars = group.loc[cond_tot_capacity_change, "variable"].rename("to")
                act_vars = cap_vars.str.replace(r"Total (Input|Output) Capacity", r"\1", regex=True).rename("from")
                a = harmonised_activities[matrix.columns.get_indexer(act_vars)]
                b = (
                    pd.concat([act_vars, cap_vars], axis=1)
                    .apply(lambda row: Q(self._units[row["from"]] + "/year").to(self._units[row["to"]]).m, axis=1)
                )
                c = self._conv_factor_cap
                group.loc[cond_tot_capacity_change, "value"] *= a * b / c
                group.loc[cond_tot_capacity_change, "variable"] = "Total " + self._ref_cap_activity

        return group
