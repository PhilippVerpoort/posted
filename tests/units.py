from src.python.config.config import flowTypes
from src.python.units.units import ureg, convUnit


# test conversion
#print(ureg('1 kg').to('MWh', 'flocon', energycontent=ureg('33.33 kWh/kg')))
print(convUnit('kW', 't/a', flowTypes['h2']))
# print(convUnit('pct', 'dimensionless'))
