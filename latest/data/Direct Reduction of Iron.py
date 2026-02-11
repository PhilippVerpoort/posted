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
# # Direct Reduction of Iron

# %%
# Dependencies.
from IPython.display import HTML, Markdown

import numpy as np
import pandas as pd
pd.options.plotting.backend = "plotly"
import plotly.express as px

from posted import TEDF


# Set variable of TEDF.
var = "Tech|Direct Reduction of Iron"

# Loading the TEDF.
tedf = TEDF.load(var)

# Define units to use for energy carriers.
units = {
    "Input|Electricity": "MWh",
    "Input|Heat": "MWh",
    "Input|Natural Gas": "MWh_NG_LHV",
    "Input|Hydrogen": "MWh_H2_LHV",
}

# %% [markdown]
# ## Fields

# %% [markdown]
# The techno-economic data is distinguished across the following additional fields.

# %% [markdown]
# ### Operation mode (`mode`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["mode"].codes.items())
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
selected = tedf.select(units=units)
aggregated = tedf.aggregate(units=units)

df_plot = (
    pd.concat([
        selected,
        aggregated.assign(source="POSTED-default"),
    ])
    .query(f"variable.isin({list(units)})")
    .assign(variable=lambda df: df["variable"].str.extract(r"^Input\|(.*)", expand=False))
    .assign(variable=lambda df: df.agg(lambda r: f"{r['variable']}{(' (' + r['component'] + ')') if r['component'] not in ['#', np.nan] else ''}", axis=1))
    .sort_values(by="variable")
)

colorway = px.colors.qualitative.D3
colours = {
    "Electricity": colorway[2],
    "Heat": colorway[3],
    "Hydrogen": colorway[0],
    "Hydrogen (Heat)": "#3F94CF",
    "Hydrogen (Reduction agent)": "#0D619C",
    "Natural Gas": colorway[1],
}

display(
    df_plot
    .plot.bar(
        x="source",
        y="value",
        color="variable",
        facet_col="mode",
        color_discrete_map=colours,
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
        yaxis_title="Energy demand per {reference_variable}  ( MWh / {reference_unit} )".format(**df_plot.iloc[0]),
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
tedf.edit_data()
