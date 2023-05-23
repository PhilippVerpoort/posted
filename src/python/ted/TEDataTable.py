import re

import pandas as pd
import pint

from src.python.units.units import ureg


class TEDataTable:
    # initialise
    def __init__(self, tid: str, datatable: pd.DataFrame):
        self._tid: str = tid
        self._df: pd.DataFrame = datatable


    # access dataframe
    @property
    def data(self):
        return self._df


    # calculate levelised cost of X
    def calcLCOX(self,
                 prices: None | dict = None,
                 wacc: int | float = 10.0,
                 lifetime: int | float = 18.0,
                 ocf: int | float = 0.95,
                 ):
        newColumns = {}

        # add capital cost data
        newColumns['cap'] = self._df['capex'] * self._calcAF(wacc, lifetime) / (ocf * ureg('a'))

        # add fixed operational cost data
        newColumns['fo'] = self._df['fopex_abs'] / (ocf * ureg('a'))

        # add energy and feedstock cost data
        colsEnF = [colID for colID in self._df.columns if any(colID.startswith(t) for t in ('energy_dem:', 'feedstock_dem:'))]
        for colID in colsEnF:
            # resulting new column name
            newColID = re.sub(r"_dem", '', colID)

            # get flow type and associated price
            flow_type = colID.split(':')[1]
            if prices is None or flow_type not in prices:
                raise Exception(f"No price information provided for '{colID}'.")
            price = prices[flow_type]

            if isinstance(price, float) or isinstance(price, int) or isinstance(price, pint.Quantity):
                newColumns[newColID] = self._df[colID] * price
            elif isinstance(price, dict) or isinstance(price, pd.DataFrame):
                if isinstance(price, dict):
                    price = pd.DataFrame.from_dict(price, orient='tight')
                newColumns[newColID] = self._df.merge(price).apply(lambda col: col['price'] * col[colID])
            else:
                raise Exception(f"Unknown type in price provided for '{flow_type}'.")

        # return
        return pd.DataFrame().assign(**newColumns)


    # calculate annuity factor
    @classmethod
    def _calcAF(cls, irate, n: int):
        return irate * (1 + irate) ** n / ((1 + irate) ** n - 1)
