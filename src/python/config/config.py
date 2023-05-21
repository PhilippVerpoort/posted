from src.python.config.read_config import readYAMLDataFile, readCSVDataFile


# load options
defaultUnits = readYAMLDataFile('default_units')


# load list of technology classes
techClasses = readYAMLDataFile('tech_classes')


# load list of technologies and specifications and insert info from tech class
techs = readYAMLDataFile('techs')
for tspecs in techs.values():
    tspecs['entry_types'] = techClasses[tspecs['class']]['entry_types']


# read data format and dtypes
dataFormat = readYAMLDataFile('ted_format')
mapColnamesDtypes = {
    colname: colspecs['dtype']
    for colname, colspecs in dataFormat.items()
}


# read flow types
flowTypes = readCSVDataFile('flow_types.csv').set_index('flowid').to_dict('index')


# read default masks
defaultMasks = readYAMLDataFile('teds/default_masks')
