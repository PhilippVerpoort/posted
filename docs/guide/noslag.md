---
title: NO-SL-AG
---

# NO-SL-AG

NO-SL-AG (also written NOSLAG) stands for **normalise, select, aggregate**. It is the workflow that converts the raw data of a TEDF into harmonised data. The three steps are implemented as methods of the `TEDF` class and build on each other: `select()` begins by normalising, and `aggregate()` begins by selecting. Users typically call only the method whose output they need.

| Step | Method | Purpose | Output |
|---|---|---|---|
| Normalise | `TEDF.normalise()` | Common units, deflated currencies, reference values of one | Raw data with converted values, same columns as the TEDF |
| Select | `TEDF.select()` | Resolve fields, pick cases, interpolate periods, harmonise variables and references | One row per source, case, component, and variable |
| Aggregate | `TEDF.aggregate()` | Sum over components, weighted average over sources and other cases | One row per remaining case and variable |

Throughout this section, examples use the electrolysis TEDF with the fields `subtech`, `size`, `country`, and `period`, and the direct-reduction TEDF with the fields `carbon_capture`, `mode`, `component`, and `period`.

## Normalise

Normalisation makes values from different sources numerically comparable without changing what they represent. It performs the following operations on every row.

1. **Parse numbers.** The `value`, `uncertainty`, and `reference_value` columns are converted to floating-point numbers. Empty cells become missing values.
2. **Determine target units.** One target unit is assigned to each variable, whether it appears in the `variable` or the `reference_variable` column. The procedure is described under [Units](units.md#default-units-and-overrides): currencies are rewritten to the default currency, the most frequent unit is chosen, and entries in the `units` argument override the choice.
3. **Convert units.** For each row, the value is multiplied by the conversion factor from the reported unit to the target unit of its variable, and divided by the conversion factor from the reported reference unit to the target unit of its reference variable. Currency conversion includes deflation between base years.
4. **Scale to a reference value of one.** The value is divided by the reference value, so that every row expresses the variable per one unit of its reference variable. The uncertainty is scaled by the same factor.
5. **Write back.** The `unit` and `reference_unit` columns hold the target units, and `reference_value` holds one for all rows with a reference variable.

The output of `normalise()` has the same columns as the raw TEDF, including fields and comment columns, and the same number of rows. A row that reports 1566 EUR_2020 per 1 kg_H2/day thus becomes a row reporting 1884 EUR_2024 per 1 kg_H2/day if the default currency is EUR_2024 and the most frequent reference unit is kg_H2/day.

```python
tedf.normalise()
tedf.normalise(units={"CAPEX": "USD_2022", "Output Capacity|Hydrogen": "kW_H2_LHV"})
```

Normalisation does not change which rows exist, what the variables are called, or which reference variable each row uses. These aspects are handled by the selection step.

## Select

Selection turns normalised data into a consistent set of rows for the cases a user is interested in. It consists of the following stages, applied in order.

1. **Drop auxiliary columns.** The `uncertainty` column and all comment columns (`source_detail`, `comment`, custom comment columns) are removed.
2. **Resolve fields.** For each field, special cell values are expanded and the requested values are kept. The `period` field is resolved last, because it may involve interpolation. This stage is described in detail below.
3. **Check for duplicates.** After expansion, each combination of field values, variable, and reference variable must occur only once. Otherwise an exception is raised.
4. **Drop singular fields.** Fields with fewer than two distinct values in the result are removed, unless `drop_singular_fields=False`. This includes `source` and `period`. For instance, if only the year 2030 is requested, the `period` column does not appear in the output.
5. **Determine reference activity and reference capacity.** Unless given as arguments, the reference activity is the most frequent reference variable among activity-type variables in the raw data, and the reference capacity is the most frequent reference variable among capacity-type variables.
6. **Apply variable mappings.** The mappings listed in the metadata file are applied in order. Rows that a mapping could not process are reported as warnings and dropped.
7. **Check reference variables.** Every variable must have exactly one reference variable in the result. Otherwise an exception is raised.
8. **Finalise.** The `unit` and `reference_unit` columns are added. If `with_parent=True`, the parent variable is prepended to variable names. If `append_references=True`, reference variables are added as rows with value one instead of being listed in separate columns.

The output has one row per source, case, component, and variable, with the columns `source`, the remaining fields, `variable`, `reference_variable`, `value`, `unit`, and `reference_unit`.

```python
tedf.select(period=[2030, 2050], subtech=["AEL", "PEM"], size="100 MW")
```

### Field selection and expansion

The `select()` and `aggregate()` methods of `TEDF` accept one keyword argument per field, e.g. `select(subtech=["AEL", "PEM"], period=[2030, 2040])`. For each field, the framework first expands the special cell values described in the [format guide](format.md#field-cell-values) and then keeps the rows that match the requested values.

**Requested values.** If a field is given as an argument, the listed values are requested. A single value is accepted in place of a list. If a field is omitted, all values that occur in that column of the TEDF are requested, after splitting comma-separated cells. The asterisk and `N/S` do not count as values here. The `period` field is the exception: when omitted, the default period from `posted.defaults` is requested instead of all observed years. The asterisk itself must not be passed as a requested value; omit the argument instead. Passing a keyword argument that is not a field of the TEDF raises an exception.

**Comma-separated cells** are split into one row per value before selection. An entry with `AEL, PEM` therefore behaves like two identical entries, one for `AEL` and one for `PEM`.

**Asterisk.** Each row with `*` is replaced by one copy per requested value. If `subtech=["AEL"]` is requested, a `*` row becomes a single `AEL` row. If the field is omitted, the row is copied once for each value observed in the column. The asterisk never expands to `N/S` unless `N/S` is requested explicitly.

**Not specified.** The treatment of `N/S` depends on the `expand_not_specified` argument.

* `True` (default): `N/S` is converted to `*` before expansion and therefore behaves like the asterisk. The value is then available for every requested case, and `N/S` does not appear in the output.
* `False`: `N/S` is kept as a field value of its own. Rows with `N/S` are returned alongside the other values when the field is omitted, and can be requested explicitly, e.g. `size=["N/S"]`. Asterisk rows are not expanded to `N/S` in this case.
* A list of field names: `N/S` is expanded only in the listed fields and kept in all others.

Expanding `N/S` is convenient when the unspecified entries should contribute to all cases, for instance when a source reports a cost without stating the plant size and this cost is to be averaged with size-specific costs from other sources. Keeping `N/S` is preferable when unspecified entries should be inspected or filtered separately.

**Hash.** The `#` entry of component fields is not expanded. It is an ordinary field value that labels the undivided total. During aggregation, all component values of a source and case are summed, including `#`.

**Duplicates.** After expansion, each combination of source, field values, variable, and reference variable must occur only once. A TEDF that reports the same variable from the same source both with `*` and with an explicit value for the same field therefore raises an error during selection. Contributors should report either the wildcard or the explicit cases, not both.

**Example.** Consider a `size` field with the entries below and no `size` argument.

| entry | expanded with `expand_not_specified=True` | expanded with `expand_not_specified=False` |
|---|---|---|
| `1 MW` | `1 MW` | `1 MW` |
| `1 MW, 100 MW` | `1 MW`, `100 MW` | `1 MW`, `100 MW` |
| `*` | `1 MW`, `100 MW`, `5 MW` | `1 MW`, `100 MW`, `5 MW` |
| `N/S` | `1 MW`, `100 MW`, `5 MW` | `N/S` |
| `5 MW` | `5 MW` | `5 MW` |

### Periods

The `period` field is a case field with numeric values, which allows values to be estimated for years that no source reports. After the asterisk has been expanded and the column has been converted to integers, the rows are grouped by all other columns, i.e. by source, remaining fields, variable, and reference variable. Within each group, the requested periods are served as follows, depending on the `period_mode` argument.

| `period_mode` | Requested year is reported | Requested year lies between reported years | Requested year lies outside reported years |
|---|---|---|---|
| `"none"` | kept | dropped | dropped |
| `"inter"` | kept | linear interpolation between the nearest reported years | dropped |
| `"extra"` | kept | dropped | value of the nearest reported year |
| `"inter+extra"` (default) | kept | linear interpolation | value of the nearest reported year |

Extrapolation is constant, i.e. a projection for 2050 is carried forward unchanged to 2060. Interpolation and extrapolation are performed per source. If a source reports only one year, that value is used for all requested years in the extrapolating modes. The values `PeriodMode.NONE`, `PeriodMode.INTERPOLATE`, `PeriodMode.EXTRAPOLATE`, and `PeriodMode.INTER_AND_EXTRAPOLATION` from `posted._columns.fields` may be passed instead of the strings.

If no `period` argument is given, the default period `posted.defaults["period"]`, which is `[2025]` unless changed, is requested. To obtain all reported years without interpolation, pass the observed years explicitly together with `period_mode="none"`.

### Reference activity and reference capacity

Within one TEDF, sources refer their data to different quantities. One source reports CAPEX per unit of hydrogen output capacity, another per unit of electrical input capacity. One source reports electricity demand per unit of hydrogen, another reports hydrogen output per unit of electricity. Harmonised data needs a single convention.

The selection step establishes one **reference activity** for all activity-type variables and one **reference capacity** for all capacity-type variables. Which variables count as activity-type or capacity-type is declared in the variable definitions through the `reference` attribute. By default, the references are the most frequent reference variables of their kind in the raw data. They can be set explicitly through the arguments `reference_activity` and `reference_capacity`.

```python
tedf.select(
    reference_activity="Output|Hydrogen",
    reference_capacity="Output Capacity|Hydrogen",
)
```

Rebasing data onto these references is performed by the variable mappings described next.

### Variable mappings

Variable mappings transform rows during selection. They are stored as Python modules in the database and are listed per TEDF in its metadata file. The mappings of the public database, in the order in which technology TEDFs apply them, are the following.

| Mapping | Transforms | Into | Notes |
|---|---|---|---|
| `full_load_hours` | `FLH` (full-load hours per year) | `OCF` (operational capacity factor) | Division by one year. |
| `fixed_opex_relative` | `OPEX Fixed Relative` (share of CAPEX per year) | `OPEX Fixed` per unit of capacity | Needs `CAPEX` from the same source and case. Warns and drops the row otherwise. |
| `fixed_opex_specific` | `OPEX Fixed Specific` (per unit of product) | `OPEX Fixed` per unit of capacity | Divides by the `OCF` of the same source and case. Assumes an OCF of 100% with a warning if none or several are found. |
| `capacities_to_activities` | Ratios of two capacities, e.g. `Input Capacity|Electricity` per `Output Capacity|Hydrogen` | Ratios of the corresponding activities, e.g. `Input|Electricity` per `Output|Hydrogen` | Multiplies both sides by one year. |
| `activities` | All activity-type rows whose reference differs from the reference activity, and all capacity-type rows whose reference differs from the reference capacity | Rows expressed relative to the reference activity and reference capacity | See below. |

The `activities` mapping is the central harmonisation step. For each source and case, it collects all activity-type rows, e.g. electricity input per hydrogen output and hydrogen output per electricity input, and solves the resulting system of linear relations for the ratio of every flow to the reference activity. A row whose variable is the reference activity itself is inverted, so that `Output|Hydrogen` per `Input|Electricity` becomes `Input|Electricity` per `Output|Hydrogen`. Capacity-type rows are rescaled with the same ratios, so that CAPEX per hydrogen output capacity becomes CAPEX per electricity input capacity if the latter is the reference capacity. Variables of the form `Total Input Capacity|X` and `Total Output Capacity|X` are converted to the total of the reference capacity. If a source does not provide the ratios needed to connect a row to the reference, the row cannot be rebased. It is reported in a warning and dropped.

Group-wise mappings operate on groups formed by all fields that remain after singular fields are dropped. This includes component fields. A relative OPEX reported for one component is therefore matched with the CAPEX of the same component only.

## Aggregate

Aggregation condenses the selected data to one value per case and variable. It proceeds as follows.

1. **Select.** The selection step is run with the same arguments.
2. **Collect masks.** Masks from the database for this TEDF are combined with masks passed in the `masks` argument. Database masks can be excluded with `masks_database=False`.
3. **Determine fields to aggregate.** The `agg` argument lists the fields to aggregate over. By default, these are all component fields and `source`. Case fields other than `source` are not aggregated unless listed.
4. **Sum over components.** For component fields in `agg`, values are summed within each combination of the remaining columns. A source reporting labour and maintenance as separate components of fixed OPEX thus contributes their sum.
5. **Average over cases.** For each combination of the remaining columns, the rows that differ only in the aggregated case fields are combined. Every row starts with a weight of one. Each mask whose `where` conditions hold for the group multiplies the weights by the weights it assigns. Rows with an undefined weight are dropped. The remaining rows are combined by a weighted arithmetic mean.
6. **Finalise.** As for selection: units are added, the parent variable is optionally prepended, and reference variables are optionally appended as rows.

```python
# Default: sum over components, average over sources.
tedf.aggregate(period=[2030])

# Additionally average over plant sizes.
tedf.aggregate(period=[2030], agg=["source", "size"])

# Keep sources and components; only apply masks and reshape.
tedf.aggregate(period=[2030], agg=[])
```

The arithmetic mean is a deliberate default. Alternative aggregation statistics, e.g. the median, are not currently supported. Weighting through masks allows the influence of individual sources to be adjusted.

The output has one row per remaining case and variable, with the remaining fields followed by `variable`, `reference_variable`, `value`, `unit`, and `reference_unit`. If no rows remain, an empty frame with these columns is returned.

### Masks

A mask is an object of class `posted.noslag.Mask` with the following parts.

* `where`: one or more conditions that every row of a group must satisfy for the mask to apply to that group. Groups are formed by the columns that are not aggregated over, so a `where` condition typically restricts the variable or a case field, e.g. `"variable == 'CAPEX'"`.
* `use`: one or more conditions that identify rows within the group, e.g. `"source == 'Example-2020'"`.
* `weight`: one weight per `use` condition. Defaults to one.
* `other`: the weight for rows that match none of the `use` conditions. Defaults to `nan`, which excludes those rows.

Weights of several applicable masks are multiplied. A row with a weight of `nan` is excluded from the average. A mask with only a `use` condition and the default `other` therefore acts as a filter that keeps only the matching rows. A mask with `weight: nan` and `other: 1.0` excludes the matching rows and keeps the rest. Conditions may be given as strings for `DataFrame.eval()`, as dictionaries mapping columns to required values, or as callables applied to each row.

```python
from posted.noslag import Mask

# Exclude the CAPEX values of one source, keep everything else.
exclude = Mask(
    where="variable == 'CAPEX'",
    use="source == 'Example-2020'",
    weight=float("nan"),
    other=1.0,
)

# Give one source twice the weight of the others.
emphasise = Mask(use="source == 'DEA-TDRF-2023'", weight=2.0, other=1.0)

tedf.aggregate(period=[2030], masks=[exclude, emphasise])
```

Masks stored in the `masks/` directory of a database are loaded automatically with the TEDF and applied by default. Their file format is described in the [Format](format.md#masks) section.

### Appending references

By default, the output lists the reference variable and its unit in separate columns. Some downstream tools prefer every quantity as a row of its own. With `append_references=True`, the reference columns are omitted and each reference variable is added as a row with the value one for every combination of remaining field values.

```python
tedf.aggregate(period=[2030], append_references=True)
```

The resulting rows state, for instance, that `Input Capacity|Electricity` equals 1 kW and `CAPEX` equals 700 EUR_2024, which together express a CAPEX of 700 EUR per kW.

## Argument reference

The arguments below are shared by `select()` and `aggregate()` unless noted otherwise. `normalise()` accepts only `units` and `with_parent`.

| Argument | Default | Description |
|---|---|---|
| `units` | `None` | Mapping of variable names to target units. Overrides the automatic choice. |
| `reference_activity` | most frequent in data | Reference variable for all activity-type variables. |
| `reference_capacity` | most frequent in data | Reference variable for all capacity-type variables. |
| `drop_singular_fields` | `True` | Remove fields with fewer than two distinct values from the output. |
| `period_mode` | `"inter+extra"` | Treatment of requested years that are not reported. See [Periods](#periods). |
| `expand_not_specified` | `True` | Whether `N/S` behaves like the asterisk. May be a list of field names. |
| `with_parent` | `False` | Prepend the parent variable to variable names in the output. |
| `append_references` | `False` | Add reference variables as rows with value one instead of columns. |
| `agg` | component fields and `source` | Fields to aggregate over. `aggregate()` only. |
| `masks` | `None` | Additional masks to apply. `aggregate()` only. |
| `masks_database` | `True` | Whether to apply the masks stored in the database. `aggregate()` only. |
| `**field_vals_select` | all values, `period` from defaults | One keyword per field with the values to select. |
