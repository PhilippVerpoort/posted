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

> **Note:** This area is still under development. More datasets will follow soon.
