from abc import ABC, abstractmethod

import pandas as pd


class AbstractCalcRoutine(ABC):
    @abstractmethod
    def calc(self, df: pd.DataFrame):
        pass
