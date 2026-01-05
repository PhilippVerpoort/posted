# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: Python (docs)
#     language: python
#     name: docs
# ---

# %% [markdown]
# # Steel casting and hot rolling

# %%
# Dependencies.
from IPython.display import HTML, Markdown

import numpy as np
import pandas as pd
pd.options.plotting.backend = "plotly"
import plotly.express as px

from posted import TEDF

# %% [markdown]
# ## Aggregated parameters

# %% [markdown]
# All data added to the POSTED database is aggregated automatically using the POSTED framework. The result yields the following parameters:

# %%
for t in ["Steel Casting", "Steel Hot Rolling"]:
    display(Markdown(f"### {t}"))
    display(
        TEDF.load(f"Tech|{t}").aggregate(append_references=True)
    )

# %% [markdown]
# ## Raw data

# %%
Markdown(f"""
The tables below contain the raw data contained in the public POSTED database. This data has not be automatically normalised or harmonised in any way. You can also find this data in the GitHub repo in this file:
{link_public_github('Tech|Steel Casting')} and {link_public_github('Tech|Steel Hot Rolling')}
""")

# %%
for t in ["Steel Casting", "Steel Hot Rolling"]:
    display(Markdown(f"### {t}"))
    display(TEDF.load(f"Tech|{t}").edit_data())
