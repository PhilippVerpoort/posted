from pathlib import Path
from re import escape
from typing import Optional
from warnings import warn

import numpy as np
import pandas as pd

from units import ureg

from . import databases, defaults, POSTEDException, POSTEDWarning
from .fields import AbstractFieldDefinition, base_columns, read_fields_comments, base_comments, base_fields
from .masking import Mask
from .read import read_yml_file, read_csv_file
from .columns import AbstractColumnDefinition, CommentDefinition
from .map_variables import map_variables


class TEDFInconsistencyException(Exception):
    """
    Exception raised for inconsistencies in TEDFs.

    Attributes:
        message -- message explaining the inconsistency
        row_id -- row where the inconsistency occurs
        col_id -- column where the inconsistency occurs
        file_path -- path to the file where the inconsistency occurs
    """
    def __init__(self, message: str = "Inconsistency detected", row_id: None | int = None,
                 col_id: None | str = None, file_path: None | Path = None):
        self.message: str = message
        self.row_id: None | int = row_id
        self.col_id: None | str = col_id
        self.file_path: None | Path = file_path

        # Add tokens at the end of the error message.
        message_tokens = []
        if file_path is not None:
            message_tokens.append(f"file \"{file_path}\"")
        if row_id is not None:
            message_tokens.append(f"line {row_id}")
        if col_id is not None:
            message_tokens.append(f"in column \"{col_id}\"")

        # Compose error message from tokens.
        exception_message: str = message
        if message_tokens:
            exception_message += (
                f"\n    " + (", ".join(message_tokens)).capitalize()
            )

        super().__init__(exception_message)


def new_inconsistency(raise_exception: bool, **kwargs) -> TEDFInconsistencyException:
    """
    Create new inconsistency object based on kwargs

    Parameters
    ----------

    """
    exception = TEDFInconsistencyException(**kwargs)
    if raise_exception:
        raise exception
    else:
        return exception


def _var_pattern(var_name: str, keep_token_names: bool = True) -> str:
    if keep_token_names:
        return r'\|'.join([
            rf'(?P<{t[1:]}>[^|]*)'
            if t[0] == '?' else
            rf'(?P<{t[1:]}>.*)'
            if t[0] == '*' else
            escape(t)
            for t in var_name.split('|')
        ])
    else:
        return r'\|'.join([
            r'(?:[^|]*)'
            if t[0] == '?' else
            rf'(?:.*)'
            if t[0] == '*' else
            escape(t)
            for t in var_name.split('|')
        ])


def _get_reference(ref_vars: pd.Series, vars: list):
    entries = ref_vars.loc[sum(ref_vars.str.fullmatch(v) for v in vars) > 0]
    return entries.value_counts().idxmax()


