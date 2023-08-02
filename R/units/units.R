library(dplyr)


source("R/path.R")

# since unit conversion does not work so nicely in R compared to pint in Python, we use the cached conversion factors
# provided by Python.
cachedUnitsPath <- pathOfDataFile("units_cached.csv")
cachedUnits <- read.csv(
    cachedUnitsPath,
    sep=',',
    quote='"',
    encoding='utf-8'
)


# get conversion factor between units, e.g. unit_from = "MWh;LHV" and unit_to = "m³;norm"
convUnit <- function(unit_from, unit_to, flow_type=NULL) {
    # if unit_from and unit_to are the same, the conversion rate is 1
    if (unit_from == unit_to) {
        return(1)
    }
    if (is.null(flow_type)) {
        values <- filter(cachedUnits, from==unit_from & to==unit_to)
    } else {
        values <- filter(cachedUnits, from==unit_from & to==unit_to & ft==flow_type)
        # if there was no match, try again without flow_type
        if (nrow(values) == 0) {
            values <- filter(cachedUnits, from==unit_from & to==unit_to)
        }
    }

    return(values$factor[1])
}


# vectorised versions
convUnitDF <- function(df, unit_from_col, unit_to_col, flow_type=NULL) {
    print("convUnitDF")
    print(df[[unit_from_col]])
    print(df[[unit_to_col]])
    print(df$flow_type)
    print(flow_type)
    r <- apply(df, 1, function (row) {
        return(convUnit(row[[unit_from_col]], row[[unit_to_col]], if(!is.null(flow_type)) flow_type else row['flow_type']))
    })
    return(r)
}
