from typing import Union

import pandas as pd
import pint

from src.python.path import pathOfFile
from src.python.read.read_config import flowTypes


# define new registry
ureg = pint.UnitRegistry()


# load definitions
ureg.load_definitions(pathOfFile('src/python/units', 'definitions.txt'))


# convert units based on currency and flow type
__convFlowKeys = ('energycontent', 'density')
def convUnit(unit_from: str, unit_to: str, ft_specs: Union[dict, None]):
    if unit_from != unit_from: return unit_from
    if ft_specs is not None:
        return ureg(f"1 {unit_from}").to(unit_to, 'curcon', 'flocon', **{k: ft_specs[k] for k in __convFlowKeys}).magnitude
    else:
        return ureg(f"1 {unit_from}").to(unit_to, 'curcon').magnitude


# vectorised versions
def convUnitDF(df: pd.DataFrame, unit_from_col: str, unit_to_col: str, ft_specs: dict = None):
    return df.apply(
        lambda row:
        convUnit(row[unit_from_col], row[unit_to_col], ft_specs or (flowTypes[row['flow_type']] if not pd.isnull(row['flow_type']) else None)),
        axis=1,
    )
