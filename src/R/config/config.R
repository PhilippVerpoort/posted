source("src/R/config/read_config.R")


# load options
defaultUnits <- readYAMLDataFile('default_units')


# load list of technology classes
techClasses <- readYAMLDataFile('tech_classes')


# load list of technologies and specifications and insert info from tech class
techs <- readYAMLDataFile('techs')
for (tid in names(techs)) {
  techs[[tid]]$entry_types <- techClasses[[techs[[tid]]$class]]$entry_types
}


# read data format and dtypes
dataFormats <- readYAMLDataFile('ted_format')
# mappings pandas dtypes to R dataframe types
dtypeMapping <- list(
    category="factor",
    str="character",
    float="numeric"
)
mapColnamesDtypes <- list()
for (colType in names(dataFormats)) {
    mapColnamesDtypes[[colType]] <- dtypeMapping[[dataFormats[[colType]]$dtype]]
}


# read flow types
flowTypes <- readCSVDataFile('flow_types.csv')
flowTypes <- split(flowTypes, flowTypes$flowid)


# read default masks
defaultMasks <- readYAMLDataFile('teds/default_masks')
