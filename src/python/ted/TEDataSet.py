import copy
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.python.path import pathOfTEDFile
from src.python.read.read_config import techs, flowTypes, defaultUnits, defaultMasks
from src.python.ted.TEDataFile import TEDataFile
from src.python.ted.TEDataTable import TEDataTable
from src.python.units.units import convUnitDF, ureg


class TEDataSet:
    # initialise
    def __init__(self,
                 tid: str,
                 load_database: bool = True,
                 load_other: None | list = None,
                 to_default_units: bool = True):
        # set fields from arguments
        self._tid: str = tid
        self._tspecs: dict = copy.deepcopy(techs[tid])
        self._dataset: None | pd.DataFrame = None

        # read TEDataFiles and combine into dataset
        self._loadFiles(load_database, load_other)

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

            # map reference dimensions to default reference units
            self._refUnitsDef[typeid] = refDim
            for dim, unit in unitMappings.items():
                self._refUnitsDef[typeid] = re.sub(dim, unit, self._refUnitsDef[typeid])

        # override with default reference unit of specific technology
        if 'default-ref-units' in self._tspecs:
            self._refUnitsDef |= self._tspecs['default-ref-units']


    # load TEDatFiles and compile into dataset
    def _loadFiles(self, load_database: bool, load_other: None | list = None):
        files = []

        # load TEDataFile from POSTED database
        if load_database:
            files.append(TEDataFile(self._tid, pathOfTEDFile(self._tid)))

        # load other TEDataFiles if specified as arguments
        if load_other is not None:
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
        if type_units is None:
            type_units = {}
        if flow_units is None:
            flow_units = {}

        # set reported units to convert to
        repUnitsDef = []
        for typeid in self._dataset['type'].unique():
            # get reported dimension of entry type
            repDim = self._tspecs['entry_types'][typeid]['rep_dim']

            # map reported dimensions to target reported units
            repUnit = repDim
            for dim, unit in defaultUnits.items():
                repUnit = re.sub(dim, unit, repUnit)
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

        return self


    # get dataset
    def getDataset(self):
        return self._dataset


    # select data
    def generateTable(self,
                      periods: int | float | list | np.ndarray,
                      subtech: None | str | list = None,
                      mode: None | str | list = None,
                      src_ref: None | str | list = None,
                      masks_database: bool = True,
                      masks_other: None | list = None,
                      no_agg: None | list = None,
                      ):
        # the dataset it the starting-point for the table
        table = self._dataset.copy()

        # drop columns that are not considered
        table.drop(columns=['region', 'unc', 'comment', 'src_comment'], inplace=True)

        # merge value and unit columns together
        table['value'] *= table['unit'].apply(lambda x: ureg(x.split(';')[0]))
        table.drop(columns=['unit'], inplace=True)

        # insert missing periods
        table = self._insertMissingPeriods(table)

        # apply quick fixes
        table = self._quickFixes(table)

        # query by selected sources
        if src_ref is None:
            pass
        elif isinstance(src_ref, str):
            table = table.query(f"src_ref=='{src_ref}'")
        elif isinstance(src_ref, list):
            table = table.query(f"src_ref.isin({src_ref})")

        # expand technology specifications for all subtechs and modes
        expandCols = {}
        for colID, selectArg in [('subtech', subtech), ('mode', mode)]:
            if subtech is None and f"{colID}s" in self._tspecs and self._tspecs[f"{colID}s"]:
                expandCols[colID] = self._tspecs[f"{colID}s"]
            elif isinstance(subtech, str):
                expandCols[colID] = [subtech]
            elif isinstance(subtech, list):
                expandCols[colID] = subtech
        table = self.__expandTechs(table, expandCols)

        # group by identifying columns and select periods/generate time series
        if isinstance(periods, int) | isinstance(periods, float):
            periods = [periods]
        table = self._selectPeriods(table, periods)

        # set default weight to 1
        table['weight'] = 1.0

        # compile all masks into list
        masks = masks_other if masks_other is not None else []
        if masks_database and self._tid in defaultMasks:
            masks += defaultMasks[self._tid]

        # apply masks and drop entries with zero weight
        for mask in masks:
            q = ' & '.join([f"{key}=='{val}'" for key, val in mask['query'].items()])
            table.loc[table.query(q).index, 'weight'] = mask['weight']
            table = table.query('weight!=0.0')

        # combine type and flow_type columns
        table['type'] = table.apply(lambda row: row['type'] if row.isna()['flow_type'] else f"{row['type']}:{row['flow_type']}", axis=1)
        table.drop(columns=['flow_type'], inplace=True)

        # aggregation
        indexCols = ['type'] + (['period'] if len(periods) > 1 else []) + (no_agg if no_agg is not None else [])
        table['value'].fillna(0.0, inplace=True)
        table['value'] *= table['weight']
        table = table \
            .groupby(['subtech', 'mode', 'type', 'period', 'src_ref'], dropna=False) \
            .agg({'value': 'sum'}) \
            .groupby(indexCols, dropna=False) \
            .agg({'value': lambda x: sum(x) / len(x)})

        return TEDataTable(self._tid, table)


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


    # insert missing periods
    def _insertMissingPeriods(self, table: pd.DataFrame):
        return table.fillna({'period': 2023})


    # quick fix function for types not implemented yet
    def _quickFixes(self, table: pd.DataFrame):
        # TODO: implement those types so we don't need to remove them
        # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
        dropTypes = ['flh', 'lifetime', 'energy_eff']
        table = table.query(f"not type.isin({dropTypes})").reset_index(drop=True)
        return table


    # group by identifying columns and select periods/generate time series
    def _selectPeriods(self, selected: pd.DataFrame, periods: float | list | np.ndarray):
        # list of columns to group by
        groupCols = ['subtech', 'mode', 'type', 'flow_type', 'component', 'src_ref']

        # perform groupby and do not drop NA values
        grouped = selected.groupby(groupCols, dropna=False)

        # create return list
        ret = []

        # loop over groups
        for keys, ids in grouped.groups.items():
            # get rows in group
            rows = selected.loc[ids, ['period', 'value']]

            # get a list of periods that exist
            periodsExist = rows['period'].unique()

            # create dataframe containing rows for all requested periods
            reqRows = pd.DataFrame.from_dict({
                'period': periods,
                'period_upper': [min([ip for ip in periodsExist if ip >= p], default=np.nan) for p in periods],
                'period_lower': [max([ip for ip in periodsExist if ip <= p], default=np.nan) for p in periods],
            })

            # set missing columns from group
            reqRows[groupCols] = keys

            # extrapolate
            condExtrapolate = (reqRows['period_upper'].isna() | reqRows['period_lower'].isna())
            rowsExtrapolate = reqRows.loc[condExtrapolate] \
                .assign(period_combined=lambda x: np.where(x.notna()['period_upper'], x['period_upper'], x['period_lower'])) \
                .merge(rows.rename(columns={'period': 'period_combined'}), on='period_combined')

            # interpolate
            rowsInterpolate = reqRows.loc[~condExtrapolate] \
                .merge(rows.rename(columns={c: f"{c}_upper" for c in rows.columns}), on='period_upper') \
                .merge(rows.rename(columns={c: f"{c}_lower" for c in rows.columns}), on='period_lower') \
                .assign(value=lambda row: row['value_lower'] + (row['period_upper'] - row['period']) /
                       (row['period_upper'] - row['period_lower']) * (row['value_upper'] - row['value_lower']))

            # combine into one dataframe and drop unused columns
            rowsAppend = pd.concat([rowsExtrapolate, rowsInterpolate]) \
                .drop(columns=['period_upper', 'period_lower', 'period_combined', 'value_upper', 'value_lower'])

            # add to return list
            ret.append(rowsAppend)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True)
