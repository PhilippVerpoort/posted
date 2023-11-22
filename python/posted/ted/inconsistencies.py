from pathlib import Path

import numpy as np
import pandas as pd

from posted.config import variables, base_format
from posted.units.units import unit_allowed


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


def check_row_consistency(main_variable: str, row: pd.Series, row_id: int, file_path: Path,
                          raise_exception: bool) -> list[TEInconsistencyException]:
    ikwargs = {'row_id': row_id, 'file_path': file_path, 'raise_exception': raise_exception}
    ret = []

    # variable may not be empty
    sub_variable = row['variable']
    if sub_variable is np.nan:
        ret.append(new_inconsistency(message=f"Empty subvariable.", col_id='variable', **ikwargs))
        return ret

    # if the variable is not empty, check whether variable is among the allowed variables
    variable = f"{main_variable}|{sub_variable}"
    var_specs = variables[variable]
    if variable not in variables:
        ret.append(new_inconsistency(message=f"Invalid subvariable {variable}.", col_id='variable', **ikwargs))

    # check whether case columns are among those defined in the technology specs
    for col_id in (c for c in row.index if c not in base_format):
        cell = row[col_id]
        if col_id in variables[variable]['case_fields'] and cell != '*' and cell not in variables[variable]['case_fields'][col_id]:
            ret.append(new_inconsistency(message=f"Invalid case field value {cell}.", col_id=col_id, **ikwargs))

    # check that reported and reference units match variable definition
    for level in ('reported', 'reference'):
        col_id = f"{level}_unit"
        unit = row[col_id]
        if f"{level}_dim" not in var_specs:
            if unit is not np.nan:
                ret.append(new_inconsistency(message=f"Unexpected unit '{unit}' for {col_id}.", col_id=col_id, **ikwargs))
            continue
        dimension = var_specs[f"{level}_dim"]

        flow_id = var_specs[f"{level}_flow_id"] if f"{level}_flow_id" in var_specs else None
        allowed, message = unit_allowed(unit=unit, flow_id=flow_id, dimension=dimension)
        if not allowed:
            ret.append(new_inconsistency(message=message, col_id=col_id, **ikwargs))

    return ret
