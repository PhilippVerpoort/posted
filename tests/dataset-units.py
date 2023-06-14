from posted.ted.TEDataSet import TEDataSet


t = TEDataSet('ELH2').generateTable(period=[2030, 2040, 2050])
print('=== Electrolysis example ===')
print(t.data)
print('=== Unstack ===')
print(t.data.unstack('period').pint.dequantify())
