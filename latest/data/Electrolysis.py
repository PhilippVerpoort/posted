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
# # Electrolysis

# %% editable=true slideshow={"slide_type": ""}
# Dependencies.
from IPython.display import HTML, Markdown

import pandas as pd
pd.options.plotting.backend = "plotly"

from posted import TEDF


# Set variable of TEDF.
var = "Tech|Electrolysis"

# Loading the TEDF.
tedf = TEDF.load(var)

# Determine periods to show.
periods = [int(p) for p in tedf.raw.period.str.split(",").explode().unique() if p != "*"]

# %% [markdown]
# ## Fields

# %% [markdown]
# The techno-economic data on electrolysis is distinguished across the following additional fields.

# %% [markdown]
# ### Subtechnologies

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["subtech"].codes.items())
)

# %% [markdown]
# ### Size

# %% [markdown]
# Mainly CAPEX but also other parameters crucially depend on the size of an electrolysis plant. The size can be added as a non-coded field. For some sources, this may not be reported and hence set to `N/S` (not specified).

# %% [markdown]
# ## Aggregated parameters

# %% [markdown]
# All data added to the POSTED database is aggregated automatically using the POSTED framework. The result yields the following parameters:

# %%
aggregated = tedf.aggregate(
    period=periods,
    period_mode="none",
    reference_capacity="Input Capacity|Electricity",
    reference_activity="Output|Hydrogen",
    expand_not_specified=False,
    append_references=True,
    agg=["source", "size"],
    units={"Input|Heat": "kWh"},
)

display(
    aggregated
    .query("~variable.str.startswith('Total')")
    .pivot(
        index=aggregated.columns[:-3],
        columns=["variable", "unit"],
        values="value",
    )
    .map(lambda x: float(f"{x:.3g}") if not pd.isnull(x) else x)
    .fillna("")
)

# %% [markdown]
# ## CAPEX

# %% [markdown]
# The figure below gives an overview of CAPEX values reported by different sources across times, subtechnology (Alkaline, PEM, Solid Oxide), and plant size.

# %%
selected = tedf.select(
    period=periods,
    period_mode="none",
    reference_capacity="Input Capacity|Electricity",
    reference_activity="Output|Hydrogen",
    expand_not_specified=False,
)

aggregated = tedf.aggregate(
    period=periods,
    period_mode="none",
    reference_capacity="Input Capacity|Electricity",
    reference_activity="Output|Hydrogen",
    expand_not_specified=False,
    agg=["source", "size"],
    units={"Input|Heat": "kWh"},
)

df_plot = (
    pd.concat([
        selected,
        aggregated.assign(source="POSTED-default", size="N/S"),
    ])
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
    .update_layout(
        legend_title=None,
        yaxis5_title="{variable} per {reference_variable}  [ {unit} / {reference_unit} ]".format(**df_plot.iloc[0]),
    )
)

# %% [markdown]
# ## Electricity demand

# %%
aggregated = tedf.aggregate(
    period=periods,
    period_mode="none",
    reference_capacity="Input Capacity|Electricity",
    reference_activity="Output|Hydrogen",
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
    .update_layout(
        legend_title=None,
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
