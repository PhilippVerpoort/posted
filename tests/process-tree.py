from posted.calc_routines.calcLCOX import LCOX
from posted.ted.TEDataSet import TEDataSet
from posted.ted.TEProcessTreeDataTable import TEProcessTreeDataTable
from posted.units.units import ureg

t1 = TEDataSet('ELH2', skip_checks=True).generateTable(period=[2030, 2050], subtech=['Alkaline', 'PEM'])
t2 = TEDataSet('IDR', skip_checks=True).generateTable(period=[2030, 2050], mode='h2')
t3 = TEDataSet('EAF', skip_checks=True).generateTable(period=[2030, 2050], mode='primary')

graph = TEProcessTreeDataTable(t3, t2, t1)
print(graph.data)

ps = {
    'elec': 50.0 * ureg('EUR/MWh'),
    'h2': 100.0 * ureg('EUR/MWh'),
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
print(graph.calc(LCOX(prices=ps)))
