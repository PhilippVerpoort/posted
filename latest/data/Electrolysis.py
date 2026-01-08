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
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Electrolysis

# %% editable=true slideshow={"slide_type": ""} hide_input=true
# Preparing notebook.

# Importing dependencies.
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
from posted import TEDF
from itables import show

# Setting up plotly for plotting.
pd.options.plotting.backend = "plotly"
pio.renderers.default = "notebook_connected"

# Loading the TEDF.
tedf = TEDF.load("Tech|Electrolysis")

# Determine periods to show.
periods = [int(p) for p in tedf.raw.period.str.split(",").explode().unique() if p != "*"]

# %% [markdown]
# ## Aggregated parameters

# %% [markdown]
# All data added to the POSTED database is aggregated automatically using the POSTED framework. The result yields the following parameters:

# %%
aggregated = tedf.aggregate(
    period=periods,
    reference_capacity="Input Capacity|Electricity",
    reference_activity="Output|Hydrogen",
    interpolate_period=False,
    expand_not_specified=False,
    append_references=True,
    agg=["source", "size"],
    units={"Input|Heat": "kWh"},
)

show(
    aggregated
    .query("~variable.str.startswith('Total')")
    .pivot(
        index=aggregated.columns[:-3],
        columns=["variable", "unit"],
        values="value",
    )
    .map(lambda x: float(f"{x:.3g}") if not np.isnan(x) else x)
    .fillna("")
)

# %% [markdown]
# ## CAPEX

# %% [markdown]
# The figure below gives an overview of CAPEX values reported by different sources across times, subtechnology (Alkaline, PEM, Solid Oxide), and plant size.

# %%
selected = tedf.select(
    period=periods,
    reference_capacity="Input Capacity|Electricity",
    reference_activity="Output|Hydrogen",
    interpolate_period=False,
    expand_not_specified=False,
)

df_plot = (
    selected
    .query("variable=='CAPEX'")
    .sort_values(by="size", key=lambda col: col.str.extract(r"([0-9]+) .*")[0].astype(float))
    .sort_values(by="period")
)

display(
    df_plot
    .plot.line(
        x="period",
        y="value",
        color="source",
        facet_col="size",
        facet_row="subtech",
        markers=True,
    )
    .update_xaxes(
        title=None,
    )
    .update_yaxes(
        title=None,
    )
    .for_each_annotation(
        lambda a: a.update(text=": ".join(a.text.split("=")))
    )
    .add_annotation(
        text="{variable} per {reference_variable}  [ {unit} / {reference_unit} ]".format(**df_plot.iloc[0]),
        x=-0.05,
        y=+0.5,
        textangle=-90,
        showarrow=False,
        xref="paper",
        yref="paper",
    )
)

# %% [markdown]
# ## Electricity demand

# %%
aggregated = tedf.aggregate(
    period=periods,
    reference_capacity="Input Capacity|Electricity",
    reference_activity="Output|Hydrogen",
    interpolate_period=False,
    expand_not_specified=False,
    agg="size",
)

df_plot = (
    aggregated
    .query("variable=='Input|Electricity'")
    .sort_values(by="period")
)

display(
    df_plot
    .plot.line(
        x="period",
        y="value",
        color="source",
        facet_col="subtech",
        markers=True,
    )
    .update_xaxes(
        title=None,
    )
    .for_each_annotation(
        lambda a: a.update(text=": ".join(a.text.split("=")))
    )
    .update_layout(
        yaxis_title="{variable} per {reference_variable}  [ {unit} / {reference_unit} ]".format(**df_plot.iloc[0]),
    )
)

# %% [markdown]
# ## Raw data

# %% [markdown]
# The table below contains the raw data contained in the public POSTED database. This data has not be automatically normalised or harmonised in any way. You can also find this data in the GitHub repo in this file:
# [posted/database/tedfs/Tech/Electrolysis.csv](https://github.com/PhilippVerpoort/posted/blob/main/posted/database/tedfs/Tech/Electrolysis.csv)

# %%
show(tedf.raw.fillna(""))
