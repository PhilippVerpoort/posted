import re

import numpy as np
import pandas as pd
from pint.errors import DimensionalityError

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine


# calculate annuity factor
def _calcAnnuityFactor(ir, n):
    try:
        n = n.astype('pint[a]').pint.m
        ir = ir.astype('pint[dimensionless]').pint.m
    except DimensionalityError:
        return np.nan

    return ir * (1 + ir) ** n / ((1 + ir) ** n - 1)

# LCOX calc routine
class LCOX(AbstractCalcRoutine):
    part = 'LCOX'

    def _calc(self, old: pd.DataFrame) -> (pd.DataFrame, dict):
        new = pd.DataFrame(index=old.index)
        missing = {}

        # capex
        if self._has(['capex', 'wacc', 'lifetime', 'ocf'], old, missing):
            new['cap'] = old['capex'] * _calcAnnuityFactor(old['wacc'], old['lifetime']) / old['ocf']

        # fopex
        if self._has(['fopex_spec', 'ocf'], old, missing):
            new['fop'] = old['fopex_spec'] / old['ocf']

        # demand cost = demand * price
        for oldType in [c for c in old if c.startswith('demand:')]:
            newType = re.sub(r"^demand:", 'dem_cost:', oldType)
            priceType = re.sub(r"^demand:", 'price:', oldType)

            if self._has([oldType, priceType], old, missing):
                new[newType] = old[oldType] * old[priceType]

        # transport cost = demand * specific transport cost
        for oldType in [c for c in old if re.match(r"^demand(_sc)?:", c)]:
            newType = re.sub(r"^demand(_sc)?:", 'transp_cost:', oldType)
            transpType = re.sub(r"^demand(_sc)?:", 'transp:', oldType)

            if self._has([transpType, oldType], old, missing):
                new[newType] = old[oldType] * old[transpType]

        return new, missing
