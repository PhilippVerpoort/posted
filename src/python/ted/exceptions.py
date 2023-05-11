class ConsistencyException(Exception):
    """Exception raised for inconsistencies in the input data.

    Attributes:
        message -- explanation of the error
        row -- row where the inconsistency occured
        file -- file where the inconsistency occured
    """

    def __init__(self,  message="Inconsistency detected", row = 0, file = ""):
        self.message = message
        self.row = row
        self.file = file

        error_message =  message
        if(row != 0):
            error_message += " in line " + str(row)
        if(file != ""):
            error_message += " in file " + str(file)

        super().__init__(error_message)