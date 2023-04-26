from src.python.path import pathOfTEDFile
from src.python.read.file_read import readYAMLDataFile, readCSVDataFile


# load options
defaultUnits = readYAMLDataFile('default_units')


# load list of technology classes
techClasses = readYAMLDataFile('tech_classes')


# load list of technologies and specifications and insert info from tech class
techs = readYAMLDataFile('techs')
for tspecs in techs.values():
    tspecs['entry_types'] = techClasses[tspecs['class']]['entry_types']


# make sure techno-economic dataset files exist for each technology
techs_missing = [tid for tid in techs if not pathOfTEDFile(tid).exists()]
if techs_missing:
    raise Exception(f"TE dataset files missing for technologies: {techs_missing}")


# read dataformats
dataFormats = readYAMLDataFile('ted_format')


# read flow types
flowTypes = readCSVDataFile('flow_types.csv').set_index('flowid').to_dict('index')
