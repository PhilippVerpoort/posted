# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Python (docs)
#     language: python
#     name: docs
# ---

# %% [markdown]
# # Electric Arc Furnace

# %%
# Dependencies.
from IPython.display import HTML, Markdown

import numpy as np
import pandas as pd
pd.options.plotting.backend = "plotly"

from posted import TEDF


# Set variable of TEDF.
var = "Tech|Electric Arc Furnace"

# Loading the TEDF.
tedf = TEDF.load(var)

# Define units to use for energy carriers.
units={
    "Electricity": "MWh",
    "Heat": "MWh",
    "Natural Gas": "MWh_NG_LHV",
    "Coal": "MWh_coal_LHV",
}

# %% [markdown]
# ## Fields

# %% [markdown]
# The techno-economic data is distinguished across the following additional fields.

# %% [markdown]
# ### Operation Mode (`mode`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["mode"].codes.items())
)

# %% [markdown]
# ### Reheating (`reheating`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["reheating"].codes.items())
)

# %% [markdown]
# ## Aggregated parameters

# %% [markdown]
# All data added to the POSTED database is aggregated automatically using the POSTED framework. The result yields the following parameters:

# %%
aggregated = tedf.aggregate(units=units, append_references=True)

display(
    aggregated
    .pivot(
        index=aggregated.columns[:-3],
        columns=["variable", "unit"],
        values="value",
    )
    .map(lambda x: float(f"{x:.3g}") if not pd.isnull(x) else x)
    .fillna("")
)

# %% [markdown]
# ## Energy demand

# %% [markdown]
# The figure below gives an overview of the energy demand reported by different sources across different energy carriers.

# %%
data_all_sources = tedf.aggregate(units=units, reheating="w/o reheating", agg="component")
data_agg_posted = tedf.aggregate(units=units, reheating="w/o reheating")

df_plot = (
    pd.concat([
        data_all_sources,
        data_agg_posted.assign(source="POSTED-default"),
    ])
    .assign(variable=lambda df: df["variable"].str.extract(r"^Input\|(.*)", expand=False))
    .query(f"variable.isin({list(units)})")
)

display(
    df_plot
    .plot.bar(
        x="source",
        y="value",
        color="variable",
        facet_col="mode",
    )
    .update_xaxes(
        title=None,
    )
    .for_each_annotation(
        lambda a: a.update(text=": ".join(a.text.split("=")))
    )
    .update_layout(
        legend_title=None,
        xaxis_title=None,
        yaxis_title="Energy demand per {reference_variable}  [ MWh / {reference_unit} ]".format(**df_plot.iloc[0]),
    )
)

# %% [markdown]
# ## Raw data

# %%
Markdown(f"""
The table below contains the raw data contained in the public POSTED database. This data has not be automatically normalised or harmonised in any way. You can also find this data in the GitHub repo in this file:
{link_public_github(var)}
""")

# %%
edit(tedf)
