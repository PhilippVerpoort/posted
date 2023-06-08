library(yaml)

source("src/R/path.R")


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


# read YAML config file
readYAMLDataFile <- function (fname) {
    fpath <- pathOfDataFile(paste0(fname, ".yml"))
    fhandle <- file(fpath, "r")
    ret <- read_yaml(file=fhandle, fileEncoding="utf-8")
    close(fhandle)
    return(ret)
}
