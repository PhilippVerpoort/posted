source("src/R/path.R")
source("src/R/read/read_config.R")


loadDataset <- function(tid, load_other = c(), load_default = TRUE) {
  fpath <- pathOfTEDFile(tid)
  print(fpath)
  dataset <- read.csv(fpath)
  print(dataset)
}
