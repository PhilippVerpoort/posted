from pathlib import Path
from typing import Final
from warnings import warn

from cet_units import ureg


# Define own warning and exceptions types.
class POSTEDException(Exception):
    pass


class POSTEDWarning(UserWarning):
    pass


# Define path to public database.
DATA_PATH: Final[Path] = (Path(__file__).parent / "database").resolve()

# Define dictionary of databases. This can be extended by the user.
databases = {
    "public": DATA_PATH,
}

# Check that the public database exists.
if not DATA_PATH.is_dir():
    del databases["public"]
    warn("Could not find anchor of public database.", POSTEDWarning)

# Define default settings.
defaults = {
    "period": [2025],
    "currency": "EUR_2024",
}

# Define flow units.
ureg.define_flows([
    "H2",
    "NG",
    "NH3",
    "MeOH",
    "H2O",
    "coal",
    "O2",
])

# Expose module members.
from posted.noslag.tedf import TEDF

__all__ = [
    "databases",
    "defaults",
    "POSTEDException",
    "POSTEDWarning",
    "TEDF",
]
