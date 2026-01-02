"""Definition and handling of columns in TEDFs."""

from typing import Final

import numpy as np
import pandas as pd
from cet_units import ureg

COL_TYPES: Final[list[str]] = ["field", "variable", "unit", "value", "comment"]


class AbstractColumnDefinition:
    """Abstract class to store column definitions.

    Attributes
    ----------
    col_type: str
        Type of the column.
    name: str
        Name of the column.
    description: str
        Description of the column.
    dtype:
        Data type of the column.
    required: bool
        Whether the column is required.

    Methods
    -------
    validate(s: pd.Series)
        Check validity of column entries for given column definition.

    """

    def __init__(
        self,
        col_type: str,
        name: str,
        description: str,
        dtype: str,
        required: bool,
    ):
        """Initialise field definition.

        Parameters
        ----------
        col_type: str
            Type of the column.
        name: str
            Name of the column.
        description: str
            Description of the column.
        dtype:
            Data type of the column.
        required: bool
            Whether the column is required.

        """
        if col_type not in COL_TYPES:
            raise Exception(
                f"Columns must be of type field, variable, unit, "
                f"value, or comment but found: {col_type}"
            )
        if not isinstance(name, str):
            raise Exception(
                f"The 'name' must be a string but found type {type(name)}: "
                f"{name}"
            )
        if not isinstance(description, str):
            raise Exception(
                f"The 'name' must be a string but found type "
                f"{type(description)}: {description}"
            )
        if not (
            isinstance(dtype, str) and dtype in ["float", "str", "category"]
        ):
            raise Exception(
                f"The 'dtype' must be a valid data type but found: {dtype}"
            )
        if not isinstance(required, bool):
            raise Exception(
                f"The 'required' argument must be a bool but found: {required}"
            )

        self._col_type: str = col_type
        self._name: str = name
        self._description: str = description
        self._dtype: str = dtype
        self._required: bool = required

    @property
    def col_type(self) -> str:
        """Get col type."""
        return self._col_type

    @property
    def name(self) -> str:
        """Get name of the column."""
        return self._name

    @property
    def description(self) -> str:
        """Get description of the column."""
        return self._description

    @property
    def dtype(self) -> str:
        """Get data type of the column."""
        return self._dtype

    @property
    def required(self) -> bool:
        """Return whether column is required."""
        return self._required

    @property
    def default(self) -> str | float:
        """Get default value of the column."""
        return np.nan

    def validate(self, s: pd.Series) -> pd.Series:
        """Check validity of column entries.

        Parameters
        ----------
        s: pd.Series
            Column entries to check.

        Returns
        -------
            pd.Series
                Return a series of booleans that indicate for each row if the
                specified cell is correct.

        """
        if self._required:
            return self._validate_values(s) & (s != "")
        else:
            return self._validate_values(s) | (s == "")

    def _validate_values(self, s: pd.Series) -> pd.Series | bool:
        return True


class VariableDefinition(AbstractColumnDefinition):
    """Class to store definition of variable columns."""

    def __init__(self, name: str, description: str, required: bool):
        """Initialise column definition.

        Parameters
        ----------
        name: str
            Name of the column.
        description: str
            Description of the column.
        required: bool
            Whether the column is required.

        """
        super().__init__(
            col_type="variable",
            name=name,
            description=description,
            dtype="category",
            required=required,
        )

    def _validate_values(self, s: pd.Series) -> pd.Series:
        # TODO: Check that variable matches REGEX.
        return s != ""


class UnitDefinition(AbstractColumnDefinition):
    """Class to store definition of unit columns."""

    def __init__(self, name: str, description: str, required: bool):
        """Initialise column definition.

        Parameters
        ----------
        name: str
            Name of the column.
        description: str
            Description of the column.
        required: bool
            Whether the column is required.

        """
        super().__init__(
            col_type="unit",
            name=name,
            description=description,
            dtype="category",
            required=required,
        )

    def _validate_values(self, s: pd.Series) -> pd.Series:
        # Wrap ureg unit check in try-except because pint raises an exception
        # if a unit expression contains a scaling factor.
        def _in_ureg(cell: str):
            try:
                return cell in ureg
            except:
                return False

        return s.apply(lambda cell: bool(cell) and _in_ureg(cell))


class ValueDefinition(AbstractColumnDefinition):
    """Class to store definition of unit columns."""

    def __init__(self, name: str, description: str, required: bool):
        """Initialise column definition.

        Parameters
        ----------
        name: str
            Name of the column.
        description: str
            Description of the column.
        required: bool
            Whether the column is required.

        """
        super().__init__(
            col_type="value",
            name=name,
            description=description,
            dtype="float",
            required=required,
        )

    def _validate_values(self, s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").notna()


class CommentDefinition(AbstractColumnDefinition):
    """Class to store definition of unit columns."""

    def __init__(self, name: str, description: str, required: bool):
        """Initialise column definition.

        Parameters
        ----------
        name: str
            Name of the column.
        description: str
            Description of the column.
        required: bool
            Whether the column is required.

        """
        super().__init__(
            col_type="comment",
            name=name,
            description=description,
            dtype="str",
            required=required,
        )
