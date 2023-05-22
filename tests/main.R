source("src/R/ted/TEDataFile.R")
source("src/R/ted/TEDataSet.R")


# TEDataFile.read('electrolysis', 'data/teds/electrolysis.csv')
dataset <- TEDataSet('electrolysis')

print(dataset$data)
