---
title: Format
---

# Format

## Databases

**POSTED is extensible via public and private databases.** The public database is part of the [public GitHub repository](https://github.com/PhilippVerpoort/posted/tree/main/posted/database) (in the `posted/database` directory). Private project-specific databases can be added to POSTED by adding a respective database path to the `databases` dictionary of the path module before executing any other POSTED code.

```python
from pathlib import Path
from posted import databases

databases |= {"my_private_database": Path("/path/to/database/")}
```

The public database is intended for the curation of a comprehensive set of general-purpose resources that should suit the needs of most users. Private databases may be used for low-threshold extensibility, for more project-specific work that is not in the interest of a broad audience, or for confidential data that cannot be made available publicly.

**Each database may contain the following components**, which should each be contained in a directory.

- `tedfs/`: This directory contains TEDFs (techno-economic data files), which are UTF8-encoded CSV files following a specific format (see below). The files are organised in a directory structure following a hierarchical system. Moreover, each TEDF file is accompanied by a metadata file in YAML format outlining the column structure (fields and comments, see below) and the allowed variables (see below). Both column and variable definitions may be defined explicitly or may refer to predefined sets.
- `variables/definitions/`: This directory may contain variable definitions in YAML format that can be referred to by TEDF metadata files (see above).
- `variables/mappings/`: This directory defines automated variable mappings as Python code.
- `masks/`: This directory contains masks, which add weights to different rows when aggregating the data using `TEDF.aggregate()`. It will make sense to define these manually for each case, but some masks useful generally will be stored here as part of the database.

## Base column format

The TEDF base format contains the following columns:

* **`variable`** — The reported variable, as defined in the metadata or a predefined set under `variables/definitions/`.
* **`reference_variable`** — The reference variable. This is only used for
* **`value`** — The value corresponding to the reported variable.
* **`uncertainty`** — The uncertainty corresponding to the reported variable.
* **`unit`** — The unit corresponding to the reported variable. This must be a valid unit string known to [`cet-units`](https://philippverpoort.github.io/cet-units/latest/).
* **`reference_value`** — The value corresponding to the reference value. This can only be entered if `reference_variable` is set.
* **`reference_unit`** — The unit corresponding to the reference variable. This can only be entered if `reference_variable` is set. This must be a valid unit string known to [`cet-units`](https://philippverpoort.github.io/cet-units/latest/).
* **`comment`** — A free-text comment on the entry. This column should especially be used to report any conversion performed if the value originally reported by a source had to be modified manually before reporting. It should also be used to report additional assumptions or deviating from original units.
* **`source`** — A valid BibTeX identifier from the `sources.bib` file.
* **`source_detail`** — Detailed information on where exactly in the source this entry can be found.

> **Note:** The `uncertainty` column can currently only be reported but not processed further with the POSTED framework. This feature may be added at a later stage.

## Fields

Fields are additional columns that can help report data that varies across cases or components. Fields can currently be of type `case` or `component`.

* **A case field:** POSTED treats these columns as different competing options for data. When data is aggregated in the select method of the NO-SL-AG framework, case fields are averaged over.
* **A component field:** POSTED treats these columns as components of the same data that require summing up. When data is aggregated in the select method of the NO-SL-AG framework, component fields are simply summed up.
