#' @title read_csv_file
#'
#' @description Read a csv datafile
#'
#' @param fpath path of the csv file
#' @export
read_csv_file <- function (fpath) {
    return(read.csv(
        fpath,
        sep=',',
        quote='"',
        encoding='utf-8'
    ))
}

#' @title read_yaml_file
#'
#' @description read YAML config file
#'
#' @param fpath path of the YAML file
#' @export
read_yml_file <- function (fpath) {
    fhandle <- file(fpath, "r", encoding="utf-8")
    ret <- yaml::read_yaml(file=fhandle, fileEncoding="utf-8")
    close(fhandle)
    return(ret)
}
