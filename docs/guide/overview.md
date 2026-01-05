---
title: User Guide
---

# User Guide

## Purpose

POSTED is aimed at researchers who want to perform techno-economic assessments or modelling exercises in the context of the energy transition, industrial ecology, climate mitigation, and related fields.

Such work often relies on techno-economic parameters, i.e. a combination of technological parameters (concerning the physical performance of a technology) and economic parameters (concerning its cost of investment and operation). Other important parameters may include market prices, technology lifetimes, or emissions intensities.

Such data is often compartmentalised and scattered across many sources (academic literature, grey literature, etc). Collecting this data for analysis, transparently tracing its origin, and consistently harmonising it is a cumbersome and tedious endeavour.

Therefore, the POSTED database and framework aims to achieve the following.

* **Curate a comprehensive collection of techno-economic data** to alleviate researchers from performing this task manually for each analysis.
* **Store this data in a machine-readable format** to ease interoperability.
* **Transparently report where original data can be found** to make research and its assumptions understandable and reproducible.
* **Simplify the conversion of raw data into specific formats** to ease further processing in other tools.
* **Avoid misunderstandings when storing and reading data** through the development and explication of clear standards.
* **Be extendable** to meet a variety of requirements by different users groups.

In particular, POSTED aspires to comply with the [FAIR principles](https://openscience.eu/article/infrastructure/guide-fair-principles) of research data.

## Workflow

A typical workflow looks like this:

1. Find techno-economic data in a original source, e.g. an academic journal article or a technical report.
2. Add this data to the POSTED database in its original format (unit, reference, etc). This is done by editing the `*.tedf` (techno-economic data file) files, which are simple UTF8-encoded comma-separated value (CSV) files.
3. Use the POSTED framework to harmonise this data alongside other data (common units, reference, etc), using the `TEDF.normalise()` function.
4. Select the specific case and/or component of the data required, e.g. a specific year, subtechnology, etc, using the `TEDF.select()` function.
5. Aggregate data over multiple sources, cases, or components using the `TEDF.aggregate()` function.
6. Use the resulting harmonised data as input for some further processing in other tools.
