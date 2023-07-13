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
print(t1.assume(assump).calc(LCOX).data)


t2 = TEDataSet('ELH2').generateTable(period=[2030, 2050], subtech=['Alkaline', 'PEM'], agg=['subtech', 'src_ref'])
print(t2.data)

assump1 = {
    'price:heat': 80.0 * ureg('EUR/MWh'),
    'price:water': 9.0 * ureg('EUR/t'),
}
assump2 = pd.DataFrame(
    index=pd.Index([2030, 2050], name='period'),
    columns=pd.Index(['price:elec'], name='type'),
    data=[50.0, 60.0],
)
print(t2.assume(assump1).assume(assump2).calc(LCOX).data.pint.dequantify())
