from typing import Union

import pandas as pd
import pint

from src.python.path import pathOfFile
from src.python.read.read_config import flowTypes


# define new registry
ureg = pint.UnitRegistry()


# load definitions
ureg.load_definitions(pathOfFile('src/python/units', 'definitions.txt'))


# check allowed dimensions for a flow type
def allowedFlowDims(flow_type: None | str):
    if flow_type != flow_type:
        allowed_dims = ['[currency]']
    else:
        flow_type_data = flowTypes[flow_type]

        allowed_dims = [str(ureg.Quantity(flow_type_data['default_unit']).dimensionality)] # default units dimension is always accepted
        if '[mass]' not in allowed_dims: # [mass] is always accepted as dimension
            allowed_dims += ['[mass]']

        if(flow_type_data['energycontent_LHV'] == flow_type_data['energycontent_LHV'] or \
           flow_type_data['energycontent_HHV'] == flow_type_data['energycontent_HHV']):
            if '[length] ** 2 * [mass] / [time] ** 2' not in allowed_dims:
                allowed_dims += ['[length] ** 2 * [mass] / [time] ** 2']

        if(flow_type_data['density_norm'] == flow_type_data['density_norm'] or \
            flow_type_data['density_std'] == flow_type_data['density_std']):
            allowed_dims += ['[volume]']
            allowed_dims += ['[length] ** 3']

    return allowed_dims


# convert units based on currency and flow type; test for exceptions, rethrow pint exceptions as own exceptions
switch_specs = {
    'LHV': [('energycontent', 'energycontent_LHV')],
    'HHV': [('energycontent', 'energycontent_HHV')],
    'norm': [('density', 'density_norm')],
    'standard': [('density', 'density_std')]
}


# get conversion factor between units, e.g. unit_from = "MWh;LHV" and unit_to = "m³;norm"
def convUnit(unit_from: str, unit_to: str, ft_specs: Union[dict, None]):
    # return None if unit_from is None
    if unit_from != unit_from: return unit_from

    # skip flow conversion if not flow type specs are provided
    if ft_specs is None:
        return ureg(f"1 {unit_from}").to(unit_to, 'curcon').magnitude

    # set convFlowKeys according to chosen specs
    __convFlowKeys = []
    for elem in [unit_from, unit_to]:
        elem_split = elem.split(";")
        if len(elem_split) > 1:
            __convFlowKeys += switch_specs[elem_split[1]]
            if elem == unit_from:
                unit_from = elem_split[0]
            else:
                unit_to = elem_split[0]
           
     # set defaults specs (LHV, norm) if not set in unit_from
    if switch_specs['LHV'] not in __convFlowKeys and switch_specs['HHV'] not in __convFlowKeys:
        __convFlowKeys += switch_specs['LHV']
    if switch_specs['norm'] not in __convFlowKeys and switch_specs['standard'] not in __convFlowKeys:
        __convFlowKeys += switch_specs['norm']

    # perform the actual conversion step
    return ureg(f"1 {unit_from}").to(unit_to, 'curcon', 'flocon', **{k[0]: ft_specs[k[1]] for k in __convFlowKeys}).magnitude


# vectorised versions
def convUnitDF(df: pd.DataFrame, unit_from_col: str, unit_to_col: str, ft_specs: dict = None):
    return df.apply(
        lambda row:
        convUnit(row[unit_from_col], row[unit_to_col], ft_specs or (flowTypes[row['flow_type']] if not pd.isnull(row['flow_type']) else None)),
        axis=1,
    )
