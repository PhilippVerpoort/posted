from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from .. import defaults
from .columns import AbstractColumnDefinition


class AbstractFieldDefinition(AbstractColumnDefinition):
    """
    Abstract class to store fields

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
        coded: bool,
        codes: Optional[dict[str, str]] = None,
    ):
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
        self._coded: bool = coded
        self._codes: None | dict[str, str] = codes

        if self._coded:
            self._allowed_values: list[str] = list(self._codes) + ["*", "N/S"]
            if field_type == "component":
                self._allowed_values.append("#")

    @property
    def field_type(self) -> str:
        """Get field type"""
        return self._field_type

    @property
    def coded(self) -> bool:
        """Return if field is coded"""
        return self._coded

    @property
    def codes(self) -> None | dict[str, str]:
        """Get field codes"""
        return self._codes

    @property
    def default(self):
        """Get symbol for default value"""
        return "*" if self._field_type == "case" else "#"

    def _validate_values(self, s: pd.Series) -> pd.Series:
        """Check if cell is allowed"""
        if not self._coded:
            return super()._validate_values(s)
        return (
            s
            .str.split(",", expand=True)
            .apply(
                lambda col: col.str.strip()
            )
            .isin(self._allowed_values + [None])
            .all(axis=1)
        )

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
            [field_vals] * locs_asterisk.sum(),
            index=df.index[locs_asterisk]
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
        return (
            df
            .loc[df[col_id].isin(field_vals)]
            .reset_index(drop=True)
        )

    def select_and_expand(
        self,
        df: pd.DataFrame,
        col_id: str,
        field_vals: None | list,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Select and expand fields which are valid for multiple periods or other
        field vals.

        Parameters
        ----------
        df: pd.DataFrame
            DataFrame where fields should be selected and expanded
        col_id: str
            col_id of the column to be selected and expanded
        field_vals: None | list
            field_vals to select and expand
        **kwargs
            Additional keyword arguments

        Returns
        -------
        pd.DataFrame
            Dataframe where fields are selected and expanded

        """
        # get list of selected field values
        if field_vals is None:
            if col_id == "period":
                field_vals = defaults["period"]
            else:
                field_vals = (
                    df[col_id]
                    .replace("*", np.nan)
                    .dropna()
                    .unique()
                    .tolist()
                )
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
        df = self._select(df, col_id, field_vals, **kwargs)

        return df


