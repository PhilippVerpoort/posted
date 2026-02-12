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
# # Integrated Blast Furnace and Basic Oxygen Furnace

# %% [markdown]
# This dataset contains techno-economic data on an integrated BF-BOF steel plant including casting and rolling with and without carbon capture.

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
var = "Tech|Integrated Blast Furnace and Basic Oxygen Furnace"

# Loading the TEDF.
tedf = TEDF.load(var)

# Define units to use.
units = {
    "Output Capacity|Steel Hot-rolled Coil": "t/yr",
    "CAPEX": "EUR_2024",
    "OPEX Fixed": "EUR_2024/yr",
    "Output|Steel Hot-rolled Coil": "t",
    "OPEX Variable": "EUR_2024",
    "Input|Natural Gas": "MWh_NG_LHV",
    "Input|Coal": "MWh_coal_LHV",
}

# %% [markdown]
# ## Fields

# %% [markdown]
# The techno-economic data is distinguished across the following additional fields.

# %% [markdown]
# ### Operation mode (`carbon_capture`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["carbon_capture"].codes.items())
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
# ## Comparison

# %% [markdown]
# The figure below compares key parameters of the different technology options.

# %%
aggregated = tedf.aggregate(units=units)

show_variables = {"CAPEX": ["CAPEX"], "Energy Demand": ["Input|Coal", "Input|Natural Gas"], "Emissions": ["GHG Emissions|CO2"]}

fig = make_subplots(
    rows=1,
    cols=len(show_variables),
    subplot_titles=list(show_variables),
)

for col, (title, variables) in enumerate(show_variables.items()):
    df_rows = (
        aggregated
        .query(f"variable.isin({variables})")
    )
    
    if title == "Energy Demand":
        unit = "MWh_LHV"
    else:
        unit = df_rows["unit"].iloc[0]
    ref_unit = df_rows["reference_unit"].iloc[0]

    color_advance = sum(1 for i, v in enumerate(show_variables.values()) for _ in v if i > col)
    
    fig.add_traces(
        df_rows
        .plot.bar(
            x="carbon_capture",
            y="value",
            color="variable",
            color_discrete_sequence=px.colors.qualitative.D3[color_advance:],
        )
        .data,
        rows=1,
        cols=col+1,
    )
    
    fig.update_layout(**{
        f"xaxis{col+1 if col else ''}": dict(categoryorder="array", categoryarray=list(tedf.fields["carbon_capture"].codes)),
        f"yaxis{col+1 if col else ''}_title": f"{title}  ( {unit}/{ref_unit} )",
    })

fig.update_layout(
    legend_title=None,
    xaxis_title=None,
    barmode="stack",
)

display(fig)

# %% [markdown]
# ## Raw data

# %%
Markdown(f"""
The table below contains the raw data contained in the public POSTED database. This data has not be automatically normalised or harmonised in any way. You can also find this data in the GitHub repo in this file:
{link_public_github(var)}
""")

# %%
tedf.edit_data()
