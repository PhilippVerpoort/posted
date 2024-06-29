# Get started

## INSTALLATION

=== "Python"
	You can install the `posted` Python package via:
	```bash
	# when using poetry
	poetry add git+https://github.com:PhilippVerpoort/posted.git

	# when using pip
	pip install git+https://github.com:PhilippVerpoort/posted.git
	```
=== "R"
	You can install the `posted` R package using `install_github` from `devtools` via:
	```R
	install_github('PhilippVerpoort/posted')
	```

Packages on [PyPI](https://pypi.org/) and [CRAN](https://cran.r-project.org/) will be made available at a later stage.



## Database format
**POSTED is extendible via public and private databases.** The public database is part of the [public GitHub repository](https://github.com/PhilippVerpoort/posted) and is located in the `inst/extdata` subdirectory. Private project-specific databases can be added to POSTED by adding a respective database path to the `databases` dictionary of the path module before executing any other POSTED code.

=== "Python"

	``` python
	import posted.path
	databases |= {"database_name":"database_path"}
	```

=== "R"
	``` R
	library(POSTED)
	databases$database_name <- "database_path"
	```

The public database is intended for the curation of a comprehensive set of general-purpose resources that should suit the needs of most users. Private databases may be used for low-threshold extendibility, for more project-specific work that is not in the interest of a broad audience, or for work that must be kept confidential and cannot be made publicly available.

**The format mandates the following components for all databases.** If these components have contents, they should be placed as subdirectories in the database directory (see here: <https://github.com/PhilippVerpoort/posted/tree/refactoring/inst/extdata/database>).   

- **Variable definitions** (in `definitions/`). In this directory, variables (and later perhaps regions) are defined in a scheme similar to that used by the IAMC for creating reporting templates for IAMs (see https://github.com/IAMconsortium/common-definitions/).
- **Techno-economic data files** (in `tedfs/`). This directory contains the actual data as CSV files in the techno-economic data file (TEDF) format and are organised following the hierarchical system of variable definitions (see below). Each file follows the TEDF format with columns either in the base format or specified as a field.
- **Fields** (in `fields/`). This directory contains additional fields (i.e. columns) for the various variables. TEDFs may only report additional columns that are either part of the base format or defined as a field. The fields are given as YAML files and are organised following the hierarchical system of variable definitions (see below).
- **Masks** (in `masks/`). This directory contains masks, which help with complex selections of data in the NPS framework and allow for default settings of selecting or dropping certain data entries (e.g. false entries that should always be disregarded and are only kept for reference).

**TEDFs, fields, and masks are organised in a hierarchical system of variable definitions.** This means that the file `…/database/tedfs/Tech/Electrolysis.csv` defines entries for variables Tech|Electrolysis|..., and so on. The columns `reported_variable` and `reference_variable` in the TEDFs are attached to the end of the parent variable defined by the path of the file.

## Flow types
POSTED defines flow types, which are used throughout the TEDF format and NPS and TEAM frameworks. Flow types may be energy carriers (e.g. electricity, heat, natural gas, hydrogen) or feedstocks (e.g. steel, ethylene, carbon-dioxide).

They are defined in the `flow_types.csv` file in each database. Flow types may be overridden by other databases in the order in which the databases are added to POSTED (i.e. private databases will normally override the public database). Flow types are also automatically loaded as tags for the variable definitions.

Flow types come with a unique ID, the so-called `flow_id`, which is used throughout POSTED (e.g. `elec` for electricity, `h2` for hydrogen, `nh3` for ammonia, etc). Moreover, the following attributes may be defined for them in separate rows:



* **Name (mandatory):** Just a longer explanation of the flow type.
* **Default unit (mandatory):** A default unit used for default unit conversion (e.g. while natural gas can be expressed in units of mass, volume, and energy, the default will be to always express it in units of energy according to its lower-heating value).
* **Conversion factors:** These are used for converting units of the flow between non-compatible unit systems (e.g. between mass, volume, and energy). For example, 1 kg of ammonia can be converted to 1 MWh according to its lower-heating value with the conversion factor of `energycontent_LHV=18.90 MJ/kg`. The available conversion factors are the energy content (for converting mass to density and back) for the lower and higher heating values (LHV and HHV), and the density (for converting volume to mass and back) for standard and normal temperature and pressure (STP and NTP).




## Technology types
POSTED defines technology types, which are used throughout the TEDF format and NPS and TEAM frameworks. Technology types should represent generic classes of technologies (e.g. electrolysis, electric-arc furnaces, direct-air capture).

They are defined in the `tech_types.csv` file in each database. Technology types may be overridden by other databases in the order in which the databases are added to POSTED (i.e. private databases will normally override the public database). Technology types are also automatically loaded as tags for the variable definitions.

Technology types come with a unique ID, the so-called `tech_id`, which is used throughout POSTED (e.g. `ELH2` for electrolysis, `EAF` for an electric-arc furnace, `DAC` for direct-air capture, etc). Moreover, the following attributes may be defined for them in separate columns:



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

These have the following base format (i.e. all TEDFs must contain these columns).

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

(See [https://github.com/PhilippVerpoort/posted/blob/02a80ef9561299381420e7dceb80dac92714024f/python/posted/columns.py#L370](https://github.com/PhilippVerpoort/posted/blob/02a80ef9561299381420e7dceb80dac92714024f/python/posted/columns.py#L370).)

Columns that are not found in the CSV file will be added by POSTED and set to the default value of the column type.

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




## The Normalise-Harmonise-Select (NHS) framework

To be written.




## The Techno-economic Assessment and Manipulation (TEAM) framework

To be written.

Value chains are defined as follows.



<p id="gdcalert1" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: equation: use MathJax/LaTeX if your publishing platform supports it. </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert2">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>






## How to work with and contribute to POSTED


### How to get/install POSTED

If you want to work with POSTED or even contribute to its development, you first need to get/install POSTED in one of three ways:



* **By cloning:** <code>git clone https://github.com/PhilippVerpoort/posted.git \
<em>Note: you must be on develop branch to work with ≥ v0.3.0</em></code>
* <strong>By installing from git (python): \
<code>poetry add git+https://github.com:PhilippVerpoort/posted.git</code></strong> \
or \
<code>pip install git+https://github.com:PhilippVerpoort/posted.git</code>
* <strong>By installing from git (R):</strong> \
<code>install_github('https://github.com:PhilippVerpoort/posted.git')</code>
* By installing from a package repository (not yet implemented): \
<em>This will later be a python package from pypi and R universe.</em>


### How to work with POSTED

This should be in the tutorials section and deleted here once the tutorials are completed

You can create TEDFs via

=== "Python"

	``` python
	from posted.tedf import TEDF
	tedf = TEDF('Tech|Electrolysis')
	```
	
=== "R"

	``` R
	library(posted)
	tedf <- TEDF$new('Tech|Electrolysis')
	```

To load the corresponding Data into the TEDFs use

=== "Python"

	``` python
	tedf.load()
	```
	
=== "R"

	``` R
	tedf$load()
	```
This loads the data as a dataframe in the data attribute of the tedf.   
You can check for inconsistencies via:

=== "Python"

	``` python
	tedf.check()
	```
	
=== "R"

	``` R
	tedf$check()
	```
	
To select data, normalise and aggregate it, you have to load the data into a DataSet via

=== "Python"

	```python
	dataset = DataSet('Tech|Electrolysis')
	```
=== "R"
	```R
	dataset = DataSet$new('Tech|Electrolysis')
	```

On this you can then use the functions. 

=== "Python"

	```python
	dataset.normalise(override={'Tech|ELH2|Input Capacity|Electricity': 'kW', 'Tech|ELH2|Output Capacity|h2': 'kW;LHV'}).query("source=='Vartiainen22'")
	```
=== "R"
	```R
	dataset$normalise(override=list('Tech|Electrolysis|Input Capacity|elec'= 'kW', 'Tech|Electrolysis|Output Capacity|h2'= 'kW;LHV'))  %>% filter(source=='Vartiainen22')
	```


### How to contribute to POSTED



* Contributions to POSTED should always be made via Pull Requests: \
[https://github.com/PhilippVerpoort/posted/pulls](https://github.com/PhilippVerpoort/posted/pulls) 
* New data can first be added to a private database (see database format above). This means installing POSTED as a dependency and then adding a directory containing the private database to its path.





