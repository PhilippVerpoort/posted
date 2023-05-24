import copy
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sigfig import round

from src.python.path import pathOfTEDFile
from src.python.config.config import techs, flowTypes, defaultUnits, defaultMasks
from src.python.ted.TEDataFile import TEDataFile
from src.python.ted.TEDataTable import TEDataTable
from src.python.units.units import convUnitDF, convUnit, ureg


class TEDataSet:
    # initialise
    def __init__(self,
                 tid: str,
                 load_other: None | list = None,
                 load_database: bool = False,
                 to_default_units: bool = True,
                 skip_checks: bool = False,
                 ):
        # set fields from arguments
        self._tid: str = tid
        self._tspecs: dict = copy.deepcopy(techs[tid])
        self._df: None | pd.DataFrame = None

        # read TEDataFiles and combine into dataset
        self._loadFiles(load_other, load_database, skip_checks)

        # set default reference units for all entry types
        self._setRefUnitsDef()

        # normalise all entries to a unified reference
        self._normToRef()

        # convert values to default units
        if to_default_units:
            self.convertUnits()


    # load TEDatFiles and compile into dataset
    def _loadFiles(self, load_other: None | list, load_database: bool, skip_checks: bool):
        files = []

        # load default TEDataFile from POSTED database
        if not load_other or load_database:
            files.append(TEDataFile(self._tid, pathOfTEDFile(self._tid)))

        # load TEDataFiles specified as arguments
        if load_other is not None:
            for o in load_other:
                if isinstance(o, TEDataFile):
                    files.append(o)
                elif isinstance(o, Path) or isinstance(o, str):
                    p = o if isinstance(o, Path) else Path(o)
                    files.append(TEDataFile(self._tid, p))
                else:
                    raise Exception(f"Unknown load type: {type(o).__name__}")

        # raise exception if no TEDataFiles can be loaded
        if not files:
            raise Exception(f"No TEDataFiles to load for technology '{self._tid}'.")

        # load all TEDataFiles and check consistency
        for f in files:
            f.load()
            if not skip_checks:
                f.check()

        # compile dataset from the dataframes loaded from the individual files
        self._df = pd.concat([f.data for f in files])


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


    # apply references to values and units
    def _normToRef(self):
        # default reference value is 1.0
        self._df['reference_value'].fillna(1.0, inplace=True)

        # add default reference unit conversion factor
        self._df['reference_unit_default'] = self._df['type'].map(self._refUnitsDef).astype(str)
        self._df['reference_unit_factor'] = np.where(
            self._df['reference_unit'].notna(),
            convUnitDF(self._df, 'reference_unit', 'reference_unit_default', self._tspecs['reference_flow']),
            1.0,
        )

        # set converted value and unit
        self._df.insert(7, 'value',
            self._df['reported_value'] \
          / self._df['reference_value'] \
          / self._df['reference_unit_factor']
        )
        self._df.insert(8, 'unc',
            self._df['reported_unc'] \
          / self._df['reference_value'] \
          / self._df['reference_unit_factor']
        )
        self._df.insert(9, 'unit', self._df['reported_unit'])

        # drop old unit and value columns
        self._df.drop(
            self._df.filter(regex=r"^(reported|reference)_(value|unc|unit).*$").columns.to_list(),
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
        repUnitsTarget = []
        for typeid in self._df['type'].unique():
            # get reported dimension of entry type
            repDim = self._tspecs['entry_types'][typeid]['rep_dim']

            # map reported dimensions to target reported units
            repUnit = repDim
            for dim, unit in defaultUnits.items():
                repUnit = re.sub(dim, unit, repUnit)
            if 'flow' not in repUnit:
                repUnitsTarget.append({'type': typeid, 'unit_convert': repUnit})
            else:
                for flowid in self._df.query(f"type=='{typeid}'")['flow_type'].unique():
                    repUnitFlow = re.sub('flow', flowTypes[flowid]['default_unit'], repUnit)
                    repUnitsTarget.append({'type': typeid, 'flow_type': flowid, 'unit_convert': repUnitFlow})

        # override from function argument
        for record in repUnitsTarget:
            if record['type'] in type_units:
                record['unit_convert'] = type_units[record['type']]
            elif 'flow_type' in record and record['flow_type'] in flow_units:
                record['unit_convert'] = flow_units[record['flow_type']]

        # add reported unit conversion factor
        self._df = self._df.merge(
            pd.DataFrame.from_records(repUnitsTarget),
            on=['type', 'flow_type'],
        )
        convFactor = convUnitDF(self._df, 'unit', 'unit_convert')
        self._df['value'] *= convFactor
        self._df['unc'] *= convFactor
        self._df['unit'] = self._df['unit_convert']
        self._df.drop(columns=['unit_convert'], inplace=True)

        return self


    # access dataframe
    @property
    def data(self):
        return self._df


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
        table = self._df.copy()

        # drop columns that are not considered
        table.drop(columns=['region', 'unc', 'comment', 'src_comment'], inplace=True)

        # insert missing periods
        table = self._insertMissingPeriods(table)

        # apply quick fixes
        table = self._quickFixes(table)

        # merge value and unit columns together
        table['value'] *= table['unit'].apply(lambda x: ureg(x.split(';')[0]))
        table.drop(columns=['unit'], inplace=True)

        # query by selected sources
        if src_ref is None:
            pass
        elif isinstance(src_ref, str):
            table = table.query(f"src_ref=='{src_ref}'")
        elif isinstance(src_ref, list):
            table = table.query(f"src_ref.isin({src_ref})")

        # expand technology specifications for all subtechs and modes
        expandCols = {}
        for colID, selectArg in {'subtech': subtech, 'mode': mode}.items():
            colIDs = f"{colID}s"
            if selectArg is None and colIDs in self._tspecs and self._tspecs[f"{colID}s"]:
                expandCols[colID] = self._tspecs[colIDs]
            elif isinstance(selectArg, str):
                expandCols[colID] = [selectArg]
            elif isinstance(selectArg, list):
                expandCols[colID] = selectArg
        table = self._expandTechs(table, expandCols)

        # group by identifying columns and select periods/generate time series
        if isinstance(periods, int) | isinstance(periods, float):
            periods = [periods]
        table = self._selectPeriods(table, periods)

        # sort table
        table.sort_values(by=['subtech', 'mode', 'type', 'component', 'src_ref', 'period'], inplace=True)

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

        # unstack type
        table = table['value'].unstack('type')

        # round values
        table = table.apply(lambda col: col.apply(lambda cell: cell if cell!=cell else round(cell.m, sigfigs=4, warn=False) * cell.u if isinstance(cell, ureg.Quantity) else round(cell, sigfigs=4, warn=False)))

        return TEDataTable(self._tid, table)


    # insert missing periods
    def _insertMissingPeriods(self, table: pd.DataFrame):
        # TODO: insert year of publication instead of current year
        table = table.fillna({'period': 2023})

        # return
        return table


    # quick fix function for types not implemented yet
    def _quickFixes(self, table: pd.DataFrame):
        # ---------- 1. Convert fopex_rel entries to fopex_abs ----------

        # copy fopex_rel entries to edit them safely
        selected_rows = table.query(f"type.isin({['fopex_rel']})").copy()

        # iterate over entries that need editing
        for index, row in selected_rows.iterrows():

            # ---- query for each row of fopex_rel the corresponding capex rows
            matching_entries = table.query(f"type.isin({['capex']})").copy()
            
            # check that other columns which might be Nan are equal
            for col in ['subtech', 'mode', 'component', 'src_ref']:
                if row[col] == row[col]:
                    matching_entries = matching_entries.query(f"{col}.isin({[row[col]]})")
            
            if(len(matching_entries) > 0):
                selected_rows.at[index,'value'] *= matching_entries['value'].iloc[0]

                selected_rows.at[index,'type'] = 'fopex_abs'

                selected_rows.at[index,'unit'] = matching_entries['unit'].iloc[0]
            else:
                # delete the corresponding row cause without fitting CAPEX entry from the same source, this value becomes meaningless
                table = table.drop([index])
                selected_rows = selected_rows.drop([index])
            
        # override main dataset
        table.loc[table['type'] == 'fopex_rel'] = selected_rows

        # ---------- 2. Convert full load hours entries to operational capacity factor ----------

        # copy fopex_rel entries to edit them safely
        selected_rows = table.query(f"type.isin({['flh']})").copy()

        # convert entries to ocf
        # value doesnt need to be changed because the standard time unit is year, so full load hours will already be converted to years by now
        selected_rows['type'] = 'ocf'
        selected_rows['unit'] = "dimensionless"

        # override main dataset
        table.loc[table['type'] == 'flh'] = selected_rows

        # ---------- 3. Convert energy_eff entries to energy_dem ----------

        if 'reference_flow' in techs[self._tid]:

            # copy energy_eff entries to edit them safely
            selected_rows = table.query(f"type.isin({['energy_eff']})").copy()
            reference_flow = techs[self._tid]['reference_flow']

            # iterate over entries that need editing
            for index, row in selected_rows.iterrows():
                # derive units based on reference_flow

                # has to be set to elec here because energy_eff entries dont have flow_type
                unit_from = flowTypes['elec']['default_unit'] 
                unit_to = flowTypes[reference_flow]['default_unit']
                conversionFactor = convUnit(unit_from=unit_from, unit_to=unit_to, ft_specs=flowTypes[reference_flow])

                # convert entry to energy_dem
                selected_rows.at[index, 'value'] = conversionFactor * (1.0/row['value'])
                selected_rows.at[index, 'type'] = 'energy_dem'
                selected_rows.at[index, 'unit'] = unit_from
                selected_rows.at[index, 'reference_unit'] = unit_to

            # override main dataset
            table.loc[table['type'] == 'energy_eff'] = selected_rows
        else:
            # no reference_flow found; energy_eff cannot be converted and has to be dropped
            entriesToDrop = table.query(f"type.isin({['energy_eff']})")
            table = table.drop(entriesToDrop.index.values)

        return table


    # expand based on subtechs, modes, and period
    def _expandTechs(self, table: pd.DataFrame, expandCols: dict):
        # loop over affected columns (subtech and mode)
        for colID, colVals in expandCols.items():
            table = pd.concat([
                table[table[colID].notna()],
                table[table[colID].isna()].drop(columns=[colID]).merge(pd.DataFrame.from_dict({colID: colVals}), how='cross'),
            ]) \
            .reset_index(drop=True)

        return table


    # group by identifying columns and select periods/generate time series
    def _selectPeriods(self, table: pd.DataFrame, periods: float | list | np.ndarray):
        # list of columns to group by
        groupCols = ['subtech', 'mode', 'type', 'flow_type', 'component', 'src_ref']

        # perform groupby and do not drop NA values
        grouped = table.groupby(groupCols, dropna=False)

        # create return list
        ret = []

        # loop over groups
        for keys, ids in grouped.groups.items():
            # get rows in group
            rows = table.loc[ids, ['period', 'value']]

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
