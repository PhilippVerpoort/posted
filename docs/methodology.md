---
hide:
  - navigation
---
# Methodology of POSTED

## Purpose and aims
The development of the POSTED framework pursues several goals:

**Obtain a comprehensive collection of techno-economic data.** The data needed for techno-economic assessments and various types of modelling is often scattered across many sources and formats. One aim of POSTED is to collect all required data in one place with a consistent format. This data will forever be publicly available under a permissive licence in order to overcome existing barriers of collaboration.

**Make data easily available for manipulation and techno-economic assessments.** Techno-economic data often comes in the form of Excel Spreadsheets, which is difficult to work with when performing assessments. Calculating the levelized cost of production or comparing parameters across different sources should be easy and straightforward with a few lines of code.

**Make data sources traceable and transparent.** When working with techno-economic data, the origin and underlying assumptions are often intransparent and hard to trace back. By being explicit about sources and reporting data only in the original units, the process of data curation becomes more open and transparent. Through the development and explication of clear standards, the misunderstandings can be avoided.
Be extendible to meet users’ requirements. The POSTED database can be extended, allowing users’ to meet the requirements of their own projects.


## Database format
**POSTED is extensible via public and private databases.** The public database is part of the [public GitHub repository](https://github.com/PhilippVerpoort/posted) and is located in the `inst/extdata` subdirectory. Private project-specific databases can be added to POSTED by adding a respective database path to the `databases` dictionary of the path module before executing any other POSTED code.

=== "Python"

	```python
	from pathlib import Path
	import posted.path
	databases |= {'database_name': Path('/path/to/database/')}
	```

=== "R"
	```R
	library(POSTED)
	databases$database_name <- "/path/to/database/"
	```

The public database is intended for the curation of a comprehensive set of general-purpose resources that should suit the needs of most users. Private databases may be used for low-threshold extensibility, for more project-specific work that is not in the interest of a broad audience, or for confidential data that cannot be made available publicly.

**The format mandates the following components for all databases.** If these components have contents, they should be placed as subdirectories in the database directory (see here: <https://github.com/PhilippVerpoort/posted/tree/refactoring/inst/extdata/database>).   

- **Variable definitions** (in `definitions/`). In this directory, variables (and later perhaps regions) are defined in a scheme similar to that used by the IAMC for creating reporting templates for IAMs (see https://github.com/IAMconsortium/common-definitions/).
- **Techno-economic data files** (in `tedfs/`). This directory contains the actual data as CSV files in the techno-economic data file (TEDF) format and are organised following the hierarchical system of variable definitions (see below). Each file follows the TEDF format with columns either in the base format or specified as a field.
- **Fields** (in `fields/`). This directory contains additional fields (i.e. columns) for the various variables. TEDFs may only report additional columns that are either part of the base format or defined as a field. The fields are given as YAML files and are organised following the hierarchical system of variable definitions (see below).
- **Masks** (in `masks/`). This directory contains masks, which help with complex selections of data in the NPS framework and allow for default settings of selecting or dropping certain data entries (e.g. false entries that should always be disregarded and are only kept for reference).

**TEDFs, fields, and masks are organised in a hierarchical system of variable definitions.** This means that the file `.../database/tedfs/Tech/Electrolysis.csv` defines entries for variables `Tech|Electrolysis|...`, and so on. The columns `variable` and `reference_variable` in the TEDFs are attached to the end of the parent variable defined by the path of the file.

## Flow types
POSTED defines flow types, which are used throughout the TEDF format and NOSLAG and unit framework. Flow types may be energy carriers (electricity, heat, fossil gas, hydrogen, etc), feedstocks (naphtha, ethylene, carbon-dioxide), or materials (steel, cement, etc).

They are defined in the `flow_types.csv` file in each database. Flow types may be overridden by other databases in the order in which the databases are added to POSTED (i.e. private databases will normally override the public database). Flow types are also automatically loaded as tags for the variable definitions.

Flow types come with a unique ID, the so-called `flow_id`, which is used throughout POSTED (`Electricity`, `Hydrogen`, `Ammonia`, etc). Moreover, the following attributes may be defined for them as attributes:

* **Name (mandatory):** Just a longer explanation of the flow type.
* **Default unit (mandatory):** A default unit used for default unit conversion. For instance, while natural gas can be expressed in units of mass, volume, or energy, POSTED will default expressing it in units of energy according to its lower-heating value.
* **Conversion factors (optional):** These are used for converting units of the flow between different dimensionalities (e.g. between mass, volume, and energy) and variants (lower or higher heating value; norm or standard density). For instance, 1 kg of ammonia can be converted to 1 MWh according to its lower-heating value with the conversion factor of `energycontent_LHV=18.90 MJ/kg`. The available conversion factors are the energy content (for converting mass to density and back) for the lower and higher heating values (LHV and HHV), and the density (for converting volume to mass and back) for standard and normal temperature and pressure (STP and NTP).

Attributes can be assigned a source by adding the respective BibTeX handle (see below) in the `source` column.


## Technology types
POSTED defines technology types, which are used throughout the TEDF format and the NOSLAG framework. Technology types should represent generic classes of technologies (electrolysis, electric-arc furnaces, direct-air capture, etc).

Technologies are defined in the `tech_types.csv` file in each database. Technology types may be overridden by other databases in the order in which the databases are added to POSTED (i.e. private databases will normally override the public database). Technology types are also automatically loaded as tags for the variable definitions.

Technology types come with a unique ID, the so-called `tech_id`, which is used throughout POSTED (`Electrolysis` for water electrolysis, `Haber-Bosch with ASU` for Haber-Bosch synthesis with an air-separation unit, `Iron Direct Reduction` for direct reduction of iron ore based on either fossil gas or hydrogen, etc). Moreover, the following attributes may be defined for them in separate columns:

* **Description (mandatory):** Just a longer explanation of the tech type.
* **Long description (mandatory):** An even longer explanation.
* **Class: **This may take the value conversion, storage, or transportation and helps distinguish between broad classes of technologies serving these different purposes.
* **Sector: **This may help group technologies according to different sectors (energy, industry, transport, buildings, CTS, CDR, etc).
* **Primary output (mandatory):** The primary output flow that should be used as default to harmonise all data.


## Sources
* Sources must be added to the respective databases in the `sources.bib` file in BibTeX format (see [https://github.com/PhilippVerpoort/posted/blob/refactoring/inst/extdata/database/sources.bib](https://github.com/PhilippVerpoort/posted/blob/refactoring/inst/extdata/database/sources.bib)).
* The BibTeX identifier should be used in the `source` column in each TEDF.
* Only one source can belong to a row of data in a TEDF! Adding multiple sources for one entry is invalid. These should be reported on separate rows.


## Techno-economic data files (TEDFs)

### Base format

The TEDF base format contains the following columns:

* **variable** — The reported variable. This column should only contain the trailing part of the variable, whereas the parent variable is given by the file path in the database (see database format from above). The combined variable (parent + reported) must be defined in the definitions.
* **reference_variable** — The reference variable. This column should only contain the trailing part of the variable, whereas the parent variable is given by the file path in the database (see database format from above). The combined variable (parent + reported) must be defined in the definitions.
* **region** — The region, e.g. a country or supranational region. Currently this data is disregarded by POSTED.
* **period** — The period, e.g. an integer or floating number.
* **value** — The value corresponding to the reported variable.
* **uncertainty** — The uncertainty corresponding to the reported variable.
* **unit** — The unit corresponding to the reported variable.
* **reference_value** — The value corresponding to the reference value.
* **reference_unit** — The unit corresponding to the reference variable.
* **comment** — A free-text comment on the entry.
* **source** — A valid BibTeX identifier from the `sources.bib` file(s).
* **source_detail** — Detailed information on where exactly in the source this entry can be found.

=== "Python"
	The base columns in Python are [defined here](https://github.com/PhilippVerpoort/posted/blob/develop/python/posted/columns.py#L617).
=== "R"
	The base columns in R are [defined here](https://github.com/PhilippVerpoort/posted/blob/develop/R/columns.R#L686).

Columns that are not found in a CSV file will be added by POSTED and set to the default value of the column type.

If one wants to specify additional columns, these need to be defined as fields in one of the databases.

By placing an asterisk (*) in a period, source, or any field column, POSTED expands these rows across all possible values for these columns in the harmonise method of the NHS framework.


### Fields

Fields can create additional columns for specific variables. Fields can currently be one of three:

* **A case field:** POSTED treats these columns as different competing options for data. When data is aggregated in the select method of the NHS framework, case fields are averaged over.
* **A component field:** POSTED treats these columns as components of the same data that require summing up. When data is aggregated in the select method of the NHS framework, component fields are simply added up.


### Masks

To be written.


## Variable definitions

To be written.

See IAMC format: [https://github.com/IAMconsortium/common-definitions](https://github.com/IAMconsortium/common-definitions)




## Units

To be written.

See pint: [https://pint.readthedocs.io/en/stable/](https://pint.readthedocs.io/en/stable/) 

See IAMC units: [https://github.com/IAMconsortium/units/](https://github.com/IAMconsortium/units/) 




## The Normalise-Select-Aggregate (NOSLAG) framework

To be written.




## The Techno-economic Assessment and Manipulation (TEAM) framework

To be written.

Value chains are defined as follows.
