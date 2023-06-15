import re

import pandas as pd
import pint

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine


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


    def _calcColumn(self, oldType: str, oldCol: pd.Series):
        if oldType == 'capex':
            return 'cap', oldCol * _calcAnnuityFactor(self._wacc, self._lifetime) / self._ocf
        elif oldType == 'fopex_spec':
            return 'fop', oldCol / self._ocf
        elif oldType.startswith('demand:'):
            newType = re.sub(r"^demand:", 'dem:', oldType)

            # get flow type and associated price
            flow_type = oldType.split(':')[1]
            if self._prices is None or flow_type not in self._prices:
                raise Exception(f"No price information provided for '{oldType}'.")
            price = self._prices[flow_type]

            if isinstance(price, float) or isinstance(price, int) or isinstance(price, pint.Quantity):
                newCol = oldCol * price
            elif isinstance(price, dict) or isinstance(price, pd.DataFrame):
                if isinstance(price, dict):
                    price = pd.DataFrame.from_dict(price, orient='tight')
                newCol = oldCol.to_frame().merge(price, left_index=True, right_index=True) \
                    .apply(lambda col: col[oldType] * col['price'])
            else:
                raise Exception(f"Unknown type in price provided for '{flow_type}'.")

            return newType, newCol

        return None, None
