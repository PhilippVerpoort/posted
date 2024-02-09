# POSTED: Potsdam Open-Source Techno-Economic Database for climate-mitigation technologies
POSTED is a public database of techno-economic data on energy and climate-mitigation technologies, along with a framework for consistent data handling and an open-source toolbox for techno-economic assessments (TEA). In particular, it provides a structure for and contains data on investment cost, energy and feedstock demand, other fixed and variable costs, emissions intensities, and other characteristics of conversion, storage, and transportation technologies in the energy and related sectors. The accompanying software code is intended for consistent maintenance of this data and for deriving straight-forward results from them, such as levelised cost, greenhouse-gas emission intensities, or marginal abatement cost.

POSTED was created and is maintained by researchers at the [Potsdam Institute for Climate Impact Research (PIK)](https://www.pik-potsdam.de/en/), a German research institute conducting integrated research for global sustainability. The source code of the accompanying framework and structure is written in both Python and R, and it is open-sourced via [this git repository](https://github.com/PhilippVerpoort/posted) and can be used and redistributed under the [MIT License](https://opensource.org/license/mit/).


## INSTALLATION
You can install the `posted` Python package via:
```bash
# when using poetry
poetry add git+https://github.com:PhilippVerpoort/posted.git

# when using pip
pip install git+https://github.com:PhilippVerpoort/posted.git
```

You can install the `posted` R package using `install_github` from `devtools` via:
```R
install_github('PhilippVerpoort/posted')
```

Packages on [PyPI](https://pypi.org/) and [CRAN](https://cran.r-project.org/) will be made available at a later stage.


## DEPENDENCY MANAGEMENT FOR TESTING AND DEVELOPMENT
Python dependencies are managed via [poetry](https://python-poetry.org/). To install dependencies in a virtual Python environment, please type the following after cloning.

```bash
poetry install
```

R dependencies are managed via [renv](https://rstudio.github.io/renv/) and saved to the `renv.lock` file. To install dependencies in a virtual R environment, please type the following after cloning.

```R
renv::restore()
```


## CITATION
To cite POSTED, please use this:

P.C. Verpoort, P. Effing, C. Bachorz, L. Gast, A. Hofmann, J. Dürrwächter, F. Ueckerdt (2023). _POSTED: Potsdam Open-Source Techno-Economic Database._ Version 0.3.0, <https://github.com/PhilippVerpoort/posted>.

A BibTeX entry for LaTeX users is:

 ```latex
@Manual{,
  title = {POSTED: Potsdam Open-Source Techno-Economic Database},
  author = {Philipp C. Verpoort and Paul Effing and Clara Bachorz and Lukas Gast and Anke Hofmann and Jakob Dürrwächter and Falko Ueckerdt},
  year = {2023},
  note = {Version 0.3.0},
  url = {https://github.com/PhilippVerpoort/posted},
}
```

Please remember that it is good scientific practice to cite the authors who published the respective data entries that you use. BibTeX identifiers for the source are reported in the `source` column in each techno-economic datafile. The respecitve BibTeX records can ben found under `inst/extdata/database/sources.bib`.


## LICENSE
In a nutshell -- Code: [MIT](https://opensource.org/license/mit/), Data: [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The source code in this repository located in subdirectories `python/` and `R/` is available under an [MIT Licence](https://opensource.org/license/mit/), a copy of which is also provided as a separate file in this repository.

The data in this repository located in subdirectory `inst/extdata/database/` is available under an [Creative Commons Attribution 4.0 Licence](https://creativecommons.org/licenses/by/4.0/), a copy of which can be found on the highlighted link.
