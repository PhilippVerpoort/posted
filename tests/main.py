from src.python.calc_routines.calcLCOX import LCOX
from src.python.ted.TEDataSet import TEDataSet
from src.python.units.units import ureg


# example: direct reduction
# t = TEDataSet('electrolysis', load_other=['/home/philippv/Documents/4-projects/10-posted/01-vcs/posted/electrolysis-test.csv'])
t = TEDataSet('direct-reduction', skip_checks=True).generateTable(period=[2030, 2050])
print('=== Direct reduction example ===')
print(t.data)

ps = {
    'elec': 50.0 * ureg('EUR/MWh'),
    'h2': 100.0 * ureg('EUR/MWh'),
    'ng': 6.0 * ureg('EUR/GJ'),
    'heat': 6.0 * ureg('EUR/GJ'),
    'ironore': 100.0 * ureg('EUR/t'),
}
print(t.calc(LCOX(prices=ps)))


# example: electrolysis
t = TEDataSet('electrolysis', skip_checks=True).generateTable(period=[2030, 2040, 2050])
print('=== Electrolysis example ===')
print(t.data)
print('=== Unstack ===')
print(t.data.unstack('period').pint.dequantify())
