from posted.units.units import convUnit


# test conversion
#print(ureg('1 kg').to('MWh', 'flocon', energycontent=ureg('33.33 kWh/kg')))
print(convUnit('kW', 't/a', 'h2'))
print(convUnit('MW;LHV', 't/a', 'h2'))
print(convUnit('MW;HHV', 't/a', 'h2'))
print(convUnit('t', 'kWh;LHV', 'h2'))
print(convUnit('t', 'kWh;HHV', 'h2'))

# print(convUnit('pct', 'dimensionless'))
