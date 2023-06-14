import pandas as pd
import pint

from posted.ted.TEDataTable import TEDataTable
from posted.units.units import convUnit


class TEProcessTreeDataTable(TEDataTable):
    def __init__(self, *tables, processGraph: None | dict = None, simplifyProcessNames: bool = True):
        # check args are of correct type
        if len(tables) < 1:
            raise Exception('Please provide at least one TEDataTable as argument.')
        if not all(isinstance(arg, TEDataTable) for arg in tables):
            raise Exception('All arguments have to be TEDataTables!')

        # set object fields from init arguments
        self._tables: dict[str: TEDataTable] = {}
        for t in tables:
            if t.name in self._tables:
                raise Exception(f"At least two tables with the same name: {t.name}")
            self._tables[t.name] = t

        # generate process tree if not provided as function argument
        if processGraph is None:
            self._graph: dict = {}
            p0 = list(self._tables.keys())[0]
            self._appendProcess(p0, [])
        else:
            self._graph: dict = processGraph
            p0 = list(self._graph.keys())[0]

        # generate merged table
        data = None
        for p in self._graph:
            table = self._tables[p.split('/')[-1]]
            proc = pd.concat([table.data], keys=[p], names=['process'], axis=1)
            if data is None:
                data = proc
            else:
                data = data.merge(proc, left_index=True, right_index=True)

        # apply demand factors
        for p, pSpecs in self._graph.items():
            for ftDem, pDem in pSpecs.items():
                tDem = self._tables[pDem.split('/')[-1]]

                demandCol = f"demand:{ftDem}"
                demandColNew = f"demand_sc:{ftDem}"

                rescale = data[p, demandCol].pint.to(tDem.refQuantity.u) / tDem.refQuantity

                for colID in data[pDem].columns:
                    if colID in tDem.refTypes:
                        continue
                    data[pDem, colID] *= rescale

                data.rename(columns={demandCol: demandColNew}, inplace=True)

        # stack process
        typeUnits = {c[1]: data[c].pint.units for c in data.columns}
        data = data.stack('process')
        for colID in typeUnits:
            data[colID] = data[colID].astype(f"pint[{typeUnits[colID]}]")

        # simplify process names
        if simplifyProcessNames:
            level = data.index.names.index('process')
            renamings = {idx: idx.split('/')[-1] for idx in data.index.levels[level]}
            data.rename(index=renamings, level=level, inplace=True)

        # set reference quantity and flow
        t0 = self._tables[p0]
        super().__init__(
            data=data,
            refQuantity=t0.refQuantity,
            refFlow=t0.refFlow,
            name='-'.join(list(self._graph.keys())),
        )


    # append process to process tree
    def _appendProcess(self, p: str, parents: list):
        t = self._tables[p]
        procPath = parents + [p]
        procName = '/'.join(procPath)
        self._graph[procName] = {}
        for colID in t.data.columns:
            if not colID.startswith('demand:'):
                continue
            ft = colID.split(':')[-1]
            for pn in self._tables:
                if pn == p:
                    continue
                if self._tables[pn].refFlow == ft:
                    self._graph[procName][ft] = '/'.join(procPath + [pn])
                    self._appendProcess(pn, procPath)
