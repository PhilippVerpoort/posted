---
title: Format
---

# Format

This section specifies the files that make up a POSTED database. The ideas behind the data model are explained in [Concepts](concepts.md).

## Databases

**POSTED is extensible via public and private databases.** The public database is part of the [public GitHub repository](https://github.com/PhilippVerpoort/posted/tree/main/posted/database) (in the `posted/database` directory) and is installed together with the package. Private project-specific databases can be added to POSTED by adding a respective database path to the `databases` dictionary before executing any other POSTED code.

```python
from pathlib import Path
from posted import databases

databases |= {"my_private_database": Path("/path/to/database/")}
```

The public database is intended for the curation of a comprehensive set of general-purpose resources that should suit the needs of most users. Private databases may be used for low-threshold extensibility, for more project-specific work that is not in the interest of a broad audience, or for confidential data that cannot be made available publicly. A TEDF is always loaded from one database, selected by the `database_id` argument of `TEDF.load()`, which defaults to `"public"`.

**Each database may contain the following components**, each contained in a directory or file of the given name.

```
database/
├── tedfs/                   # techno-economic data files and their metadata
│   ├── Emission Factor.csv
│   ├── Emission Factor.yaml
│   └── Tech/
│       ├── Electrolysis.csv
│       ├── Electrolysis.yaml
│       └── ...
├── variables/
│   ├── definitions/         # reusable variable definitions (YAML)
│   │   └── technology.yaml
│   └── mappings/            # variable mappings (Python)
│       ├── activities.py
│       └── ...
├── masks/                   # default masks per TEDF (YAML)
│   └── Tech/
│       └── Electrolysis.yaml
└── sources.bib              # bibliographic records (BibTeX)
```

- `tedfs/`: This directory contains TEDFs (techno-economic data files), which are UTF-8 encoded CSV files following the format described below. The files are organised in a directory structure that mirrors the hierarchy of variable names. Each TEDF is accompanied by a metadata file in YAML format with the same base name that declares the column structure (fields and comments) and the variables of the file. Both column and variable definitions may be given explicitly or may refer to predefined sets.
- `variables/definitions/`: This directory contains variable definitions in YAML format that can be referred to by the metadata files of TEDFs.
- `variables/mappings/`: This directory contains variable mappings as Python modules. Mappings transform one representation of a variable into another during the selection step. A TEDF lists the mappings to apply in its metadata file.
- `masks/`: This directory contains masks, which assign weights to rows when aggregating data. Masks stored here are applied by default when the corresponding TEDF is aggregated. The directory structure mirrors that of `tedfs/`.
- `sources.bib`: A BibTeX file with one entry per source referenced in the TEDFs of this database.

## Techno-economic data files

### Naming and parent variable

A TEDF consists of a CSV file and a YAML file with the same base name. Its position below `tedfs/` defines its **parent variable**, with directory separators replaced by `|`. The file `tedfs/Tech/Electrolysis.csv` has the parent variable `Tech|Electrolysis` and is loaded with `TEDF.load("Tech|Electrolysis")`. All variables reported in the file are implicitly prefixed with the parent variable. The variable `CAPEX` in this file denotes `Tech|Electrolysis|CAPEX`.

The CSV file is read with `,` as separator, `"` as quote character, and UTF-8 encoding. All cells are read as text. Empty cells are permitted only in columns that are not required. The first row holds the column identifiers.

### Base columns

The TEDF base format contains the following columns. They are present in every TEDF. Columns missing in the CSV file are added as empty columns when the file is read.

| Column | Required | Description |
|---|---|---|
| `source` | yes | A valid BibTeX identifier from the `sources.bib` file of the database. Exactly one identifier per row. |
| `source_detail` | yes | Detailed information on where exactly in the source this entry can be found, e.g. page, table, figure, or spreadsheet cell. |
| `variable` | yes | The reported variable, relative to the parent variable. Must be defined in the metadata or in a predefined set under `variables/definitions/`. |
| `reference_variable` | no | The reference variable, relative to the parent variable. Used for variables that are reported in reference to other variables, e.g. CAPEX per rated capacity or energy input per unit of product. |
| `value` | yes | The value corresponding to the reported variable. |
| `uncertainty` | no | The uncertainty corresponding to the reported variable, in the same unit as the value. |
| `unit` | yes | The unit corresponding to the reported variable. Must be a valid unit string known to [`cet-units`](https://philippverpoort.github.io/cet-units/latest/). See [Units](units.md). |
| `reference_value` | no | The value corresponding to the reference variable. Only permitted if `reference_variable` is set. |
| `reference_unit` | no | The unit corresponding to the reference variable. Only permitted if `reference_variable` is set. Must be a valid unit string known to `cet-units`. |
| `comment` | no | A free-text comment on the entry. This column should be used to report any conversion performed if the value originally reported by a source had to be modified before reporting, as well as additional assumptions or deviations from the original units. |

The columns `source` and the fields described below must be filled in every row. The columns `source_detail`, `variable`, `value`, and `unit` are required as well.

> **Note:** The `uncertainty` column can currently only be reported but not processed further with the POSTED framework. It is normalised alongside the value and then dropped in the selection step. This feature may be added at a later stage.

**Example.** The row below reports from a technology catalogue that a 1 MW alkaline electrolyser has a CAPEX of 1566 EUR (2020 prices) per kg of hydrogen output capacity per day in the year 2020, with an uncertainty of 918 EUR.

```
source,source_detail,subtech,size,period,country,variable,reference_variable,value,uncertainty,unit,reference_value,reference_unit,comment
DEA-TDRF-2023,"Sheet 86 AEC 1MW, Row 24",AEL,1 MW,2020,GLO,CAPEX,Output Capacity|Hydrogen,1566,918,EUR_2020,1,kg_H2/day,
```

The reference value need not be one. The row below reports that 541 cubic metres of hydrogen are consumed per 1.1 tonnes of direct reduced iron, with the conversion assumption documented in the comment.

```
Agora-KSV-2023,"Page 79, Tabelle 12",H2,No Capture,Input|Hydrogen,Output|Direct Reduced Iron,2022,#,541,,cubic_meter_H2_norm,1.1,t,"This source states 541 Nm³ of hydrogen per tonne of steel, but does not state how much DRI it assumes per steel. The conversion factor from Devlin et al, 2022 of 1.1 DRI/tSteel is therefore used."
```

### Fields

Fields are additional columns that can help report data that varies across cases or components. Fields can currently be of type `case` or `component`.

* **A case field:** POSTED treats these columns as different competing options for data. When data is aggregated in the aggregate step of the NO-SL-AG framework, case fields are averaged over.
* **A component field:** POSTED treats these columns as components of the same data that require summing up. When data is aggregated in the aggregate step of the NO-SL-AG framework, component fields are simply summed up.

Fields may be **coded** or **non-coded**. A coded field defines a fixed set of allowed values (the codes) in the metadata file, and every cell must contain one of these codes or one of the special values below. A non-coded field accepts any text. The `source` column is a coded case field whose codes are the BibTeX identifiers in `sources.bib`. The `period` column is a non-coded case field that accepts integer years.

Two fields are predefined.

* **`source`** is present in every TEDF and does not need to be declared.
* **`period`** must be declared in the metadata file if the TEDF uses it, with the entry `period: period`. TEDFs without a period column, e.g. emission factors, are permitted. If a TEDF has no `period` column, selecting by period is not possible.

Field identifiers must not coincide with base column identifiers. Field columns may be placed anywhere in the CSV file. By convention they are placed between `source_detail` and `variable`.

### Field cell values

Every field cell must be filled. Besides a single plain value, the following entries are permitted. How they are processed when selecting data is described in the [NO-SL-AG guide](noslag.md#field-selection-and-expansion).

* **Multiple values (`A, B`)** — A cell may list several comma-separated values if the entry applies equally to each of them. For example, an entry with `AEL, PEM` in a `subtech` field reports one value that holds for both alkaline and PEM electrolysis. Spaces around the commas are ignored. This is not available for the `source` column. Because the comma is the separator, individual values in a multi-value field must not contain commas themselves.
* **Asterisk (`*`)** — The entry applies to all values of this field. Use it when a source reports a value without distinguishing between cases, e.g. a total plant capacity that is the same for every sub-technology, or a parameter that does not depend on the period. The asterisk is a wildcard, not a value of its own. For the `period` column it is the only permitted non-numeric entry.
* **Not specified (`N/S`)** — The source does not state which value of this field the entry refers to. This differs from the asterisk. The asterisk asserts that the value holds for all cases, whereas `N/S` records that the case is unknown. It is intended for case fields, e.g. a cost figure from a report that does not mention the plant size.
* **Hash (`#`)** — Only in component fields. It marks an entry that reports the total, i.e. the quantity is not subdivided into components. It is an ordinary value from the point of view of selection and aggregation. Since aggregation sums over all component values within a source and case, a quantity should be reported either as a total with `#` or itemised by component, never both, as this would double-count.

The asterisk and `N/S` may be used in any field, including non-coded ones. For coded fields they count as allowed values in addition to the codes. When reporting data, prefer the most specific entry that the source supports: a plain value where the case is known, a comma-separated list where the value is known to hold for several cases, the asterisk where it holds for all cases, and `N/S` only where the source gives no information.

### Metadata file

Each TEDF is accompanied by a YAML file with the same base name. It has up to three top-level keys.

```yaml
columns:
    subtech:
        name: Subtechnology
        description: Subtechnology
        type: case
        coded: True
        codes:
            AEL: Alkaline electrolysis
            PEM: Proton-exchange membrane electrolysis
            SOEC: High-temperature solid-oxide electrolysis
    size:
        name: Plant size
        description: Total size (capacity) of the assumed plant
        type: case
        coded: False
    period: period
variables:
    predefined:
        - technology
mappings:
    - full_load_hours
    - fixed_opex_relative
    - fixed_opex_specific
    - capacities_to_activities
    - activities
```

**`columns`** declares the additional columns of the CSV file. Each key is a column identifier. The value is either the name of a predefined column, currently only `period`, or a mapping with the following entries.

| Entry | Required | Description |
|---|---|---|
| `type` | yes | `case`, `component`, or `comment`. |
| `name` | yes | Human-readable name of the column. |
| `description` | yes | Explanation of what the column distinguishes. |
| `coded` | for fields | Whether the field only accepts the codes listed under `codes`. |
| `codes` | if coded | Mapping of allowed codes to their descriptions. |

Columns of type `comment` are free-text columns that are carried along with the raw data but dropped during selection, like the base column `comment`. Columns in the CSV file that are not declared in the metadata are treated as comment columns and a warning is issued.

**`variables`** declares the variables that may appear in the `variable` and `reference_variable` columns. The entry `predefined` lists files from `variables/definitions/` (without the `.yaml` extension) whose definitions are included. The entry `custom` holds definitions written directly in the metadata file, using the same syntax as the definition files. Both may be combined, and later definitions override earlier ones with the same name.

**`mappings`** lists the variable mappings from `variables/mappings/` (without the `.py` extension) that are applied during selection, in the given order. Order matters when one mapping depends on the output of another. The standard order for technology TEDFs is shown above and is explained in the [NO-SL-AG](noslag.md#variable-mappings) section.

## Variable definitions

Variable definitions describe the variables that may appear in TEDFs. They are stored as YAML mappings from variable name to attributes, either in files under `variables/definitions/` or under `variables: custom:` in a metadata file.

```yaml
CAPEX:
    description: CAPital EXpenditure (in reference to capacity specified by reference variable)
    reference: capacity
    dimension: "[currency]"
    default_unit: "{default currency}"
Input|?flow_type:
    description: Input (energy or feedstock) needed
    reference: activity
    dimension: "[{flow_type_dimension}]"
    default_unit: "{flow_type_default_unit}"
Lifetime:
    description: Expected time a facility can be in production for
    dimension: "[time]"
    default_unit: "a"
```

| Attribute | Description |
|---|---|
| `description` | Explanation of the variable. |
| `reference` | How the variable relates to a reference variable. `activity` for variables reported per unit of a flow, `capacity` for variables reported per unit of capacity, `intensive` or absent for variables without a reference. This attribute controls the harmonisation of references during selection. |
| `dimension` | Expected dimensionality of the unit, in `pint` notation. Documentary; not currently checked by the framework. |
| `default_unit` | Default unit for the variable. Documentary; the framework currently derives target units from the data as described under [Units](units.md#default-units-and-overrides). |

Variable names may contain placeholders for name segments. A segment `?name` matches exactly one segment of a variable name, e.g. `Input|?flow_type` matches `Input|Electricity` and `Input|Hydrogen`. A segment `*name` matches the remainder of a variable name including further `|` separators. Placeholders allow one definition to cover a family of variables.

The public database provides the definition set `technology`, which covers the variables used by technology TEDFs: `CAPEX`, `OPEX Fixed`, `OPEX Fixed Specific`, `OPEX Fixed Relative`, `OPEX Variable`, `Lifetime`, `OCF`, `FLH`, `Input|?flow_type`, `Output|?flow_type`, `Input Capacity|?flow_type`, `Output Capacity|?flow_type`, `Total Input Capacity|?flow_type`, `Total Output Capacity|?flow_type`, `Emissions|?emission_type`, `Capture Rate`, and others. The current list is in [`technology.yaml`](https://github.com/PhilippVerpoort/posted/blob/main/posted/database/variables/definitions/technology.yaml).

## Variable mappings

Variable mappings are Python modules in `variables/mappings/`. Each module defines exactly one class derived from `AbstractVariableMapper` or `AbstractVariableGroupMapper` in `posted.noslag.mapping`. The module name is the identifier used in the `mappings` list of metadata files.

A mapper implements three methods.

* `_condition()` returns a boolean series marking the rows that the mapping applies to.
* `_prepare_units()` determines unit conversion factors and registers units for variables that the mapping creates. Optional.
* `_map(df, cond)` transforms the marked rows and returns the modified frame. For `AbstractVariableMapper` it is called once for the whole frame. For `AbstractVariableGroupMapper` it is called once per combination of field values, which allows a mapping to use other variables of the same source and case, e.g. the CAPEX belonging to a relative OPEX.

A mapper may declare `_warning_types`, a mapping of warning identifiers to messages, and call `_add_warning()` to flag rows that could not be mapped. Such rows are reported to the user and dropped. The simplest mapping in the public database converts full-load hours into a capacity factor.

```python
"""Convert full-load hours to operational capacity factor."""

import pandas as pd
from cet_units import Q

from posted.noslag.mapping import AbstractVariableMapper


class FullLoadHoursMapper(AbstractVariableMapper):
    """Convert full-load hours to operational capacity factor."""

    def _condition(self) -> pd.Series:
        return self._df["variable"] == "FLH"

    def _prepare_units(self) -> None:
        if "OCF" not in self._units:
            self._units["OCF"] = "dimensionless"
        self._conv_factor: float = (
            (Q(self._units["FLH"]) / Q("year")).to(self._units["OCF"]).m
        )

    def _map(self, df: pd.DataFrame, cond: pd.Series) -> pd.DataFrame:
        df.loc[cond, "variable"] = "OCF"
        df.loc[cond, "value"] *= self._conv_factor

        return df
```

The mapper receives the frame with the columns `variable`, `reference_variable`, and `value`, a dictionary of target units per variable, the row groups, the patterns of activity-type and capacity-type variables, and the reference activity and reference capacity. The mappings shipped with the public database are described in the [NO-SL-AG](noslag.md#variable-mappings) section.

## Masks

Default masks for a TEDF are stored in `masks/` under the same relative path as the TEDF, e.g. `masks/Tech/Electrolysis.yaml` for `tedfs/Tech/Electrolysis.csv`. The file holds a list of mask specifications. Each specification is passed to the constructor of `posted.noslag.Mask`.

```yaml
- where: "variable == 'CAPEX'"
  use: "source == 'Example-2020'"
  weight: nan
  other: 1.0
  comment: CAPEX in this source is misquoted from another publication.
```

| Key | Description |
|---|---|
| `where` | Condition or list of conditions that all rows of a group must satisfy for the mask to apply to that group. |
| `use` | Condition or list of conditions identifying rows that receive a weight. |
| `weight` | Weight or list of weights, one per `use` condition. Defaults to 1. A weight of `nan` excludes the row. |
| `other` | Weight for rows of the group that match none of the `use` conditions. Defaults to `nan`, i.e. such rows are excluded. |
| `comment` | Free-text explanation. |

Conditions are strings evaluated with `DataFrame.eval()` on the selected data, mappings of column to value that must all be equal, or callables that receive a row and return a boolean. The variable column at that stage does not include the parent variable. The semantics of masks during aggregation are described in the [NO-SL-AG](noslag.md#masks) section.

## Sources

Sources are stored in `sources.bib` in BibTeX format. The BibTeX key is the identifier used in the `source` column of all TEDFs of the database. Keys in the public database follow the pattern `Author-Year` or `Institution-Acronym-Year`, e.g. `Vartiainen-2022` or `DEA-TDRF-2023`.

The following rules are enforced by the test suite of the public database.

* Every identifier used in a TEDF must have an entry in `sources.bib`.
* Every entry in `sources.bib` must be used in at least one TEDF.
* Entries must be sorted alphabetically by key, case-insensitively.
* Every entry must be parseable and formattable by `pybtex`.

In addition to standard BibTeX fields, the non-standard field `pdf` may hold a direct link to a PDF file. It is used alongside `doi` and `url` to generate the links on the [Sources](../sources.md) page.

Only one source may belong to a row of data. If the same value is reported by several sources, it is entered once per source on separate rows.
