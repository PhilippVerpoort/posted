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
# # Industrial Heat Generation

# %% [markdown]
# This dataset contains techno-economic data on industrial heat generation technologies, including gas-fired and electric steam boilers as well as large-scale and high-temperature heat pumps.

# %%
# Dependencies.
from IPython.display import HTML, Markdown

import pandas as pd
pd.options.plotting.backend = "plotly"
import plotly.express as px

from posted import TEDF


# Set variable of TEDF.
var = "Tech|Industrial Heat Generation"

# Loading the TEDF.
tedf = TEDF.load(var)

# Periods covered by DEA TIPIH 2026 data.
periods_dea = [2025, 2030, 2035, 2040, 2050]

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
# ### Heat source (`heat_source`)

# %%
Markdown(
    "\n".join(f"* **{code}**: {desc}" for code, desc in tedf.fields["heat_source"].codes.items())
)

# %% [markdown]
# ## Aggregated parameters

# %% [markdown]
# All DEA-sourced data in this dataset can be aggregated via the NOSLAG workflow, which yields the following parameters:

# %%
aggregated = tedf.aggregate(
    period=periods_dea,
    period_mode="none",
    agg=["source", "heat_source", "size"],
    append_references=True,
)

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
# ## CAPEX

# %% [markdown]
# The figure below shows projected CAPEX for each technology from 2025 to 2050 as reported by the DEA.

# %%
df_plot = (
    tedf.aggregate(
        period=periods_dea,
        period_mode="none",
        agg=["source", "heat_source"],
    )
    .query("variable == 'CAPEX'")
    .assign(
        category=lambda df: df["subtech"].str.contains("boiler").map(
            {True: "Boiler", False: "Heat pump"}
        ),
        label=lambda df: df["subtech"] + " (" + df["size"] + ")",
    )
    .sort_values("period")
)

display(
    df_plot
    .plot.line(
        x="period",
        y="value",
        color="label",
        facet_col="category",
        markers=True,
    )
    .update_xaxes(title=None)
    .update_yaxes(title=None)
    .for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    .update_layout(
        legend_title="Technology",
        yaxis_title="{variable} per {reference_variable}  ( {unit} / {reference_unit} )".format(**df_plot.iloc[0]),
    )
)

# %% [markdown]
# ## Efficiency and COP

# %% [markdown]
# The figure below compares energy input per unit of heat output in 2025. For boilers the relevant metric is thermal efficiency; for heat pumps it is the coefficient of performance (COP).

# %%
df_plot = (
    tedf.aggregate(
        period=[2025],
        period_mode="none",
        agg=["source", "heat_source", "size"],
    )
    .query("variable.str.startswith('Input|')")
    .assign(carrier=lambda df: df["variable"].str.removeprefix("Input|"))
)

display(
    df_plot
    .plot.bar(
        x="subtech",
        y="value",
        color="carrier",
        barmode="group",
        color_discrete_sequence=px.colors.qualitative.D3,
    )
    .update_xaxes(title=None)
    .update_layout(
        legend_title="Energy carrier",
        yaxis_title="Energy input per heat output  ( {unit} / {reference_unit} )".format(**df_plot.iloc[0]),
    )
)

# %% [markdown]
# ## Investment cost by heat source

# %% [markdown]
# The figure below shows investment cost data from Pieper (2018) for large-scale heat pumps across different heat sources and plant sizes.

# %%
df_plot = (
    tedf.aggregate(
        period=[2018],
        period_mode="none",
        agg=["subtech"],
    )
    .query("source == 'Pieper-2018' and variable == 'CAPEX'")
    .sort_values(
        by="size",
        key=lambda col: col.str.extract(r"([0-9.]+)")[0].astype(float),
    )
)

display(
    df_plot
    .plot.bar(
        x="heat_source",
        y="value",
        color="size",
        barmode="group",
        color_discrete_sequence=px.colors.qualitative.D3,
    )
    .update_xaxes(title=None)
    .update_layout(
        legend_title="Plant size",
        yaxis_title="{variable} per {reference_variable}  ( {unit} / {reference_unit} )".format(**df_plot.iloc[0]),
    )
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
