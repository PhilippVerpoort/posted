import pint

from src.path import pathOfFile


# define new registry
ureg = pint.UnitRegistry()


# load definitions
ureg.load_definitions(pathOfFile('src/units', 'definitions.txt'))
