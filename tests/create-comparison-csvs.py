from posted.calc_routines.LCOX import LCOX
from posted.ted.TEDataSet import TEDataSet
from posted.ted.TEProcessTreeDataTable import TEProcessTreeDataTable
from posted.units.units import ureg
from pathlib import Path

datasets_to_be_tested = ["ELH2", "IDR", "EAF", "MEOH-SYN", "HBNH3-ASU", "HOTROLL", "CAST", "DAC"]
Path("./tests/comparison/").mkdir(parents=True, exist_ok=True)

for dataset in datasets_to_be_tested:
    d = TEDataSet(dataset)
    d.data.to_csv(
            "./tests/comparison/" + dataset + "Python.csv",
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )