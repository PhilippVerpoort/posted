# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python (docs)
#     language: python
#     name: docs
# ---

# %% [markdown]
# # Gas Turbine

# %% [markdown]
# This dataset contains techno-economic data on a gas turbines (conventional, hydrogen-ready, conventional with carbon capture).

# %%
# Dependencies.
from IPython.display import HTML, Markdown

import numpy as np
import pandas as pd
pd.options.plotting.backend = "plotly"
import plotly.express as px
from plotly.subplots import make_subplots

from posted import TEDF


# Set variable of TEDF.
var = "Tech|Gas Turbine"

# Loading the TEDF.
tedf = TEDF.load(var)

# Define units to use.
units = {
    "Output Capacity|Hydrogen": "MW_H2_LHV",
    "CAPEX": "EUR_2024",
    "OPEX Fixed": "EUR_2024/yr",
    "OPEX Variable": "EUR_2024",
    "Output|Electricity": "MWh",
    "Output Capacity|Electricity": "MW",
}

# %% [markdown]
# ## Fields

# %% [markdown]
# The techno-economic data is distinguished across the following fields.

# %% [markdown]
# ### Subtechnologies (`subtech`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["subtech"].codes.items())
)

# %% [markdown]
# ### Hydrogen operation (`mode_h2`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["mode_h2"].codes.items())
)

# %% [markdown]
# ## Aggregated parameters

# %% [markdown]
# All data in this dataset can be aggregated via the NOSLAG workflow, which yields the following parameters:

# %%
aggregated = tedf.aggregate(units=units, append_references=True)

display(
    aggregated
    .pivot(
        index=aggregated.columns[:-3],
        columns=["variable", "unit"],
        values="value",
    )
    # Drop hydrogen operation mode for subtechnologies where it doesn't make sense.
    .query("mode_h2!='H2' or subtech=='CCGT H2-ready'")
    .map(lambda x: float(f"{x:.3g}") if not pd.isnull(x) else x)
    .fillna("")
    .sort_index(key=lambda idx: pd.Series(idx).apply(list(tedf.fields[idx.name].codes).index))
)

# %% [markdown]
# ## Raw data

# %%
Markdown(f"""
The table below contains the raw data contained in this dataset. The raw data has not be normalised or harmonised 
in any way and should closely resemble the data as it is reported by the respective sources. You can also find 
this data in the GitHub repo in this file:
{link_public_github(var)}
""")

# %%
tedf.edit_data()
