source("R/ted/TEDataFile.R")
source("R/ted/TEDataSet.R")


test <- TEDataSet$new(tid="ELH2")
print(test$data()) # this should give 40 rows (right now its only 13 and lots of them are missing values)

write.csv(
    test$data(),
    file="ELH2WithR2.csv",
    #quote=FALSE,
    row.names=FALSE,
    #sep=",",
    #qmethod="escape",
    fileEncoding="UTF-8",
    na=""
)

test <- TEDataSet$new(tid="IDR")

write.csv(
    test$data(),
    file="IDRWithR2.csv",
    #quote=FALSE,
    row.names=FALSE,
    #sep=",",
    #qmethod="escape",
    fileEncoding="UTF-8",
    na=""
)

test <- TEDataSet$new(tid="EAF")

write.csv(
    test$data(),
    file="EAFWithR2.csv",
    #quote=FALSE,
    row.names=FALSE,
    #sep=",",
    #qmethod="escape",
    fileEncoding="UTF-8",
    na=""
)


