source("R/posted/path.R")

cached_units_path <- file.path(BASE_PATH, "R_unit_cache.csv")
cached_units <- read.csv(
    cached_units_path,
    sep=',',
    quote='"',
    encoding='utf-8'
)



unit_variants <- list(
    LHV = list(param = 'energycontent', value = 'energycontent_LHV', dimension = 'energy'),
    HHV = list(param = 'energycontent', value = 'energycontent_HHV', dimension = 'energy'),
    norm = list(param = 'density', value = 'density_norm', dimension = 'volume'),
    std = list(param = 'density', value = 'density_std', dimension = 'volume')
)

unit_convert <- function(unit_from, unit_to, flow_type=NULL) {
 
    if (unit_from == unit_to) {
        return(1)
    }
    if (is.null(flow_type)) {
        values <- dplyr::filter(cached_units, from==unit_from & to==unit_to)
    } else {
        values <- dplyr::filter(cached_units, from==unit_from & to==unit_to & ft==flow_type)
        # if there was no match, try again without flow_type
        if (nrow(values) == 0) {
            values <- dplyr::filter(cached_units, from==unit_from & to==unit_to)
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