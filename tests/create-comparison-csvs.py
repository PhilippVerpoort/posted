from posted.calc_routines.LCOX import LCOX
from posted.ted.TEDataSet import TEDataSet
from posted.ted.TEProcessTreeDataTable import TEProcessTreeDataTable
from posted.units.units import ureg

t1 = TEDataSet('ELH2')

t1.data.to_csv(
            "ELH2WithPython.csv",
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )

t1 = TEDataSet('IDR')

t1.data.to_csv(
            "IDRWithPython.csv",
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )

t1 = TEDataSet('EAF')

t1.data.to_csv(
            "EAFWithPython.csv",
            index=False,
            sep=',',
            quotechar='"',
            encoding='utf-8',
            na_rep='',
        )