from posted.config import variables


class TEBase:
    # initialise
    def __init__(self, main_variable: str):
        # set variable from function argument
        self._main_variable: str = main_variable

        # set technology specifications
        self._var_specs: dict = {key: val for key, val in variables.items() if key.startswith(self._main_variable)}

    @property
    def main_variable(self) -> str:
        return self._main_variable