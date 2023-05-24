import numpy as np
import pandas as pd
import pint_pandas
from sigfig import round

from src.python.calc_routines.AbstractCalcRoutine import AbstractCalcRoutine


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
    def calc(self, routine: AbstractCalcRoutine, unit: None | str = None):
        # call calc routine
        newColumns = routine.calc(self._df)

        # compile new dataframe from new columns
        results = pd.DataFrame().assign(**newColumns)

        # adjust units
        results = results.apply(lambda col: col.pint.to(unit) if unit is not None else col.pint.to_reduced_units())

        # round values
        roundVec = np.vectorize(lambda scalar: round(scalar, sigfigs=4, warn=False) if scalar==scalar else scalar)
        for colName in results.columns:
            results[colName] = pint_pandas.PintArray(roundVec(results[colName].values.quantity.m), dtype=results[colName].dtype)

        # return
        return results
