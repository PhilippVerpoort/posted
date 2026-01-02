from abc import ABC, abstractmethod
from warnings import warn

# import importlib.util
# import sys
# from pathlib import Path
# from importlib import import_module
# from pkg_resources import iter_entry_points

import pandas as pd

from posted import POSTEDWarning


class AbstractVariableMapper(ABC):
    _selected: pd.DataFrame
    _units: dict[str, str]
    _cond: pd.Series
    _warning_types: dict[str, str] = {}
    _warnings: dict[str, list[pd.Series]] = {}


    def __init__(self,
                 selected: pd.DataFrame,
                 units: dict[str, str],
                 activities: list[str],
                 capacities: list[str],
                 reference_activity: str,
                 reference_capacity: str):
        self._selected = selected
        self._units = units
        self._activities = activities
        self._capacities = capacities
        self._reference_activity = reference_activity
        self._reference_capacity = reference_capacity

        self._cond = self._condition(selected)
        if not self._cond.any():
            return

        self._prepare_units()
        self._warning_types = self._prepare_warnings()
        self._warnings = {}

    @property
    def cond(self) -> pd.Series:
        return self._cond

    def _add_warning(self, warn_id: str, warn_loc: pd.Series) -> None:
        if warn_id not in self._warnings:
            self._warnings[warn_id] = [warn_loc]
        else:
            self._warnings[warn_id].append(warn_loc)

    def raise_warnings(self) -> None:
        for warn_id, warn_locs in self._warnings.items():
            locs = pd.concat(warn_locs)
            rows = self._selected.loc[locs.reindex(self._selected.index, fill_value=False)]
            warn(self._warning_types[warn_id] + "\n" + str(rows), POSTEDWarning)

    @abstractmethod
    def _condition(self, selected: pd.DataFrame) -> pd.Series:
        pass

    def _prepare_units(self) -> None:
        return

    def _prepare_warnings(self) -> dict[str, str]:
        return {}

    @abstractmethod
    def _map(self,
             group: pd.DataFrame,
             cond: pd.Series) -> pd.DataFrame:
        pass

    def map(self, group: pd.DataFrame) -> pd.DataFrame:
        group_cond = self._cond.loc[group.index]
        if not group_cond.any():
            return group

        mapped = self._map(group, group_cond)
        return mapped.where(group_cond, other=group)


def _apply_mappers(group: pd.DataFrame, mappers: list[AbstractVariableMapper]) -> pd.DataFrame:
    orig_index = group.index.copy()
    ret = group
    for mapper in mappers:
        ret = mapper.map(ret)
        if not ret.index.equals(orig_index):
            raise Exception("Index mistmatch.")
    return ret


def map_variables(selected: pd.DataFrame,
                  units: dict[str,str],
                  fields: list[str],
                  activities: list[str],
                  capacities: list[str],
                  reference_activity: str,
                  reference_capacity: str):

    # Arguments for creating mapper instances.
    kwargs = dict(
        selected=selected,
        units=units,
        activities=activities,
        capacities=capacities,
        reference_activity=reference_activity,
        reference_capacity=reference_capacity,
    )

    # Get mappers.
    from .database.variables.mappings.full_load_hours import FullLoadHoursMapper
    from .database.variables.mappings.fixed_opex_relative import FixedOPEXRelativeMapper
    from .database.variables.mappings.fixed_opex_specific import FixedOPEXSpecificMapper
    from .database.variables.mappings.activities import ActivitiesMapper

    mappers = [
        FullLoadHoursMapper(**kwargs),
        FixedOPEXRelativeMapper(**kwargs),
        FixedOPEXSpecificMapper(**kwargs),
        ActivitiesMapper(**kwargs),
    ]

    # Map variables.
    mapped = (
        selected
        .groupby(fields)[["variable", "reference_variable", "value"]]
        .apply(
            _apply_mappers,
            mappers=mappers,
        )
        .reset_index(level=fields)
    )

    # Raise warnings.
    for mapper in mappers:
        mapper.raise_warnings()

    return mapped, units


# var_mappings: list[AbstractVariableMapping] = []
# for entry_point in iter_entry_points(group='your_package.plugins'):
#     module = import_module(entry_point.module_name)
#     main_function = getattr(module, entry_point.attrs[0])
#     var_mappings.append(main_function)
#
#
#
#
# def import_module_from_path(module_name, module_path):
#     """
#     Import a module from a given path.
#
#     Args:
#         module_name (str): The name to give to the imported module.
#         module_path (str or Path): The path to the module file.
#
#     Returns:
#         module: The imported module.
#     """
#     # Convert the path to a Path object if it isn't already
#     module_path = Path(module_path) if not isinstance(module_path, Path) else module_path
#
#     # Create a module spec from the file location
#     spec = importlib.util.spec_from_file_location(module_name, module_path)
#
#     # Create a new module based on that spec
#     module = importlib.util.module_from_spec(spec)
#
#     # Add the module to the sys.modules dictionary so it can be imported
#     # by other modules that import it and by modules imported by it
#     sys.modules[module_name] = module
#
#     # Execute the module to load its contents
#     spec.loader.exec_module(module)
#
#     return module
#
# def load_var_mappings()
#
# # Example usage
# module_path = Path('/path/to/your/module.py')
# module = import_module_from_path('module_name', module_path)
#
# # Now you can use the module
# print(module.some_function())
