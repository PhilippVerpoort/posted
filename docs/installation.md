---
hide:
  - navigation
  - toc
---


# How to work with and contribute to POSTED

If you want to use POSTED or even contribute to its development, you first need to get/install POSTED in one of two ways:

* By installing the `posted` package as a dependency.
* By cloning the git [repository on GitHub](https://github.com/PhilippVerpoort/posted.git).


## Installing POSTED as a package

=== "Python"
	You can install the `posted` Python package via:
	```bash
	# when using poetry
	poetry add git+https://github.com:PhilippVerpoort/posted.git

	# when using pip
	pip install git+https://github.com:PhilippVerpoort/posted.git
	```
	A [PyPI](https://pypi.org/) package will be made available at a later stage.
=== "R"
	You can install the `posted` R package using `install_github` from `devtools` via:
	```R
	install_github('PhilippVerpoort/posted')
	```
	A [CRAN](https://cran.r-project.org/) package will be made available at a later stage.

This will allow you to use the data contained in POSTED's public database and general-purpose functions from the NOSLAG and TEAM frameworks.



## Cloning POSTED from source

* The POSTED source code and public database are [available on GitHub](https://github.com/PhilippVerpoort/posted.git).
* Please submit any questions as [issues](https://github.com/PhilippVerpoort/posted/issues) and changes/additions as [pull requests](https://github.com/PhilippVerpoort/posted/pulls).
