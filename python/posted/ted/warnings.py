# importing modules
import warnings
from pathlib import Path

class TEIncorrectRowWarning(Warning):
    """Warning raised for incorrect rows in the input data that cannot be converted or mapped.

    Attributes:
        message -- explanation of the error
        row -- row where the error occured
        col -- column where the error occured
        file -- file where the error occured
    """
    def __init__(self, message: str = "Incorrect row detected", rowID: None | int = None,
                 colID: None | str = None, filePath: None | Path = None):
        self.message: str = message
        self.rowID: None | int = rowID
        self.colID: None | str = colID
        self.filePath: None | Path = filePath

        # add tokens at the end of the error message
        messageTokens = []
        if filePath is not None:
            messageTokens.append(f"file \"{filePath}\"")
        if rowID is not None:
            messageTokens.append(f"line {rowID}")
        if colID is not None:
            messageTokens.append(f"in column \"{colID}\"")

        # compose error message from tokens
        warningMessage: str = message
        if messageTokens:
            warningMessage += f"\n    " + (", ".join(messageTokens)).capitalize()

        super().__init__(warningMessage)