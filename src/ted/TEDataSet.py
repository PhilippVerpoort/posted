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


    # check bat dataframe is consistent
    def __checkConsistency(self):
        # TODO: check reported units match dataFormats['bat']

        # TODO: check reference units match techs[techid]

        pass


    # convert value, unc, and units (reported and reference) to default units
    def __normaliseUnits(self):
        # default reference value is 1.0
        self._dataset['reference_value'].fillna(1.0, inplace=True)

        # add default reference unit
        ref_dims = {id: specs['ref_dim'] for id, specs in self._tspecs['entry_types'].items()}
        self._dataset['reference_unit_default'] = self._dataset['type'].map(ref_dims)
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
        self._dataset['reported_unit_default'] = self._dataset['type'].map(rep_dims)
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

        print(self._dataset)
