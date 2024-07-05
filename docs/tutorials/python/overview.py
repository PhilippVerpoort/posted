# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Overview of working with POSTED

# ## Prerequisits

# #### Dependencies

# First, we import some general-purpose libraries. The python-side of `posted` depends on `pandas` for working with dataframes. Here we also use `plotly` and `itables` for plotting and inspecting data, but `posted` does not depend on those and other tools could be used instead. The package `igraph` is an optional dependency used for representing the interlinkages in value chains. The package `matplotlib` is only used for plotting igraphs, which is again optional.

# +
import pandas as pd

import plotly
from itables import init_notebook_mode

init_notebook_mode(all_interactive=True)
pd.options.plotting.backend = "plotly"

# for value chains only
import igraph as ig
import matplotlib.pyplot as plt
# -

# #### Importing POSTED

# The `posted` package has to be installed in the python environment. If it is not installed yet, you can easily install it from the GitHub source code using `pip`.

try:
    import posted
except ImportError:
    # ! pip install git+https://github.com:PhilippVerpoort/posted.git@develop

# Import specific functions and classes from POSTED that will be used later.

from posted.tedf import TEDF
from posted.noslag import DataSet
from posted.units import Q, U
from posted.team import CalcVariable, LCOX, FSCP, ProcessChain, annuity_factor

# Use some basic plotly and pandas functions for plotting and output analysis

# ## NOSLAG

# #### Electrolysis CAPEX

# Let's compare CAPEX data for electrolysis in years 2020–2050 for Alkaline and PEM across different sources (Danish Energy Agency, Breyer, Fraunhofer, IRENA) for different electrolyser plant sizes.

# +
# select data from TEDFs
df_elh2 = DataSet('Tech|Electrolysis').select(
        period=[2020, 2030, 2040, 2050],
        subtech=['AEL', 'PEM'],
        override={'Tech|Electrolysis|Output Capacity|Hydrogen': 'kW;LHV'},
        source=['DEARF23', 'Vartiainen22', 'Holst21', 'IRENA22'],
        size=['1 MW', '5 MW', '100 MW'],
        extrapolate_period=False
    ).query(f"variable=='Tech|Electrolysis|CAPEX'")

# display a few examples
display(df_elh2.sample(15).sort_index())

# sort data and plot
df_elh2.assign(size_sort=lambda df: df['size'].str.split(' ', n=1, expand=True).iloc[:, 0].astype(int)) \
       .sort_values(by=['size_sort', 'period']) \
       .plot.line(x='period', y='value', color='source', facet_col='size', facet_row='subtech')
# -

# Based on those many sources and cases (size and subtechnology), we can now aggregate the data for further use.

DataSet('Tech|Electrolysis').aggregate(
        period=[2020, 2030, 2040, 2050],
        subtech=['AEL', 'PEM'],
        override={'Tech|Electrolysis|Output Capacity|Hydrogen': 'kW;LHV'},
        source=['DEARF23', 'Vartiainen22', 'Holst21', 'IRENA22'],
        size=['1 MW', '5 MW', '100 MW'],
        agg=['subtech', 'size', 'source'],
        extrapolate_period=False,
    ).team.varsplit('Tech|Electrolysis|*variable') \
    .query(f"variable.isin({['CAPEX', 'Output Capacity|Hydrogen']})")

# #### Energy demand of green vs. blue hydrogen production

# Next, let's compare the energy demand of methane reforming (for blue hydrogen) and different types of electrolysis (for green hydrogen).

pd.concat([
        DataSet('Tech|Methane Reforming').aggregate(period=2030, source='Lewis22'),
        DataSet('Tech|Electrolysis').aggregate(period=2030, agg=['source', 'size']),
    ]) \
    .reset_index(drop=True) \
    .team.varsplit('Tech|?tech|Input|?fuel') \
    .assign(tech=lambda df: df.apply(lambda row: f"{row['tech']}<br>({row['subtech']})" if pd.isnull(row['capture_rate']) else f"{row['tech']}<br>({row['subtech']}, {row['capture_rate']} CR)", axis=1)) \
    .plot.bar(x='tech', y='value', color='fuel') \
    .update_layout(
        xaxis_title='Technologies',
        yaxis_title='Energy demand  ( MWh<sub>LHV</sub> / MWh<sub>LHV</sub> H<sub>2</sub> )',
        legend_title='Energy carriers',
    )

# #### Energy demand of iron direct reduction

# Next, let's compare the energy demand of iron direct reduction (production of low-carbon crude iron) across sources.

DataSet('Tech|Iron Direct Reduction') \
    .aggregate(period=2030, mode='h2', agg=[]) \
    .team.varsplit('Tech|Iron Direct Reduction|Input|?fuel') \
    .query(f"fuel != 'Iron Ore'") \
    .team.varcombine('{fuel} ({component})') \
    .plot.bar(x='source', y='value', color='variable') \
    .update_layout(
        xaxis_title='Sources',
        yaxis_title='Energy demand  ( MWh<sub>LHV</sub> / t<sub>DRI</sub> )',
        legend_title='Energy carriers'
    )

