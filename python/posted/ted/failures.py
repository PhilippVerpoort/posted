import warnings
from typing import Hashable

import pandas as pd


class TEMappingFailure(Warning):
    """Warning raised for rows in TEDataSets where mappings fail.

    Attributes:
        row_data -- the data of the row that causes the failure
        message -- explanation of the error
    """
    def __init__(self, row_data: pd.DataFrame, message: str = "Failure when selecting from dataset."):
        # save constructor arguments as public fields
        self.row_data: pd.DataFrame = row_data
        self.message: str = message

        # compose warning message
        warning_message: str = message + f"\n{row_data}"

        # call super constructor
        super().__init__(warning_message)
