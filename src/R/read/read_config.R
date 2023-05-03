source("src/R/read/file_read.R")


# load options
defaultUnits <- readYAMLDataFile('default_units')


# load list of technology classes
techClasses <- readYAMLDataFile('tech_classes')


# load list of technologies and specifications and insert info from tech class
techs <- readYAMLDataFile('techs')
for (tid in names(techs)) {
  techs[[tid]]$entry_types <- techClasses[[techs[[tid]]$class]]$entry_types
}


# make sure techno-economic dataset files exist for each technology
# TODO: Decide if we want to implement this in R too.


# read dataformats
dataFormats <- readYAMLDataFile('ted_format')


# read flow types
flowTypes <- readCSVDataFile('flow_types.csv')


# read default masks
defaultMasks <- readYAMLDataFile('teds/default_masks')