# We can also compare the energy demand for operation with hydrogen or with fossil gas for only one source.

DataSet('Tech|Iron Direct Reduction') \
    .select(period=2030, source='Jacobasch21') \
    .team.varsplit('Tech|Iron Direct Reduction|Input|?fuel') \
    .query(f"fuel.isin({['Electricity', 'Fossil Gas', 'Hydrogen']})") \
    .plot.bar(x='mode', y='value', color='fuel') \
    .update_layout(
        xaxis_title='Mode of operation',
        yaxis_title='Energy demand  ( MWh<sub>LHV</sub> / t<sub>DRI</sub> )',
        legend_title='Energy carriers'
    )

# #### Energy demand of Haber-Bosch synthesis

# Finally, let's compare the energy demand of Haber-Bosch synthesis between an integrated SMR plant and a plant running on green hydrogen.

pd.concat([
        DataSet('Tech|Haber-Bosch with ASU').aggregate(period=2024, agg='component'),
        DataSet('Tech|Haber-Bosch with Reforming').aggregate(period=2024, agg='component')
    ]) \
    .reset_index(drop=True) \
    .team.varsplit('Tech|?tech|*variable') \
    .query(f"variable.str.startswith('Input|')") \
    .plot.bar(x='source', y='value', color='variable') \
    .update_layout(
        xaxis_title='Sources',
        yaxis_title='Energy demand  ( MWh<sub>LHV</sub> / t<sub>NH<sub>3</sub></sub> )',
        legend_title='Energy carriers'
    )

# ## TEAM

# #### CalcVariable

# New variables can be calculated manually via the `CalcVariable` class. The next example demonstrates this for calculating the levelised cost of hydrogen.

assumptions = pd.DataFrame.from_records([
    {'elec_price_case': f"Case {i}", 'variable': 'Price|Electricity', 'unit': 'EUR_2020/MWh', 'value': 30 + (i-1)*25}
    for i in range(1, 4)
] + [
    {'variable': 'Tech|Electrolysis|OCF', 'value': 50, 'unit': 'pct'},
    {'variable': 'Annuity Factor', 'value': annuity_factor(Q('5 pct'), Q('18 a')).m, 'unit': '1/a'},
])
display(assumptions)

# +
df_calc = pd.concat([
        DataSet('Tech|Electrolysis').aggregate(period=[2030, 2040, 2050], subtech=['AEL', 'PEM'], agg=['size', 'source']),
        assumptions,
    ]).team.perform(CalcVariable(**{
        'LCOX|Green Hydrogen|Capital Cost': lambda x: (x['Annuity Factor'] * x['Tech|Electrolysis|CAPEX'] / x['Tech|Electrolysis|Output Capacity|Hydrogen'] / x['Tech|Electrolysis|OCF']),
        'LCOX|Green Hydrogen|OM Cost Fixed': lambda x: x['Tech|Electrolysis|OPEX Fixed'] / x['Tech|Electrolysis|Output Capacity|Hydrogen'] / x['Tech|Electrolysis|OCF'],
        'LCOX|Green Hydrogen|Input Cost|Electricity': lambda x: x['Price|Electricity'] * x['Tech|Electrolysis|Input|Electricity'] / x['Tech|Electrolysis|Output|Hydrogen'],
    }), only_new=True) \
    .team.unit_convert(to='EUR_2020/MWh')

display(df_calc.sample(15).sort_index())
# -

df_calc.team.varsplit('LCOX|Green Hydrogen|?component') \
    .sort_values(by=['elec_price_case', 'value']) \
    .plot.bar(x='period', y='value', color='component', facet_col='elec_price_case', facet_row='subtech')

# #### Pivot

# POSTED uses the `pivot` dataframe method to bring the data into a usable format.

pd.concat([
        DataSet('Tech|Electrolysis').aggregate(period=[2030, 2040, 2050], subtech=['AEL', 'PEM'], agg=['size', 'source']),
        assumptions,
    ]).team.pivot_wide().pint.dequantify()

# #### LCOX of blue and green hydrogen

# POSTED also contains predefined methods for calculating LCOX. Here we apply it to blue and green hydrogen.

