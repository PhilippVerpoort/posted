---
title: Contribute
---

# How to contribute to POSTED

Contributions to the data curated in POSTED and to the functionalities implemented in its code are very much encouraged and greatly appreciated.

## By creating a pull request on GitHub

POSTED — including its public database and the source code of its underlying Python framework — is managed on a [public GitHub repository](https://github.com/PhilippVerpoort/posted).

You can contribute your data directly by:

* [Forking POSTED on GitHub](https://github.com/PhilippVerpoort/posted/fork)
* Clone your fork and make local edits
* Commit your changes to your forked repository
* Create a pull request [here](https://github.com/PhilippVerpoort/posted/pulls)

Generic information on creating pull requests can be found [here](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).

This method has many advantages, e.g. automated testing procedures, discussing changes through the GitHub interface, full public transparency, etc.

## By sending a data file to the maintainers

GitHub pull requests may be a barrier for contribution to some users. We therefore also encourage users to send us their raw data directly.

Data files can be sent directly via email to `philipp DOT verpoort AT pik MINUS potsdam DOT de` (email address obfuscated to protect against web crawlers). Files can be attached directly to emails (if less than 10 MB in size) or uploaded to an appropriate file-sharing service. Files may be shared as comma-separated value (CSV) ASCII files, as XLSX files (typically created using Microsoft® Excel® or compatible software), or ODS files (typically created using LibreOffice™, Apache OpenOffice™, or other compatible software).

Contributors are encouraged to try to use the correct [format](format.md) when providing their data. However, the data does not have to be in the perfect and final format yet when sharing. The authors of POSTED are happy to help convert data to the correct format.

## Things to bear in mind

Here is a list of things to bear in mind while collecting data for POSTED and submitting it for inclusion in the public database.

* **What data to include:** Generally, the idea is to have relevant data reported in POSTED. This does not mean that the data has to be of high quality. Quality-filtering may happen through selecting data (possibly with masks) using the POSTED framework. If you think that somebody would find the data at hand interesting or relevant for a specific technology or related component, then it can be included. As such, literature that reports certain data but has its focus on very different topics or methods may be included if it is relevant because no other literature reports better data.
* **Report values as the source does:** Enter values in the unit, with the reference quantity, and for the year that the source states. Do not convert units, deflate currencies, or rescale to a different plant size by hand. The framework performs these conversions. See [Concepts](concepts.md#raw-data-and-harmonised-data).
* **Document unavoidable conversions:** If a value cannot be entered without a manual step, e.g. because a source reports per tonne of steel while the TEDF refers to direct reduced iron, record the assumption and the conversion factor in the `comment` column.
* **Use reference variables:** Report ratios as a variable and a reference variable with separate values and units rather than as a compound unit. A CAPEX of 1000 EUR per kW is entered with `value` 1000, `unit` `EUR_2020`, `reference_variable` `Output Capacity|Hydrogen`, `reference_value` 1, and `reference_unit` `kW`.
* **Be precise about provenance:** Fill `source_detail` so that another person can find the number in the source without searching, e.g. the table number, the page, or the spreadsheet cell.
* **Choose the most specific field entry the source supports:** A plain value where the case is known, a comma-separated list where a value holds for several cases, the asterisk where it holds for all cases, and `N/S` only where the source gives no information. See [Format](format.md#field-cell-values).
* **One source per row:** If several sources report the same value, enter it once per source.
* **Add the source to `sources.bib`:** Every new source needs a BibTeX entry. Keep the file sorted alphabetically by key and include a DOI, URL, or PDF link where available.

## Adding a new TEDF

A new technology or variable group is added as a new TEDF. The steps are as follows.

1. Choose a parent variable, e.g. `Tech|My Technology`, and create `tedfs/Tech/My Technology.csv` and `tedfs/Tech/My Technology.yaml` in the database.
2. In the metadata file, declare the fields the data needs, reference the variable definitions (`predefined: [technology]` for technologies), and list the mappings to apply. Copy the metadata of a similar TEDF as a starting point. See [Format](format.md#metadata-file).
3. Enter the data in the CSV file following the [format](format.md).
4. Add any new sources to `sources.bib`.
5. Run the test suite (see below). It validates all TEDFs and runs the full NO-SL-AG workflow on each of them.
6. For the public database, add a notebook `docs/data/My Technology.py` in the `jupytext` percent format that presents the dataset. The existing notebooks serve as templates. The notebooks are executed and converted during the documentation build.

## Running the tests

The repository uses `uv` for environment management and `unittest` for testing.

```bash
uv sync
uv run python -m unittest discover -v
```

The tests check that every TEDF validates, that the NO-SL-AG workflow runs on every TEDF, and that the source identifiers in the TEDFs and in `sources.bib` are consistent. Code contributions are additionally checked with `ruff`.

```bash
uv sync --group dev
uv run ruff check ./posted/ ./tests
uv run ruff format --check ./posted/ ./tests/
```

## Building the documentation

The documentation is built with `mkdocs`. The data notebooks are executed before the build.

```bash
uv sync --group docs
uv run scripts/register_docs_kernel.py
BUILD_POSTED_DOCS=1 uv run jupytext --to notebook --execute docs/data/*.py
uv run mkdocs serve
```

## Contributing code

Changes to the framework, e.g. new variable mappings, new field types, or bug fixes, follow the same pull-request procedure. Please open an issue first for larger changes so that the design can be discussed. Code should follow the existing style, pass `ruff`, and come with a test where feasible.
