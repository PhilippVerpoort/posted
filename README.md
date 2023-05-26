# POSTED: Potsdam Open-Source Techno-Economic Database for climate-mitigation technologies
POSTED is a consistent framework, public database, and open-source toolbox of techno-economic data of climate-mitigation technologies. In particular, it provides a structure and contains actual data on capital expenditure, operational expenditure, energy and feedstock demand, emissions intensities, and other related characteristics of conversion, storage, and transportation technologies in the energy and related sectors. The accompanying software code is intended for consistent maintenance of this data and for deriving straight-forward results from them, such as levelised cost, levelised emissions intensities, or marginal abatement cost.

POSTED was created and is maintained by researchers at the [Potsdam Institute for Climate Impact Research (PIK)](https://www.pik-potsdam.de). The source code of the accompanying framework and structure is written in both Pythong and R, and it is open-sourced via [this git repository](https://github.com/PhilippVerpoort/posted) and can be used and redistributed via the [GNU GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.en.html) License.


## DEPENDENCY MANAGEMENT
Python dependencies are managed via [poetry](https://python-poetry.org/). To install dependencies in a virtual Python environment, please type the following after cloning.

```bash
poetry install
```

R dependencies are managed via [renv](https://rstudio.github.io/renv/). To install dependencies in a virtual R environment, please type the following after cloning.

```R
renv::restore()
```


## CITATION
To cite POSTED, please use this:

P.C. Verpoort, C. Bachorz, P. Effing, L. Gast, A. Hofmann, J. Dürrwächter, F. Ueckerdt (2023). _POSTED: Potsdam Open-Source Techno-Economic Database for climate-mitigation and sustainability-transition technologies._ Version 0.1.0, <https://github.com/PhilippVerpoort/posted>.

A BibTeX entry for LaTeX users is:

 ```latex
@Manual{,
  title = {POSTED: Potsdam Open-Source Techno-Economic Database for climate-mitigation and sustainability-transition technologies},
  author = {Philipp C. Verpoort and Clara Bachorz and Paul Effing and Lukas Gast and Anke Hofmann and Jakob Dürrwächter and Falko Ueckerdt},
  year = {2023},
  note = {Version 0.1.0},
  url = {https://github.com/PhilippVerpoort/posted},
}
```


## LICENSE
In short — Code: [GNU GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.en.html), Data: [Public Domain](https://creativecommons.org/publicdomain/zero/1.0/).

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License** as published by the Free Software Foundation, **version 3.0** of the License or later. You should have received a copy of the GNU General Public License along with this copy of the POSTED software. See the LICENSE file in the root directory. If not, see https://www.gnu.org/licenses/gpl-3.0.en.html.

Note that the database cannot be license-protected, and so it can be regarded as part of the public domain: anyone can use it for anything. Please remember that it is good scientific practice to cite the authors who published the respective data entries you used.
