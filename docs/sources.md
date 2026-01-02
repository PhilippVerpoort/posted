---
hide:
  - navigation
---

This page contains bibliographic information for the sources referenced in the `source` column of the techno-economic data files.

```python exec="true" session="index" showcode="false"
import pandas as pd
from posted import load_sources, format_sources


sources = load_sources("public")
sources_formatted = format_sources(sources, form='html')
df_table = pd.DataFrame.from_dict(sources_formatted, orient="index").reset_index()

def combine_urls(row: pd.Series) -> str:
    ret = []
    if row["url_doi"]:
        ret.append(f"[ :simple-doi: DOI ]({row['url_doi']}){{ .sm-button }}")
    if row["url"] and (not row["doi"] or (row["doi"] == row["url_doi"])):
        ret.append(f"[ :material-link-box: Link ]({row['url']}){{ .sm-button }} ")
    if row["pdf"]:
        ret.append(f"[ :fontawesome-solid-file-pdf: PDF ]({row['pdf']}){{ .sm-button }} ")
    return " ".join(ret)

col1 = (
    df_table["index"]
    .apply(lambda ref_id: f"<p id=\"{ref_id}\">[{ref_id}](../sources/#{ref_id})</p>")
    .rename("Identifier")
)
col2 = df_table["bib"].rename("Bibliographic information")
col3 = df_table.apply(combine_urls, axis=1).rename("Link")

print(
    pd.concat([col1, col2, col3], axis=1)
    .apply(lambda col: col.str.replace("|", "\\|").str.replace("\n", " "))
    .fillna('')
    .to_markdown(index=False)
)
```
