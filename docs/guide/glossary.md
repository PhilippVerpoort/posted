---
title: Glossary
---

# Glossary

**Activity-type variable**
: A variable that describes a flow or cost during operation and is reported relative to another flow, e.g. electricity input per unit of hydrogen output. Declared with `reference: activity` in the variable definitions. See [Concepts](concepts.md#variables-and-reference-variables).

**Aggregate**
: The third step of NO-SL-AG. Sums over component fields, averages over case fields, and applies masks. See [NO-SL-AG](noslag.md#aggregate).

**Asterisk (`*`)**
: Field entry meaning that a value applies to all values of the field. Expanded to all requested values during selection. See [Format](format.md#field-cell-values).

**Base column**
: One of the columns present in every TEDF: `source`, `source_detail`, `variable`, `reference_variable`, `value`, `uncertainty`, `unit`, `reference_value`, `reference_unit`, and `comment`. See [Format](format.md#base-columns).

**Capacity-type variable**
: A variable tied to the installed plant and reported relative to a capacity, e.g. CAPEX per unit of output capacity. Declared with `reference: capacity` in the variable definitions.

**Case field**
: A field whose values are competing alternatives, e.g. sub-technologies or years. Averaged over when aggregated. See [Concepts](concepts.md#cases-and-components).

**Coded field**
: A field with a fixed set of allowed values (codes) defined in the metadata file.

**Component field**
: A field whose values are parts that add up to a whole, e.g. cost items. Summed over when aggregated.

**Database**
: A directory containing TEDFs, metadata, variable definitions, mappings, masks, and sources. POSTED ships a public database and can register private ones. See [Format](format.md#databases).

**Field**
: An additional column of a TEDF that distinguishes cases or components. Defined in the metadata file of the TEDF.

**Hash (`#`)**
: Entry in a component field marking a total that is not subdivided into components.

**Harmonised data**
: Output of the NO-SL-AG workflow in which all values of a variable share one unit and one reference. See [Concepts](concepts.md#raw-data-and-harmonised-data).

**Mask**
: A rule that assigns weights to rows matching a condition during aggregation. Used to exclude or weight entries. See [NO-SL-AG](noslag.md#masks).

**Metadata file**
: The YAML file accompanying each TEDF. Declares fields, comment columns, variable definitions, and mappings. See [Format](format.md#metadata-file).

**Normalise**
: The first step of NO-SL-AG. Converts units, deflates currencies, and scales values to reference values of one. See [NO-SL-AG](noslag.md#normalise).

**NO-SL-AG**
: The normalise, select, aggregate workflow for converting raw data into harmonised data. Also written NOSLAG.

**Not specified (`N/S`)**
: Field entry meaning that the source does not state which value of the field an entry refers to.

**Parent variable**
: The leading part of a variable name that is given by the position of a TEDF in the database, e.g. `Tech|Electrolysis`. Used to load a TEDF.

**Period**
: Predefined case field holding the year a value refers to. Supports interpolation and extrapolation.

**Raw data**
: The data as entered in a TEDF, in the units and references of the original source.

**Reference activity, reference capacity**
: The common reference variables onto which all activity-type and capacity-type variables are rebased during selection.

**Reference variable**
: The denominator of a reported ratio, e.g. `Output Capacity|Hydrogen` for a CAPEX value. Has its own value and unit.

**Select**
: The second step of NO-SL-AG. Filters and expands fields, interpolates periods, and applies variable mappings. See [NO-SL-AG](noslag.md#select).

**Source**
: The publication a value is taken from, identified by a BibTeX key from `sources.bib`. Treated as a case field.

**TEDF**
: Techno-economic data file. A CSV file with one row per reported value, accompanied by a metadata file. See [Format](format.md#techno-economic-data-files).

**Variable**
: The name of the reported quantity, e.g. `CAPEX` or `Input|Electricity`. Hierarchical, with segments separated by `|`.

**Variable definition**
: An entry describing a variable, including its relation to a reference (activity, capacity, or intensive), its dimension, and its default unit. Stored in `variables/definitions/` or in the metadata file.

**Variable mapping**
: Code in `variables/mappings/` that converts one form of a variable into another during selection, e.g. full-load hours into a capacity factor. See [NO-SL-AG](noslag.md#variable-mappings).
