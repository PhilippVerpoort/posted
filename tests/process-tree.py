from posted.ted.TEDataSet import TEDataSet
from posted.ted.TEProcessTreeDataTable import TEProcessTreeDataTable


t1 = TEDataSet('ELH2', skip_checks=True).generateTable(period=[2030, 2050], subtech=['Alkaline', 'PEM'])
t2 = TEDataSet('IDR', skip_checks=True).generateTable(period=[2030, 2050], mode='h2')
t3 = TEDataSet('EAF', skip_checks=True).generateTable(period=[2030, 2050], mode='primary')

graph = TEProcessTreeDataTable(t3, t2, t1)
print(graph.data)
