---
hide:
  - navigation
  - toc
---

<p align="center">
  <img src="assets/logos/logo-light.svg" class="only-light" alt="POSTED Header Logo" style="max-width: 600px; width: 100%; margin-bottom: 20px;">
  <img src="assets/logos/logo-dark.svg" class="only-dark" alt="POSTED Header Logo" style="max-width: 600px; width: 100%; margin-bottom: 20px;">
</p>


# POSTED: Potsdam Open-Source Techno-Economic Database

[![DOI](https://zenodo.org/badge/616985767.svg)](https://doi.org/10.5281/zenodo.10639752)
[![Code Licence: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/PhilippVerpoort/posted/blob/main/LICENSE.md)
[![Data License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://github.com/PhilippVerpoort/posted/blob/main/posted/database/LICENSE.md)
[![Documentation Status](https://img.shields.io/badge/docs-online-blue)](https://philippverpoort.github.io/posted/latest/)
[![CI](https://github.com/PhilippVerpoort/posted/actions/workflows/ci.yml/badge.svg)](https://github.com/PhilippVerpoort/posted/actions/workflows/ci.yml)
[![Code style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-109cf5?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
![Python versions](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)

POSTED stands for **Potsdam Open-Source Techno-Economic Database**. It is pronounced the same way as the English word [posted](https://dictionary.cambridge.org/pronunciation/english/posted) /ˈpəʊs.tɪd/.

POSTED is a public database of techno-economic data on energy and climate-mitigation technologies and a framework for consistent handling of this database.

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } __User Guide__

    ---

    Understand the basic concepts of POSTED.

    [:octicons-arrow-right-24: Read documentation](guide/overview.md)

-   :material-database:{ .lg .middle } __Database__

    ---

    Look at the data currently available in the database.

    [:octicons-arrow-right-24: Look at the data](data/index.md)

-   :material-file-code:{ .lg .middle } __API Reference__

    ---

    Inspect the functions and classes of the POSTED framework written in Python.

    [:octicons-arrow-right-24: Read the code docs](api/index.md)

</div>

## Credits and Thanks

* The software creation and data curation have been primarily conducted at the [Potsdam Institute for Climate Impact Research (PIK)](https://www.pik-potsdam.de/), a German research institute conducting integrated research for global sustainability.
* This work has been completed as part of the Ariadne project with funding from the German Federal Ministry of Research, Technology and Space (grant nos. 03SFK5A, 03SFK5A0-2).
* The software code has been written by P.C. Verpoort, with support by L. Heidweiler and P. Effing.
* The data has been curated primarily by P.C. Verpoort, with many valuable contributions by other colleagues from PIK (see [`CITATION.cff`](https://github.com/PhilippVerpoort/posted/blob/main/CITATION.cff) for a full list).

## How to cite

* To cite a release (recommended), please refer to a specific version archived on [Zenodo](https://zenodo.org/doi/10.5281/zenodo.10639752).
* To cite a specific commit, please refer to the citation information in [`CITATION.cff`](https://github.com/PhilippVerpoort/posted/blob/main/CITATION.cff) and include the commit hash.
* In addition to citing this database, you may also want to cite the original sources. Bibliographic information for individual sources can be found under [Sources](sources.md) or in the BibTeX file [`sources.bib`](https://github.com/PhilippVerpoort/posted/blob/main/posted/database/sources.bib).

## Licenses

The software code located in `posted/` in this repository is licensed under an [MIT Licence](https://github.com/PhilippVerpoort/posted/blob/main/LICENSE.md).

The data located in `posted/database/` in this repository is licensed under a [CC-BY-4.0](https://github.com/PhilippVerpoort/posted/blob/main/posted/database/LICENSE.md).
