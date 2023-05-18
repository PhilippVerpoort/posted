from pathlib import Path

import numpy as np
import pandas as pd

from src.python.config.config import techs, techClasses
from src.python.units.units import allowedFlowDims, ureg


class TEInconsistencyException(Exception):
    """Exception raised for inconsistencies in the input data.

    Attributes:
        message -- explanation of the error
        row -- row where the inconsistency occurred
        col -- column where the inconsistency occurred
        file -- file where the inconsistency occurred
    """
    def __init__(self, message: str = "Inconsistency detected", rowID: None | int = None,
                 colID: None | str = None, filePath: None | Path = None):
        self.message: str = message
        self.rowID: None | int = rowID
        self.colID: None | str = colID
        self.filePath: None | Path = filePath

        # add tokens at the end of the error message
        messageTokens = []
        if filePath is not None:
            messageTokens.append(f"file \"{filePath}\"")
        if rowID is not None:
            messageTokens.append(f"line {rowID}")
        if colID is not None:
            messageTokens.append(f"in column \"{colID}\"")

        # compose error message from tokens
        exceptionMessage: str = message
        if messageTokens:
            exceptionMessage += f"\n    " + (", ".join(messageTokens)).capitalize()

        super().__init__(exceptionMessage)


def createException(re: bool, ex: TEInconsistencyException):
    if re:
        raise ex
    else:
        return ex


def checkRowConsistency(tid: str, row: pd.Series, re: bool = True, **kwargs) -> list[TEInconsistencyException]:
    ret = []

    # check whether subtech and mode is among those defined in the technology specs
    for colID in ['subtech', 'mode']:
        cell = row[colID]
        if f"{colID}s" in techs[tid]:
            # NaNs are accepted; only real values can violate consistency here
            if cell not in techs[tid][f"{colID}s"] and cell is not np.nan:
                ret.append(createException(re, TEInconsistencyException(f"invalid {colID}: {cell}", colID=colID, **kwargs)))
        else:
            if cell is not np.nan:
                ret.append(createException(re, TEInconsistencyException(f"{colID} should be empty, but the column contains: {cell}", colID=colID, **kwargs)))

    # check whether type is among those types defined in the technology class specs
    cell = row['type']
    if cell not in techClasses['conversion']['entry_types']:
        raise TEInconsistencyException(f"invalid entry type: {cell}", colID='type', **kwargs)

    # check whether reported unit and reference unit match the entry type and flow type specified
    switchUnitDims = {
        'currency': '[currency]',
        'dimensionless': 'dimensionless',
        'time': '[time]'
        # 'flow' is defined in __allowed_flow_dims
    }
    for colID, colDim in [('reported_unit', 'rep_dim'), ('reference_unit', 'ref_dim')]:
        unit_type = techClasses['conversion']['entry_types'][row['type']][colDim]

        # --- The following determines the allowed dimensions based on the entry_type.
        # Depending on the type of entry_type different dimensions and their combinations are added to the dimensions variable.
        dimension = []
        formula = unit_type.split('/')
        if len(formula) > 1:  # unit_type is a composite of two dimensions
            if (formula[0] == 'flow'):  # if flow is the dimension, the flow_type has to be checked
                dims_enum = allowedFlowDims(row['flow_type'])
            else:
                dims_enum = switchUnitDims[formula[0]]
            if (formula[1] == 'flow'):  # if flow is the dimension, the flow_type has to be checked
                dims_denom = allowedFlowDims(row['flow_type'])
            else:
                dims_denom = switchUnitDims[formula[1]]

            if type(dims_enum) is list or type(
                    dims_denom) is list:  # one of the dimensions is quivalent to a list of dimensions
                if type(dims_enum) is list:  # the first dimension is quivalent to a list of dimensions, iteration is needed
                    for elem_enum in dims_enum:
                        if type(dims_denom) is list:  # the second dimension is quivalent to a list of dimensions as well,iteration is needed
                            for elem_denom in dims_denom:
                                dimension += [elem_enum + ' / ' + elem_denom]
                        else:  # the second dimension is not quivalent to a list of dimensions
                            dimension += [elem_enum + ' / ' + dims_denom]
                else:  # the first dimension is not quivalent to a list of dimensions
                    if type(dims_denom) is list:  # the second dimension is quivalent to a list of dimensions, iteration is needed
                        for elem_denom in dims_denom:
                            dimension += [dims_enum + ' / ' + elem_denom]
                    else:  # the second dimension is not quivalent to a list of dimensions
                        dimension += [dims_enum + ' / ' + dims_denom]
            else:
                dimension = [dims_enum + ' / ' + dims_denom]
        else:  # unit_type is a single dimension
            if (unit_type == 'flow'):  # if flow is the dimension, the flow_type has to be checked
                allowed_dims = allowedFlowDims(row['flow_type'])
            else:
                allowed_dims = switchUnitDims[unit_type]

            if type(allowed_dims) is list:
                for dim in allowed_dims:
                    dimension += [dim]
            else:
                dimension = switchUnitDims[unit_type]

        # --- The dimensions variable is now set to all allowed dimensions for this row

        if row[colID] is np.nan:
            # only reported unit has to be non NaN
            if colID == 'reported_unit':
                ret.append(createException(re, TEInconsistencyException('invalid reported_unit: NaN value', colID=colID, **kwargs)))
        else:
            unit_to_check = row[colID]

            # check if unit is connected to a variant (LHV, HHV, norm or standard)
            unit_splitted = unit_to_check.split(';')
            if (len(unit_splitted) > 1):  # the unit is connected to a variant
                unit_identifier = unit_splitted[0]
                unit_variant = unit_splitted[1]

                if unit_identifier not in ureg:
                    ret.append(createException(re, TEInconsistencyException(f"invalid {colID}: {unit_identifier} is not a valid unit", colID=colID, **kwargs)))
                elif (str(ureg.Quantity(unit_identifier).dimensionality) in [
                    '[length] ** 3']):  # unit is of dimension volume
                    if unit_variant not in ['norm', 'standard']:  # only ["norm", "standard"] variants are allowed for volume
                        ret.append(createException(re, TEInconsistencyException(
                            f"invalid {colID} variant: {unit_variant} is not a valid variant of {unit_identifier}", colID=colID, **kwargs)))
                elif (str(ureg.Quantity(unit_identifier).dimensionality) in [
                    '[length] ** 2 * [mass] / [time] ** 2']):  # unit is of type energy
                    if unit_variant not in ['LHV', 'HHV']:  # only ["LHV", "HHV"] variants are allowed for volume
                        ret.append(createException(re, TEInconsistencyException(
                            f"invalid {colID} variant: {unit_variant} is not a valid variant of {unit_identifier}", colID=colID, **kwargs)))
                else:  # unit is nether volume nor energy: inconsistency because there should not be a variant connected
                    ret.append(createException(re, TEInconsistencyException(
                        f"invalid {colID}: variants for unit {unit_identifier} are not allowed", colID=colID, **kwargs)))

                unit_to_check = unit_identifier  # set unit variable to proceed with consistency checks

            if unit_to_check not in ureg or str(ureg.Quantity(unit_to_check).dimensionality) not in dimension:
                ret.append(createException(re, TEInconsistencyException(f"invalid {colID}: {unit_to_check} is not of type {unit_type}", colID=colID, **kwargs)))

    return ret
