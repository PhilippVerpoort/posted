"""Definition and handling of fields in TEDFs."""

from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from .. import POSTEDException, defaults
from .columns import AbstractColumnDefinition


class AbstractFieldDefinition(AbstractColumnDefinition):
    """Abstract class to store field definition.

    Parameters
    ----------
    field_type: str
        Type of the field
    name: str
        Name of the field
    description: str
        Description of the field
    dtype: str
        Data type of the field
    multi: bool
        Whether multiple comma-separated values can be entered in one cell.
    coded: bool
        If the field is coded
    coded: Optional[dict[str,str]], optional
        Codes for the field


    Methods
    -------
    is_allowed
        Check if cell is allowed
    select_and_expand
        Select and expand fields

    """

    def __init__(
        self,
        field_type: str,
        name: str,
        description: str,
        dtype: str,
        multi: bool,
        coded: bool,
        codes: Optional[dict[str, str]] = None,
    ):
        """Initialise field definition."""
        if field_type not in ["case", "component"]:
            raise Exception("Fields must be of type case or component.")
        super().__init__(
            col_type="field",
            name=name,
            description=description,
            dtype=dtype,
            required=True,
        )

        self._field_type: str = field_type
        self._multi: bool = multi
        self._coded: bool = coded
        self._codes: None | dict[str, str] = codes

        if self._coded and not isinstance(self._codes, dict):
            raise POSTEDException("Codes of field must be dict of strings.")

    @property
    def field_type(self) -> str:
        """Get field type."""
        return self._field_type

    @property
    def coded(self) -> bool:
        """Return whether field is coded."""
        return self._coded

    @property
    def codes(self) -> None | dict[str, str]:
        """Get field codes."""
        return self._codes

    @property
    def allowed_values(self) -> list[str]:
        """Get list of allowed values."""
        if not self._coded:
            return []
        allowed_values = list(self._codes or []) + ["*", "N/S"]
        if self._field_type == "component":
            allowed_values.append("#")
        return allowed_values

    @property
    def default(self):
        """Get symbol for default value."""
        return "*" if self._field_type == "case" else "#"

    def _validate_values(self, s: pd.Series) -> pd.Series:
        """Check if cell is allowed."""
        if not self._coded:
            return super()._validate_values(s)
        if self._multi:
            return (
                s.str.split(",", expand=True)
                .apply(lambda col: col.str.strip())
                .isin(self.allowed_values + [None])
                .all(axis=1)
            )
        else:
            return s.isin(self.allowed_values)

    def _expand(
        self,
        df: pd.DataFrame,
        col_id: str,
        field_vals: list[str],
        **kwargs,
    ) -> pd.DataFrame:
        # Convert comma-separated values to multiple rows.
        df[col_id] = df[col_id].str.split(",")
        df = df.explode(col_id)
        df[col_id] = df[col_id].str.strip()

        # Convert asterisk into multiple values.
        locs_asterisk = df[col_id] == "*"
        df.loc[locs_asterisk, col_id] = pd.Series(
            [field_vals] * locs_asterisk.sum(), index=df.index[locs_asterisk]
        )
        df = df.explode(col_id)

        # Convert `period` column to integers.
        if isinstance(self, PeriodFieldDefinition):
            df[col_id] = df[col_id].astype(int)

        return df

    def _select(
        self, df: pd.DataFrame, col_id: str, field_vals: list, **kwargs
    ):
        # Select fields.
        return df.loc[df[col_id].isin(field_vals)].reset_index(drop=True)

    def select_and_expand(
        self,
        df: pd.DataFrame,
        col_id: str,
        field_vals: None | list,
        **kwargs,
    ) -> pd.DataFrame:
        """Select and expand fields.

        Select observations that match specific field values and expand
        observations to all field values that they apply to.

        Parameters
        ----------
        df: pd.DataFrame
            DataFrame where fields should be selected and expanded.
        col_id: str
            col_id of the column to be selected and expanded.
        field_vals: None | list
            field_vals to select and expand.
        **kwargs
            Additional keyword arguments.

        Returns
        -------
        pd.DataFrame
            Dataframe where fields are selected and expanded

        """
        # Get list of selected field values.
        keep_vals = []
        if field_vals is None:
            if col_id == "period":
                field_vals = defaults["period"]
            else:
                # Collect individual values from (comma-separated) cells. The
                # asterisk expands to these but not to N/S. Rows with N/S are
                # nonetheless kept.
                vals = df[col_id].str.split(",").explode().str.strip()
                field_vals = vals[~vals.isin(["*", "N/S"])].unique().tolist()
                keep_vals = ["N/S"]
        else:
            # Ensure that `field_vals` is a list of elements (not tuple or
            # single value).
            if isinstance(field_vals, tuple):
                field_vals = list(field_vals)
            elif not isinstance(field_vals, list):
                field_vals = [field_vals]

            if "*" in field_vals:
                raise Exception(
                    f"Selected values for field '{col_id}' must "
                    f"not contain the asterisk. Omit the "
                    f"'{col_id}' argument to select all entries."
                )

        df = self._expand(df, col_id, field_vals, **kwargs)
        df = self._select(df, col_id, field_vals + keep_vals, **kwargs)

        return df


