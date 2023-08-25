import copy

from posted.config.read_config import readYAMLDataFile, readCSVDataFile


# The default units for some dimensions (e.g. time, currency). 
# 
# @usage (NOT EXPORTED)
# @seealso Uses readYAMLDataFile.
# @name defaultUnits
# load options
defaultUnits = {f"[{key}]": val for key, val in readYAMLDataFile('default_units').items()}


# Technology classes (e.g. storage, conversion and transport) specifications and their entry types.
# 
# @usage (NOT EXPORTED)
# @name techClasses
# @seealso Uses readYAMLDataFile.
# load list of technology classes
techClasses = readYAMLDataFile('tech_classes')


# Technology specifications (e.g. name, desc, sector, case_fields, ...).
# 
# @usage (NOT EXPORTED)
# @seealso Uses readYAMLDataFile.
# @name techs
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


# Entry type specifications and their default data types.
# 
# @usage (NOT EXPORTED)
# @name baseFormat
# @seealso Uses readYAMLDataFile.
# read data format and dtypes
baseFormat = readYAMLDataFile('base_format')


#' Flow type information (e.g. default unit, energy content, density).
#' 
#' @usage (NOT EXPORTED)
#' @name flowTypes
#' @seealso Uses readCSVDataFile.
flowTypes = readCSVDataFile('flow_types.csv').set_index('flowid').to_dict('index')


#' Default masks that are applied to the flow types.
#'
#' @usage (NOT EXPORTED)
#' @name defaultMasks
#' @seealso Uses readYAMLDataFile.
# read default masks
defaultMasks = readYAMLDataFile('teds/default_masks')
