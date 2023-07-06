import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sigfig import round
import warnings

from posted.path import pathOfTEDFile
from posted.config.config import techs, flowTypes, defaultUnits, defaultMasks
from posted.ted.TEBase import TEBase
from posted.ted.TEDataFile import TEDataFile
from posted.ted.TEDataTable import TEDataTable
from posted.units.units import convUnitDF, convUnit, ureg
from posted.ted.failures import TEGenerationFailure


class TEDataSet(TEBase):
    # initialise
    def __init__(self,
                 tid: str,
                 load_other: None | list = None,
                 load_database: bool = False,
                 check_incons: bool = False,
                 ):
        TEBase.__init__(self, tid)

        # initialise object fields
        self._df: None | pd.DataFrame = None

        # read TEDataFiles and combine into dataset
        self._loadFiles(load_other, load_database, check_incons)

        # check types
        self._checkTypes()

        # adjust units: set default reference and reported units and normalise
        self._adjustUnits()


    # load TEDatFiles and compile into dataset
    def _loadFiles(self, load_other: None | list, load_database: bool, check_incons: bool):
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

        # load all TEDataFiles and check consistency if requested
        for f in files:
            f.load()
            if check_incons:
                f.check()

        # compile dataset from the dataframes loaded from the individual files
        self._df = pd.concat([f.data for f in files])


    # reduce rows to those with types and flow_types within allowed values
    def _checkTypes(self):
        # TODO: Raise TEInconsistencyException
        cond = self._df['type'].isin(list(self._tspecs['entry_types'])) & \
               (self._df['flow_type'].isin(list(flowTypes.keys())) |
                self._df['flow_type'].isna())
        self._df = self._df.loc[cond].reset_index(drop=True)


    # adjust units: set default reference and reported units and normalise
    def _adjustUnits(self):
        # set default reference units for all entry types
        self._setRefUnitsDef()

        # normalise reference units of all entries
        self._normRefUnits()

        # set default reported units for all entry types
        self._setRepUnitsDef()

        # normalise reported units of all entries
        self._normRepUnits()


    # determine default reference units of entry types from technology class
    def _setRefUnitsDef(self):
        self._refUnits = {}
        for typeid in self._tspecs['entry_types']:
            # set to nan if entry type has no reference dimension
            if 'ref_dim' not in self._tspecs['entry_types'][typeid]:
                self._refUnits[typeid] = np.nan
            else:
                # get reference dimension
                refDim = self._tspecs['entry_types'][typeid]['ref_dim']

                # create a mapping from dimensions to default units
                unitMappings = defaultUnits.copy()
                if self.refFlow is not None:
                    unitMappings |= {'[flow]': flowTypes[self.refFlow]['default_unit']}

                # map reference dimensions to default reference units
                self._refUnits[typeid] = refDim
                for dim, unit in unitMappings.items():
                    self._refUnits[typeid] = self._refUnits[typeid].replace(dim, unit)


        # override with default reference unit of specific technology
        if 'default-ref-units' in self._tspecs:
            self._refUnits |= self._tspecs['default-ref-units']


    # normalise reference units
    def _normRefUnits(self):
        # default reference value is 1.0
        self._df['reference_value'].fillna(1.0, inplace=True)

        # add default reference unit conversion factor
        self._df['reference_unit_default'] = self._df['type'].map(self._refUnits).astype(str)
        self._df['reference_unit_factor'] = np.where(
            self._df['reference_unit'].notna(),
            convUnitDF(self._df, 'reference_unit', 'reference_unit_default', self.refFlow),
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


    # set units of entries
    def _setRepUnitsDef(self):
        types = set(self._df['type'].unique().tolist() + ['fopex', 'fopex_spec'])
        self._repUnits = []
        for typeid in types:
            # get reported dimension of entry type
            repDim = self._tspecs['entry_types'][typeid]['rep_dim']

            # map reported dimensions to target reported units
            repUnit = repDim
            for dim, unit in defaultUnits.items():
                repUnit = repUnit.replace(dim, unit)
            if '[flow]' not in repUnit:
                self._repUnits.append({'type': typeid, 'unit': repUnit})
            else:
                for flowid in self._df.query(f"type=='{typeid}'")['flow_type'].unique():
                    repUnitFlow = repUnit.replace('[flow]', flowTypes[flowid]['default_unit'])
                    self._repUnits.append({'type': typeid, 'flow_type': flowid, 'unit': repUnitFlow})


    # normalise reported units
    def _normRepUnits(self):
        testi = self._df.merge(
            pd.DataFrame.from_records(self._repUnits).rename(columns={'unit': 'unit_convert'}),
            on=['type', 'flow_type'],
        )

        dfRepUnits = pd.DataFrame.from_records(self._repUnits).rename(columns={'unit': 'unit_convert'})
        def performJoinFlowTypeTolerance(row):
            # define columns to join on
            joinCols = ['type']
            # add flow_type to join columns if it is specified in dfRepUnits and not NaN
            if(dfRepUnits.query(f"type.isin({[row['type']]}) and flow_type.isnull()").empty):
                joinCols.append('flow_type')

            # convert row to dataframe
            row = row.to_frame().transpose()

            # join row df with dfRepUnits on joinCols and leave out suffixes for row df
            joinResult = row.merge(dfRepUnits, on=joinCols, suffixes=('', '_y'))
            return joinResult

        # perform the FlowTypeTolerance join on all rows
        dfJoins = self._df.apply(performJoinFlowTypeTolerance, axis=1)
        # concat all the join results to one dataframe
        self._df = pd.concat(dfJoins.to_list(), ignore_index=True)[self._df.columns.to_list() + ['unit_convert']]

        convFactor = convUnitDF(self._df, 'unit', 'unit_convert')
        self._df['value'] *= convFactor
        self._df['unc'] *= convFactor
        self._df['unit'] = self._df['unit_convert']
        self._df.drop(columns=['unit_convert'], inplace=True)


    # convert values to defined units (use defaults if non provided)
    def convertUnits(self, type_units: None | dict = None, flow_units: None | dict = None):
        # raise exception if no updates to units are provided
        if type_units is None and flow_units is None:
            return

        # update reported units of dataset from function argument
        for record in self._repUnits:
            if type_units is not None and record['type'] in type_units:
                record['unit'] = type_units[record['type']]
            elif flow_units is not None and 'flow_type' in record and record['flow_type'] in flow_units:
                record['unit'] = flow_units[record['flow_type']]

        # normalise reported units
        self._normRepUnits()

        return self


    # access dataframe
    @property
    def data(self):
        return self._df


    # get reported unit for entry type
    def getRepUnit(self, typeid: str, flowid: str | None = None):
        if flowid is None:
            return next(e['unit'] for e in self._repUnits if e['type'] == typeid)
        else:
            return next(e['unit'] for e in self._repUnits if e['type'] == typeid and e['flow_type'] == flowid)


    # get reference unit for entry type
    def getRefUnit(self, typeid: str):
        return self._refUnits[typeid]


    # select data
    def generateTable(self,
                      agg: None | list = None,
                      masks_database: bool = True,
                      masks_other: None | list = None,
                      keepSingularIndexLevels: bool = False,
                      **kwargs):
        # the dataset it the starting-point for the table
        table = self._df.copy()

        # drop columns that are not considered
        table.drop(columns=['region', 'unc', 'comment', 'src_comment'], inplace=True)

        # select by sources
        if 'src_ref' not in kwargs or kwargs['src_ref'] is None:
            pass
        elif isinstance(kwargs['src_ref'], str):
            table = table.query(f"src_ref=='{kwargs['src_ref']}'")
        elif isinstance(kwargs['src_ref'], list):
            table = table.query(f"src_ref.isin({kwargs['src_ref']})")

        # expand all case fields
        expandCols = {}
        for idxName, colSpecs in self._tspecs['case_fields'].items():
            if (idxName not in kwargs or kwargs[idxName] is None) and colSpecs:
                expandCols[idxName] = colSpecs['options']
            elif idxName in kwargs and kwargs[idxName] is not None and isinstance(kwargs[idxName], str):
                expandCols[idxName] = [kwargs[idxName]]
            elif idxName in kwargs and kwargs[idxName] is not None and isinstance(kwargs[idxName], list):
                expandCols[idxName] = kwargs[idxName]
        table = self._expandTechs(table, expandCols)

        # insert missing periods
        table = self._insertMissingPeriods(table)

        # select/interpolate periods
        if 'period' not in kwargs or kwargs['period'] is None:
            period = datetime.date.today().year
        else:
            period = kwargs['period']
        if isinstance(period, int) | isinstance(period, float):
            period = [period]
        table = self._selectPeriods(table, period)

        # apply quick fixes
        table = self._applyTypeMappings(table)

        # combine type, flow_type, and unit columns
        table['type'] = table.apply(
            lambda row: f"{row['type']}{':'+str(row['flow_type']) if row.notna()['flow_type'] else ''} [{row['unit']}]",
            axis=1,
        )
        table.drop(columns=['flow_type', 'unit'], inplace=True)

        # apply masks
        table = self._applyMasks(table, masks_other, masks_database)

        # sort table
        sorting = ['type'] + self._caseFields + ['src_ref', 'period', 'component']
        table = table.sort_values(by=sorting).reset_index(drop=True)

        # aggregation
        if agg is None:
            agg = ['src_ref']
        groupForSum = [c for c in table.columns if c not in ['component', 'value']]
        groupForAgg = [c for c in groupForSum if c not in agg]
        table['value'].fillna(0.0, inplace=True)
        table = table \
            .groupby(groupForSum, dropna=False) \
            .agg({'value': 'sum'}) \
            .groupby(groupForAgg, dropna=False) \
            .agg({'value': 'mean'})

        # unstack type
        table = table.unstack('type')

        # rename case fields
        table.rename(
            index={idxName: (f"{idxName}:{self._tid}" if idxName in self._tspecs['case_fields'] else idxName) for idxName in table.index.names},
            inplace=True,
        )

        # round values
        table = table.apply(lambda col: col.apply(lambda cell:
            cell if cell!=cell else round(cell, sigfigs=4, warn=False)
        ))

        # move units from column name to pint column unit
        newTable = []
        for typeName in table['value'].columns:
            tokens = typeName.split(' ')
            typeNameNew = tokens[0]
            unit = tokens[1]
            newCol = table['value', typeName] \
                .rename(('value', typeNameNew)) \
                .astype(f"pint{unit}")
            newTable.append(newCol)
        table = pd.concat(newTable, axis=1)

        # update column level names
        table.columns.names = ['part', 'type']

        # drop index levels representing case fields with precisely one option
        if not keepSingularIndexLevels:
            if table.index.nlevels > 1:
                singularIndexLevels = [level.name for level in table.index.levels if len(level)==1]
            else:
                singularIndexLevels = table.index.names if table.index.nunique() == 1 else []
            if len(singularIndexLevels) < table.index.nlevels:
                table.index = table.index.droplevel(singularIndexLevels)
            else:
                table = table.reset_index(drop=True)

        # create TEDataTable object and return
        return TEDataTable(
            data=table,
            refQuantity=ureg(self.refUnit),
            refFlow=self.refFlow,
            name=self._tid,
        )


    # insert missing periods
    def _insertMissingPeriods(self, table: pd.DataFrame) -> pd.DataFrame:
        # TODO: insert year of publication instead of current year
        table = table.fillna({'period': 2023})

        # return
        return table


    # apply mappings between entry types
    def _applyTypeMappings(self, table: pd.DataFrame) -> pd.DataFrame:
        # list of columns to group by
        groupCols = self._caseFields + ['period', 'src_ref']

        # perform groupby and do not drop NA values
        grouped = table.groupby(groupCols, dropna=False)

        # create return list
        ret = []

        # loop over groups
        for keys, ids in grouped.groups.items():
            # get rows in group
            rows = table.loc[ids, [c for c in table if c not in groupCols]].copy()

            # 1. convert fopex_rel to fopex
            capex = rows.query(f"type=='capex'")
            cond = (rows['type'] == 'fopex_rel')
            if cond.any():
                if capex.empty:
                    warnings.warn(TEGenerationFailure(rows.loc[cond], 'No CAPEX value matching a relative FOPEX value found.'))
                rows.loc[cond] = rows.loc[cond].assign(value=lambda row:
                    np.nan if capex.empty else row['value'] *
                    (capex.query(f"component=='{row['component'].iloc[0]}'")['value'].iloc[0]
                    if (row['component'].notna().all() and not capex.query(f"component=='{row['component'].iloc[0]}'").empty)
                    else capex['value'].sum()),
                )
                rows.loc[cond, 'unit'] = np.nan if capex.empty else (capex['unit'].iloc[0]+'/a')
                rows.loc[cond, 'type'] = 'fopex'

            # 2. convert fopex to fopex_spec
            cond = (rows['type'] == 'fopex')
            if cond.any():
                convFacRep = convUnit(self.getRepUnit('fopex') + '*a', self.getRepUnit('fopex_spec'))
                convFacRef = convUnit(self.getRefUnit('fopex') + '*a', self.getRefUnit('fopex_spec'), self.refFlow)

                rows.loc[cond, 'value'] *= convFacRep / convFacRef
                rows.loc[cond, 'unit'] = rows.loc[cond, 'unit'].apply(lambda u: str(ureg(u + '*a').to_reduced_units().u))
                rows.loc[cond, 'type'] = 'fopex_spec'

            # 3. convert unit of CAPEX (???)
            # convFacRef = convUnit(self.getRefUnit('capex') + '*a', self.getRefUnit('fopex_spec'), self.refFlow)
            #
            # rowsCAPEX = table['type'] == 'capex'
            # table.loc[rowsCAPEX, 'value'] /= convFacRef

            # 4. convert FLH to OCF
            cond = (rows['type'] == 'flh')
            if cond.any():
                convFac = convUnit(self.getRepUnit('flh'), 'a')
                rows.loc[cond, 'value'] *= convFac
                rows.loc[cond, 'unit'] = 'dimensionless'
                rows.loc[cond, 'type'] = 'ocf'

            # 5. convert energy_eff to demand
            cond = (rows['type'] == 'energy_eff')
            if cond.any():
                if 'reference_flow' not in self._tspecs:
                    warnings.warn(TEGenerationFailure(rows.loc[cond], 'Found efficiency but technology has no reference flow.'))
                else:
                    rows.loc[cond, 'value'] = rows.loc[cond, 'value'].assign(
                        value=lambda row: 1 / row['value'] * convUnit(self.refUnit, self.getRepUnit('demand', row['flow_type'])),
                        unit=lambda row: self.getRepUnit('demand', row['flow_type']),
                    )
                    rows.loc[cond, 'type'] = 'demand'

            # set missing columns from group
            rows[groupCols] = keys

            # add to return list
            ret.append(rows)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True)


    # expand based on subtechs, modes, and period
    def _expandTechs(self, table: pd.DataFrame, expandCols: dict) -> pd.DataFrame:
        # loop over affected columns (subtech and mode)
        for colID, colVals in expandCols.items():
            table = pd.concat([
                table[table[colID].notna() & table[colID].isin(colVals)],
                table[table[colID].isna()].drop(columns=[colID]).merge(pd.DataFrame.from_dict({colID: colVals}), how='cross'),
            ]) \
            .reset_index(drop=True)

        # return
        return table


    # group by identifying columns and select periods/generate time series
    def _selectPeriods(self, table: pd.DataFrame, period: float | list | np.ndarray) -> pd.DataFrame:
        # list of columns to group by
        groupCols = ['type', 'flow_type', 'unit'] + self._caseFields + ['component', 'src_ref']

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
                'period': period,
                'period_upper': [min([ip for ip in periodsExist if ip >= p], default=np.nan) for p in period],
                'period_lower': [max([ip for ip in periodsExist if ip <= p], default=np.nan) for p in period],
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


    # apply masks
    def _applyMasks(self, table, masks_other, masks_database) -> pd.DataFrame:
        # compile all masks into list
        masks = masks_other if masks_other is not None else []
        if masks_database and self._tid in defaultMasks:
            masks += defaultMasks[self._tid]

        # set weight from masks
        table['weight'] = 1.0
        for mask in masks:
            q = ' & '.join([f"{key}=='{val}'" for key, val in mask['query'].items()])
            table.loc[table.query(q).index, 'weight'] = mask['weight']

        # drop entries with zero weight and apply weights to values otherwise
        table = table.query('weight!=0.0').reset_index(drop=True)
        table['value'] *= table['weight']
        table.drop(columns=['weight'], inplace=True)

        return table
