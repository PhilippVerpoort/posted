# read CSV data file
read_csv_file <- function (fpath) {
    return(read.csv(
        fpath,
        sep=',',
        quote='"',
        encoding='utf-8'
    ))
}

# read YAML config file
read_yml_file <- function (fpath) {
    fhandle <- file(fpath, "r", encoding="utf-8")
    ret <- yaml::read_yaml(file=fhandle, fileEncoding="utf-8")
    close(fhandle)
    return(ret)
}