source("R/path.R")

#' Read a CSV data file.
#' 
#' This function reads in a csv file specified by the relative file path.
#' @usage (NOT EXPORTED)
#' @param fname The relative file path.
#' @seealso Uses \link{pathOfDataFile}.
# read CSV data file
readCSVDataFile <- function (fname) {
    fpath <- pathOfDataFile(fname)
    return(read.csv(
        fpath,
        sep=',',
        quote='"',
        encoding='utf-8'
    ))
}

#' Read a YAML data file.
#' 
#' This function reads in a yaml file specified by the relative file path (without the file extension).
#' @usage (NOT EXPORTED)
#' @param fname The relative file path (without the file extension).
#' @seealso Uses \link{pathOfDataFile}.
# read YAML config file
readYAMLDataFile <- function (fname) {
    fpath <- pathOfDataFile(paste0(fname, ".yml"))
    fhandle <- file(fpath, "r", encoding="utf-8")
    ret <- yaml::read_yaml(file=fhandle, fileEncoding="utf-8")
    close(fhandle)
    return(ret)
}
