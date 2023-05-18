from src.python.ted.TEDataSet import TEDataSet


# example: direct reduction
t = TEDataSet('direct-reduction').generateTable(2030, no_agg=['mode'])
print('=== Direct reduction example ===')
print(t.data)
print('=== Unstack ===')
print(t.data.unstack('mode'))


# example: electrolysis
t = TEDataSet('electrolysis').generateTable([2030, 2040, 2050], no_agg=['subtech'])
print('=== Electrolysis example ===')
print(t.data)
print('=== Unstack ===')
print(t.data.unstack('period'))