class PeriodMode(Enum):
    """Mode for dealing with period column(s) when selecting.

    Period-type fields columns can be used for interpolation or extrapolation
    when field values are selected that are not observed in the raw data. When
    using PeriodMode.NONE, period-type fields behave like other case fields.
    """

    NONE = 0
    INTERPOLATE = 1
    EXTRAPOLATE = 2
    INTER_AND_EXTRAPOLATION = 3

    @classmethod
    def from_str(cls, s):
        """Obtain enum element from string."""
        if s == "inter":
            return cls.INTERPOLATE
        elif s == "extra":
            return cls.EXTRAPOLATE
        elif s == "inter+extra":
            return cls.INTER_AND_EXTRAPOLATION
        try:
            return cls[s.upper()]
        except KeyError:
            raise ValueError(f"'{s}' is not a valid {cls.__name__}")


class PeriodFieldDefinition(AbstractFieldDefinition):
    """Class to store Period fields.

    Parameters
    ----------
    name: str
        Name of the field
    description: str
        Description of the field

    Methods
    -------
    is_allowed
        Checks if cell is allowed

    """

    def __init__(self, name: str, description: str):
        """Initialise field.

        Initialise custom field definition by initialising parent class.
        """
        super().__init__(
            field_type="case",
            name=name,
            description=description,
            dtype="float",
            multi=True,
            coded=False,
        )

    def _validate_values(self, s: pd.Series) -> pd.Series:
        """Check if cell is allowed.

        That is the case if it is either * or comma-separated digits.
        """
        if not self._coded:
            return super()._validate_values(s)
        if self._multi:
            return (
                s.str.split(",", expand=True)
                .apply(lambda col: col.str.strip())
                .apply(lambda col: col.str.match(r"(\*|^\d+)$"))
                .all(axis=1)
            )
        else:
            return s.isin(self.allowed_values)

    def _select(
        self,
        df: pd.DataFrame,
        col_id: str,
        field_vals: list[int | float],
        **kwargs,
    ) -> pd.DataFrame:
        """Select periods, interpolating and extrapolating as requested.

        For each group of rows sharing identical values in all columns
        except `col_id` and `value`, generate rows for all requested
        periods by exactly matching observed periods, by taking the value
        of the nearest observed period if no period is observed on one
        side (extrapolation), or by linearly interpolating between the
        nearest observed periods on both sides. Periods with missing
        values count as not observed.

        Rows are returned in group order, and within each group in the
        order of the requested periods. Group key columns are returned
        with object dtype.

        The implementation pivots the data to a group-by-period matrix and
        performs the selection with a handful of matrix operations, which
        avoids the per-group pandas overhead of looping over groups and
        merging per-group time series.
        """
        # Perform a normal selection if arugment `period_mode` is NONE.
        if kwargs.get("period_mode") == PeriodMode.NONE:
            return super()._select(
                df=df,
                col_id=col_id,
                field_vals=field_vals,
                **kwargs,
            )

        period_mode = kwargs.get("period_mode")
        extrapolate = period_mode in [
            PeriodMode.EXTRAPOLATE,
            PeriodMode.INTER_AND_EXTRAPOLATION,
        ]
        interpolate = period_mode in [
            PeriodMode.INTERPOLATE,
            PeriodMode.INTER_AND_EXTRAPOLATION,
        ]

        if df.empty:
            return df

        # Group by identifying columns. Group ids follow the group order of
        # a groupby iteration; one representative row per group provides
        # the group keys.
        group_cols = [c for c in df.columns if c not in [col_id, "value"]]
        group_ids = df.groupby(group_cols, dropna=False).ngroup()
        duplicates = df.duplicated(subset=group_cols + [col_id])
        if duplicates.any():
            raise POSTEDException(
                f"Duplicate {col_id} entries for one combination of "
                "fields and variable:\n" + str(df.loc[duplicates])
            )
        keys = (
            df.assign(_group=group_ids)
            .groupby("_group")
            .head(1)
            .set_index("_group")[group_cols]
            .sort_index()
            .astype(object)
        )
        # Use the same null value as groupby itself for missing keys.
        keys = keys.where(keys.notna(), np.nan)

        # Pivot to a matrix with one row per group and one column per
        # observed period. Periods with missing values count as not
        # observed.
        wide = df.assign(_group=group_ids).pivot(
            index="_group", columns=col_id, values="value"
        )
        column_order = wide.columns.to_numpy().astype(float).argsort()
        periods = wide.columns.to_numpy()[column_order].astype(float)
        values = wide.to_numpy("float64")[:, column_order]
        observed = ~np.isnan(values)

        req = pd.Series(list(field_vals))
        req_periods = req.astype(float).to_numpy()
        k = len(periods)

        # For each group and requested period, locate the nearest observed
        # periods below and above. Argmax over booleans locates the first
        # observed column, searching the reversed matrix the last one.
        upper = np.full((len(keys), len(req_periods)), np.nan)
        lower = np.full_like(upper, np.nan)
        upper_col = np.full(upper.shape, -1)
        lower_col = np.full(upper.shape, -1)
        match = np.zeros(upper.shape, bool)
        match_value = np.full(upper.shape, np.nan)
        for j, period in enumerate(req_periods):
            above = observed & (periods >= period)
            loc = above.any(axis=1)
            upper_col[loc, j] = above[loc].argmax(axis=1)
            upper[loc, j] = periods[upper_col[loc, j]]
            below = observed & (periods <= period)
            loc = below.any(axis=1)
            lower_col[loc, j] = k - 1 - below[loc, ::-1].argmax(axis=1)
            lower[loc, j] = periods[lower_col[loc, j]]
            observed_col = np.flatnonzero(periods == period)
            if len(observed_col):
                match[:, j] = observed[:, observed_col[0]]
                match_value[:, j] = values[:, observed_col[0]]

        # For unobserved requested periods, take the value of the nearest
        # observed period if no period is observed on one side
        # (extrapolation), or linearly interpolate between the values on
        # both sides.
        one_sided = np.isnan(upper) | np.isnan(lower)
        extra = ~match & one_sided
        inter = ~match & ~one_sided
        lower_value = np.take_along_axis(
            values, np.clip(lower_col, 0, None), axis=1
        )
        upper_value = np.take_along_axis(
            values, np.clip(upper_col, 0, None), axis=1
        )
        extra_value = np.where(np.isnan(upper), lower_value, upper_value)
        with np.errstate(invalid="ignore"):
            inter_value = lower_value + (req_periods - lower) / (
                upper - lower
            ) * (upper_value - lower_value)

        # Assemble the returned rows: per group, in group order, all
        # requested periods that are matched, extrapolated or interpolated
        # as permitted by `period_mode`, in the order of the requests.
        keep = match | (extra & extrapolate) | (inter & interpolate)
        group_idx, req_idx = np.nonzero(keep)
        if not len(group_idx):
            return df.iloc[[]]
        value = np.select(
            [match[group_idx, req_idx], extra[group_idx, req_idx]],
            [match_value[group_idx, req_idx], extra_value[group_idx, req_idx]],
            inter_value[group_idx, req_idx],
        )
        return pd.DataFrame(
            {
                col_id: req.to_numpy()[req_idx],
                **{c: keys[c].to_numpy()[group_idx] for c in group_cols},
                "value": value,
            }
        )


