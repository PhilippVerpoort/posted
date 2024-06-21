# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: posted
#     language: python
#     name: python3
# ---

# load libraries
import pandas as pd
import os
import sys
# confiure display options
pd.options.plotting.backend = "plotly"
pd.set_option('display.max_rows', None)
# set right path for module

module_path = os.path.abspath(os.path.join('.'))
module_path = module_path + "/python"
if module_path not in sys.path:
    sys.path.append(module_path)

# +
from matplotlib import pyplot as plt
import numpy as np
x = np.linspace(0, 5, 10)
y = x ** 2

plt.figure()
plt.plot(x, y, 'r')
plt.xlabel('x')
plt.ylabel('y')
plt.title('title')
plt.show()
# -

import plotly.express as px
fig = px.bar(x=["a", "b", "c"], y=[1, 3, 2])
fig.show()

from posted.tedf import TEDF
from posted.noslag import DataSet

tedf = TEDF('Tech|Electrolysis')
tedf.load()
tedf.check()
display(tedf.data)

# +

DataSet('Tech|Electrolysis').normalise(override={'Tech|ELH2|Input Capacity|Electricity': 'kW', 'Tech|ELH2|Output Capacity|h2': 'kW;LHV'}).query("source=='Vartiainen22'")
# -

DataSet('Tech|Electrolysis').normalise(override={ 'Tech|ELH2|Output Capacity|Hydrogen': 'kW;LHV'})

display(DataSet('Tech|Electrolysis').select(period=2020, subtech='AEL', size='100 MW', override={'Tech|Electrolosys|Output Capacity|Hydrogen': 'kW;LHV'}))

DataSet('Tech|Electrolysis').select(period=2030, source='Yates20', subtech='AEL', size='100 MW', override={'Tech|Electrolysis|Output Capacity|h2': 'kW;LHV'}, extrapolate_period=False)

DataSet('Tech|Electrolysis').select(subtech=['AEL', 'PEM'], size='100 MW', override={'Tech|Electrolysis|Input Capacity|Electricity': 'kW'})

DataSet('Tech|Electrolysis').aggregate(subtech='AEL', size='100 MW', agg='subtech', override={'Tech|ELH2|Output Capacity|Hydrogen': 'kW;LHV'})

from posted.units import unit_convert
df_compare_electrolysis = DataSet('Tech|Electrolysis') \
    .select(period=[2020, 2030, 2040, 2050], subtech=['AEL', 'PEM'], override={'Tech|Electrolysis|Output Capacity|Hydrogen': 'kW;LHV'}, source=['DEARF23', 'Vartiainen22', 'Holst21', 'IRENA22'], size=['1 MW', '5 MW', '100 MW'], extrapolate_period=False) \
    .query(f"variable=='Tech|Electrolysis|Capital Cost'")
display(df_compare_electrolysis)
# df_compare_electrolysis \
#     .assign(size_sort=lambda df: df['size'].str.split(' ', n=1, expand=True).iloc[:, 0].astype(int)) \
#     .sort_values(by=['size_sort', 'period']) \
#     .plot.line(x='period', y='value', color='source', facet_col='size', facet_row='subtech')

from posted.units import unit_convert
unit_convert("m**3/hour;norm",'MWh/a;LHV' , 'Hydrogen')

# +
# display(DataSet('Tech|Methane Reforming').aggregate(period=2030).query("variable.str.contains('OM Cost')"))
# display(DataSet('Tech|Methane Reforming').aggregate(period=2030).query("variable.str.contains('Demand')"))

DataSet('Tech|Methane Reforming').aggregate(period=2030).sort_values(by="variable")
# -

TEDF('Tech|Direct Air Capture').load().data

DataSet('Tech|Direct Air Capture').normalise()

DataSet('Tech|Direct Air Capture').select()

# +
#NSHADataSet('Tech|MEOH-SYN').select(period=2040)
# -

TEDF('Tech|Haber-Bosch with ASU').load().check()
DataSet('Tech|Haber-Bosch with ASU').normalise()

DataSet('Tech|Haber-Bosch with ASU').select(period=2020)

DataSet('Tech|Haber-Bosch with ASU').aggregate(period=2020)
