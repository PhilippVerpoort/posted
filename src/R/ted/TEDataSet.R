source("src/R/path.R")
source("src/R/read/read_config.R")

library(dplyr)


# load dataset
loadDataset <- function(tid, load_other = list(), load_default = TRUE, to_default_units = TRUE) {
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

    # insert missing periods
    dataset <- insertMissingPeriods(dataset)

    # apply references to values and units
    dataset <- normaliseUnits(tid, dataset)

    # convert values to default units
    if (to_default_units) {
        dataset <- convertUnits(tid, dataset)
    }

    return(dataset)
}


# check dataset is consistent
checkConsistency <- function(tid, dataset) {
    # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
    # TODO: implement those types so we don't need to remove them
    dropTypes <- c("flh", "lifetime", "energy_eff")
    dataset <- dataset %>% filter(!type %in% dropTypes)

    return(dataset)
}


# insert missing periods
insertMissingPeriods <- function(dataset) {
    dataset["period"][is.na(dataset["period"])] <- 2023
    return(dataset)
}


# apply references to values and units
normaliseUnits <- function(tid, dataset) {
    return(dataset)
}


# convert values to default units
convertUnits <- function(tid, dataset) {
    return(dataset)
}