class SourceFieldDefinition(AbstractFieldDefinition):
    """Class to store source field definition.

    Parameters
    ----------
    name: str
        Name of the field
    description: str
        Description of the field

    """

    def __init__(self, name: str, description: str):
        """Initialize field."""
        super().__init__(
            field_type="case",
            name=name,
            description=description,
            dtype="category",
            multi=False,
            coded=True,
            codes={},  # Codes are set from BibTeX entries manually.
        )

    def set_bibtex_codes(self, codes: list[str]):
        """Set allowed codes of the field based on the BibTeX identifiers."""
        self._codes = {c: c for c in codes}


class CustomFieldDefinition(AbstractFieldDefinition):
    """Class to store custom field definition.

    Parameters
    ----------
    **field_specs:
        Specs of the custom fields

    """

    def __init__(self, **field_specs):
        """Initialise field.

        Initialise custom field definition by initialising parent class. Check
        if the field specs are of the required type and format first.
        """
        if not (
            "type" in field_specs
            and isinstance(field_specs["type"], str)
            and field_specs["type"] in ["case", "component"]
        ):
            raise Exception(
                "Field type must be provided and equal to 'case' or "
                "'component'."
            )
        if not (
            "name" in field_specs and isinstance(field_specs["name"], str)
        ):
            raise Exception("Field name must be provided and of type string.")
        if not (
            "description" in field_specs
            and isinstance(field_specs["description"], str)
        ):
            raise Exception(
                "Field description must be provided and of type string."
            )
        if not (
            "coded" in field_specs and isinstance(field_specs["coded"], bool)
        ):
            raise Exception("Field coded must be provided and of type bool.")
        if field_specs["coded"] and not (
            "codes" in field_specs and isinstance(field_specs["codes"], dict)
        ):
            raise Exception(
                "Field codes must be provided and contain a dict of possible "
                "codes."
            )

        super().__init__(
            field_type=field_specs["type"],
            name=field_specs["name"],
            description=field_specs["description"],
            dtype="category",
            multi=True,
            coded=field_specs["coded"],
            codes=field_specs["codes"] if "codes" in field_specs else None,
        )
