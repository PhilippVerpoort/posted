from pathlib import Path

from posted.ted.TEDataSet import TEDataSet


t = TEDataSet('ELH2', load_other=[Path(__file__).parent / 'external-file.csv'])
print(t.data)
