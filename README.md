# POSTED: Potsdam open-source techno-economic database

POSTED is a database of techno-economic data (CAPEX, OPEX, energy demand, feedstocks demand, etc) for technologies and processes relevant to the energy system and the net-zero transition. It is published along with software tools for simple and easy techno-economic analysis (cost comparisons, emissions intensities, marginal abatement cost).

Both are created and maintained by researchers at the [Potsdam Institute for Climate Impact Research (PIK)](https://www.pik-potsdam.de). They are available open-source via this git repository and can be used and redistributed via the [MIT license](https://choosealicense.com/licenses/mit/).


## Dependency management

Python dependencies are managed via [poetry](https://python-poetry.org/). To install dependencies in a virtual environment, please type the following after cloning.

```bash
poetry install
```

R dependencies are manage via [renv](https://rstudio.github.io/renv/). To install dependencies in a virtual environment, please type the following after cloning.

```bash
renv::restore()
```

## Citation

To cite POSTED, please use this:

P.C. Verpoort, C. Bachorz, J. Dürrwächter, L. Gast, A. Hofmann, P. Effing, F. Ueckerdt (2023). _POSTED: Potsdam open-source techno-economic database._ Version 0.1.0, <https://github.com/PhilippVerpoort/posted>.

A BibTeX entry for LaTeX users is

 ```latex
@Manual{,
  title = {POSTED: Potsdam open-source techno-economic database},
  author = {},
  year = {2023},
  note = {Version 0.1.0},
  url = {https://github.com/PhilippVerpoort/posted},
}
```


## License

[MIT](https://choosealicense.com/licenses/mit/)
