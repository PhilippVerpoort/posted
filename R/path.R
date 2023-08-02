BASE_PATH <- "./inst/extdata"

pathOfFile <- function(dname, fname) {
  return(file.path(BASE_PATH, dname, fname))
}


pathOfDataFile <- function(fname) {
  return(file.path(BASE_PATH, fname))
}


pathOfTEDFile <- function(tid) {
  return(file.path(BASE_PATH, "teds", paste0(tid, ".csv")))
}

pathOfOutputFile <- function(fname) {
  return(file.path(BASE_PATH, "output", fname))
}