source("R/path.R")
#' The cached conversion factors between units.
#' 
#' @usage (NOT EXPORTED)
#' @seealso Uses \link{pathOfDataFile}.
#' @name cachedUnits
# since unit conversion does not work so nicely in R compared to pint in Python, we use the cached conversion factors
# provided by Python.
cachedUnitsPath <- pathOfDataFile("units_cached.csv")
cachedUnits <- read.csv(
    cachedUnitsPath,
    sep=',',
    quote='"',
    encoding='utf-8'
)
#' Get conversion factor between units.
#' 
#' @param unit_from The unit to convert from.
#' @param unit_to The unit to convert to.
#' @param flow_type The flow type.
#' @name convUnit
#' @examples
#' convUnit("MWh;LHV", "m³;norm")
#' @export
#' @return The conversion factor.
# get conversion factor between units, e.g. unit_from = "MWh;LHV" and unit_to = "m³;norm"
convUnit <- function(unit_from, unit_to, flow_type=NULL) {
    # if unit_from and unit_to are the same, the conversion rate is 1
    if (unit_from == unit_to) {
        return(1)
    }
    if (is.null(flow_type)) {
        values <- dplyr::filter(cachedUnits, from==unit_from & to==unit_to)
    } else {
        values <- dplyr::filter(cachedUnits, from==unit_from & to==unit_to & ft==flow_type)
        # if there was no match, try again without flow_type
        if (nrow(values) == 0) {
            values <- dplyr::filter(cachedUnits, from==unit_from & to==unit_to)
        }
        # if there was no match at all, report a warning
        if (nrow(values) == 0) {
            if (is.na(flow_type)) {
                warning(sprintf("No conversion factor found for unit '%s' to '%s'.", unit_from, unit_to))
            } else {
                warning(sprintf("No conversion factor found for unit '%s' to '%s' and flow type '%s'.", unit_from, unit_to, flow_type))
            }
            return(NA)
        }
    }
    return(values$factor[1])
}
#' Convert a dataframe column from one unit to another.
#' 
#' @param df The dataframe.
#' @param unit_from_col The column with the unit to convert from.
#' @param unit_to_col The column with the unit to convert to.
#' @param flow_type The flow type.
#' @name convUnitDF
#' @examples
#' convUnitDF(data.frame(unit_from=c("MWh;LHV", "MWh;LHV"), unit_to=c("m³;norm", "m³;norm")))
#' @return A one column data frame that contains the conversion factors
#' @export
# vectorised versions
convUnitDF <- function(df, unit_from_col, unit_to_col, flow_type=NULL) {
    r <- apply(df, 1, function (row) {
        return(convUnit(row[[unit_from_col]], row[[unit_to_col]], if(!is.null(flow_type)) flow_type else row['flow_type']))
    })
    return(r)
}
