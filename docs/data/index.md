---
title: Data
---

# Data

This section presents the techno-economic data files (TEDFs) of the public database. Each page describes one dataset: the fields it distinguishes, the parameters obtained from aggregating it with the [NO-SL-AG](../guide/noslag.md) workflow, selected comparisons across sources, and the raw data as entered from the sources. The pages are generated from Jupyter notebooks that can be downloaded and re-run with the package installed.

For full detail, please consult the [repository on GitHub](https://github.com/PhilippVerpoort/posted/tree/main/posted/database/tedfs) or install and run the Python package. The structure of the files is specified in the [Format](../guide/format.md) section.

```python exec="true" showcode="false"
from pathlib import Path

for file in (Path(".") / "docs" / "data").glob("*.ipynb"):
    print(f"* [{file.stem}]({file.stem})")
```

> **Note:** The list above contains all datasets that already meet the consistency requirements and have fully been integrated into POSTED. For new datasets and additions to existing datasets under review, please look at the Issues and Pull Requests on GitHub.
