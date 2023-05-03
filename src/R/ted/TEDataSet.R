source("src/R/path.R")
source("src/R/read/read_config.R")


loadDataset <- function(tid, load_other = c(), load_default = TRUE) {

    # read TED data from CSV files
    mapColnamesDtypes <- list()
    for (colType in names(dataFormats)) {
        mapColnamesDtypes[[colType]] <- dataFormats[[colType]]$dtype
    }

    p <- pathOfTEDFile(tid)
    dataset <- readTEDFile(p, mapColnamesDtypes)
    return(dataset)
}
