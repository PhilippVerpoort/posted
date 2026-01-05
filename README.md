[![DOI](https://zenodo.org/badge/616985767.svg)](https://doi.org/10.5281/zenodo.10639752)
[![Code Licence: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Data License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](./posted/database/LICENSE.md)
[![Documentation Status](https://img.shields.io/badge/docs-online-blue)](https://philippverpoort.github.io/posted/latest/)
[![CI](https://github.com/PhilippVerpoort/posted/actions/workflows/ci.yml/badge.svg)](https://github.com/PhilippVerpoort/posted/actions/workflows/ci.yml)
[![Code style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-109cf5?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
![Python versions](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)

![POSTED Logo](docs/assets/logos/logo-light.svg)

# POSTED: Potsdam open-source techno-economic database

POSTED stands for **Potsdam Open-Source Techno-Economic Database**. It is pronounced the same way as the English word [posted](https://dictionary.cambridge.org/pronunciation/english/posted) /ˈpəʊs.tɪd/.

POSTED is a public database of techno-economic data on energy and climate-mitigation technologies and a framework for consistent handling of this database.

For more help, please consult the [documentation](https://philippverpoort.github.io/posted/latest).

## Installation

You can install POSTED via `pip` directly from GitHub:

```bash
pip install git+https://github.com/PhilippVerpoort/posted.git
````

Or clone and install locally:

```bash
git clone https://github.com/PhilippVerpoort/posted.git
cd posted
pip install .
```

> **Note:** The package will be published on PyPI in the near future for simpler installation.

## Credits and Thanks

* This package has been developed at the [Potsdam Institute for Climate Impact Research (PIK)](https://www.pik-potsdam.de/) by P.C. Verpoort with much appreciated support by L. Heidweiler and P. Effing.
* The data has been curated by P.C. Verpoort with many valuable contributions by other colleagues from PIK (see [`CITATION.cff`](CITATION.cff) for a full list).
* This work has been completed as part of the Ariadne project with funding from the German Federal Ministry of Research, Technology and Space (grant nos. 03SFK5A, 03SFK5A0-2).

## How to cite

* To cite a release (recommended), please refer to a specific version archived on [Zenodo](https://zenodo.org/doi/10.5281/zenodo.10639752).
* To cite a specific commit, please refer to the citation information in [`CITATION.cff`](CITATION.cff) and include the commit hash.
* In addition to citing this database, you may also want to cite the original sources. Bibliographic information for individual sources can be found under [Sources](https://philippverpoort.github.io/posted/latest/sources) or in the BibTeX file [`sources.bib`](posted/database/sources.bib).

## Licenses

The source code located in `posted/` in this repository is licensed under an [MIT Licence](LICENSE.md).

The data located in `posted/database/` in this repository is licensed under a [CC-BY-4.0](./posted/database/LICENSE.md).
