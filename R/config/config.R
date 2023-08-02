source("R/config/read_config.R")


# load options
defaultUnits <- readYAMLDataFile('default_units')
names(defaultUnits) <- paste0("[", names(defaultUnits), "]")

# load list of technology classes
techClasses <- readYAMLDataFile('tech_classes')

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
#}
#for (tspecs in techs) {
#    techClass <- techClasses[[tspecs$class]]
#    tspecs$entry_types <- techClass$entry_types
#
#    if (!('case_fields' %in% tspecs)) {
#        tspecs$case_fields <- list()
#    } else {
#        caseFields <- list()
#        for (caseType in names(tspecs$case_fields)) {
#            caseFields[[caseType]] <- techClass$case_fields[[caseType]]
#            caseFields[[caseType]]$dtype <- 'category'
#            caseFields[[caseType]]$required <- FALSE
#            caseFields[[caseType]]$options <- tspecs$case_fields[[caseType]]
#        }
#        tspecs$case_fields <- caseFields
#    }   
}
# read data format and dtypes
baseFormat <- readYAMLDataFile('base_format')
# mappings pandas dtypes to R dataframe types
dtypeMapping <- list(
    category="factor",
    str="character",
    float="numeric"
)
mapColnamesDtypes <- list()
for (colType in names(baseFormat)) {
    mapColnamesDtypes[[colType]] <- dtypeMapping[[baseFormat[[colType]]$dtype]]
}

# read flow types
flowTypes <- readCSVDataFile('flow_types.csv')
flowTypes <- split(flowTypes, flowTypes$flowid)

# read default masks
defaultMasks <- readYAMLDataFile('teds/default_masks')