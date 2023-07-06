import copy

from posted.config.config import techs, baseFormat, flowTypes


class TEBase:
    def __init__(self, tid: str):
        # set tid from function argument
        self._tid: str = tid

        # set technology specifications
        self._tspecs: dict = techs[tid]

        # set data format
        self._setDataFormat()

        # initialise dtype mapping
        self._dtypeMapping: None | dict = None


    # set data format
    def _setDataFormat(self):
        # generate data format from base format and technology case fields
        self._dataFormat: dict = {}
        for key, val in baseFormat.items():
            self._dataFormat[key] = val

            # insert case fields after flow_type column
            if key == 'flow_type':
                self._dataFormat |= self._tspecs['case_fields']

        self._caseFields = list(self._tspecs['case_fields'].keys())


    # get data format
    @property
    def dataFormat(self):
        return copy.deepcopy(self._dataFormat)


    # get reference unit
    @property
    def refUnit(self):
        return flowTypes[self.refFlow]['default_unit']


    # get reference flow
    @property
    def refFlow(self):
        return self._tspecs['reference_flow']


    # get dtype mapping
    def _getDtypeMapping(self):
        if self._dtypeMapping is None:
            self._dtypeMapping = {
                colName: colSpecs['dtype']
                for colName, colSpecs in self._dataFormat.items()
            }

        return self._dtypeMapping
