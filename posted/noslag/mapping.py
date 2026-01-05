from abc import ABC, abstractmethod
from importlib.util import spec_from_file_location, module_from_spec
from warnings import warn

import pandas as pd

from posted import POSTEDWarning, databases


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

    def raise_warnings(self, selected: pd.DataFrame) -> None:
        for warn_id, warn_locs in self._warnings.items():
            locs = pd.concat(warn_locs)
            rows = selected.loc[
                locs.reindex(selected.index, fill_value=False)
            ]
            rows = rows[[c for c in rows if c not in self._df]].join(self._df)
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
    database_id: str,
    mappings: list[str],
):
    # GroupBy once.
    if fields:
        groups = (
            selected
            .groupby(fields, sort=False)
            .indices
            .values()
        )
    else:
        groups = [selected.index]

    # Arguments for creating mapper instances.
    kwargs = dict(
        groups=groups,
        units=units,
        activities=activities,
        capacities=capacities,
        reference_activity=reference_activity,
        reference_capacity=reference_capacity,
    )

    # Load mappers.
    mapper_classes = _load_mappings(database_id, mappings)

    # Loop over mappers.
    orig_index = selected.index.copy()
    df = selected[["variable", "reference_variable", "value"]]
    for mapper_cls in mapper_classes:
        mapper = mapper_cls(df=df, **kwargs)
        df = mapper.map()
        mapper.raise_warnings(selected)
        if not df.index.equals(orig_index):
            raise Exception("Index mismatch.")

    # Combine with fields.
    df = selected[[c for c in selected if c not in df]].join(df)

    return df, units


def _load_mappings(
        database_id: str,
        mappings: list[str],
    ) -> list[type[AbstractVariableMapper]]:
    mappings_dir_path = databases[database_id] / "variables" / "mappings"
    ret = []

    for mapping in mappings:
        mapping_path = mappings_dir_path / f"{mapping}.py"
        if not mapping_path.is_file():
            raise FileNotFoundError(f"Mapping {mapping} could not be found.")

        spec = spec_from_file_location(mapping, mapping_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        ret_file = []
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if (isinstance(attribute, type) and
                issubclass(attribute, AbstractVariableMapper) and
                attribute != AbstractVariableMapper and
                attribute != AbstractVariableGroupMapper):
                ret_file.append(attribute)

        if not ret_file:
            raise ValueError(f"No valid mapper defined in {mapping}.py")
        elif len(ret_file) > 2:
            raise ValueError(f"More than one mapper defined in {mapping}.py")

        ret.extend(ret_file)

    return ret
