import copy
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.python.path import pathOfTEDFile
from src.python.read.read_config import techs, flowTypes, defaultUnits, defaultMasks
from src.python.ted.TEDataFile import TEDataFile
from src.python.units.units import convUnitDF


class TEDataSet:
    # initialise
    def __init__(self, tid: str, *load_other, load_database: bool = True, to_default_units: bool = True):
        # set fields from arguments
        self._tid: str = tid
        self._tspecs: dict = copy.deepcopy(techs[tid])
        self._dataset: None | pd.DataFrame = None

        # read TEDataFiles and combine into dataset
        self._loadFiles(load_database, load_other)

        # insert missing periods
        self._insertMissingPeriods()

        # apply quick fixes
        self._quickFixes()

        # set default reference units for all entry types
        self._setRefUnitsDef()

        # normalise all entries to a unified reference
        self._normToRef()

        # convert values to default units
        if to_default_units:
            self.convertUnits()


    # determine default reference units of entry types from technology class
    def _setRefUnitsDef(self):
        self._refUnitsDef = {}
        for typeid in self._tspecs['entry_types']:
            # get reference dimension
            refDim = self._tspecs['entry_types'][typeid]['ref_dim']

            # create a mapping from dimensions to default units
            unitMappings = defaultUnits.copy()
            if 'reference_flow' in self._tspecs:
                unitMappings |= {'flow': flowTypes[self._tspecs['reference_flow']]['default_unit']}

            # map reference dimensions to default units
            self._refUnitsDef[typeid] = refDim
            for dim, unit in unitMappings.items():
                self._refUnitsDef[typeid] = re.sub(dim, unit, self._refUnitsDef[typeid])

        # override with default reference unit of specific technology
        if 'default-ref-units' in self._tspecs:
            self._refUnitsDef |= self._tspecs['default-ref-units']


    # load TEDatFiles and compile into dataset
    def _loadFiles(self, load_database: bool, load_other: tuple):
        files = []

        # load TEDataFile from POSTED database
        if load_database:
            files.append(TEDataFile(self._tid, pathOfTEDFile(self._tid)))

        # load other TEDataFiles specified as arguments
        for o in load_other:
            if isinstance(o, TEDataFile):
                files.append(o)
            elif isinstance(o, Path) or isinstance(o, str):
                p = o if isinstance(o, Path) else Path(o)
                files.append(TEDataFile(self._tid, p))

        # raise exception if no TEDataFiles can be loaded
        if not files:
            raise Exception(f"No TEDataFiles to load for technology '{self._tid}'.")

        # load all TEDataFiles and check consistency
        for f in files:
            f.load()
            f.check()

        # compile dataset from the dataframes loaded from the individual files
        self._dataset = pd.concat([f.getData() for f in files])


    # insert missing periods
    def _insertMissingPeriods(self):
        self._dataset.fillna({'period': 2023}, inplace=True)


    # quick fix function for types not implemented yet
    def _quickFixes(self):
        # TODO: implement those types so we don't need to remove them
        # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
        dropTypes = ['flh', 'lifetime', 'energy_eff']
        self._dataset = self._dataset.query(f"not type.isin({dropTypes})").reset_index(drop=True)


    # apply references to values and units
    def _normToRef(self):
        # default reference value is 1.0
        self._dataset['reference_value'].fillna(1.0, inplace=True)

        # add default reference unit conversion factor
        self._dataset['reference_unit_default'] = self._dataset['type'].map(self._refUnitsDef).astype(str)
        self._dataset['reference_unit_factor'] = np.where(
            self._dataset['reference_unit'].notna(),
            convUnitDF(self._dataset, 'reference_unit', 'reference_unit_default', flowTypes[self._tspecs['reference_flow']]),
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
    def convertUnits(self, type_units: None | dict = None, flow_units: None | dict = None):
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
