library("diffobj")
library(dplyr)
library(posted)


datasets_to_be_tested <- list("ELH2", "IDR", "EAF", "MEOH-SYN", "HBNH3-ASU", "HOTROLL", "CAST", "DAC")
results <- list()

for (dataset in datasets_to_be_tested) {
    d <- TEDataSet$new(tid=dataset)
    write.csv(
        d$data(),
        file=paste0(paste0("./tests/comparison/", dataset), "R.csv"),
        #quote=FALSE,
        row.names=FALSE,
        #sep=",",
        #qmethod="escape",
        fileEncoding="UTF-8",
        na=""
    )
    # compare the output of the R implementation with the output of the Python implementation
    f1 <- paste0(paste0("./tests/comparison/", dataset), "R.csv")
    f2 <- paste0(paste0("./tests/comparison/", dataset), "Python.csv")
    
    results[[dataset]] <- summary(diffCsv(f1, f2, pager="off"))@all.eq
}

# print the results
for (dataset in datasets_to_be_tested) {
    result <- results[[dataset]]
    # check if result is of length zero
    if (length(result) == 0) {
        result <- "OK"
    }
    print(paste0(dataset, ": ", result))
}