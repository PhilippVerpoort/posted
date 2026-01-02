from __future__ import annotations

from pathlib import Path
from re import escape
from typing import TYPE_CHECKING, Optional
from warnings import warn

import numpy as np
import pandas as pd
from cet_units import ureg

from posted import (
    POSTEDException,
    POSTEDWarning,
    databases,
    defaults,
)

from .._columns import (
    AbstractColumnDefinition,
    AbstractFieldDefinition,
    CommentDefinition,
    _base_column_src,
    _read_fields_comments,
    base_columns_other,
    base_columns_src_detail,
)
from .._columns.fields import PeriodMode
from .._read import read_tedf_from_csv, read_yaml
from ._masking import Mask
from .mapping import _map_variables

if TYPE_CHECKING:
    from ipydatagrid import DataGrid


def _var_pattern(var_name: str, keep_token_names: bool = True) -> str:
    if keep_token_names:
        return r"\|".join(
            [
                rf"(?P<{t[1:]}>[^|]*)"
                if t[0] == "?"
                else rf"(?P<{t[1:]}>.*)"
                if t[0] == "*"
                else escape(t)
                for t in var_name.split("|")
            ]
        )
    else:
        return r"\|".join(
            [
                r"(?:[^|]*)"
                if t[0] == "?"
                else r"(?:.*)"
                if t[0] == "*"
                else escape(t)
                for t in var_name.split("|")
            ]
        )


def _get_reference(ref_vars: pd.Series, vars: list):
    if not vars:
        return None
    entries = ref_vars.loc[sum(ref_vars.str.fullmatch(v) for v in vars) > 0]
    return entries.value_counts().idxmax()


def _get_file_path(
    database_id: str,
    parent_variable: str,
    ftype: str = "tedfs",
    ending: str = "csv",
) -> Path:
    database_path = databases[database_id]
    rel_path = "/".join(parent_variable.split("|"))

    return database_path / ftype / (rel_path + "." + ending)


