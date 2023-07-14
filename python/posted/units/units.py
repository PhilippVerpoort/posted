from pathlib import Path

import pandas as pd
import pint
import pint_pandas
import re

from posted.path import pathOfFile
from posted.config.config import flowTypes


# define new registry
ureg = pint.UnitRegistry()
pint_pandas.PintType.ureg = ureg


# display format
ureg.Unit.default_format = "~P"
pint_pandas.PintType.ureg.default_format = "~P"


# load definitions
ureg.load_definitions(pathOfFile(Path(__file__).parent, 'definitions.txt'))

def simplifyUnit(unit: str) -> str:
    # replace currency manually with UnitContainer object, because manually added dimensions are not recognized by ureg
    unit = unit.replace('[currency]', 'ureg("USD")')

    # replace every dimension in unit with UnitContainer object of base unit of dimension
    unit = re.sub(r'\[([^\d\W]+)\]', r'(ureg.get_base_units(list(ureg.get_compatible_units("[\1]"))[0])[1])', unit)
    # evaluate unit
    unit = eval('1 * ' + unit)

    # convert unit to reduced units: this simplifies the unit
    unit_red = unit.to_reduced_units()
    # get dimensionality of reduced unit
    unit_dim = str(ureg.Quantity(unit_red).dimensionality)
    return unit_dim

# check allowed dimensions for a flow type
def allowedFlowDims(flow_type: None | str):
    if flow_type != flow_type:
        allowed_dims = ['[currency]']
    else:
        flow_type_data = flowTypes[flow_type]

        allowed_dims = [str(ureg.Quantity(flow_type_data['default_unit']).dimensionality)] # default units dimension is always accepted

        if(flow_type_data['energycontent_LHV'] == flow_type_data['energycontent_LHV'] or \
           flow_type_data['energycontent_HHV'] == flow_type_data['energycontent_HHV']):
            if '[length] ** 2 * [mass] / [time] ** 2' not in allowed_dims:
                allowed_dims += ['[length] ** 2 * [mass] / [time] ** 2']
            if '[mass]' not in allowed_dims: # [mass] is always accepted when there is a energydensity
                allowed_dims += ['[mass]']

        if(flow_type_data['density_norm'] == flow_type_data['density_norm'] or \
            flow_type_data['density_std'] == flow_type_data['density_std']):
            allowed_dims += ['[volume]']
            allowed_dims += ['[length] ** 3']
            if '[mass]' not in allowed_dims: # [mass] is always accepted when there is a energydensity
                allowed_dims += ['[mass]']

    return allowed_dims


# convert units based on currency and flow type; test for exceptions, rethrow pint exceptions as own exceptions
switch_specs = {
    'LHV': [('energycontent', 'energycontent_LHV')],
    'HHV': [('energycontent', 'energycontent_HHV')],
    'norm': [('density', 'density_norm')],
    'standard': [('density', 'density_std')]
}


# get conversion factor between units, e.g. unit_from = "MWh;LHV" and unit_to = "m³;norm"
def convUnit(unit_from: str | float, unit_to: str | float, flow_type: None | str = None):
    # return None if unit_from is None
    if unit_from != unit_from: return unit_from

    # skip flow conversion if not flow type specs are provided
    if flow_type is None:
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
    #print(switch_specs['LHV'])
    #print(switch_specs['HHV'] not in __convFlowKeys)
    if switch_specs['LHV'][0] not in __convFlowKeys and switch_specs['HHV'][0] not in __convFlowKeys:
        __convFlowKeys += switch_specs['LHV']
    if switch_specs['norm'][0] not in __convFlowKeys and switch_specs['standard'][0] not in __convFlowKeys:
        __convFlowKeys += switch_specs['norm']

    # perform the actual conversion step
    ft_specs = flowTypes[flow_type]
    return ureg(f"1 {unit_from}").to(unit_to, 'curcon', 'flocon', **{k[0]: ft_specs[k[1]] for k in __convFlowKeys}).magnitude


# vectorised versions
def convUnitDF(df: pd.DataFrame, unit_from_col: str, unit_to_col: str, flow_type: None | str = None):
    return df.apply(
        lambda row:
        convUnit(row[unit_from_col], row[unit_to_col], flow_type or (row['flow_type'] if not pd.isnull(row['flow_type']) else None)),
        axis=1,
    )
