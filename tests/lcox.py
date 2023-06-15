from posted.calc_routines.LCOX import LCOX
from posted.ted.TEDataSet import TEDataSet
from posted.units.units import ureg


t1 = TEDataSet('IDR').generateTable(period=[2030, 2050])
print(t1.data)

ps = {
    'elec': 50.0 * ureg('EUR/MWh'),
    'h2': 100.0 * ureg('EUR/MWh'),
    'ng': 6.0 * ureg('EUR/GJ'),
    'heat': 6.0 * ureg('EUR/GJ'),
    'ironore': 100.0 * ureg('EUR/t'),
}
print(t1.calc(LCOX(prices=ps)))


t2 = TEDataSet('ELH2').generateTable(period=[2030, 2050], subtech=['Alkaline', 'PEM'], agg=['subtech', 'src_ref'])
print(t2.data)

ps = {
    'elec': 50.0 * ureg('EUR/MWh'),
    'heat': 50.0 * ureg('EUR/MWh'),
    'water': 9.0 * ureg('EUR/t'),
}
print(t2.calc(LCOX(prices=ps)).pint.dequantify())
