import pandas as pd

from posted.calc_routines.LCOX import LCOX
from posted.ted.TEDataSet import TEDataSet
from posted.units.units import ureg


t1 = TEDataSet('HBNH3-ASU').generateTable(period=[2030, 2050])
print(t1.data)

assump = {
    'price:h2': 100.0 * ureg('EUR/MWh'),
    'price:heat': 6.0 * ureg('EUR/GJ'),
}
print(t1.calc(LCOX, assump=assump).data)


t2 = TEDataSet('ELH2').generateTable(period=[2030, 2050], subtech=['Alkaline', 'PEM'], agg=['subtech', 'src_ref'])
print(t2.data)

a1 = {
    'price:heat': 80.0 * ureg('EUR/MWh'),
    'price:water': 9.0 * ureg('EUR/t'),
}
a2 = pd.Series(
    index=[2030, 2050],
    data=[50.0, 60.0],
).to_frame('price:elec')
a2.index.names = ['period']
print(t2.assume(a1).assume(a2).calc(LCOX).data.pint.dequantify())
