library(docstring)
library(roxygen2)

# Read in converion factors from R_unit_cache
cached_units_path <- file.path(BASE_PATH, "R_unit_cache.csv")
cached_units <- read.csv(
    cached_units_path,
    sep=',',
    quote='"',
    encoding='utf-8'
)


# define unit variants
unit_variants <- list(
    LHV = list(param = 'energycontent', value = 'energycontent_LHV', dimension = 'energy'),
    HHV = list(param = 'energycontent', value = 'energycontent_HHV', dimension = 'energy'),
    norm = list(param = 'density', value = 'density_norm', dimension = 'volume'),
    std = list(param = 'density', value = 'density_std', dimension = 'volume')
)

#' @title unit_convert
#'
#' Converts units with optional flow context handling based on
#' specified variants and flow ID. The function checks if the input units are not NaN,
#' then it proceeds to handle different cases based on the presence of a flow context and unit
#' variants.
#'
#' @param unit_from Character or numeric. Unit to convert from.
#' @param unit_to Character or numeric. Unit to convert to.
#' @param flow_id Character or NULL. Identifier for the specific flow or process.
#'
#' @return Numeric. Conversion factor between \code{unit_from} and \code{unit_to}.
#'
#' @examples
#' # Example usage:
#' unit_convert("m", "km", flow_id = NULL)
#'
#' @export
unit_convert <- function(unit_from, unit_to, flow_id=NULL) {




    if(is.na(unit_from) | is.na(unit_to)) {
        return(NaN)
    }
    # if unit_from and unit_to are the same, return 1
    if (unit_from == unit_to) {
        return(1)
    }

    # if there is no flow ID take conversion from cached units, else proceed with flow_id
    if (is.null(flow_id)) {
        values <- dplyr::filter(cached_units, from==unit_from & to==unit_to)
        if (nrow(values) == 0) {
            warning(sprintf("No conversion factor found for unit '%s' to '%s'.", unit_from, unit_to))
        }
    } else {
        values <- dplyr::filter(cached_units, from==unit_from & to==unit_to & ft==flow_id)

        # if there was no match, try again without flow_id
        if (nrow(values) == 0) {
            values <- dplyr::filter(cached_units, from==unit_from & to==unit_to)
        }
        # if there was no match at all, report a warning
        if (nrow(values) == 0) {
            if (is.na(flow_id)) {
                warning(sprintf("No conversion factor found for unit '%s' to '%s'.", unit_from, unit_to))
            } else {
                warning(sprintf("No conversion factor found for unit '%s' to '%s' and flow type '%s'.", unit_from, unit_to, flow_id))
            }
            return(NA)
        }
    }

    # return
    return(values$factor[1])
}
