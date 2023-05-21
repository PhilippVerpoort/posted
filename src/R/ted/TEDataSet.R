source("src/R/path.R")
source("src/R/config/read_config.R")

library(dplyr)


TEDataSet <- function(tid, load_other=list(), load_database=FALSE, to_default_units=TRUE) {
    # read TEDataFiles and combine into dataset
    dataset <- TEDataSet.loadFiles(tid=tid, load_other=load_other, load_database=load_database)

    # set default reference units for all entry types
    refUnitsDef <- TEDataSet.setRefUnitsDef(tid=tid)

    # normalise all entries to a unified reference
    dataset <- TEDataSet.normToRef(tid=tid, dataset=dataset, refUnitsDef=refUnitsDef)

    # convert values to default units
    if (to_default_units) {
        dataset <- TEDataSet.convertUnits(tid=tid, dataset=dataset)
    }

    # return TEDataSet object as list
    return(list(
      tid=tid,
      dataset=dataset,
      refUnitsDef=refUnitsDef
    ))
}


# load TEDatFiles and compile into dataset
TEDataSet.loadFiles <- function(tid, load_other, load_database) {
    files <- list()

    # load default TEDataFile from POSTED database
    if ((!!length(load_other)) | load_database) {
        files <- append(files, TEDataFile.read(tid, pathOfTEDFile(tid)))
    }

    # load TEDataFiles specified as arguments
    if (!!length(load_other)) {
        for (o in load_other) {
            if (typeof(o) == "list") {
                files <- append(files, o)
            }
            else if (typeof(o) == "character") {
                files <- append(files, TEDataFile.read(tid, o))
            }
            else {
                stop("Unknown load type.")
            }
        }
    }

    # raise exception if no TEDataFiles can be loaded
    if (!!length(files)) {
        stop(paste0("No TEDataFiles to load for technology '", tid, "'."))
    }

    # compile dataset from the dataframes loaded from the individual files
    datasetList <- list()
    for (i in seq_along(files)) {
        datasetList[[i]] <- files[[i]]$data
    }
    dataset <- dplyr::bind_rows(datasetList)

    # return
    return(dataset)
}


# determine default reference units of entry types from technology class
TEDataSet.setRefUnitsDef <- function(tid) {
    tspecs <- techs[[tid]]

    refUnitsDef <- list()
    for (typeid in names(tspecs$entry_types)) {
        # get reference dimension
        refDim <- tspecs$entry_types[[typeid]]$ref_dim

        # create a mapping from dimensions to default units
        unitMappings <- defaultUnits
        if ('reference_flow' %in% names(tspecs)) {
            a <- list(flow=flowTypes[[tspecs$reference_flow]]$default_unit)
            unitMappings <- append(unitMappings, a)
        }

        # map reference dimensions to default reference units
        refUnitsDef[[typeid]] <- refDim
        for (dim in names(unitMappings)) {
            unit <- unitMappings[[dim]]
            refUnitsDef[[typeid]] <- sub(dim, unit, refUnitsDef[[typeid]])
        }
    }

    # override with default reference unit of specific technology
    if ('default-ref-units' %in% tspecs) {
        refUnitsDef <- append(refUnitsDef, tspecs[['default-ref-units']])
    }

    # return
    return(refUnitsDef)
}


# apply references to values and units
TEDataSet.normToRef <- function(tid, dataset, refUnitsDef) {
    return(dataset)
}


# convert values to defined units (use defaults if non provided)
TEDataSet.convertUnits <- function(tid, dataset) {
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
