import pandas as pd


class TEGenerationFailure(Warning):
    """Warning raised for incorrect rows in the input data that cannot be converted or mapped.

    Attributes:
        message -- explanation of the error
        row_data -- the data of the row that causes the failure
    """
    def __init__(self, row_data: pd.DataFrame, message: str = "Failure when generating table from dataset."):
        # save constructor arguments as public fields
        self.rowData: pd.DataFrame = row_data
        self.message: str = message

        # compose warning message
        warningMessage: str = message + f"\n{row_data}"

        # call super constructor
        super().__init__(warningMessage)
