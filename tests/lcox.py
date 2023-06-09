from posted.calc_routines.calcLCOX import LCOX
from posted.ted.TEDataSet import TEDataSet
from posted.units.units import ureg


t = TEDataSet('direct-reduction', skip_checks=True).generateTable(period=[2030, 2050])
print(t.data)

ps = {
    'elec': 50.0 * ureg('EUR/MWh'),
    'h2': 100.0 * ureg('EUR/MWh'),
    'ng': 6.0 * ureg('EUR/GJ'),
    'heat': 6.0 * ureg('EUR/GJ'),
    'ironore': 100.0 * ureg('EUR/t'),
}
print(t.calc(LCOX(prices=ps)))
