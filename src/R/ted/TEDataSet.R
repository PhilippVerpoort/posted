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

    return(dataset)
}
