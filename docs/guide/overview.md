---
title: Overview
---

# Overview

## Purpose

POSTED is aimed at researchers who perform techno-economic assessments or modelling exercises in the context of the energy transition, industrial ecology, climate mitigation, and related fields.

Such work relies on techno-economic parameters, i.e. a combination of technological parameters (concerning the physical performance of a technology, such as energy demand or conversion efficiency) and economic parameters (concerning its cost of investment and operation). Other relevant parameters include market prices, technology lifetimes, or emission intensities.

This data is compartmentalised and scattered across many sources (academic literature, grey literature, technical reports, databases of public agencies, etc). Collecting it for an analysis, tracing its origin transparently, and harmonising it consistently is a cumbersome and error-prone endeavour that is repeated by many research groups in parallel.

POSTED addresses this problem with two components.

* **A public database** of techno-economic data, curated as a set of techno-economic data files (TEDFs) that record values as they are reported in the original sources.
* **A Python framework** that converts this raw data into harmonised, analysis-ready data in a reproducible way. The central part of this framework is the NO-SL-AG (normalise, select, aggregate) workflow.

The POSTED database and framework aim to achieve the following.

* **Curate a comprehensive collection of techno-economic data** to relieve researchers from performing this task manually for each analysis.
* **Store this data in a machine-readable format** to ease interoperability.
* **Transparently report where original data can be found** to make research and its assumptions understandable and reproducible.
* **Simplify the conversion of raw data into specific formats** to ease further processing in other tools.
* **Avoid misunderstandings when storing and reading data** through the development and explication of clear standards.
* **Be extendable** to meet a variety of requirements by different user groups.

In particular, POSTED aspires to comply with the [FAIR principles](https://openscience.eu/article/infrastructure/guide-fair-principles) of research data.

## Design principles

Three principles shape the design of POSTED. They are explained in more detail in the [Concepts](concepts.md) section.

**Report data as found in the source, harmonise in code.** A TEDF records each value with the unit, the reference quantity, and the period stated by the original source. No manual unit conversion, currency deflation, or rescaling takes place when data is entered. All of these transformations are performed by the framework when the data is read. This separation keeps the database transparent and auditable: every number in a TEDF can be checked against its source, and every transformation is documented in code rather than in the heads of contributors.

**Make the structure of the data explicit.** Techno-economic data varies along several dimensions: across sources, across variants of a technology (sub-technologies, plant sizes, operation modes), across time, and across sub-components of a cost or energy demand. POSTED represents each of these dimensions as a column of the TEDF with a defined type. The type determines how the framework treats the dimension when selecting and aggregating data, for instance whether values are averaged or summed.

**Separate data collection from data judgement.** Values from sources of varying quality can coexist in the database. Whether a value is used in a specific analysis is decided when the data is selected and aggregated, for instance by restricting to specific sources or by applying masks that weight or exclude entries. Contributors are not required to judge the quality of a source before adding its data.

## Components at a glance

| Component | What it is | Where to read more |
|---|---|---|
| Database | A directory with TEDFs, their metadata, variable definitions, variable mappings, masks, and a BibTeX file of sources. POSTED ships a public database and can register private ones. | [Format](format.md#databases) |
| TEDF | A techno-economic data file: a CSV file plus a YAML metadata file describing one technology or one group of related variables. | [Format](format.md#techno-economic-data-files) |
| Variables | Named quantities such as `CAPEX` or `Input|Electricity`. Many variables are reported relative to a reference variable, e.g. CAPEX per unit of output capacity. | [Concepts](concepts.md#variables-and-reference-variables) |
| Fields | Additional columns that distinguish cases (competing alternatives, averaged over) and components (parts of a whole, summed up). | [Concepts](concepts.md#cases-and-components) |
| NO-SL-AG | The three-step workflow normalise, select, aggregate that turns raw data into harmonised data. | [NO-SL-AG](noslag.md) |
| Units | Unit handling, including flow-specific units and currencies with base years, via the `cet-units` package. | [Units](units.md) |
| Sources | Bibliographic records in BibTeX format referenced from every row of data. | [Format](format.md#sources) |

## Workflow

A typical workflow looks like this.

1. **Find** techno-economic data in an original source, e.g. an academic journal article or a technical report.
2. **Record** this data in a TEDF in its original form (unit, reference quantity, period, etc). TEDFs are UTF-8 encoded comma-separated value (CSV) files. See [Format](format.md).
3. **Normalise** the data alongside data from other sources to common units and reference values using `TEDF.normalise()`. See [NO-SL-AG](noslag.md#normalise).
4. **Select** the cases and components required for the analysis, e.g. a specific year or sub-technology, using `TEDF.select()`. This step also harmonises variables, e.g. by expressing all energy inputs relative to the same output. See [NO-SL-AG](noslag.md#select).
5. **Aggregate** the data over sources, cases, or components using `TEDF.aggregate()`. See [NO-SL-AG](noslag.md#aggregate).
6. **Use** the resulting harmonised data as input for further processing in other tools.

Steps 3 to 5 build on each other: `select()` runs `normalise()` internally and `aggregate()` runs `select()` internally. Users therefore typically call only one of the three methods.

For a hands-on introduction, continue with [Getting Started](getting-started.md). For the ideas behind the data model, continue with [Concepts](concepts.md).
