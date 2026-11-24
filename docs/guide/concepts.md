---
title: Concepts
---

# Concepts

This section explains the ideas behind the POSTED data model. It describes what the pieces of a techno-economic data file mean and why they are structured as they are. The precise file format is specified in [Format](format.md), and the processing steps are described in [NO-SL-AG](noslag.md).

## Raw data and harmonised data

POSTED distinguishes strictly between two representations of the same data.

**Raw data** is what contributors enter into the database. Every row of a TEDF records one value together with the context in which the source reports it: the unit, the quantity it refers to, the year, the sub-technology, the source, and the position within the source. The guiding rule is to stay as close to the original publication as possible. If a report states an investment cost of 1566 EUR per kg of hydrogen per day in 2020 prices, that is what the row contains, even if other sources use EUR per kW or USD per tonne per year.

**Harmonised data** is what the framework produces from raw data. All values of a variable are expressed in one unit and relative to one reference quantity, currencies are deflated to one base year, variants of a variable are mapped onto a canonical form, and values are interpolated to the requested years. Harmonised data from different sources is directly comparable and can be averaged.

This separation has consequences for how the database is maintained. Contributors never convert values by hand, because every conversion would hide an assumption that cannot be checked later. When a source reports a value in a form that cannot be expressed directly, e.g. a cost per tonne of steel where the TEDF is about direct reduced iron, the conversion is recorded in the `comment` column so that it remains traceable. Where a conversion is systematic, e.g. from full-load hours to a capacity factor, it is implemented once in the framework as a variable mapping rather than being repeated by every contributor.

## Variables and reference variables

A **variable** names the quantity that a row reports. Variable names are hierarchical, with segments separated by a vertical bar, e.g. `CAPEX`, `Input|Electricity`, or `Output Capacity|Hydrogen`. The leading part of the hierarchy, the **parent variable**, is given by the position of the TEDF in the database rather than being repeated in each row. The row `Input|Electricity` in the file `tedfs/Tech/Electrolysis.csv` therefore stands for `Tech|Electrolysis|Input|Electricity`.

Many techno-economic parameters are ratios. A specific investment cost is a cost per unit of capacity, an energy demand is an energy input per unit of product, an emission intensity is a mass of CO2 per unit of output. POSTED represents such ratios explicitly by splitting them into two variables.

* The **variable** is the numerator, e.g. `CAPEX` or `Input|Electricity`.
* The **reference variable** is the denominator, e.g. `Output Capacity|Hydrogen` or `Output|Hydrogen`.

Each half has its own value and unit. A row may therefore state that 1566 EUR of CAPEX corresponds to 1 kg of hydrogen output capacity per day, or that 541 cubic metres of hydrogen are consumed per 1.1 tonnes of direct reduced iron. This representation serves three purposes.

1. **Faithfulness.** Sources report ratios in many ways, and the two-part representation can store all of them without conversion.
2. **Unit handling.** Numerator and denominator are converted separately, so a cost in EUR per kg of hydrogen per day can be converted to EUR per kW of hydrogen output by converting only the denominator.
3. **Rebasing.** When several sources refer their data to different quantities, e.g. one to hydrogen output and another to electricity input, the framework can rebase all of them onto one common reference using the conversion ratios that the same source provides.

Variable definitions classify how a variable relates to its reference. Three kinds matter for processing.

* **Activity-type variables** describe flows during operation and are reported per unit of another flow, e.g. energy inputs per unit of product or variable OPEX per unit of product. Their reference variable is itself a flow, e.g. `Output|Hydrogen`.
* **Capacity-type variables** describe quantities tied to the installed plant and are reported per unit of capacity, e.g. CAPEX or fixed OPEX. Their reference variable is a capacity, e.g. `Output Capacity|Hydrogen`.
* **Intensive variables** are dimensionless or self-contained and have no reference variable, e.g. a lifetime, a capacity factor, or a capture rate.

In harmonised data, all activity-type variables of a TEDF share one **reference activity** and all capacity-type variables share one **reference capacity**. The framework determines these by default as the most common reference variables found in the data. They can also be set explicitly, e.g. to express an electrolyser's data per unit of electricity input rather than per unit of hydrogen output.

## Cases and components

Techno-economic data for one technology rarely consists of a single number per variable. Sources distinguish sub-technologies, plant sizes, operating modes, regions, and years. They also break quantities down into parts, e.g. investment cost into equipment and installation, or hydrogen demand into reduction agent and heating.

POSTED represents each such distinction as a **field**, i.e. an additional column in the TEDF. Fields come in two types that differ in what the entries mean in relation to each other.

* **Case fields** hold competing alternatives. The values in a case field are different answers to the same question, e.g. alkaline versus PEM electrolysis, a 1 MW versus a 100 MW plant, or the year 2030 versus 2050. Only one of them applies at a time. When data is aggregated over a case field, the values are **averaged**, because they are alternative estimates of the same quantity.
* **Component fields** hold parts of a whole. The values in a component field are contributions that together make up the reported quantity, e.g. several cost items that add up to the total fixed OPEX. When data is aggregated over a component field, the values are **summed**.

