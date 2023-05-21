BASE_PATH <- "."


pathOfFile <- function(dname, fname) {
  return(file.path(BASE_PATH, dname, fname))
}


pathOfDataFile <- function(fname) {
  return(file.path(BASE_PATH, "data", fname))
}


pathOfTEDFile <- function(tid) {
  return(file.path(BASE_PATH, "data", "teds", paste0(tid, ".csv")))
}


getPath <- function() {
  return(here::here())
}
