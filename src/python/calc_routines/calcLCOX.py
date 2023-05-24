import re

import pandas as pd
import pint

from src.python.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine
from src.python.units.units import ureg


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
        newColumns['cap'] = df['capex'] * _calcAnnuityFactor(self._wacc, self._lifetime) / (self._ocf * ureg('a'))

        # add fixed operational cost data
        newColumns['fo'] = df['fopex_abs'] / (self._ocf * ureg('a'))

        # add energy and feedstock cost data
        colsEnF = [colName for colName in df.columns if any(colName.startswith(t) for t in ('energy_dem:', 'feedstock_dem:'))]
        for colName in colsEnF:
            # resulting new column name
            newColName = re.sub(r"_dem", '', colName)

            # get flow type and associated price
            flow_type = colName.split(':')[1]
            if self._prices is None or flow_type not in self._prices:
                raise Exception(f"No price information provided for '{colName}'.")
            price = self._prices[flow_type]

            if isinstance(price, float) or isinstance(price, int) or isinstance(price, pint.Quantity):
                newColumns[newColName] = df[colName] * price
            elif isinstance(price, dict) or isinstance(price, pd.DataFrame):
                if isinstance(price, dict):
                    price = pd.DataFrame.from_dict(price, orient='tight')
                newColumns[newColName] = df.merge(price).apply(lambda col: col['price'] * col[colName])
            else:
                raise Exception(f"Unknown type in price provided for '{flow_type}'.")

        # return
        return newColumns
