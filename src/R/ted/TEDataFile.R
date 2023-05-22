source("src/R/config/config.R")


# read TED CSV input file
TEDataFile.read <- function(tid, path) {
    # read data
    df <- read.csv(
        path,
        colClasses=mapColnamesDtypes,
        sep=',',
        quote='"',
        encoding='utf-8',
        na.strings=c('', ' ')
    )

    # return TEDataFile object as list
    return(list(
        tid=tid,
        path=path,
        data=df
    ))
}
