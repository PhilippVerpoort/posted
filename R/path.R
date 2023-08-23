BASE_PATH <- "./inst/extdata"

#' Path of a file in a given directory
#' 
#' This function returns the path of a file in a given directory.
#' @usage (NOT EXPORTED)
#' @param dname The directory name.
#' @param fname The file name.
pathOfFile <- function(dname, fname) {
  return(file.path(BASE_PATH, dname, fname))
}

#' Path of a data file
#' 
#' This function returns the path of a file in the data directory.
#' @usage (NOT EXPORTED)
#' @param fname The file name.
pathOfDataFile <- function(fname) {
  return(file.path(BASE_PATH, fname))
}

#' Path of a TED file
#' 
#' This function returns the path of a TED data file in the TED directory.
#' @usage (NOT EXPORTED)
#' @param tid The technology ID.
pathOfTEDFile <- function(tid) {
  return(file.path(BASE_PATH, "teds", paste0(tid, ".csv")))
}

#' Path of an output file
#' 
#' This function returns the path of a file in the output directory.
#' @usage (NOT EXPORTED)
#' @param fname The file name.
pathOfOutputFile <- function(fname) {
  return(file.path(BASE_PATH, "output", fname))
}