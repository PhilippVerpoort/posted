import copy
import re
from pathlib import Path

import numpy as np
import pandas as pd

import pint

from src.python.path import pathOfTEDFile
from src.python.read.file_read import readTEDFile
from src.python.read.read_config import techs, dataFormats, flowTypes, defaultUnits, defaultMasks, techClasses
from src.python.units.units import convUnitDF, ureg
from src.python.ted.exceptions import ConsistencyException


class TEDataSet:
    # initialise
    def __init__(self, tid: str):
        self._tid = tid
        self._tspecs = copy.deepcopy(techs[tid])
        self._dataset: None|pd.DataFrame = None

        # determine default reference units of entry types from technology class
        self._refFlowType = flowTypes[self._tspecs['primary']]
        self._repUnitsDef = {}
        for typeid in self._tspecs['entry_types']:
            refUnit = self._tspecs['entry_types'][typeid]['ref_dim']
            units = defaultUnits | {'flow': self._refFlowType['default_unit']}
            for d, u in units.items():
                refUnit = re.sub(d, u, refUnit)
            self._repUnitsDef[typeid] = refUnit

        # override with default reference unit of specific technology
        if 'default-ref-units' in self._tspecs:
            self._repUnitsDef |= self._tspecs['default-ref-units']


    # loading data and performing basic initial processing
    def load(self, *load_other, load_default: bool = True, to_default_units: bool = True):
        self._loadPaths = [Path(p) for p in load_other] + ([pathOfTEDFile(self._tid)] if load_default else [])

        if not self._loadPaths:
            raise Exception(f"No TED files to load for technology '{self._tid}'.")

        # read TED data from CSV files
        mapColnamesDtypes = {
            colname: colspecs['dtype']
            for colname, colspecs in dataFormats.items()
        }
        self._dataset = pd.concat([
            readTEDFile(p, mapColnamesDtypes)
            for p in self._loadPaths
        ])

        # check that the TED is consistent
        self.__checkConsistency()

        # insert missing periods
        self.__insertMissingPeriods()

        # apply references to values and units
        self.__normaliseUnits()

        # convert values to default units
        if to_default_units:
            self.convertUnits()

        return self


     # check allowed dimensions for a flow type
    def __allowed_flow_dims(self,flow_type):
        if flow_type != flow_type: 
            allowed_dims = ['[currency]']
        else:
            
            flow_type_data = flowTypes[flow_type]

            allowed_dims = [str(ureg.Quantity(flow_type_data["default_unit"]).dimensionality)] # defualt units dimension is always accepted
            if '[mass]' not in allowed_dims: # [mass] is always accepted as dimension
                allowed_dims += ['[mass]']

            if(flow_type_data["energycontent_LHV"] == flow_type_data["energycontent_LHV"] or \
               flow_type_data["energycontent_HHV"] == flow_type_data["energycontent_HHV"]):
                if '[length] ** 2 * [mass] / [time] ** 2' not in allowed_dims:
                    allowed_dims += ['[length] ** 2 * [mass] / [time] ** 2']

            if(flow_type_data["density_norm"] == flow_type_data["density_norm"] or \
                flow_type_data["density_std"] == flow_type_data["density_std"]):
                allowed_dims += ['[volume]']
                allowed_dims += ['[length] ** 3']
        return allowed_dims

    # check bat dataframe is consistent
    def __checkConsistency(self):

        # check if subtechs and modes in data match defined categories
        for col in [('subtech', 'subtechs'), ('mode', 'modes')]:
            if col[1] in techs[self._tid]:
                for index,row in self._dataset[[col[0]]].iterrows():
                    row = row[col[0]]
                    if row not in techs[self._tid][col[1]]:

                        # NaNs in subtech are accepted; only real values can violate consistency here
                        if row == row:
                            raise ConsistencyException("invalid " + col[0] + ": " + row , index+1, self._tid + ".csv")
                            
            else:
                if not self._dataset[col[0]].isna().all():
                    raise ConsistencyException(col[0] + " should be empty, but the column contains values",0, self._tid + ".csv")
        
        # check if types match with defined entry types
        for index,row in self._dataset[['type']].iterrows():
            row = row['type']
            if row not in techClasses['conversion']['entry_types']:
                raise ConsistencyException("invalid entry type: " + row ,index+1, self._tid + ".csv")
        
        # check if reported unit and reference unit match with unit category of entry type and with flow type

        switch_unit_dimensions={
        'currency': '[currency]',
        'dimensionless':  'dimensionless',
        'time': '[time]'
        # 'flow' is defined in __allowed_flow_dims
        }
    
        # check for both ref_unit and rep_unit
        for col in [('reported_unit', 'rep_dim'), ('reference_unit', 'ref_dim')]:
            # iterrate over dataset to determine exact location of possible inconsistencies
            for index, row in self._dataset[['type','flow_type',col[0]]].iterrows():
                unit_type = techClasses['conversion']['entry_types'][row['type']][col[1]]

                # --- The following determines the allowed dimensions based on the entry_type.
                # Depending on the type of entry_type different dimensions and their combinations are added to the dimensions variable.
                dimension = []
                formula = unit_type.split("/")
                if len(formula) > 1: # unit_type is a composite of two dimensions
                    if(formula[0] == "flow"): # if flow is the dimension, the flow_type has to be checked
                        dims_enum = self.__allowed_flow_dims(row["flow_type"])
                    else:
                        dims_enum = switch_unit_dimensions[formula[0]]
                    if(formula[1] == "flow"): # if flow is the dimension, the flow_type has to be checked
                        dims_denom = self.__allowed_flow_dims(row["flow_type"])
                    else:
                        dims_denom = switch_unit_dimensions[formula[1]]

                    if type(dims_enum) is list or type(dims_denom) is list: # one of the dimensions is quivalent to a list of dimensions
                        if type(dims_enum) is list: # the first dimension is quivalent to a list of dimensions, iteration is needed
                            for elem_enum in dims_enum:
                                if type(dims_denom) is list: # the second dimension is quivalent to a list of dimensions as well,iteration is needed
                                    for elem_denom in dims_denom:
                                        dimension += [elem_enum + " / " + elem_denom]
                                else: # the second dimension is not quivalent to a list of dimensions
                                    dimension += [elem_enum + " / " + dims_denom]
                        else: # the first dimension is not quivalent to a list of dimensions
                            if type(dims_denom) is list: # the second dimension is quivalent to a list of dimensions, iteration is needed
                                for elem_denom in dims_denom:
                                    dimension += [dims_enum + " / " + elem_denom]
                            else: # the second dimension is not quivalent to a list of dimensions
                                dimension += [dims_enum + " / " + dims_denom]
                    else:
                        dimension = [dims_enum + " / " + dims_denom]
                else: # unit_type is a single dimension
                    if(unit_type == "flow"): # if flow is the dimension, the flow_type has to be checked
                        allowed_dims = self.__allowed_flow_dims(row["flow_type"])
                    else:
                        allowed_dims = switch_unit_dimensions[unit_type]

                    if type(allowed_dims) is list:
                        for dim in allowed_dims:
                            dimension += [dim]
                    else:
                        dimension = switch_unit_dimensions[unit_type]
                
                # --- The dimensions variable is now set to all allowed dimensions for this row

                if row[col[0]] == row[col[0]]:
                    unit_to_check = row[col[0]]

                    # check if unit is connected to a variant (LHV, HHV, norm or standard)
                    unit_splitted = unit_to_check.split(";")
                    if (len(unit_splitted) > 1): # the unit is connected to a variant
                        unit_identifier = unit_splitted[0]
                        unit_variant = unit_splitted[1]

                        if unit_identifier not in ureg:
                            raise ConsistencyException("invalid " + col[0] + " : " + unit_identifier + " is not a valid unit" ,index+1, self._tid + ".csv")
                        elif (str(ureg.Quantity(unit_identifier).dimensionality) in ['[length] ** 3']): # unit is of dimension volume
                            if unit_variant not in ["norm", "standard"]: # only ["norm", "standard"] variants are allowed for volume
                               raise ConsistencyException("invalid " + col[0] + " variant: " + unit_variant + " is not a valid variant of " + unit_identifier ,index+1, self._tid + ".csv")
                        elif (str(ureg.Quantity(unit_identifier).dimensionality) in ['[length] ** 2 * [mass] / [time] ** 2']): # unit is of type energy
                            if unit_variant not in ["LHV", "HHV"]: # only ["LHV", "HHV"] variants are allowed for volume
                               raise ConsistencyException("invalid " + col[0] + " variant: " + unit_variant + " is not a valid variant of " + unit_identifier ,index+1, self._tid + ".csv")
                        else: # unit is nether volume nor energy: inconsistency because there shouldnt be a variant connected
                            raise ConsistencyException("invalid " + col[0] + ": variants for unit " + unit_identifier + " are not allowed" ,index+1, self._tid + ".csv")
                        
                        unit_to_check = unit_identifier # set unit variable to proceed with consistency checks

                    if unit_to_check not in ureg or str(ureg.Quantity(unit_to_check).dimensionality) not in dimension:
                        raise ConsistencyException("invalid " + col[0] + ": " + unit_to_check + " is not of type " + unit_type ,index+1, self._tid + ".csv")
                else:
                    # only reported unit has to be non NaN
                    if(col[0] == "reported_unit"):
                        raise ConsistencyException("invalid reported_unit: NaN value" ,index+1, self._tid + ".csv")
            
        # TODO: check reported units match dataFormats['bat']

        # TODO: check reference units match techs[techid]

        # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
        # TODO: implement those types so we don't need to remove them
        dropTypes = ['flh', 'lifetime', 'energy_eff']
        self._dataset = self._dataset.query(f"not type.isin({dropTypes})").reset_index(drop=True)

        # replace Nm³/Sm³ with m³
        # TODO: implement these units in the unit registry. Same for LHV and HHV.
        self._dataset['reported_unit'] = self._dataset['reported_unit'].replace('(Nm³|Sm³)', 'm³', regex=True)


    # insert missing periods
    def __insertMissingPeriods(self):
        self._dataset.fillna({'period': 2023}, inplace=True)


    # apply references to values and units
    def __normaliseUnits(self):
        # default reference value is 1.0
        self._dataset['reference_value'].fillna(1.0, inplace=True)

        # add default reference unit conversion factor
        self._dataset['reference_unit_default'] = self._dataset['type'].map(self._repUnitsDef).astype(str)
        self._dataset['reference_unit_factor'] = np.where(
            self._dataset['reference_unit'].notna(),
            convUnitDF(self._dataset, 'reference_unit', 'reference_unit_default', self._refFlowType),
            1.0,
        )

        # set non-unit conversion factor to 1.0 if not set otherwise
        self._dataset['conv_factor'].fillna(1.0, inplace=True)

        # set converted value and unit
        self._dataset.insert(7, 'value',
            self._dataset['reported_value'] \
          / self._dataset['reference_value'] \
          / self._dataset['reference_unit_factor'] \
          * self._dataset['conv_factor']
        )
        self._dataset.insert(8, 'unc',
            self._dataset['reported_unc'] \
          / self._dataset['reference_value'] \
          / self._dataset['reference_unit_factor'] \
          * self._dataset['conv_factor']
        )
        self._dataset.insert(9, 'unit', self._dataset['reported_unit'])

        # drop old unit and value columns
        self._dataset.drop(
            self._dataset.filter(regex=r"^(reported|reference)_(value|unc|unit).*$").columns.to_list() + ['conv_factor'],
            axis=1,
            inplace=True,
        )


    # convert values to defined units (use defaults if non provided)
    def convertUnits(self, type_units=None, flow_units=None):
        if flow_units is None:
            flow_units = {}
        if type_units is None:
            type_units = {}

        # get default units
        repUnitsDef = []
        for typeid in self._dataset['type'].unique():
            repUnit = self._tspecs['entry_types'][typeid]['rep_dim']
            for d, u in defaultUnits.items():
                repUnit = re.sub(d, u, repUnit)
            if 'flow' not in repUnit:
                repUnitsDef.append({'type': typeid, 'unit_convert': repUnit})
            else:
                for flowid in self._dataset.query(f"type=='{typeid}'")['flow_type'].unique():
                    repUnitFlow = re.sub('flow', flowTypes[flowid]['default_unit'], repUnit)
                    repUnitsDef.append({'type': typeid, 'flow_type': flowid, 'unit_convert': repUnitFlow})

        # override from function argument
        for record in repUnitsDef:
            if record['type'] in type_units:
                record['unit_convert'] = type_units[record['type']]
            elif 'flow_type' in record and record['flow_type'] in flow_units:
                record['unit_convert'] = flow_units[record['flow_type']]

        # add reported unit conversion factor
        self._dataset = self._dataset.merge(
            pd.DataFrame.from_records(repUnitsDef),
            on=['type', 'flow_type'],
        )
        convFactor = convUnitDF(self._dataset, 'unit', 'unit_convert')
        self._dataset['value'] *= convFactor
        self._dataset['unc'] *= convFactor
        self._dataset.drop(columns=['unit'], inplace=True)
        self._dataset.rename(columns={'unit_convert': 'unit'}, inplace=True)


    # get dataset
    def getDataset(self):
        return self._dataset


    # select data
    def selectData(self,
            periods: float | list | np.ndarray,
            subtechs: None | str | list = None,
            modes: None | str | list = None,
            sources: None | str | list = None,
            masks: None | list = None,
            mask_default: bool = True,
            aggregate: bool = True,
        ):

        # query by selected sources
        if sources is None:
            selected = self._dataset
        elif isinstance(sources, str):
            selected = self._dataset.query(f"src_ref=='{sources}'")
        else:
            selected = self._dataset.query(f"src_ref.isin({sources})")
        selected = selected.reset_index(drop=True)

        # expand technology specifications for all subtechs and modes
        expandCols = {}
        for colID, selectArg in [('subtech', subtechs), ('mode', modes)]:
            if subtechs is None and f"{colID}s" in self._tspecs and self._tspecs[f"{colID}s"]:
                expandCols[colID] = self._tspecs[f"{colID}s"]
            elif isinstance(subtechs, str):
                expandCols[colID] = [subtechs]
            elif isinstance(subtechs, list):
                expandCols[colID] = subtechs
        selected = self.__expandTechs(selected, expandCols)

        # drop columns that cannot be considered when selecting periods and aggregating
        selected.drop(columns=['region', 'unc', 'comment', 'src_comment'], inplace=True)

        # group by identifying columns and select periods/generate time series
        selected = self.__selectPeriods(selected, periods)

        # set default weight to 1
        selected.insert(0, 'weight', 1.0)

        # apply masks
        if masks is None:
            masks = []
        if mask_default and self._tid in defaultMasks:
            masks += defaultMasks[self._tid]
        for mask in masks:
            q = ' & '.join([f"{key}=='{val}'" for key, val in mask['query'].items()])
            selected.loc[selected.query(q).index, 'weight'] = mask['weight']

        # aggregate
        if aggregate:
            selected['value'].fillna(0.0, inplace=True)
            selected['value'] *= selected['weight']
            selected = selected \
                .groupby(['subtech', 'mode', 'type', 'period', 'flow_type', 'src_ref'], dropna=False) \
                .agg({'value': 'sum', 'unit': 'first'}) \
                .groupby(['subtech', 'mode', 'type', 'period', 'flow_type'], dropna=False) \
                .agg({'value': 'mean', 'unit': 'first'}) \
                .reset_index()

        return selected


    # expand based on subtechs, modes, and period
    def __expandTechs(self,
            selected: pd.DataFrame,
            expandCols: dict,
         ):

        for colID, colVals in expandCols.items():
            selected = pd.concat([
                selected[selected[colID].notna()],
                selected[selected[colID].isna()].drop(columns=[colID]).merge(pd.DataFrame.from_dict({colID: colVals}), how='cross'),
            ]) \
            .reset_index(drop=True)

        return selected.sort_values(by=['subtech', 'mode', 'type', 'component', 'src_ref', 'period'])


    # group by identifying columns and select periods/generate time series
    def __selectPeriods(self, selected: pd.DataFrame, periods: float | list | np.ndarray):
        groupCols = ['subtech', 'mode', 'type', 'flow_type', 'component', 'src_ref']
        grouped = selected.groupby(groupCols, dropna=False)

        ret = []
        for keys, ids in grouped.groups.items():
            rows = selected.loc[ids].sort_values(by='period')
            newRows = rows \
                .merge(pd.DataFrame.from_dict({'period': periods}), on='period', how='outer') \
                .sort_values(by='period') \
                .set_index('period')
            newRows['value'].interpolate(method='index', inplace=True)
            newRows['unit'] = rows.iloc[0]['unit']
            newRows[groupCols] = keys
            newRows = newRows.query(f"period in @periods").reset_index()
            ret.append(newRows)

        return pd.concat(ret).reset_index(drop=True)
