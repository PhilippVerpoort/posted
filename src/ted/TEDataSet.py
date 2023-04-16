import copy
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.path import pathOfTEDFile
from src.read.file_read import readTEDFile
from src.read.read_config import techs, dataFormats, flowTypes, defaultUnits
from src.units.units import convUnitDF


class TEDataSet:
    # initialise
    def __init__(self, tid: str, load_default: bool = True, load_other: list = None):
        self._tid = tid
        self._tspecs = copy.deepcopy(techs[tid])
        self._dataset = None

        self._loadPaths = ([pathOfTEDFile(tid)] if load_default else []) + \
                          ([Path(p) for p in load_other] if load_other else [])


    # loading data and performing basic initial processing
    def load(self):
        if not self._loadPaths:
            raise Exception(f"No TED files to load for technology '{self._tid}'.")

        # read bat data from CSV files
        mapColsDtypes = {
            colname: colspecs['dtype']
            for colname, colspecs in dataFormats.items()
        }
        self._dataset = pd.concat([
            readTEDFile(p, mapColsDtypes)
            for p in self._loadPaths
        ])

        # check the bat dataframe is consistent
        self.__checkConsistency()

        # adjust units to match default units for inputs and outputs
        self.__normaliseUnits()

        # insert missing periods
        self.__insertMissingPeriods()


    # get dataset
    def getDataSet(self):
        return self._dataset


    # check bat dataframe is consistent
    def __checkConsistency(self):
        # TODO: check reported units match dataFormats['bat']

        # TODO: check reference units match techs[techid]

        # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
        # TODO: implement those types so we don't need to remove them
        dropTypes = ['flh', 'lifetime', 'energy_eff']
        self._dataset = self._dataset.query(f"not type.isin({dropTypes})").reset_index(drop=True)

        # replace Nm³/Sm³ with m³
        # TODO: implement these units in the unit registry. Same for LHV and HHV.
        self._dataset['reported_unit'] = self._dataset['reported_unit'].replace('(Nm³|Sm³)', 'm³', regex=True)

        pass


    # convert value, unc, and units (reported and reference) to default units
    def __normaliseUnits(self):
        # default reference value is 1.0
        self._dataset['reference_value'].fillna(1.0, inplace=True)

        # add default reference unit
        ref_dims = {id: specs['ref_dim'] for id, specs in self._tspecs['entry_types'].items()}
        self._dataset['reference_unit_default'] = self._dataset['type'].map(ref_dims).astype(str)
        for dim, unit in defaultUnits.items():
            self._dataset['reference_unit_default'] = self._dataset['reference_unit_default'].replace(dim, unit, regex=True)
        flowTypeRef = flowTypes[self._tspecs['primary']]
        self._dataset['reference_unit_default'] = self._dataset['reference_unit_default'].replace('quantity', flowTypeRef['default_unit'], regex=True)

        # override with default reference unit of specific technology
        if 'default-ref-units' in self._tspecs:
            for typeid, unit in self._tspecs['default-ref-units'].items():
                self._dataset.loc[self._dataset['type']==typeid, 'reference_unit_default'] = unit

        # add reference unit conversion factor if a reference unit is provided
        self._dataset['reference_unit_factor'] = np.where(
            self._dataset['reference_unit'].notna(),
            convUnitDF(self._dataset, 'reference_unit', 'reference_unit_default', flowTypeRef),
            1.0,
        )

        # add default reported unit
        rep_dims = {id: specs['rep_dim'] for id, specs in self._tspecs['entry_types'].items()}
        self._dataset['reported_unit_default'] = self._dataset['type'].map(rep_dims).astype(str)
        for dim, unit in defaultUnits.items():
            self._dataset['reported_unit_default'] = self._dataset['reported_unit_default'].replace(dim, unit, regex=True)
        typesWithFlow = [typeid for typeid, typespecs in self._tspecs['entry_types'].items() if 'quantity' in typespecs['rep_dim']]
        condFlow = (self._dataset['type'].isin(typesWithFlow))
        self._dataset.loc[condFlow, 'reported_unit_default'] = \
            self._dataset.loc[condFlow].apply(lambda row:
            re.sub('quantity', flowTypes[row['flow_type']]['default_unit'], row['reported_unit_default']),
            axis=1,
        )

        # add reported unit conversion factor
        self._dataset['reported_unit_factor'] = convUnitDF(self._dataset, 'reported_unit', 'reported_unit_default')

        # set non-unit conversion factor to 1.0 if not set otherwise
        self._dataset['conv_factor'].fillna(1.0, inplace=True)

        # set converted value and unit
        self._dataset.insert(7, 'value',
            self._dataset['reported_value'] \
          * self._dataset['reported_unit_factor'] \
          / self._dataset['reference_value'] \
          / self._dataset['reference_unit_factor'] \
          * self._dataset['conv_factor']
        )
        self._dataset.insert(8, 'unc',
            self._dataset['reported_unc'] \
          * self._dataset['reported_unit_factor'] \
          / self._dataset['reference_value'] \
          / self._dataset['reference_unit_factor'] \
          * self._dataset['conv_factor']
        )
        self._dataset.insert(9, 'unit',
            self._dataset.apply(lambda row:
                row['reported_unit_default'] + '/' + (row['reference_unit_default'] if '/' not in
                row['reference_unit_default'] else ('('+row['reference_unit_default'])+')'),
                axis=1,
            )
        )
        condDimensionless = (self._dataset['unit']=='dimensionless/dimensionless')
        self._dataset.loc[condDimensionless, 'unit'] = 'dimensionless'

        # drop old unit and value columns
        self._dataset.drop(
            self._dataset.filter(regex=r"^(reported|reference)_(value|unc|unit).*$").columns.to_list() + ['conv_factor'],
            axis=1,
            inplace=True,
        )


    # insert missing periods
    def __insertMissingPeriods(self):
        self._dataset.fillna({'period': 2023}, inplace=True)


    # select data
    def selectData(self,
            periods: float | list | np.ndarray,
            subtechs: None | str | list = None,
            modes: None | str | list = None,
            sources: None | str | list = None,
        ):

        # filter by selected sources
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
        selected = selected.drop(columns=['region', 'unc', 'comment', 'src_comment'])

        # group by identifying columns and select periods/generate time series
        selected = self.__selectPeriods(selected, periods)

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
        groupCols = ['subtech', 'mode', 'type', 'component', 'src_ref']
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
            newRows = newRows.query(f"period in @periods")
            ret.append(newRows)

        return pd.concat(ret).reset_index(drop=True)
