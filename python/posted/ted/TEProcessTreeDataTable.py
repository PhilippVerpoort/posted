import pandas as pd

from posted.ted.TEDataTable import TEDataTable
from posted.units.units import convUnit, ureg


class TEProcessTreeDataTable:
    def __init__(self, *args, tableDict: None | dict = None, processTree: None | dict = None):
        # check args are of correct type
        if len(args) < 1 and (tableDict is None or len(tableDict) == 0):
            raise Exception('Please provide at least one TEDataTable as argument.')
        elif len(args) > 0 and tableDict is not None:
            raise Exception('Please provide only single TEDataTables objects or the processMap as arguments.')
        if not all(isinstance(arg, TEDataTable) for arg in args):
            raise Exception('All arguments have to be TEDataTables!')

        # set object fields from init arguments
        self._tables: dict = tableDict if tableDict is not None else {arg.tid: arg for arg in args}

        # generate process tree if not provided as function argument
        if processTree is None:
            self._tree: dict = {}
            t0 = list(self._tables.values())[0]
            self._appendProcess(t0, [])
        else:
            self._tree: dict = processTree

        # generate merged table
        self._df = None
        for p in self._tree:
            table = self._tables[p.split('/')[-1]]
            proc = pd.concat([table.data], keys=[p], names=['process'], axis=1)
            if self._df is None:
                self._df = proc
            else:
                self._df = self._df.merge(proc, left_index=True, right_index=True)

        # apply demand factors
        for p, pSpecs in self._tree.items():
            for ftDem, pDem in pSpecs.items():
                tDem = self._tables[pDem.split('/')[-1]]

                demandCol = f"demand:{ftDem}"
                demandColNew = f"demand_sc:{ftDem}"

                rescale = self._df[p, demandCol]
                rescale *= convUnit(str(rescale.pint.units), tDem.referenceUnit, ftDem) / ureg(tDem.referenceUnit)

                for colID in self._df[pDem].columns:
                    if not tDem.hasRefDim(colID):
                        continue
                    self._df[pDem, colID] *= rescale

                self._df.rename(columns={demandCol: demandColNew}, inplace=True)

        # stack process
        self._df = self._df.stack('process')


    # append process to process tree
    def _appendProcess(self, t: TEDataTable, parents: list):
        procPath = parents + [t.tid]
        procName = '/'.join(procPath)
        self._tree[procName] = {}
        for colID in t.data.columns:
            if not colID.startswith('demand:'):
                continue
            ft = colID.split(':')[-1]
            for tn in self._tables.values():
                if t==tn:
                    continue
                if ft==tn.referenceFlow:
                    self._tree[procName][ft] = '/'.join(procPath + [tn.tid])
                    self._appendProcess(tn, procPath)


    # data property
    @property
    def data(self):
        return self._df
