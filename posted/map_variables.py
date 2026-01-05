from abc import ABC, abstractmethod
from warnings import warn

import pandas as pd

from posted import POSTEDWarning


class AbstractVariableMapper(ABC):
    _df: pd.DataFrame
    _group: list[pd.Series]
    _units: dict[str, str]
    _cond: pd.Series
    _warning_types: dict[str, str] = {}
    _warnings: dict[str, list[pd.Series]] = {}

    def __init__(
        self,
        df: pd.DataFrame,
        groups: list[pd.Series],
        units: dict[str, str],
        activities: list[str],
        capacities: list[str],
        reference_activity: str,
        reference_capacity: str,
    ):
        self._df = df
        self._groups = groups
        self._units = units
        self._activities = activities
        self._capacities = capacities
        self._reference_activity = reference_activity
        self._reference_capacity = reference_capacity

        self._warnings = {}

    def _add_warning(self, warn_id: str, warn_loc: pd.Series) -> None:
        if warn_id not in self._warnings:
            self._warnings[warn_id] = [warn_loc]
        else:
            self._warnings[warn_id].append(warn_loc)

    def raise_warnings(self) -> None:
        for warn_id, warn_locs in self._warnings.items():
            locs = pd.concat(warn_locs)
            rows = self._df.loc[
                locs.reindex(self._df.index, fill_value=False)
            ]
            warn(
                self._warning_types[warn_id] + "\n" + str(rows),
                POSTEDWarning,
            )

    @abstractmethod
    def _condition(self) -> pd.Series:
        pass

    def _prepare_units(self) -> None:
        return

    @abstractmethod
    def _map(self, df: pd.DataFrame, cond: pd.Series) -> pd.DataFrame:
        pass

    def map(self) -> pd.DataFrame:
        cond = self._condition()
        if not cond.any():
            return self._df
        self._prepare_units()
        mapped = self._map(self._df.copy(), cond)
        return mapped.where(cond, other=self._df)


class AbstractVariableGroupMapper(AbstractVariableMapper):
    @abstractmethod
    def _map(self, group: pd.DataFrame, cond_group: pd.Series) -> pd.DataFrame:
        pass

    def map(self) -> pd.DataFrame:
        cond = self._condition()
        if not cond.any():
            return self._df
        self._prepare_units()
        df = self._df.copy()
        for idx in self._groups:
            group_cond = cond.loc[idx]
            if not group_cond.any():
                continue
            df.loc[idx] = self._map(df.loc[idx], group_cond)
        return df.where(cond, other=self._df)


def map_variables(
    selected: pd.DataFrame,
    units: dict[str, str],
    fields: list[str],
    activities: list[str],
    capacities: list[str],
    reference_activity: str,
    reference_capacity: str,
):
    # GroupBy once.
    groups = (
        selected
        .groupby(fields, sort=False)
        .indices
        .values()
    )

    # Arguments for creating mapper instances.
    kwargs = dict(
        groups=groups,
        units=units,
        activities=activities,
        capacities=capacities,
        reference_activity=reference_activity,
        reference_capacity=reference_capacity,
    )

    # Get mappers.
    from .database.variables.mappings.full_load_hours import (
        FullLoadHoursMapper
    )
    from .database.variables.mappings.fixed_opex_relative import (
        FixedOPEXRelativeMapper
    )
    from .database.variables.mappings.fixed_opex_specific import (
        FixedOPEXSpecificMapper
    )
    from posted.database.variables.mappings.capacities_to_activities import (
        CapacitiesToActivities
    )
    from .database.variables.mappings.activities import ActivitiesMapper

    mapper_classes = [
        FullLoadHoursMapper,
        FixedOPEXRelativeMapper,
        FixedOPEXSpecificMapper,
        CapacitiesToActivities,
        ActivitiesMapper,
    ]

    # Loop over mappers.
    orig_index = selected.index.copy()
    df = selected[["variable", "reference_variable", "value"]]
    for mapper_cls in mapper_classes:
        mapper = mapper_cls(df=df, **kwargs)
        df = mapper.map()
        mapper.raise_warnings()
        if not df.index.equals(orig_index):
            raise Exception("Index mismatch.")

    # Combine with fields.
    df = selected[[c for c in selected if c not in df]].join(df)

    return df, units
