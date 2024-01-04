from posted.config import variables
from posted.path import databases
from posted.utils.read import read_yml_file


def read_fields(variable: str):
    ret = {}

    for database_id in databases:
        fpath = databases[database_id] / 'fields' / ('/'.join(variable.split('|')) + '.yml')
        if fpath.exists():
            if not fpath.is_file():
                raise Exception(f"Expected YAML file, but not a file: {fpath}")

            ret |= {
                k: v
                for k, v in read_yml_file(fpath).items()
            }

    return ret


def read_masks(variable: str):
    ret = []

    for database_id in databases:
        fpath = databases[database_id] / 'masks' / ('/'.join(variable.split('|')) + '.yml')
        if fpath.exists():
            if not fpath.is_file():
                raise Exception(f"Expected YAML file, but not a file: {fpath}")

            ret += read_yml_file(fpath)

    return ret


class TEBase:
    # initialise
    def __init__(self, parent_variable: str):
        # set variable from function argument
        self._parent_variable: str = parent_variable

        # set technology specifications
        self._var_specs: dict = {key: val for key, val in variables.items() if key.startswith(self._parent_variable)}

    @property
    def parent_variable(self) -> str:
        return self._parent_variable
