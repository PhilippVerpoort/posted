source("R/config_read_config.R")

#' The default units for some dimensions (e.g. time, currency). 
#' 
#' @usage (NOT EXPORTED)
#' @seealso Uses \link{readYAMLDataFile}.
#' @name defaultUnits
# load options
defaultUnits <- readYAMLDataFile('default_units')
names(defaultUnits) <- paste0("[", names(defaultUnits), "]")

#' Technology classes (e.g. storage, conversion and transport) specifications and their entry types.
#' 
#' @usage (NOT EXPORTED)
#' @name techClasses
#' @seealso Uses \link{readYAMLDataFile}.
# load list of technology classes
techClasses <- readYAMLDataFile('tech_classes')


#' Technology specifications (e.g. name, desc, sector, case_fields, ...).
#' 
#' @usage (NOT EXPORTED)
#' @seealso Uses \link{readYAMLDataFile}.
#' @name techs
# load list of technologies and specifications and insert info from tech class
techs <- readYAMLDataFile('techs')
for (i in seq_len(length(techs))) {
    techClass <- techClasses[[techs[[i]]$class]]
    techs[[i]]$entry_types <- techClass$entry_types
    if (!('case_fields' %in% names(techs[[i]]))) {
        techs[[i]]$case_fields <- list()
    } else {
        caseFields <- list()
        for (caseType in names(techs[[i]]$case_fields)) {
            caseFields[[caseType]] <- techClass$case_fields[[caseType]]
            caseFields[[caseType]]$dtype <- 'category'
            caseFields[[caseType]]$required <- FALSE
            caseFields[[caseType]]$options <- techs[[i]]$case_fields[[caseType]]
        }
        techs[[i]]$case_fields <- caseFields
    }
}

#' Entry type specifications and their default data types.
#' 
#' @usage (NOT EXPORTED)
#' @name baseFormat
#' @seealso Uses \link{readYAMLDataFile}.
# read data format and dtypes
baseFormat <- readYAMLDataFile('base_format')

#' Mapping of pandas dtypes to R dataframe types.
#' 
#' @usage (NOT EXPORTED)
#' @name dtypeMapping
# mappings pandas dtypes to R dataframe types
dtypeMapping <- list(
    category="factor",
    str="character",
    float="numeric"
)

#' Default data type for each entry type.
#' 
#' @usage (NOT EXPORTED)
#' @name defaultDtypes
mapColnamesDtypes <- list()
for (colType in names(baseFormat)) {
    mapColnamesDtypes[[colType]] <- dtypeMapping[[baseFormat[[colType]]$dtype]]
}

#' Flow type information (e.g. default unit, energy content, density).
#' 
#' @usage (NOT EXPORTED)
#' @name flowTypes
#' @seealso Uses \link{readCSVDataFile}.
# read flow types
flowTypes <- readCSVDataFile('flow_types.csv')
flowTypes <- split(flowTypes, flowTypes$flowid)

#' Default masks that are applied to the flow types.
#'
#' @usage (NOT EXPORTED)
#' @name defaultMasks
#' @seealso Uses \link{readYAMLDataFile}.
# read default masks
defaultMasks <- readYAMLDataFile('teds/default_masks')
