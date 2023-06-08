import copy

from posted.config.read_config import readYAMLDataFile, readCSVDataFile


# load options
defaultUnits = {f"[{key}]": val for key, val in readYAMLDataFile('default_units').items()}


# load list of technology classes
techClasses = readYAMLDataFile('tech_classes')


# load list of technologies and specifications and insert info from tech class
techs = readYAMLDataFile('techs')
for tspecs in techs.values():
    techClass = techClasses[tspecs['class']]
    tspecs['entry_types'] = techClass['entry_types']

    if 'case_fields' not in tspecs:
        tspecs['case_fields'] = {}
    else:
        caseFields = {}
        for caseType in tspecs['case_fields']:
            caseFields[caseType] = copy.deepcopy(techClass['case_fields'][caseType])
            caseFields[caseType]['dtype'] = 'category'
            caseFields[caseType]['required'] = False
            caseFields[caseType]['options'] = tspecs['case_fields'][caseType]
        tspecs['case_fields'] = caseFields


# read data format and dtypes
baseFormat = readYAMLDataFile('base_format')


# read flow types
flowTypes = readCSVDataFile('flow_types.csv').set_index('flowid').to_dict('index')


# read default masks
defaultMasks = readYAMLDataFile('teds/default_masks')
