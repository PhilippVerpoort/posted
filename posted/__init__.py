from pathlib import Path
from typing import Final
from warnings import warn

from units import ureg


# Define path to public database.
DATA_PATH: Final[Path] = (Path(__file__).parent / "database").resolve()

# Define dictionary of databases. This can be extended by the user.
databases = {
    "public": DATA_PATH,
}

# Check that the public database exists.
if not (DATA_PATH / ".anchor").exists():
    del databases["public"]
    warn("Could not find anchor of public database.", UserWarning)


# Define own warning and exceptions types.
class POSTEDException(Exception):
    pass


class POSTEDWarning(UserWarning):
    pass


# Define default settings.
defaults = {
    "period": [2025],
    "currency": "EUR_2024",
}

# Define flow units.
ureg.define_flows(["H2", "NG", "NH3", "MeOH", "H2O"])

# Expose module members.
from .tedf import TEDF
from .sources import load_sources
from .formatting import format_sources

__all__ = [
    "TEDF",
    "load_sources",
    "format_sources",
    "databases",
    "defaults",
    "POSTEDException",
    "POSTEDWarning",
]
