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
# # Steam Methane Reforming

# %% [markdown]
# This dataset contains techno-economic data on steam methane reforming (including auto-thermal reforming) with and without carbon capture for producing hydrogen.

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
var = "Tech|Steam Methane Reforming"

# Loading the TEDF.
tedf = TEDF.load(var)

# Define units to use.
units = {
    "Output Capacity|Cement": "MW_H2_LHV",
    "CAPEX": "EUR_2024",
    "OPEX Fixed": "EUR_2024/yr",
    "Output|Hydrogen": "MWh_H2_LHV",
    "OPEX Variable": "EUR_2024",
    "Input|Natural Gas": "MWh_NG_LHV",
}

# %% [markdown]
# ## Fields

# %% [markdown]
# The techno-economic data is distinguished across the following fields.

# %% [markdown]
# ### Carbon capture (`carbon_capture`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["subtech"].codes.items())
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
    .loc[lambda df: df[("Capture Rate", "percent")].notnull()]
    .map(lambda x: float(f"{x:.3g}") if not pd.isnull(x) else x)
    .fillna("")
    .loc[list(tedf.fields["subtech"].codes)]
)

# %% [markdown]
# ## Comparison

# %% [markdown]
# The figure below compares key parameters of the different technology options.

# %%
aggregated = tedf.aggregate(units=units, agg=[])

show_variables = {
    "CAPEX": ["CAPEX"],
    "Energy Demand": ["Input|Natural Gas"],
    "Capture Rate": ["Capture Rate"],
}

fig = make_subplots(
    rows=1,
    cols=len(show_variables),
    subplot_titles=list(show_variables),
)

for col, (title, variables) in enumerate(show_variables.items()):
    df_rows = (
        aggregated
        .query(f"variable.isin({variables})")
        .assign(case=lambda df: df.apply(lambda row: "{subtech} {capture_rate} ({source})".format(**row), axis=1))
        .sort_values(by=["subtech", "capture_rate", "source"], key=lambda col: col.apply(["SMR", "ATR"].index) if col.name=="subtech" else col)
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
            x="case",
            y="value",
            color="variable",
            color_discrete_sequence=px.colors.qualitative.D3[color_advance:],
        )
        .data,
        rows=1,
        cols=col+1,
    )
    
    fig.update_layout(**{
        f"xaxis{col+1 if col else ''}": dict(categoryorder="array", categoryarray=df_rows["case"].unique().tolist()),
        f"yaxis{col+1 if col else ''}_title": f"{title}  ( {unit}/{ref_unit} )" if ref_unit==ref_unit else f"{title}  ( {unit} )",
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
The table below contains the raw data contained in this dataset. The raw data has not be normalised or harmonised 
in any way and should closely resemble the data as it is reported by the respective sources. You can also find 
this data in the GitHub repo in this file:
{link_public_github(var)}
""")

# %%
tedf.edit_data()
