import pandas as pd


class TEDataTable:
    # initialise
    def __init__(self, tid: str, datatable: pd.DataFrame):
        self._tid: str = tid
        self._df: pd.DataFrame = datatable


    @property
    def data(self):
        return self._df
