# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
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
# # Haber-Bosch with Air Separation Unit

# %% [markdown]
# This dataset contains techno-economic data on Haber-Bosch synthesis plants with an Air-Separation Unit (ASU).

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
var = "Tech|Haber-Bosch with Air Separation Unit"

# Loading the TEDF.
tedf = TEDF.load(var)

# Define units to use.
units = {
    "CAPEX": "EUR_2024",
    "OPEX Fixed": "EUR_2024/yr",
    "OPEX Variable": "EUR_2024",
    "Output Capacity|Ammonia": "t_NH3/year",
    "Output|Ammonia": "t_NH3",
}

# %% [markdown]
# ## Aggregated parameters

# %% [markdown]
# All data in this dataset can be aggregated via the NOSLAG workflow, which yields the following parameters:

# %%
aggregated = tedf.aggregate(units=units, append_references=True)

display(
    aggregated
    .set_index(["variable", "unit"])
    .T
    .map(lambda x: float(f"{x:.3g}") if not pd.isnull(x) else x)
    .fillna("")
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
