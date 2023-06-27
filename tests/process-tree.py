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

assump = {
    'price:ng': 6.0 * ureg('EUR/GJ'),
    'price:heat': 6.0 * ureg('EUR/GJ'),
    'price:ironore': 100.0 * ureg('EUR/t'),
    'price:alloys': 1777.0 * ureg('EUR/t'),
    'price:coal': 4.0 * ureg('EUR/GJ'),
    'price:graph_electr': 100.0 * ureg('EUR/t'),
    'price:lime': 100.0 * ureg('EUR/t'),
    'price:nitrogen': 100.0 * ureg('EUR/t'),
    'price:oxygen': 100.0 * ureg('EUR/t'),
    'price:steelscrap': 100.0 * ureg('EUR/t'),
    'price:water': 10.0 * ureg('EUR/t'),
    'wacc': 8.0 * ureg('pct'),
    'lifetime': 20 * ureg('a'),
    'ocf': 95.0 * ureg('pct'),
}
lcox = graph.calc(LCOX, assump=assump, keep='value')
print('===== LCOX data =====')
print(lcox.data)
