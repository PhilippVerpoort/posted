import copy
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.python.path import pathOfTEDFile
from src.python.read.file_read import readTEDFile
from src.python.read.read_config import techs, dataFormats, flowTypes, defaultUnits, defaultMasks
from src.python.units.units import convUnitDF


class TEDataSet:
    # initialise
    def __init__(self, tid: str):
        self._tid = tid
        self._tspecs = copy.deepcopy(techs[tid])
        self._dataset: pd.DataFrame = None

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


    # check dataset is consistent
    def __checkConsistency(self):
        # TODO: check reported units match dataFormats['bat']

        # TODO: check reference units match techs[techid]

        # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
        # TODO: implement those types so we don't need to remove them
        # TODO: drop all rows with types not declared in `tech_classes.yml`
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
    def convertUnits(self, type_units: dict = {}, flow_units: dict = {}):
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