class TEDF:
    """
    Class to handle Techno-Economic Data Files (TEDFs).

    Parameters
    ----------
    parent_variable: str
        Variable from which Data should be collected
    database_id: str, default: public
        Database from which to load data
    file_path: Path, optional
        File Path from which to load file
    data: pd.DataFrame, optional
        Specific Technoeconomic data

    Methods
    ----------
    load
        Load TEDF if it has not been read yet.
    read
        Read TEDF from CSV file.
    write
        Write TEDF to CSV file.
    check
        Check if TEDF is consistent.
    check_row
        Check that row in TEDF is consistent and return all
        inconsistencies found for row.
    """
    # Typed declarations.
    _df: pd.DataFrame | None
    _columns: list[str]
    _parent_variable: str | None
    _variables: dict[str, dict]
    _fields: dict[str, AbstractFieldDefinition]
    _comments: dict[str, CommentDefinition]
    _masks: list[Mask]

    def __init__(self,
                 df: pd.DataFrame,
                 parent_variable: str | None = None,
                 variables: dict | None = None,
                 fields: dict | None = None,
                 comments: dict | None = None,
                 masks: list[Mask] | None = None):
        """Initialise parent class and object fields"""
        self._parent_variable = parent_variable
        self._variables = variables or {}
        self._fields = fields or {}
        self._comments = comments or {}
        self._masks = masks or []

        self._columns = (
            list(self._fields) +
            [c for c in base_columns if c not in self._fields] +
            [c for c in self._comments if c not in base_columns]
        )

        unknown_cols = [c for c in df if c not in self._columns]
        if unknown_cols:
            i = len(unknown_cols)
            warn(f"Unknown column{'s'[:i^1]} treated as comment{'s'[:i^1]}: " +
                 ','.join(unknown_cols), POSTEDWarning)
            self._comments |= {c: CommentDefinition() for c in unknown_cols}
            self._columns += unknown_cols

        self._df = df[self._columns]

    @property
    def raw(self) -> pd.DataFrame:
        return self._df

    @property
    def parent_variable(self) -> str:
        return self._parent_variable

    @property
    def fields(self) -> dict[str, AbstractFieldDefinition]:
        return self._fields

    @property
    def comments(self) -> dict[str, CommentDefinition]:
        return self._comments

    @property
    def columns(self) -> dict[str, AbstractColumnDefinition]:
        cols = base_columns | self._fields | self._comments
        return {
            col: cols[col]
            for col in self._df.columns
        }

    @property
    def variables(self) -> dict[str, dict]:
        return self._variables

    @classmethod
    def load(cls, parent_variable: str):
        if not isinstance(parent_variable, str):
            raise POSTEDException("Argument `variable` must be a valid string.")

        rel_path = "/".join(parent_variable.split("|"))

        # Load data.
        df = pd.concat([
            read_csv_file(database_path / "tedfs" / (rel_path + ".csv"))
            for database_path in databases.values()
        ])

        # Load meta.
        columns = {}
        variables = {}
        masks = []

        for database_path in databases.values():
            fpath = database_path / "tedfs" / (rel_path + ".yaml")
            if fpath.is_file():
                fcontents = read_yml_file(fpath)
                if "columns" in fcontents:
                    columns |= fcontents["columns"]
                if "variables" in fcontents:
                    if "predefined" in fcontents["variables"]:
                        for predefined in fcontents["variables"]["predefined"]:
                            variables |= read_yml_file(database_path / "variables" / "definitions" / (predefined + ".yaml"))
                    if "custom" in fcontents["variables"]:
                        variables |= fcontents["variables"]["custom"]

            fpath = database_path / "masks" / (rel_path + ".yaml")
            if fpath.is_file():
                fcontents = read_yml_file(fpath)
                masks += [
                    Mask(**mask_specs)
                    for mask_specs in fcontents
                ]

        custom_fields, custom_comments = read_fields_comments(columns)
        fields = base_fields | custom_fields
        comments = base_comments | custom_comments

        return TEDF(
            df=df,
            parent_variable=parent_variable,
            variables=variables,
            fields=fields,
            comments=comments,
            masks=masks,
        )

    def normalise(self,
                  units: Optional[dict[str, str]] = None,
                  with_parent: bool = False) -> pd.DataFrame | None:
        """
        Normalise data by converting reference values to 1.0 and converting to
        default unit for each variable.

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
        normalised.insert(normalised.columns.tolist().index("uncertainty")+1, "unit", np.nan)
        normalised["unit"] = normalised["variable"].map(units)
        normalised.insert(normalised.columns.tolist().index("unit")+1, "reference_value", 1.0)
        normalised.insert(normalised.columns.tolist().index("reference_value")+1, "reference_unit", np.nan)
        normalised["reference_unit"] = normalised["reference_variable"].map(units)

        # Prepend parent variable.
        if with_parent:
            if self._parent_variable is None:
                raise Exception("Can only prepend parent variable if not None.")
            normalised["variable"] = normalised["variable"].str.cat([self._parent_variable], sep="|")

        return normalised

    def _normalise(self, units: dict[str, str] | None) -> tuple[pd.DataFrame, dict[str, str]]:
        units = units or {}

        # Get full list of variables and corresponding units.
        df_vars_units = pd.concat([
            self._df[["variable", "unit"]],
            self._df[["reference_variable", "reference_unit"]]
            .dropna(how="all")
            .rename(columns={"reference_variable": "variable", "reference_unit": "unit"})
        ])

        # Determine default units for all variables.
        currencies_pattern = rf"({'|'.join(ureg.currencies)})_\d{{4}}"
        units = (
            df_vars_units
            .assign(
                unit=df_vars_units["unit"].str.replace(currencies_pattern, defaults["currency"], regex=True),
            )
            .groupby("variable")["unit"]
            .agg(lambda x: x.mode()[0])
            .to_dict()
        ) | units

        # Determine unit conversion factors.
        conv_factors = (
            df_vars_units
            .groupby("variable")["unit"]
            .apply(lambda group: pd.Series({u: ureg(u).to(units[group.name]).m for u in group.unique()}))
            .reset_index()
            .rename(columns={"unit": "conv_factor", "level_1": "unit"})
        )

        # For now, we simply assume that there is no column called `conv_factor`.
        assert(s not in self._df for s in ["factor", "conv_factor", "reference_conv_factor"])

        # Then we can just merge in the conversion factors and apply.
        normalised = (
            self._df
            .merge(
                conv_factors,
                on=["variable", "unit"],
                how="left",
            )
            .merge(
                conv_factors.rename(columns=lambda s: "reference_" + s),
                on=["reference_variable", "reference_unit"],
                how="left",
            )
            .assign(
                factor=lambda df:
                df["conv_factor"]
                / (df["reference_value"] * df["reference_conv_factor"])
                .where(df["reference_variable"].notnull(), other=1.0),
                value=lambda df: df["value"] * df["factor"],
                uncertainty=lambda df: df["uncertainty"] * df["factor"],
            )
            .drop(columns=[
                "factor",
                "conv_factor",
                "reference_conv_factor",
                "reference_value",
                "unit",
                "reference_unit",
            ])
        )

        # Return normalised data and variable units.
        return normalised, units

    # Prepare data for selection.
    def select(self,
               units: Optional[dict[str, str]] = None,
               reference_activity: Optional[str] = None,
               reference_capacity: Optional[str] = None,
               drop_singular_fields: bool = True,
               extrapolate_period: bool = True,
               with_parent: bool = False,
               expand_not_specified: bool | list[str] = True,
               **field_vals_select) -> pd.DataFrame:
        """
        Select desired data from the dataframe.

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
        extrapolate_period: bool, optional
            If True, extrapolate values by extrapolation, if no value for this period is given
        with_parent: bool, optional
            Whether to prepend the parent variable. Default is False.
        expand_not_specified: bool | list[str], optional
            Whether to expand fields with value `N/S` (not specified) to all allowed values. If `True` is passed, then
            allow `N/S` is expanded for all fields. If a list of strings is passed, then only the contained fields are
            expanded. If False is passed, then no field is expanded. Default is True.
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
            extrapolate_period=extrapolate_period,
            expand_not_specified=expand_not_specified,
            **field_vals_select,
        )

        # Insert reference variable, unit, and reference unit.
        selected["reference_variable"] = selected["variable"].map(ref_vars)
        selected["unit"] = selected["variable"].map(units)
        selected["reference_unit"] = selected["reference_variable"].map(units)

        # Prepend parent variable.
        if with_parent:
            if self._parent_variable is None:
                raise Exception("Can only prepend parent variable if not None.")
            selected["variable"] = selected["variable"].str.cat([self._parent_variable], sep="|")

        # Order columns.
        selected = selected[[
            col
            for col in self._columns
            if col in selected
        ]]

        return selected

    def _select(self,
                units: dict[str, str] | None,
                reference_activity: str | None,
                reference_capacity: str | None,
                drop_singular_fields: bool,
                extrapolate_period: bool,
                expand_not_specified: bool | list[str],
                **field_vals_select) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
        # Start from normalised data.
        normalised, units = self._normalise(units)
        selected = normalised

        # Drop columns containing comments and the uncertainty column (which is currently unsupported).
        selected.drop(
            columns=['uncertainty'] + list(self._comments),
            inplace=True,
        )

        # Raise exception if fields listed in arguments that is not in the columns.
        for field_id in field_vals_select:
            if not any(field_id == col_id for col_id in self._fields):
                raise Exception(f"Field '{field_id}' does not exist and cannot be used for selection.")

        # Order fields for selection: period must be selected last due to the interpolation.
        fields_select_order = (
            list(field_vals_select) +
            [col for col in self._fields if col not in field_vals_select and col != "period"] +
            (["period"] if "period" in self._fields else [])
        )

        # Expand non-specified values in fields if requested.
        if expand_not_specified is True:
            expand_not_specified = self._fields
        elif expand_not_specified is False:
            expand_not_specified = []
        else:
            if any(f not in self._fields for f in expand_not_specified):
                raise Exception("N/S values can only be expanded on fields: " +
                                ", ".join(self._fields))
        for field_id in expand_not_specified:
            selected[field_id].replace("N/S", "*")

        # Select and expand fields.
        for field_id in fields_select_order:
            selected = self._fields[field_id].select_and_expand(
                df=selected,
                col_id=field_id,
                field_vals=field_vals_select.get(field_id, None),
                extrapolate_period=extrapolate_period,
                expand_not_specified=expand_not_specified,
            )

        # Check for duplicates.
        field_var_cols = selected[list(self._fields) + ["variable", "reference_variable"]]
        duplicates = field_var_cols.duplicated()
        if duplicates.any():
            raise POSTEDException("Duplicate field/variable entries:\n" + str(field_var_cols.loc[duplicates]))

        # Drop fields with only one value.
        if drop_singular_fields:
            selected.drop(
                columns=[
                    col_id for col_id in self._fields
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
        reference_activity = reference_activity or _get_reference(self._df["reference_variable"], activities)
        capacities = [
            _var_pattern(var_name, keep_token_names=False)
            for var_name, var_specs in self._variables.items()
            if var_specs.get("reference", None) == "capacity"
        ]
        reference_capacity = reference_capacity or _get_reference(self._df["reference_variable"], capacities)

        # Map variables.
        fields = [c for c in self._fields if c in selected]
        mapped, units = map_variables(
            selected=selected,
            units=units,
            fields=fields,
            activities=activities,
            capacities=capacities,
            reference_activity=reference_activity,
            reference_capacity=reference_capacity,
        )

        # Drop rows with failed mappings.
        mapped = (
            mapped
            .dropna(subset='value')
            .reset_index(drop=True)
        )

        # Get dict of variables and corresponding reference variables.
        ref_vars = (
            mapped[['variable', 'reference_variable']]
            .drop_duplicates()
            .set_index('variable')['reference_variable']
        )

        # Check for multiple reference variables per reported variable.
        if not ref_vars.index.is_unique:
            duplicated_vars = ref_vars.index[ref_vars.index.duplicated()]
            raise Exception(f"Multiple reference variables per reported variable found:\n" +
                            ref_vars[duplicated_vars].to_string() + "\n\n" +
                            "These are the rows:\n" +
                            mapped.loc[mapped["variable"].isin(duplicated_vars)].to_string())
        ref_vars = ref_vars.to_dict()

        # Remove reference_variable column.
        mapped.drop(columns=['reference_variable'], inplace=True)

        # Return.
        return mapped, units, ref_vars


    def aggregate(self,
                  units: Optional[dict[str, str]] = None,
                  reference_activity: Optional[str] = None,
                  reference_capacity: Optional[str] = None,
                  drop_singular_fields: bool = True,
                  extrapolate_period: bool = True,
                  agg: Optional[str | list[str] | tuple[str]] = None,
                  masks: Optional[list[Mask]] = None,
                  masks_database: bool = True,
                  expand_not_specified: bool | list[str] = True,
                  **field_vals_select) -> pd.DataFrame:
        """
        Aggregates data based on specified parameters, applies masks,
        and cleans up the resulting DataFrame.

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
        extrapolate_period: bool, optional
            If True, extrapolate values by extrapolation, if no value
            for this period is given
        expand_not_specified: bool | list[str], optional
            Whether to expand fields with value `N/S` (not specified) to all allowed values. If `True` is passed, then
            allow `N/S` is expanded for all fields. If a list of strings is passed, then only the contained fields are
            expanded. If False is passed, then no field is expanded. Default is True.
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
            extrapolate_period=extrapolate_period,
            drop_singular_fields=drop_singular_fields,
            expand_not_specified=expand_not_specified,
            **field_vals_select
        )

        # Compile masks from databases and from argument into one list.
        if masks is not None and any(not isinstance(m, Mask) for m in masks):
            raise Exception("Function argument 'masks' must contain a list of "
                            "posted.masking.Mask objects.")
        masks = (self._masks if masks_database else []) + (masks or [])

        # Aggregate over fields that should be aggregated.
        component_fields = [
            col_id for col_id, field in self._fields.items()
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
                    raise Exception(f"Field ID in argument 'agg' must be a "
                                    f"string but found: {a}")
                if not any(a == col_id for col_id in self._fields):
                    raise Exception(f"Field ID in argument 'agg' is not a "
                                    f"valid field: {a}")

        # Aggregate over component fields.
        group_cols = [
            c for c in selected.columns
            if not (c == 'value' or (c in agg and c in component_fields))
        ]
        aggregated = (
            selected
            .groupby(group_cols, dropna=False)
            .agg({'value': 'sum'})
            .reset_index()
        )

        # Aggregate over cases fields.
        group_cols = [
            c for c in aggregated.columns
            if not (c == 'value' or c in agg)
        ]
        ret = []
        for keys, rows in aggregated.groupby(group_cols, dropna=False):
            # Set default weights to 1.0.
            rows = rows.assign(weight=1.0)

            # Update weights by applying masks.
            for mask in masks:
                if mask.matches(rows):
                    rows['weight'] *= mask.get_weights(rows)

            # Drop all rows with weights equal to nan.
            rows.dropna(subset='weight', inplace=True)

            if not rows.empty:
                # Aggregate with weights.
                out = (
                    rows
                    .groupby(group_cols, dropna=False)[['value', 'weight']]
                    .apply(lambda cols: pd.Series({
                        'value': np.average(
                            cols['value'],
                            weights=cols['weight'],
                        ),
                    }))
                )

                # Add to return list.
                ret.append(out)
        if not ret:
            return pd.DataFrame(columns=group_cols + ["variable", "value", "unit"])
        aggregated = pd.concat(ret).reset_index()

        # Append reference variables.
        var_ref_unique = {
            ref_vars[var]
            for var in aggregated["variable"].unique()
            if not pd.isnull(ref_vars[var])
        }
        agg_append = []
        for ref_var in var_ref_unique:
            agg_append.append(pd.DataFrame({
                'variable': [ref_var],
                'value': [1.0],
            } | {
                col_id: ['*']
                for col_id, field in self._fields.items()
                if col_id in aggregated
            }))
        if agg_append:
            agg_append = pd.concat(agg_append).reset_index(drop=True)
            for col_id, field in self._fields.items():
                if col_id not in aggregated:
                    continue
                agg_append = field.select_and_expand(
                    agg_append,
                    col_id,
                    aggregated[col_id].unique().tolist(),
                )
            aggregated = (
                pd.concat([aggregated, agg_append], ignore_index=True)
                .sort_values(by=group_cols + ["variable"])
                .reset_index(drop=True)
            )

        # Insert unit.
        aggregated["unit"] = aggregated["variable"].map(units)

        # Order columns.
        aggregated = aggregated[[
            col
            for col in self._columns
            if col in aggregated
        ]]

        # Return.
        return aggregated
