"""NOSLAG: Normalise-Select-Aggregate framework.

The noslag module implements the handling of techno-economic data frames:
loading from source files, normalising units and reference values, selecting
fields, and aggregating over fields.
"""

from ._masking import Mask
from ._tedf import TEDF

__all__ = [
    "Mask",
    "TEDF",
]