class TEDF:
    """Class for handling Techno-Economic Data Frames (TEDFs).

    This class is used for loading TEDFs from CSV files and performing various
    steps in the NOSLAG (normalise-select-aggregate) framework.

    Attributes
    ----------
    raw: pd.DataFrame
        The underlying raw data.
    parent_variable: str
        Parent variable to assume as prefix to variables found in data.
    fields: dict
        Fields defined for this TEDF.
    columns: dict
        Columns (fields and base columns) defined for this TEDF.
    variables: dict
        Variables defined for this TEDF.
    validated: None | pd.DataFrame
        Validation state of dataframe if validation has been run.

    Methods
    -------
    load(parent_variable: str, database_id: str = "public")
        Load TEDF if it has not been read yet.
    edit_data()
        Set up ipydatawidget for interactively editing raw data.
    update_data(df: pd.DataFrame)
        Overwrite raw data from a provided dataframe.
    save_data()
        Write raw data to file (based on database_id and parent_variable).
    validate()
        Validate raw data loaded in TEDF.

    """

    def __init__(
        self,
        df: pd.DataFrame,
        parent_variable: str | None = None,
        database_id: str | None = None,
        variables: dict | None = None,
        custom_fields: dict | None = None,
        custom_comments: dict | None = None,
        masks: list[Mask] | None = None,
        mappings: list[str] | None = None,
    ):
        """Initialise parent class and object fields.

        Parameters
        ----------
        df: pd.DataFrame,
            Raw TEDF data.
        parent_variable: str, default: None
            Parent variable to assume as prefix to variables found in data.
        database_id: str, default: None
            Database from which to load data.
        variables: dict, default: None
            Variable definitions to use for data.
        custom_fields: dict, default: None
            Custom field column definitions.
        custom_comments: dict, default: None
            Custom comment column definitions.
        masks: list, default: None
            Default masks to apply when selecting.
        mappings:
            Mappings to apply when selecting.

        """
        self._parent_variable: str | None = parent_variable
        self._database_id: str | None = database_id
        self._variables: dict[str, dict] = variables or {}
        self._masks: list[Mask] = masks or []
        self._validated: pd.DataFrame | None = None
        self._mappings: list[str] | None = mappings or []

        # Combine all fields.
        source_column = _base_column_src()
        self._fields: dict[str, AbstractFieldDefinition] = {
            "source": source_column
        } | (custom_fields or {})

        # Combine all comments.
        self._comments: dict[str, CommentDefinition] = (
            base_columns_src_detail
            | {"comment": CommentDefinition}
            | (custom_comments or {})
        )

        # Combine all columns.
        self._columns: dict[str, AbstractColumnDefinition] = (
            {"source": source_column}
            | base_columns_src_detail
            | (custom_fields or {})
            | base_columns_other
        )

        # Deal with unknown columns.
        unknown_cols = [c for c in df.columns if c not in self._columns]
        if unknown_cols:
            i = len(unknown_cols)
            warn(
                f"Unknown column{'s'[: i ^ 1]} treated as "
                f"comment{'s'[: i ^ 1]}: "
                + ", ".join(str(c) for c in unknown_cols),
                POSTEDWarning,
            )
            unknown_cols = {
                c: CommentDefinition(
                    name=str(c),
                    description="",
                    required=False,
                )
                for c in unknown_cols
            }
            self._comments |= unknown_cols
            self._columns |= unknown_cols

        # Add missing columns.
        missing_cols = [c for c in self._columns if c not in df.columns]
        if missing_cols:
            df[missing_cols] = ""

        self._df: pd.DataFrame = df[list(self._columns)]

    @property
    def raw(self) -> pd.DataFrame:
        return self._df

    @property
    def parent_variable(self) -> None | str:
        return self._parent_variable

    @property
    def fields(self) -> dict[str, AbstractFieldDefinition]:
        return self._fields

    @property
    def comments(self) -> dict[str, CommentDefinition]:
        return self._comments

    @property
    def columns(self) -> dict[str, AbstractColumnDefinition]:
        return self._columns

    @property
    def variables(self) -> dict[str, dict]:
        return self._variables

    @property
    def validated(self) -> None | pd.DataFrame:
        return self._validated

    @classmethod
    def load(cls, parent_variable: str, database_id: str = "public"):
        if not isinstance(parent_variable, str):
            raise POSTEDException(
                "Argument `variable` must be a valid string."
            )
        if database_id not in databases:
            raise POSTEDException(
                "Argument `database_id` must correspond to a valid ID in the "
                "`databases` registered in the POSTED package."
            )

        # Load data.
        fpath = _get_file_path(database_id, parent_variable)
        df = read_tedf_from_csv(fpath)

        # Load config.
        variables = {}
        custom_columns = {}
        masks = []
        mappings: list[str] = []

        for database_path in databases.values():
            fpath = _get_file_path(database_id, parent_variable, ending="yaml")
            if fpath.is_file():
                fcontents = read_yaml(fpath)
                if "variables" in fcontents:
                    if "predefined" in fcontents["variables"]:
                        for predefined in fcontents["variables"]["predefined"]:
                            variables |= read_yaml(
                                database_path
                                / "variables"
                                / "definitions"
                                / (predefined + ".yaml")
                            )
                    if "custom" in fcontents["variables"]:
                        variables |= fcontents["variables"]["custom"]
                if "columns" in fcontents:
                    custom_columns |= fcontents["columns"]
                if "mappings" in fcontents:
                    mappings += fcontents["mappings"]

            fpath = _get_file_path(
                database_id,
                parent_variable,
                ftype="masks",
                ending="yaml",
            )
            if fpath.is_file():
                fcontents = read_yaml(fpath)
                masks += [Mask(**mask_specs) for mask_specs in fcontents]

        custom_fields, custom_comments = _read_fields_comments(custom_columns)

        return TEDF(
            df=df,
            parent_variable=parent_variable,
            database_id=database_id,
            variables=variables,
            custom_fields=custom_fields,
            custom_comments=custom_comments,
            masks=masks,
            mappings=mappings,
        )

    def edit_data(self) -> DataGrid:
        from .._widget import build_edit_grid

        return build_edit_grid(self)

    def update_data(self, df: pd.DataFrame):
        self._df = df

    def save_data(self):
        if self._database_id is None or self._parent_variable is None:
            raise POSTEDException(
                "Cannot save TEDF as file without database "
                "ID and parent variable."
            )
        fpath = _get_file_path(self._database_id, self._parent_variable)

        self._df.to_csv(
            fpath,
            sep=",",
            quotechar='"',
            encoding="utf-8",
            index=False,
        )

    def validate(self):
        # Load sources for validation.
        from ..sources import load_sources

        if self._database_id is not None:
            sources = list(load_sources(database_id=self._database_id).entries)
            self._fields["source"].set_bibtex_codes(sources)

        self._validated = pd.DataFrame()
        for col_id, col_def in self._columns.items():
            self._validated[col_id] = col_def.validate(self._df[col_id])

    def _prepare(self) -> pd.DataFrame:
        df = self._df.mask(self._df == "")

        # Value, uncertainty, and reference value must be floats.
        for col_id in ["value", "uncertainty", "reference_value"]:
            df[col_id] = pd.to_numeric(df[col_id])

        # TODO: Turn fields into categories.

        return df

    def normalise(
        self, units: Optional[dict[str, str]] = None, with_parent: bool = False
    ) -> pd.DataFrame | None:
        """Normalise data.

        Normalise units, reference units, and reference values by multiplying
        value column with respective conversion factor needed to convert
        reference values to 1.0 and all units to harmonised units for each
        variable.

        Parameters
        ----------
        units: dict[str,str], optional
            Dictionary with key-value pairs of units to use for variables.
        with_parent: bool, optional
            Whether to prepend the parent variable. Default is False.

        Returns
        -------
        pd.DataFrame
            DataFrame containing normalised raw data.

        """
        normalised, units = self._normalise(units)

        # Insert unit, reference value, and reference unit.
        normalised.insert(
            normalised.columns.tolist().index("uncertainty") + 1,
            "unit",
            np.nan,
        )
        normalised["unit"] = normalised["variable"].map(units)
        normalised.insert(
            normalised.columns.tolist().index("unit") + 1,
            "reference_value",
            1.0,
        )
        normalised.insert(
            normalised.columns.tolist().index("reference_value") + 1,
            "reference_unit",
            np.nan,
        )
        normalised["reference_unit"] = normalised["reference_variable"].map(
            units
        )

        # Prepend parent variable.
        if with_parent:
            if self._parent_variable is None:
                raise Exception(
                    "Can only prepend parent variable if not None."
                )
            normalised["variable"] = (
                self._parent_variable + "|" + normalised["variable"]
            )

        # Order columns.
        normalised = normalised[
            [col for col in self._columns if col in normalised]
        ]

        return normalised

    def _normalise(
        self, units: dict[str, str] | None
    ) -> tuple[pd.DataFrame, dict[str, str]]:
        units = units or {}
        prepared = self._prepare()

        # Get full list of variables and corresponding units.
        df_vars_units = pd.concat(
            [
                prepared[["variable", "unit"]],
                prepared[["reference_variable", "reference_unit"]]
                .dropna(how="all")
                .rename(
                    columns={
                        "reference_variable": "variable",
                        "reference_unit": "unit",
                    }
                ),
            ]
        )

        # Determine default units for all variables.
        currencies_pattern = rf"({'|'.join(ureg.currencies)})_\d{{4}}"
        units = (
            df_vars_units.assign(
                unit=df_vars_units["unit"].str.replace(
                    currencies_pattern, defaults["currency"], regex=True
                ),
            )
            .groupby("variable")["unit"]
            .agg(lambda x: x.mode()[0])
            .to_dict()
        ) | units

        # Determine unit conversion factors.
        conv_factors = (
            df_vars_units.groupby("variable")["unit"]
            .apply(
                lambda group: pd.Series(
                    {
                        u: ureg(u).to(units[group.name]).m
                        for u in group.unique()
                    }
                )
            )
            .reset_index()
            .rename(columns={"unit": "conv_factor", "level_1": "unit"})
        )

        # For now, we simply assume that no column `conv_factor` exists.
        assert (
            s not in prepared
            for s in ["factor", "conv_factor", "reference_conv_factor"]
        )

        # Merge conversion factors.
        normalised = prepared.merge(
            conv_factors,
            on=["variable", "unit"],
            how="left",
        )

        if normalised["reference_variable"].notnull().any():
            normalised = normalised.merge(
                conv_factors.rename(columns=lambda s: "reference_" + s),
                on=["reference_variable", "reference_unit"],
                how="left",
            )
        else:
            normalised = normalised.assign(reference_conv_factor=1.0)

        # Assign updated values.
        normalised = normalised.assign(
            factor=lambda df: (
                df["conv_factor"]
                / (df["reference_value"] * df["reference_conv_factor"]).where(
                    df["reference_variable"].notnull(),
                    other=1.0,
                )
            ),
            value=lambda df: df["value"] * df["factor"],
            uncertainty=lambda df: df["uncertainty"] * df["factor"],
        ).drop(
            columns=[
                "factor",
                "conv_factor",
                "reference_conv_factor",
                "reference_value",
                "unit",
                "reference_unit",
            ]
        )

        # Return normalised data and variable units.
        return normalised, units

    # Prepare data for selection.
    def select(
        self,
        units: Optional[dict[str, str]] = None,
        reference_activity: Optional[str] = None,
        reference_capacity: Optional[str] = None,
        drop_singular_fields: bool = True,
        period_mode: str | PeriodMode = PeriodMode.INTER_AND_EXTRAPOLATION,
        expand_not_specified: bool | list[str] = True,
        with_parent: bool = False,
        append_references: bool = False,
        **field_vals_select,
    ) -> pd.DataFrame:
        """Select desired data from the dataframe.

        Parameters
        ----------
        units: dict[str,str], optional
            Dictionary with key-value pairs of units to use for variables.
        reference_activity: str, optional
            Reference activity.
        reference_capacity: str, optional
            Reference capacity.
        drop_singular_fields: bool, optional
            If True, drop custom fields with only one value
        period_mode: str | PeriodMode, optional
            Whether to interpolate, extrapolate, interpolate and extrapolate,
            or perform no such action with the values based on the period
            field.
        expand_not_specified: bool | list[str], optional
            Whether to expand fields with value `N/S` (not specified) to all
            allowed values. If `True` is passed, then allow `N/S` is expanded
            for all fields. If a list of strings is passed, then only the
            contained fields are expanded. If False is passed, then no field
            is expanded. Default is True.
        with_parent: bool, optional
            Whether to prepend the parent variable. Default is False.
        append_references: bool, optional
            Whether to append reference activities and reference capacities as
            additional rows instead of leaving them as separate columns.
        **field_vals_select
            IDs of values to select

        Returns
        -------
        pd.DataFrame
            DataFrame with selected Values

        """
        selected, units, ref_vars = self._select(
            units=units,
            reference_activity=reference_activity,
            reference_capacity=reference_capacity,
            drop_singular_fields=drop_singular_fields,
            period_mode=period_mode,
            expand_not_specified=expand_not_specified,
            **field_vals_select,
        )

        # Finalise dataframe and return.
        return self._finalise(
            df=selected,
            append_references=append_references,
            group_cols=[c for c in self._fields if c in selected],
            ref_vars=ref_vars,
            units=units,
            with_parent=with_parent,
        )

    def _select(
        self,
        units: dict[str, str] | None,
        reference_activity: str | None,
        reference_capacity: str | None,
        drop_singular_fields: bool,
        period_mode: str | PeriodMode,
        expand_not_specified: bool | list[str],
        **field_vals_select,
    ) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
        # Start from normalised data.
        normalised, units = self._normalise(units)
        selected = normalised

        # Drop columns containing comments and the uncertainty column (which
        # is currently unsupported).
        selected.drop(
            columns=["uncertainty"] + list(self._comments),
            inplace=True,
        )

        # Raise exception if fields given as arguments are not in the columns.
        for field_id in field_vals_select:
            if not any(field_id == col_id for col_id in self._fields):
                raise Exception(
                    f"Field '{field_id}' does not exist and cannot be used "
                    f"for selection."
                )

        # Order fields before selection. Columns of type PeriodFieldDefinition
        # must be selected last due to the interpolation.
        fields_select_order = list(set(field_vals_select) | set(self._fields))
        if "period" in fields_select_order:
            fields_select_order.remove("period")
            fields_select_order.append("period")

        # Expand non-specified values in fields if requested.
        if expand_not_specified is True:
            expand_not_specified = self._fields
        elif expand_not_specified is False:
            expand_not_specified = []
        else:
            if any(f not in self._fields for f in expand_not_specified):
                raise Exception(
                    "N/S values can only be expanded on fields: "
                    + ", ".join(self._fields)
                )
        for field_id in expand_not_specified:
            selected[field_id].replace("N/S", "*")

        # Convert str to PeriodMode if needed.
        if isinstance(period_mode, str):
            period_mode = PeriodMode.from_str(period_mode)

        # Select and expand fields.
        for field_id in fields_select_order:
            selected = self._fields[field_id].select_and_expand(
                df=selected,
                col_id=field_id,
                field_vals=field_vals_select.get(field_id, None),
                expand_not_specified=expand_not_specified,
                period_mode=period_mode,
            )

        # Check for duplicates.
        field_var_cols = selected[
            list(self._fields) + ["variable", "reference_variable"]
        ]
        duplicates = field_var_cols.duplicated()
        if duplicates.any():
            raise POSTEDException(
                "Duplicate field/variable entries:\n"
                + str(field_var_cols.loc[duplicates])
            )

        # Drop fields with only one value.
        if drop_singular_fields:
            selected.drop(
                columns=[
                    col_id
                    for col_id in self._fields
                    if selected[col_id].nunique() < 2
                ],
                inplace=True,
            )

        # Determine activity and capacity variables and their references.
        activities = [
            _var_pattern(var_name, keep_token_names=False)
            for var_name, var_specs in self._variables.items()
            if var_specs.get("reference", None) == "activity"
        ]
        reference_activity = reference_activity or _get_reference(
            self._df["reference_variable"], activities
        )
        capacities = [
            _var_pattern(var_name, keep_token_names=False)
            for var_name, var_specs in self._variables.items()
            if var_specs.get("reference", None) == "capacity"
        ]
        reference_capacity = reference_capacity or _get_reference(
            self._df["reference_variable"], capacities
        )

        # Map variables.
        fields = [c for c in self._fields if c in selected]
        mapped, units = _map_variables(
            selected=selected,
            units=units,
            fields=fields,
            activities=activities,
            capacities=capacities,
            reference_activity=reference_activity,
            reference_capacity=reference_capacity,
            database_id=self._database_id,
            mappings=self._mappings,
        )

        # Drop rows with failed mappings.
        mapped = mapped.dropna(subset="value").reset_index(drop=True)

        # Get dict of variables and corresponding reference variables.
        ref_vars = (
            mapped[["variable", "reference_variable"]]
            .drop_duplicates()
            .set_index("variable")["reference_variable"]
        )

        # Check for multiple reference variables per reported variable.
        if not ref_vars.index.is_unique:
            duplicated_vars = ref_vars.index[ref_vars.index.duplicated()]
            raise Exception(
                "Multiple reference variables per reported variable found:\n"
                + ref_vars[duplicated_vars].to_string()
                + "\n\n"
                + "These are the rows:\n"
                + mapped.loc[
                    mapped["variable"].isin(duplicated_vars)
                ].to_string()
            )
        ref_vars = ref_vars.to_dict()

        # Remove reference_variable column.
        mapped.drop(columns=["reference_variable"], inplace=True)

        # Return.
        return mapped, units, ref_vars

    def aggregate(
        self,
        units: Optional[dict[str, str]] = None,
        reference_activity: Optional[str] = None,
        reference_capacity: Optional[str] = None,
        drop_singular_fields: bool = True,
        period_mode: PeriodMode | str = PeriodMode.INTER_AND_EXTRAPOLATION,
        agg: Optional[str | list[str] | tuple[str]] = None,
        masks: Optional[list[Mask]] = None,
        masks_database: bool = True,
        expand_not_specified: bool | list[str] = True,
        with_parent: bool = False,
        append_references: bool = False,
        **field_vals_select,
    ) -> pd.DataFrame:
        """Aggregate data.

        Perform aggregation based on specified parameters, apply masks, and
        clean up the resulting DataFrame.

        Parameters
        ----------
        units: dict[str, str], optional
            Dictionary with key, value paris of variables to override
        reference_activity: str, optional
            The activity variable to align all activities on.
        reference_capacity: str, optional
            The capacity variable to align all capacities on.
        drop_singular_fields: bool, optional
            If True, drop custom fields with only one value
        period_mode: str | PeriodMode, optional
            Whether to interpolate, extrapolate, interpolate and extrapolate,
            or perform no such action with the values based on the period
            field.
        expand_not_specified: bool | list[str], optional
            Whether to expand fields with value `N/S` (not specified) to all
            allowed values. If `True` is passed, then allow `N/S` is expanded
            for all fields. If a list of strings is passed, then only the
            contained fields are expanded. If False is passed, then no field
            is expanded. Default is True.
        with_parent: bool, optional
            Whether to prepend the parent variable. Default is False.
        agg : Optional[str | list[str] | tuple[str]]
            Specifies which fields to aggregate over.
        masks : Optional[list[Mask]]
            Specifies a list of Mask objects that will be applied to the
            data during aggregation. These masks can be used to filter
            or weight the data based on certain conditions defined in
            the Mask objects.
        masks_database : bool, optional
            Determines whether to include masks from databases in the
            aggregation process. If set to `True`, masks from databases
            will be included along with any masks provided as function
            arguments. If set to `False`, only the masks provided as
            function arguments will be applied.
        append_references: bool, optional
            Whether to append reference activities and reference capacities as
            additional rows instead of leaving them as separate columns.
        **field_vals_select:
            Field names and values provided as keyword arguments. For
            instance, `case=["case1", "case2"]` will select the two respective
            cases if `case` is a field column in the underlying TEDF.

        Returns
        -------
        pd.DataFrame
            The `aggregate` method returns a pandas DataFrame that has
            been cleaned up and aggregated based on the specified
            parameters and input data. The method performs aggregation
            over component fields and cases fields, applies weights
            based on masks, drops rows with NaN weights, aggregates with
            weights, inserts reference variables, sorts columns and
            rows, rounds values, and inserts units before returning the
            final cleaned and aggregated DataFrame.

        """
        # Run select().
        selected, units, ref_vars = self._select(
            units=units,
            reference_activity=reference_activity,
            reference_capacity=reference_capacity,
            period_mode=period_mode,
            drop_singular_fields=drop_singular_fields,
            expand_not_specified=expand_not_specified,
            **field_vals_select,
        )

        # Compile masks from databases and from argument into one list.
        if masks is not None and any(not isinstance(m, Mask) for m in masks):
            raise Exception(
                "Function argument 'masks' must contain a list of "
                "posted.masking.Mask objects."
            )
        masks = (self._masks if masks_database else []) + (masks or [])

        # Aggregate over fields that should be aggregated.
        component_fields = [
            col_id
            for col_id, field in self._fields.items()
            if field.field_type == "component"
        ]
        if agg is None:
            agg = component_fields + ["source"]
        else:
            if isinstance(agg, tuple):
                agg = list(agg)
            elif not isinstance(agg, list):
                agg = [agg]
            for a in agg:
                if not isinstance(a, str):
                    raise Exception(
                        f"Field ID in argument 'agg' must be a "
                        f"string but found: {a}"
                    )
                if not any(a == col_id for col_id in self._fields):
                    raise Exception(
                        f"Field ID in argument 'agg' is not a valid field: {a}"
                    )

        # Aggregate over component fields.
        group_cols = [
            c
            for c in selected.columns
            if not (c == "value" or (c in agg and c in component_fields))
        ]
        aggregated = (
            selected.groupby(group_cols, dropna=False)
            .agg({"value": "sum"})
            .reset_index()
        )

        # Aggregate over cases fields.
        group_cols = [
            c for c in aggregated.columns if not (c == "value" or c in agg)
        ]
        ret = []
        for keys, rows in aggregated.groupby(group_cols, dropna=False):
            # Set default weights to 1.0.
            rows = rows.assign(weight=1.0)

            # Update weights by applying masks.
            for mask in masks:
                if mask.matches(rows):
                    rows["weight"] *= mask.get_weights(rows)

            # Drop all rows with weights equal to nan.
            rows.dropna(subset="weight", inplace=True)

            if not rows.empty:
                # Aggregate with weights.
                out = rows.groupby(group_cols, dropna=False)[
                    ["value", "weight"]
                ].apply(
                    lambda cols: pd.Series(
                        {
                            "value": np.average(
                                cols["value"],
                                weights=cols["weight"],
                            ),
                        }
                    )
                )

                # Add to return list.
                ret.append(out)

        # If nothing is found, return empty dataframe.
        if not ret:
            add_cols = (
                []
                if append_references
                else ["reference_variable", "reference_unit"]
            )
            return pd.DataFrame(
                columns=group_cols + ["variable", "value", "unit"] + add_cols
            )
        aggregated = pd.concat(ret).reset_index()

        # Finalise dataframe and return.
        return self._finalise(
            df=aggregated,
            append_references=append_references,
            group_cols=group_cols,
            ref_vars=ref_vars,
            units=units,
            with_parent=with_parent,
        )

    def _finalise(
        self,
        df: pd.DataFrame,
        append_references: bool,
        group_cols: list[str],
        ref_vars: dict[str, str],
        units: dict[str, str],
        with_parent: bool,
    ) -> pd.DataFrame:
        # Append reference variables.
        if any(isinstance(v, str) and v for v in ref_vars.values()):
            if append_references:
                var_ref_unique = {
                    ref_vars[var]
                    for var in df["variable"].unique()
                    if not pd.isnull(ref_vars[var])
                }
                to_append = []
                for ref_var in var_ref_unique:
                    to_append.append(
                        pd.DataFrame(
                            {
                                "variable": [ref_var],
                                "value": [1.0],
                            }
                            | {
                                col_id: ["*"]
                                for col_id, field in self._fields.items()
                                if col_id in df
                            }
                        )
                    )

                if to_append:
                    to_append = pd.concat(to_append, ignore_index=True)
                    for col_id, field in self._fields.items():
                        if col_id not in df.columns:
                            continue
                        to_append = field.select_and_expand(
                            to_append,
                            col_id,
                            df[col_id].unique().tolist(),
                        )
                    df = (
                        pd.concat([df, to_append], ignore_index=True)
                        .sort_values(by=group_cols + ["variable"])
                        .reset_index(drop=True)
                    )
            else:
                df["reference_variable"] = df["variable"].map(ref_vars)
                df["reference_unit"] = df["reference_variable"].map(units)

        # Insert unit(s).
        df["unit"] = df["variable"].map(units)

        # Prepend parent variable.
        if with_parent:
            if self._parent_variable is None:
                raise Exception(
                    "Can only prepend parent variable if not None."
                )
            df["variable"] = self._parent_variable + "|" + df["variable"]

        # Order columns.
        df = df[[col for col in self._columns if col in df]]

        return df
