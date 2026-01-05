import numpy as np
import pandas as pd

from units import ureg


def is_float(string: str) -> bool:
    """Checks if a given string can be converted to a floating-point
    number in Python.

    Parameters
    ----------
    string : str
        String to check

    Returns
    -------
        bool
            True if conversion was successful, False if not
    """
    try:
        float(string)
        return True
    except ValueError:
        return False


class AbstractColumnDefinition:
    """
    Abstract class to store columns

    Parameters
    ----------
    col_type: str
        Type of the column
    name: str
        Name of the column
    description: str
        Description of the column
    dtype:
        Data type of the column
    required: bool
        Bool that specifies if the column is required

    Methods
    -------
        is_allowed
            Check if cell is allowed
    """

    def __init__(
        self,
        col_type: str,
        name: str,
        description: str,
        dtype: str,
        required: bool,
    ):
        if col_type not in ["field", "variable", "unit", "value", "comment"]:
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
    def col_type(self):
        """Get col type"""
        return self._col_type

    @property
    def name(self):
        """Get name of the column"""
        return self._name

    @property
    def description(self):
        """Get description of the column"""
        return self._description

    @property
    def dtype(self):
        """Get data type of the column"""
        return self._dtype

    @property
    def required(self):
        """Return if column is required"""
        return self._required

    @property
    def default(self):
        """Get default value of the column"""
        return np.nan

    def is_allowed(self, cell: str | float | int) -> bool:
        """Check if Cell is allowed

        Parameters
        ----------
            cell: str | float | int
                Cell to check
        Returns
        -------
            bool
                If the cell is allowed
        """
        return True


class VariableDefinition(AbstractColumnDefinition):
    """
    Class to store variable columns

    Parameters
    ----------
    col_type: str
        Type of the column
    name: str
        Name of the column
    description: str
        Description of the column
    required: bool
        Bool that specifies if the column is required

    Methods
    -------
    is_allowed
        Check if cell is allowed
    """

    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type="variable",
            name=name,
            description=description,
            dtype="category",
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        if pd.isnull(cell):
            return not self._required
        return isinstance(cell, str) and cell in variables


class UnitDefinition(AbstractColumnDefinition):
    """
    Class to store Unit columns

    Parameters
    ----------
    col_type: str
        Type of the column
    name: str
        Name of the column
    description: str
        Description of the column
    required: bool
        Bool that specifies if the column is required

    Methods
    -------
    is_allowed
        Check if cell is allowed
    """

    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type="unit",
            name=name,
            description=description,
            dtype="category",
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        if pd.isnull(cell):
            return not self._required
        if not isinstance(cell, str):
            return False
        return cell in ureg


class ValueDefinition(AbstractColumnDefinition):
    """
    Class to store Value columns

    Parameters
    ----------
    col_type: str
        Type of the column
    name: str
        Name of the column
    description: str
        Description of the column
    required: bool
        Bool that specifies if the column is required

    Methods
    -------
    is_allowed
        Check if cell is allowed
    """

    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type="value",
            name=name,
            description=description,
            dtype="float",
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        if pd.isnull(cell):
            return not self._required
        return isinstance(cell, float | int)


class CommentDefinition(AbstractColumnDefinition):
    """
    Class to store comment columns

    Parameters
    ----------
    col_type: str
        Type of the column
    name: str
        Name of the column
    description: str
        Description of the column
    required: bool
        Bool that specifies if the column is required

    Methods
    -------
    is_allowed
        Check if cell is allowed
    """

    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type="comment",
            name=name,
            description=description,
            dtype="str",
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        return True
