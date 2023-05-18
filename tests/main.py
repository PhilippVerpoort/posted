from src.python.read.read_config import techs
from src.python.ted.TEDataSet import TEDataSet


for tid in ['direct-reduction']:
    #if techs[tid]['class'] != 'conversion': continue

    table = TEDataSet(tid).generateTable([2020, 2030, 2040, 2050])
    print(table.data)
