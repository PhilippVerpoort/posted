library(yaml)

source("src/R/path.R")


# mappings pandas dtypes to R dataframe types
dtypeMapping <- list(
    category="factor",
    str="character",
    float="numeric"
)


# read TED CSV input file
readTEDFile <- function (path, mapColnamesDtypes) {
    # apply mapping from pandas dtypes to R dataframe types
    colClasses <- c()
    for (colName in names(mapColnamesDtypes)) {
        colClasses <- append(colClasses, dtypeMapping[[mapColnamesDtypes[[colName]]]])
    }

    return(read.csv(
        path,
        col.names=names(mapColnamesDtypes),
        colClasses=colClasses,
        sep=',',
        quote='"',
        encoding='utf-8'
    ))
}


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