class PeriodMode(Enum):
    NONE = 0
    INTERPOLATE = 1
    EXTRAPOLATE = 2
    INTER_AND_EXTRAPOLATION = 3

    @classmethod
    def from_str(cls, s):
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
    """
    Class to store Period fields.

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
        """Initialize parent class"""
        super().__init__(
            field_type="case",
            name=name,
            description=description,
            dtype="float",
            coded=False,
        )

    def _validate_values(self, s: pd.Series) -> pd.Series:
        """Check if cell is a float or *"""
        return s.str.match(r"(\*|^\d+)$")

    def _select(
        self,
        df: pd.DataFrame,
        col_id: str,
        field_vals: list[int | float],
        **kwargs,
    ) -> pd.DataFrame:
        # Perform a normal selection if arugment `period_mode` is NONE.
        if kwargs.get("period_mode") == PeriodMode.NONE:
            return super()._select(
                df=df,
                col_id=col_id,
                field_vals=field_vals,
                **kwargs,
            )

        # Group by identifying columns and select periods/generate time series
        # get list of groupable columns.
        group_cols = [c for c in df.columns if c not in [col_id, "value"]]

        # Perform groupby and do not drop NA values.
        grouped = df.groupby(group_cols, dropna=False)

        # Create return list.
        ret = []

        # Loop over groups.
        for keys, rows in grouped:
            # Get rows in group.
            rows = rows[[col_id, "value"]]

            # Get a list of periods that exist
            periods_exist = rows[col_id].unique()

            # Create dataframe containing rows for all requested periods.
            req_rows = pd.DataFrame.from_dict(
                {
                    f"{col_id}": field_vals,
                    f"{col_id}_upper": [
                        min(
                            [ip for ip in periods_exist if ip >= p],
                            default=np.nan,
                        )
                        for p in field_vals
                    ],
                    f"{col_id}_lower": [
                        max(
                            [ip for ip in periods_exist if ip <= p],
                            default=np.nan,
                        )
                        for p in field_vals
                    ],
                }
            )

            # Set missing columns from group.
            req_rows[group_cols] = keys

            # Check case.
            cond_match = req_rows[col_id].isin(periods_exist)
            cond_extrapolate = (
                req_rows[f"{col_id}_upper"].isna()
                | req_rows[f"{col_id}_lower"].isna()
            )

            # Match.
            rows_match = req_rows.loc[cond_match].merge(rows, on=col_id)

            # Extrapolate.
            if (
                kwargs.get("period_mode") in
                [PeriodMode.EXTRAPOLATE, PeriodMode.INTER_AND_EXTRAPOLATION]
            ):
                rows_extrapolate = (
                    req_rows.loc[~cond_match & cond_extrapolate]
                    .assign(
                        period_combined=lambda x: np.where(
                            x.notna()[f"{col_id}_upper"],
                            x[f"{col_id}_upper"],
                            x[f"{col_id}_lower"],
                        ),
                    )
                    .merge(
                        rows.rename(columns={col_id: f"{col_id}_combined"}),
                        on=f"{col_id}_combined",
                    )
                )
            else:
                rows_extrapolate = None

            # Interpolate.
            if (
                kwargs.get("period_mode") in
                [PeriodMode.INTERPOLATE, PeriodMode.INTER_AND_EXTRAPOLATION]
            ):
                rows_interpolate = (
                    req_rows.loc[~cond_match & ~cond_extrapolate]
                    .merge(
                        rows.rename(
                            columns={c: f"{c}_upper" for c in rows.columns}
                        ),
                        on=f"{col_id}_upper",
                    )
                    .merge(
                        rows.rename(
                            columns={c: f"{c}_lower" for c in rows.columns}
                        ),
                        on=f"{col_id}_lower",
                    )
                    .assign(
                        value=lambda row: row["value_lower"]
                        + (row[f"{col_id}_upper"] - row[col_id])
                        / (row[f"{col_id}_upper"] - row[f"{col_id}_lower"])
                        * (row["value_upper"] - row["value_lower"])
                    )
                )
            else:
                rows_interpolate = None

            # Combine into one dataframe and drop unused columns.
            rows_append = pd.concat([
                rows_match,
                rows_extrapolate,
                rows_interpolate,
            ])
            if rows_append.empty:
                continue
            rows_append.drop(
                columns=[
                    c
                    for c in [
                        f"{col_id}_upper",
                        f"{col_id}_lower",
                        f"{col_id}_combined",
                        "value_upper",
                        "value_lower",
                    ]
                    if c in rows_append.columns
                ],
                inplace=True,
            )

            # add to return list
            ret.append(rows_append)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True) if ret else df.iloc[[]]


class SourceFieldDefinition(AbstractFieldDefinition):
    """
    Class to store Source fields.

    Parameters
    ----------
    name: str
        Name of the field
    description: str
        Description of the field
    """

    def __init__(self, name: str, description: str):
        """Initialize parent class"""
        super().__init__(
            field_type="case",
            name=name,
            description=description,
            dtype="category",
            coded=True,
            codes={},  # Codes are set from BibTeX entries manually.
        )

    def set_bibtex_codes(self, codes: list[str]):
        self._codes = {c: c for c in codes}


class CustomFieldDefinition(AbstractFieldDefinition):
    """
    Class to store Custom fields

    Parameters
    ----------
    **field_specs:
        Specs of the custom fields
    """

    def __init__(self, **field_specs):
        """Check if the field specs are of the required type and format,
        initialize parent class"""
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
            coded=field_specs["coded"],
            codes=field_specs["codes"] if "codes" in field_specs else None,
        )
