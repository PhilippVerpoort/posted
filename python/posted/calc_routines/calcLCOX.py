import re

import pandas as pd
import pint

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine
from posted.units.units import ureg


# calculate annuity factor
def _calcAnnuityFactor(irate: float, n: int):
    return irate * (1 + irate) ** n / ((1 + irate) ** n - 1)


# LCOX calc routine
class LCOX(AbstractCalcRoutine):
    def __init__(self,
                 prices: None | dict = None,
                 wacc: float = 0.10,
                 lifetime: int | float = 18,
                 ocf: int | float = 0.95,
                 ):
        self._prices = prices
        self._wacc = wacc
        self._lifetime = lifetime
        self._ocf = ocf


    def calc(self, df: pd.DataFrame):
        newColumns = {}

        # add capital cost data
        newColumns['cap'] = df['capex'] * (_calcAnnuityFactor(self._wacc, self._lifetime)/ureg('a')) / self._ocf

        # add fixed operational cost data
        newColumns['fop'] = df['fopex_spec'] / self._ocf

        # add energy and feedstock cost data
        colsEnF = [colName for colName in df.columns if colName.startswith('demand:')]
        for colName in colsEnF:
            # resulting new column name
            newColName = re.sub(r"^demand:", 'dem:', colName)

            # get flow type and associated price
            flow_type = colName.split(':')[1]
            if self._prices is None or flow_type not in self._prices:
                raise Exception(f"No price information provided for '{colName}'.")
            price = self._prices[flow_type]

            if isinstance(price, float) or isinstance(price, int) or isinstance(price, pint.Quantity):
                newColumns[colName] = df[colName] * price
            elif isinstance(price, dict) or isinstance(price, pd.DataFrame):
                if isinstance(price, dict):
                    price = pd.DataFrame.from_dict(price, orient='tight')
                newColumns[newColName] = df.merge(price).apply(lambda col: col[colName] * col['price'])
            else:
                raise Exception(f"Unknown type in price provided for '{flow_type}'.")

        # return
        return newColumns
