import copy

from posted.config.config import techs, baseFormat, flowTypes

class TEBase:
    """ The base class for all TE classes.

    This abstract class defines the basic structure of a TE class.
    This includes tid, data format, technology specifications, and dtype mapping.

    Attributes
    ----------
    _tid : str
        The technology ID.
    _tspecs : dict
        The technology specifications.
    _dataFormat : dict
        The data format.
    _caseFields : list
        The case fields.
    _dtypeMapping : None | dict
        The dtype mapping.

    Methods
    -------
    __init__(tid: str)
        Create a TEBase object.
    _setDataFormat()
        Set the data format.
    dataFormat
        Get the data format.
    refUnit
        Get the default reference unit.
    refFlow
        Get the reference flow.
    _getDtypeMapping()
        Get the default data type (data type mapping).
    """
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
        """ Set the data format.

        Returns
        -------
        None
        """
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
        """ Get the data format.

        Returns
        -------
        dict
            The data format.
        """
        return copy.deepcopy(self._dataFormat)


    # get reference unit
    @property
    def refUnit(self):
        """ Get the default reference unit.
        
        Returns
        -------
        str
            The default reference unit.
        """
        return flowTypes[self.refFlow]['default_unit']


    # get reference flow
    @property
    def refFlow(self):
        """ Get the reference flow.

        Returns
        -------
        str
            The reference flow.
        """
        return self._tspecs['reference_flow']


    # get dtype mapping
    def _getDtypeMapping(self):
        """ Get the default data type (data type mapping).

        Returns
        -------
        dict
            The default data type.
        """
        if self._dtypeMapping is None:
            self._dtypeMapping = {
                colName: colSpecs['dtype']
                for colName, colSpecs in self._dataFormat.items()
            }

        return self._dtypeMapping
