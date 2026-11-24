---
title: Getting Started
---

# Getting Started

## Installation

POSTED requires Python 3.11 or 3.12. The package can be installed via `pip` directly from GitHub.

```bash
pip install git+https://github.com/PhilippVerpoort/posted.git
```

To install a specific release, append the tag name.

```bash
pip install git+https://github.com/PhilippVerpoort/posted.git@v0.6.0
```

Alternatively, clone the repository and install it locally. This is the recommended way for contributors.

```bash
git clone https://github.com/PhilippVerpoort/posted.git
cd posted
pip install -e .
```

The project uses [`uv`](https://docs.astral.sh/uv/) for dependency management. Contributors can set up the development environment with `uv sync --group dev` and the documentation environment with `uv sync --group docs`.

The public database is shipped as part of the package, so no separate download of data is required.

> **Note:** The package will be published on PyPI in the near future for simpler installation.

## Loading a TEDF

Each techno-economic data file (TEDF) is identified by its parent variable, which corresponds to its path in the database. The TEDF for water electrolysis is located at `tedfs/Tech/Electrolysis.csv` and has the parent variable `Tech|Electrolysis`.

```python
from posted import TEDF

tedf = TEDF.load("Tech|Electrolysis")
```

The raw data can be inspected as a pandas DataFrame. It contains the values as reported by the sources.

```python
tedf.raw
```

The fields of the TEDF, i.e. the columns that distinguish cases and components, are described in its metadata.

```python
for field_id, field in tedf.fields.items():
    print(field_id, field.field_type, field.codes)
```

## Harmonising data

The three steps of the NO-SL-AG workflow are available as methods of the `TEDF` class. Each step includes the previous ones, so a single call is sufficient.

```python
# Convert all entries to common units and reference values.
normalised = tedf.normalise()

# Additionally select cases, harmonise variables, and interpolate periods.
selected = tedf.select(period=[2030, 2040], subtech=["AEL", "PEM"])

# Additionally average over sources and sum over components.
aggregated = tedf.aggregate(period=[2030, 2040], subtech=["AEL", "PEM"])
```

The arguments `period` and `subtech` refer to fields of the electrolysis TEDF. Any field can be used as a keyword argument to restrict the selection. Fields that are omitted are selected in full. The [NO-SL-AG](noslag.md) section explains the behaviour of each step and all available arguments in detail.

The result of `aggregate()` is a tidy DataFrame with one row per remaining case and variable. For the call above, the columns are the fields `subtech`, `size`, `country`, and `period`, followed by `variable`, `reference_variable`, `value`, `unit`, and `reference_unit`. Sources have been averaged over, so no `source` column remains (`source` is the only aggregation field by default; other aggregation options can be chosen via arguments).

```python
aggregated.query("variable == 'CAPEX'")
```

## Choosing units and references

By default, the framework chooses the most common unit per variable found in the data, with currencies converted to the default currency. Units can be overridden per variable, and the reference quantities for activity-type and capacity-type variables can be set explicitly.

```python
aggregated = tedf.aggregate(
    period=[2030],
    units={"CAPEX": "EUR_2024", "Output|Hydrogen": "MWh_H2_LHV"},
    reference_capacity="Output Capacity|Hydrogen",
    reference_activity="Output|Hydrogen",
)
```

See [Units](units.md) for the unit notation and [Concepts](concepts.md#variables-and-reference-variables) for the role of reference variables.

## Changing defaults

The default period and the default currency are stored in a dictionary that can be modified before data is processed.

```python
import posted

posted.defaults["period"] = [2030]
posted.defaults["currency"] = "USD_2022"
```

## Registering a private database

Project-specific or confidential data can be kept in a private database with the same structure as the public one. It is registered by adding its path to the `databases` dictionary.

```python
from pathlib import Path
import posted

posted.databases["my_project"] = Path("/path/to/my_database")

tedf = TEDF.load("Tech|My Technology", database_id="my_project")
```

The structure of a database is described in the [Format](format.md#databases) section.

## Validating data

A TEDF can be checked for formal consistency, e.g. valid units, numeric values, allowed field codes, and known source identifiers.

```python
tedf.validate()
tedf.validated  # DataFrame of booleans, one per cell
```

This check is also run by the test suite for all TEDFs in the public database.

## Next steps

* [Concepts](concepts.md) explains the data model behind TEDFs.
* [Format](format.md) specifies the files of a database.
* [NO-SL-AG](noslag.md) describes the harmonisation workflow in detail.
* The [Data](../data/index.md) section shows the content of each TEDF in the public database.
