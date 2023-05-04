source("src/R/path.R")
source("src/R/read/read_config.R")

library(dplyr)


loadDataset <- function(tid, load_other = list(), load_default = TRUE) {
    loadPaths <- load_other
    if (load_default) {
        loadPaths <- append(loadPaths, pathOfTEDFile(tid))
    }

    # read TED data from CSV files
    mapColnamesDtypes <- list()
    for (colType in names(dataFormats)) {
        mapColnamesDtypes[[colType]] <- dataFormats[[colType]]$dtype
    }
    datasetList <- list()
    for (i in seq_along(loadPaths)) {
        p <- loadPaths[[i]]
        datasetList[[i]] <- readTEDFile(p, mapColnamesDtypes)
    }
    dataset <- dplyr::bind_rows(datasetList)

    # check that the TED is consistent
    dataset <- checkConsistency(tid, dataset)

    # adjust units to match default units for inputs and outputs
    dataset <- normaliseUnits(tid, dataset)

    # insert missing periods
    dataset <- insertMissingPeriods(dataset)

    return(dataset)
}


# check dataset is consistent
checkConsistency <- function(tid, dataset) {
    # TODO: check reported units match dataFormats['bat']

    # TODO: check reference units match techs[techid]

    # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
    # TODO: implement those types so we don't need to remove them
    dropTypes <- c("flh", "lifetime", "energy_eff")
    dataset <- dataset %>% filter(!type %in% dropTypes)

    # replace Nm³/Sm³ with m³
    # TODO: implement these units in the unit registry. Same for LHV and HHV.
    dataset["reported_unit"][dataset["reported_unit"] == 'Nm³'] <- "m³"

    return(dataset)
}


# convert value, unc, and units (reported and reference) to default units
normaliseUnits <- function(tid, dataset) {
    return(dataset)
}


# insert missing periods
insertMissingPeriods <- function(dataset) {
    dataset["period"][is.na(dataset["period"])] <- 2023
    return(dataset)
}
