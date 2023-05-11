from typing import Union

import pandas as pd
import pint

from src.python.path import pathOfFile
from src.python.read.read_config import flowTypes


# define new registry
ureg = pint.UnitRegistry()


# load definitions
ureg.load_definitions(pathOfFile('src/python/units', 'definitions.txt'))


# convert units based on currency and flow type; test for exceptions, rethrow pint exceptions as own exceptions
switch_specs={
        'LHV': [('energycontent','energycontent_LHV')],
        'HHV':  [('energycontent','energycontent_HHV')],
        'norm': [('density','density_norm')],
        'standard': [('density','density_std')]
        }

def convUnit(unit_from: str, unit_to: str, ft_specs: Union[dict, None]): # unit_to = "MWh;LHV", Nm³ := "m³;norm"
    if unit_from != unit_from: return unit_from
    __convFlowKeys =[]

    # set convFlowKeys according to chosen specs
    for elem in [unit_from, unit_to]:
        elem_split = elem.split(";")
        if len(elem_split) > 1:
            __convFlowKeys += switch_specs[elem_split[1]]
            if elem == unit_from:
                unit_from = elem_split[0]
            else:
                unit_to = elem_split[0]
           
     # set defaults (low, norm) specs if not set in unit param
    if switch_specs['LHV'] not in __convFlowKeys and switch_specs['HHV'] not in __convFlowKeys:
        __convFlowKeys += switch_specs['LHV']
    if switch_specs['norm'] not in __convFlowKeys and switch_specs['standard'] not in __convFlowKeys:
        __convFlowKeys += switch_specs['norm']

    if ft_specs is not None:
        return ureg(f"1 {unit_from}").to(unit_to, 'curcon', 'flocon', **{k[0]: ft_specs[k[1]] for k in __convFlowKeys}).magnitude
    else:
        return ureg(f"1 {unit_from}").to(unit_to, 'curcon').magnitude


# vectorised versions
def convUnitDF(df: pd.DataFrame, unit_from_col: str, unit_to_col: str, ft_specs: dict = None):
    return df.apply(
        lambda row:
        convUnit(row[unit_from_col], row[unit_to_col], ft_specs or (flowTypes[row['flow_type']] if not pd.isnull(row['flow_type']) else None)),
        axis=1,
    )
