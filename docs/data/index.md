---
title: Data
---

# Data

Each TEDF will be made available here for quick inspection. For full detail, please consult the [repository on GitHub](https://github.com/PhilippVerpoort/posted/) or install and run the Python package.

```python exec="true" showcode="false"
from pathlib import Path

for file in (Path(".") / "docs" / "data").glob("*.ipynb"):
    print(f"* [{file.stem}]({file.stem})")
```

> **Note:** The list above contains all datasets that already meet the consistency requirements and have fully been integrated into POSTED. For new datasets and additions to existing datasets under review, please look at the Issues and Pull Requests on GitHub.
