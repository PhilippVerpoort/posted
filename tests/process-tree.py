from posted.calc_routines.LCOX import LCOX
from posted.ted.TEDataSet import TEDataSet
from posted.ted.TEProcessTreeDataTable import TEProcessTreeDataTable
from posted.units.units import ureg


t1 = TEDataSet('ELH2').generateTable(period=2040, subtech=['Alkaline', 'PEM'], agg=['subtech', 'src_ref'])
t2 = TEDataSet('IDR').generateTable(period=2040, mode='h2')
t3 = TEDataSet('EAF').generateTable(period=2040, mode='primary')

print('===== ELH2 data =====')
print(t1.data, "\n\n")
print('===== IDR data =====')
print(t2.data, "\n\n")
print('===== EAF data =====')
print(t3.data, "\n\n")

graph = TEProcessTreeDataTable(t3, t2, t1)
print('===== Graph data =====')
print(graph.data, "\n\n")

ps = {
    'ng': 6.0 * ureg('EUR/GJ'),
    'heat': 6.0 * ureg('EUR/GJ'),
    'ironore': 100.0 * ureg('EUR/t'),
    'alloys': 1777.0 * ureg('EUR/t'),
    'coal': 4.0 * ureg('EUR/GJ'),
    'graph_electr': 100.0 * ureg('EUR/t'),
    'lime': 100.0 * ureg('EUR/t'),
    'nitrogen': 100.0 * ureg('EUR/t'),
    'oxygen': 100.0 * ureg('EUR/t'),
    'steelscrap': 100.0 * ureg('EUR/t'),
    'water': 10.0 * ureg('EUR/t'),
}
lcox = graph.calc(LCOX(prices=ps), keep='missing')
print('===== LCOX data =====')
print(lcox.data)
