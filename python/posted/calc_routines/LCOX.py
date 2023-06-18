import re

import pandas as pd
import pint

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine
from posted.calc_routines.MissingAssumptionsException import MissingAssumptionsException


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
        # set part property via super constructor
        super().__init__(part='cost')

        # set
        self._prices = prices
        self._wacc = wacc
        self._lifetime = lifetime
        self._ocf = ocf


    def _calcColumn(self, oldType: str, oldCol: pd.Series) -> None | tuple:
        if oldType == 'capex':
            return 'cap', oldCol * _calcAnnuityFactor(self._wacc, self._lifetime) / self._ocf
        elif oldType == 'fopex_spec':
            return 'fop', oldCol / self._ocf
        elif oldType.startswith('demand:'):
            newType = re.sub(r"^demand:", 'dem:', oldType)

            # get flow type and associated price
            flow_type = oldType.split(':')[1]
            if self._prices is None or flow_type not in self._prices:
                raise MissingAssumptionsException(f"No price information provided for '{oldType}'.", type=oldType)
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

        return
