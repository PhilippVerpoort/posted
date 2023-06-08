from pathlib import Path

import numpy as np
import pandas as pd

from posted.config.config import techs, techClasses, flowTypes
from posted.units.units import allowedFlowDims, simplifyUnit, ureg


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

    # check whether flow type (if non NaN) is among defined flow types
    cell = row['flow_type']
    if cell is not np.nan:
        if cell not in flowTypes.keys():
            ret.append(createException(re, TEInconsistencyException(f"invalid flow type: {cell}", colID='flow_type', **kwargs)))
    else:
        # for entries of type demand or energy_eff, flow_type has to be set
        if row['type'] in ['demand', 'energy_eff']:
            ret.append(createException(re, TEInconsistencyException(f"invalid flow type: {cell}. Flow type has to be set for entries of type {row['type']}", colID='flow_type', **kwargs)))

    # check whether subtech and mode are among those defined in the technology specs
    for colID in ['subtech', 'mode']:
       
        # check if subtechs/modes are defined for the technology
        if colID in techs[tid]['case_fields']:
            cell = row[colID]
            # NaNs are accepted; only real values can violate consistency here
            if cell not in techs[tid]['case_fields'][colID]['options'] and cell is not np.nan:
                ret.append(createException(re, TEInconsistencyException(f"invalid {colID}: {cell}", colID=colID, **kwargs)))
        else:
            if colID in row and row[colID] is not np.nan:
                ret.append(createException(re, TEInconsistencyException(f"{colID} should be empty, but the column contains: {cell}", colID=colID, **kwargs)))

    # check whether type is among those types defined in the technology class specs
    cell = row['type']
    # get technology class
    tech_class = techs[tid]['class']
    if cell is np.nan or cell not in techClasses[tech_class]['entry_types']:
        raise TEInconsistencyException(f"invalid entry type: {cell}", colID='type', **kwargs)

    # check whether reported unit and reference unit match the entry type and flow type specified

    for colID, colDim in [('reported_unit', 'rep_dim'), ('reference_unit', 'ref_dim')]:
        unit_to_check = row[colID]
        # if dimensions are not given for rep/ref, the unit cell has to be empty
        if colDim not in techClasses[tech_class]['entry_types'][cell]:
            if unit_to_check is not np.nan:
                ret.append(createException(re, TEInconsistencyException(f"invalid {colID}: {cell} does not allow {colID}, but value was provided", colID=colID, **kwargs)))
            break

        unit_type = techClasses[tech_class]['entry_types'][cell][colDim]

        # --- The following determines the allowed dimensions based on the entry_type.
        # Depending on the type of entry_type different dimensions and their combinations are added to the dimensions variable.
        dimension = []
        formula = unit_type.split('/')

        # for every element in the formula, the allowed dimensions are determined
        # After that, every possible combination of the allowed dimensions of each element are added to the dimension variable
        allowed_dims = []
        for elem in formula:
            if elem == '[flow]': # or use reference_flow here!
                if colID == 'reference_unit':
                    # for reference_unit, the tech-specific reference_flow is used
                    allowed_dims.append(allowedFlowDims(techs[tid]['reference_flow']))
                else:
                    # for reported_unit, the flow_type cell is used
                    allowed_dims.append(allowedFlowDims(row['flow_type']))
            else:
                allowed_dims.append([elem])
        # list of dimension combinations
        dimension = []
        # iterate over all dimensions lists in allowed_dims
        for dim_list in allowed_dims:
            dimensionNew = []
            # iterate over all dimensions in the list of dimensions
            for dim in dim_list:
                # if dimension is still empty, the first element is added unchanged to the dimension variable
                if dimension == []:
                    dimensionNew = dim_list
                    break
                else:
                    # if dimension is not empty, the dimension is combined with the elements of the dimension variable and added to dimensionNew
                    dimensionNew += [simplifyUnit(x + ' / ' + dim) for x in dimension]
            # dimension is updated with the new dimensionNew containing one more level of dimension combinations
            dimension = dimensionNew
        
        # --- The dimensions variable is now set to all allowed dimensions for this row

        if row[colID] is np.nan:
            # only reported unit has to be non NaN
            if colID == 'reported_unit':
                ret.append(createException(re, TEInconsistencyException('invalid reported_unit: NaN value', colID=colID, **kwargs)))
        else:
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