# +
df_lcox_bluegreen = pd.concat([
        pd.DataFrame.from_records([
            {'elec_price_case': f"Case {i}", 'variable': 'Price|Electricity', 'unit': 'EUR_2020/MWh', 'value': 30 + (i-1)*25}
            for i in range(1, 4)
        ]),
        pd.DataFrame.from_records([
            {'ng_price_case': 'High' if i-1 else 'Low', 'variable': 'Price|Fossil Gas', 'unit': 'EUR_2020/MWh', 'value': 40 if i-1 else 20}
            for i in range(1, 3)
        ]),
        DataSet('Tech|Electrolysis').aggregate(period=2030, subtech=['AEL', 'PEM'], agg=['size', 'subtech', 'source']),
        DataSet('Tech|Methane Reforming').aggregate(period=2030, capture_rate=['55.70%', '94.50%'])
            .team.varsplit('Tech|Methane Reforming|*comp')
            .team.varcombine('{variable} {subtech} ({capture_rate})|{comp}')
    ]) \
    .team.perform(
        LCOX('Output|Hydrogen', 'Electrolysis', name='Green Hydrogen', interest_rate=0.1, book_lifetime=18),
        LCOX('Output|Hydrogen', 'Methane Reforming SMR (55.70%)', name='Blue Hydrogen (Low CR)', interest_rate=0.1, book_lifetime=18),
        LCOX('Output|Hydrogen', 'Methane Reforming ATR (94.50%)', name='Blue Hydrogen (High CR)', interest_rate=0.1, book_lifetime=18),
        only_new=True,
    ) \
    .team.unit_convert(to='EUR_2022/MWh')

display(df_lcox_bluegreen)
# -

df_lcox_bluegreen.team.varsplit('LCOX|?fuel|*comp') \
    .plot.bar(x='fuel', y='value', color='comp', facet_col='elec_price_case', facet_row='ng_price_case')

# #### LCOX of Methanol

# Let's calculate the levelised cost of green methanol (from electrolytic hydrogen). First we can do this simply based on a hydrogen price (i.e. without accounting for electrolysis).

# +
df_lcox_meoh = pd.concat([
        DataSet('Tech|Methanol Synthesis').aggregate(period=[2030, 2050]),
        pd.DataFrame.from_records([
            {'period': 2030, 'variable': 'Price|Hydrogen', 'unit': 'EUR_2022/MWh', 'value': 120},
            {'period': 2050, 'variable': 'Price|Hydrogen', 'unit': 'EUR_2022/MWh', 'value': 80},
            {'period': 2030, 'variable': 'Price|Captured CO2', 'unit': 'EUR_2022/t', 'value': 150},
            {'period': 2050, 'variable': 'Price|Captured CO2', 'unit': 'EUR_2022/t', 'value': 100},
        ]),
    ]) \
    .team.perform(LCOX(
        'Output|Methanol', 'Methanol Synthesis', name='Green Methanol',
        interest_rate=0.1, book_lifetime=10.0), only_new=True,
    ) \
    .team.unit_convert('EUR_2022/MWh')

display(df_lcox_meoh)
# -

df_lcox_meoh.team.varsplit('LCOX|Green Methanol|*component') \
    .plot.bar(x='period', y='value', color='component')

# Next, we can calculate the LCOX of green methanol for a the value chain consisting of electrolysis, low-temperature direct air capture, and methanol synthesis. The heat for the direct air capture will be provided by an industrial heat pump.

# +
pc = ProcessChain(
    'Green Methanol',
    {'Methanol Synthesis': {'Methanol': Q('1 MWh')}},
    'Heatpump for DAC -> Heat => Direct Air Capture -> Captured CO2 => Methanol Synthesis;Electrolysis -> Hydrogen => Methanol Synthesis -> Methanol',
)

g, lay = pc.igraph()
fig, ax = plt.subplots()
ax.set_title(pc.name)
ig.plot(g, target=ax, layout=lay, vertex_label=[n.replace(' ', '\n') for n in g.vs['name']], edge_label=[n.replace(' ', '\n') for n in g.es['name']], vertex_label_size=8, edge_label_size=6)

# +
df_lcox_meohvc = pd.concat([
        DataSet('Tech|Electrolysis').aggregate(period=[2030, 2050], subtech=['AEL', 'PEM'], size=['1 MW', '100 MW'], agg=['subtech', 'size', 'source']),
        DataSet('Tech|Direct Air Capture').aggregate(period=[2030, 2050], subtech='LT-DAC'),
        DataSet('Tech|Heatpump for DAC').aggregate(period=[2030, 2050]),
        DataSet('Tech|Methanol Synthesis').aggregate(period=[2030, 2050]),
        pd.DataFrame.from_records([
            {'period': 2030, 'variable': 'Price|Electricity', 'unit': 'EUR_2022/MWh', 'value': 50},
            {'period': 2050, 'variable': 'Price|Electricity', 'unit': 'EUR_2022/MWh', 'value': 30},
        ]),
    ]) \
    .team.perform(pc) \
    .team.perform(LCOX(
        'Methanol Synthesis|Output|Methanol', process_chain='Green Methanol',
        interest_rate=0.1, book_lifetime=10.0,
    ), only_new=True) \
    .team.unit_convert('EUR_2022/MWh')

display(df_lcox_meohvc)
# -

df_lcox_meohvc.team.varsplit('LCOX|Green Methanol|?process|*component') \
    .plot.bar(x='period', y='value', color='component', hover_data='process')