The `source` column is present in every TEDF and is treated as a case field, because different sources are competing estimates of the same quantity. The `period` column is a predefined case field that most TEDFs declare, because the same quantity in different years represents alternative points in time. Whether a TEDF needs further fields, and which, is decided per technology and declared in its metadata. The electrolysis TEDF, for instance, distinguishes `subtech`, `size`, and `country`. The TEDF for direct reduction of iron distinguishes `carbon_capture` and `mode` as case fields and has a `component` field.

The distinction between cases and components also informs how missing information is encoded. A source may report a value that holds for all alternatives of a case, which is recorded with an asterisk (`*`). A source may fail to state which alternative a value refers to, which is recorded as not specified (`N/S`). A source may report a total without breaking it into components, which is recorded with a hash (`#`) in the component field. The [Format](format.md#field-cell-values) section defines these entries, and the [NO-SL-AG](noslag.md#field-selection-and-expansion) section explains how they are resolved when data is selected.

## Periods

The `period` field records the year a value refers to. For historical data this is the year of the estimate. For projections it is the target year of the projection. Periods behave like any other case field with one addition: because years are ordered, the framework can interpolate between reported years and extrapolate beyond them. A request for the year 2035 can thus be served from a source that reports 2030 and 2040. This treatment is configurable and can be switched off.

## Sources

Every row of a TEDF names exactly one source, identified by a BibTeX key that is defined in the `sources.bib` file of the database. A second column, `source_detail`, records where within the source the value can be found, e.g. a table, page, or spreadsheet cell. Together they allow each number in the database to be traced back to its origin.

The source is itself a case field. Aggregating over sources means averaging the estimates of different publications, which is the default behaviour of the aggregation step. Sources can also be used to restrict a selection, e.g. to compare only two particular studies, or to weight and exclude entries through masks.

## Databases

A **database** is a directory containing TEDFs, their metadata, variable definitions, variable mappings, masks, and the BibTeX file of sources. POSTED ships one public database inside the package. Additional databases, e.g. for project-specific or confidential data, can be registered at runtime and are read with the same code paths.

The public database is intended for a comprehensive set of general-purpose data that serves most users. Private databases provide a low-threshold way to extend POSTED without going through the review process of the public database, and they allow working with data that cannot be published.

## Variable mappings

Sources express the same information in different forms. One source gives fixed operating cost as a percentage of CAPEX, another as an absolute cost per unit of capacity, a third as a cost per unit of product. One source gives the utilisation of a plant as full-load hours, another as a capacity factor. Harmonised data must express each of these in one canonical form.

POSTED handles such cases with **variable mappings**: small pieces of code, stored in the database, that transform one representation of a variable into another during the selection step. A mapping is applied uniformly to all data in a TEDF, so the transformation is documented once and applied consistently. Some mappings need other variables from the same source and case, e.g. the CAPEX to convert a relative OPEX into an absolute one. If a required variable is missing, the framework issues a warning and drops the affected entry rather than guessing. The mappings of the public database are listed in the [NO-SL-AG](noslag.md#variable-mappings) section.

## Masks

Not every value in the database should enter every analysis. A source may be known to misquote another, or a user may prefer to weight recent sources more strongly. Rather than deleting such entries, which would destroy information, POSTED keeps them and lets the aggregation step decide. A **mask** assigns weights to rows that match a condition. A weight of zero or an undefined weight excludes a row, and intermediate weights produce a weighted average. Masks can be stored in the database as defaults for a TEDF or passed to the aggregation step by the user.

## Units and flows

Techno-economic data combines physical units, energy units, and currencies. Flows such as hydrogen or ammonia can be quantified by mass, by volume, or by energy content, and conversion between these depends on the substance and on conventions such as lower or higher heating value. Currencies additionally carry a base year.

POSTED delegates unit handling to the `cet-units` package, which extends the `pint` library with flow-specific units such as `kg_H2` or `MWh_NH3_LHV` and with currencies such as `EUR_2020`. Normalisation converts all values of a variable to a single unit, including conversions between mass and energy for flows and deflation between currency years. The [Units](units.md) section describes the notation.

## Summary

| Concept | Role in the data model | Treatment in processing |
|---|---|---|
| Parent variable | Identifies a TEDF and prefixes its variables | Optionally prepended to output |
| Variable and reference variable | Numerator and denominator of a reported ratio | Converted separately, rebased onto common references |
| Case field | Competing alternatives, including `source` and `period` | Selected by value, averaged when aggregated |
| Component field | Parts that add up to a whole | Summed when aggregated |
| Period | Year of the estimate | Interpolated and extrapolated on request |
| Variable mapping | Code converting one form of a variable into another | Applied during selection |
| Mask | Weights for rows matching a condition | Applied during aggregation |
| Unit | Physical unit, flow unit, or currency with base year | Converted during normalisation |
