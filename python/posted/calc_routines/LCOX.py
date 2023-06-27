import re

import pandas as pd

from posted.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine


# calculate annuity factor
def _calcAnnuityFactor(ir, n):
    n = n.astype('pint[a]').pint.m
    ir = ir.astype('pint[dimensionless]').pint.m

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

        # demand
        for oldType in [c for c in old if c.startswith('demand:')]:
            newType = re.sub(r"^demand:", 'dem:', oldType)
            priceType = re.sub(r"^demand:", 'price:', oldType)

            if self._has([oldType, priceType], old, missing):
                new[newType] = old[oldType] * old[priceType]

        return new, missing
