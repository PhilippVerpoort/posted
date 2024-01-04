from pathlib import Path

import numpy as np
import pandas as pd

from posted.config import variables, base_format
from posted.units.units import unit_allowed


def is_float(string: str) -> bool:
    try:
        float(string)
        return True
    except ValueError:
        return False


class TEInconsistencyException(Exception):
    """Exception raised for inconsistencies in the input data.

    Attributes:
        msg -- message explaining the inconsistency
        rowID -- row where the inconsistency occurs
        colID -- column where the inconsistency occurs
        filePath -- path to the file where the inconsistency occurs
    """
    def __init__(self, message: str = "Inconsistency detected", row_id: None | int = None,
                 col_id: None | str = None, file_path: None | Path = None):
        self.message: str = message
        self.row_id: None | int = row_id
        self.col_id: None | str = col_id
        self.file_path: None | Path = file_path

        # add tokens at the end of the error message
        message_tokens = []
        if file_path is not None:
            message_tokens.append(f"file \"{file_path}\"")
        if row_id is not None:
            message_tokens.append(f"line {row_id}")
        if col_id is not None:
            message_tokens.append(f"in column \"{col_id}\"")

        # compose error message from tokens
        exception_message: str = message
        if message_tokens:
            exception_message += f"\n    " + (", ".join(message_tokens)).capitalize()

        super().__init__(exception_message)


# create a new inconsistency object based on function arguments and either raise or return. returning will typically
# occur in file-editing mode in the GUI, whereas raising will happen in active usage and testing.
def new_inconsistency(raise_exception: bool, **kwargs) -> TEInconsistencyException:
    exception = TEInconsistencyException(**kwargs)
    if raise_exception:
        raise exception
    else:
        return exception


def check_row_consistency(parent_variable: str, fields: dict, row: pd.Series, row_id: int, file_path: Path,
                          raise_exception: bool) -> list[TEInconsistencyException]:
    ikwargs = {'row_id': row_id, 'file_path': file_path, 'raise_exception': raise_exception}
    ret = []

    # check whether fields are among those defined in the technology specs
    for col_id in (c for c in row.index if c not in base_format):
        if col_id not in fields:
            ret.append(new_inconsistency(
                message=f"Invalid field {col_id}.", col_id=col_id, **ikwargs,
            ))
        else:
            cell = row[col_id]
            if fields[col_id]['type'] == 'cases':
                if pd.isnull(cell) or (fields[col_id]['coded'] and cell not in fields[col_id]['codes'] and cell != '*'):
                    ret.append(new_inconsistency(
                        message=f"Invalid case field value '{cell}'.", col_id=col_id, **ikwargs,
                    ))
            if fields[col_id]['type'] == 'components':
                if pd.isnull(cell) or (fields[col_id]['coded'] and cell not in fields[col_id]['codes'] and cell != '*'):
                    ret.append(new_inconsistency(
                        message=f"Invalid component field value '{cell}'.", col_id=col_id, **ikwargs,
                    ))

    # period may not be empty
    if pd.isnull(row['period']):
        ret.append(new_inconsistency(
            message=f"Period cell is empty.", col_id='period', **ikwargs,
        ))
    elif (not isinstance(row['period'], float) and
          not isinstance(row['period'], int) and
          not (isinstance(row['period'], str) and (is_float(row['period']) or row['period'] == '*'))):
        ret.append(new_inconsistency(
            message=f"Period is not a valid entry: {row['period']}", col_id='period', **ikwargs,
        ))

    # variable may not be empty
    reported_subvariable = row['reported_variable']
    reference_subvariable = row['reference_variable']
    if not isinstance(reported_subvariable, str):
        ret.append(new_inconsistency(message=f"Empty reported variable.", col_id='reported_variable', **ikwargs))
        return ret

    # if the variable is not empty, check whether variable is among the allowed variables
    reported_variable = f"{parent_variable}|{reported_subvariable}"
    reference_variable = f"{parent_variable}|{reference_subvariable}"
    if reported_variable not in variables:
        ret.append(new_inconsistency(
            message=f"Invalid reported variable '{reported_variable}'.", col_id='reported_variable', **ikwargs,
        ))
        return ret
    if reference_variable not in variables and 'default_reference' in variables[reported_variable]:
        ret.append(new_inconsistency(
            message=f"Invalid reference variable '{reference_variable}'.", col_id='reference_variable', **ikwargs,
        ))
        return ret

    # check that reported and reference units match variable definition
    for level, variable in [('reported', reported_variable),
                             ('reference', reference_variable),]:
        if not isinstance(reference_subvariable, str):
            continue
        var_specs = variables[variable]
        col_id = f"{level}_unit"
        unit = row[col_id]
        if 'dimension' not in var_specs:
            if unit is not np.nan:
                ret.append(new_inconsistency(
                    message=f"Unexpected unit '{unit}' for {col_id}.", col_id=col_id, **ikwargs,
                ))
            continue
        dimension = var_specs['dimension']

        flow_id = var_specs['flow_id'] if 'flow_id' in var_specs else None
        allowed, message = unit_allowed(unit=unit, flow_id=flow_id, dimension=dimension)
        if not allowed:
            ret.append(new_inconsistency(message=message, col_id=col_id, **ikwargs))

    return ret
