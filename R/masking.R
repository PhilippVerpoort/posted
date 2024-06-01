source("R/path.R")
source("R/read.R")
library(docstring)
library(roxygen2)


apply_cond <- function(df, cond) {
  #' apply_cond
  #'
  #' Takes a pandas DataFrame and a condition, which can be a string, dictionary,
  #' or callable, and applies the condition to the DataFrame using \code{eval} or \code{apply}
  #' accordingly.
  #'
  #' @param df DataFrame. A pandas DataFrame containing the data on which the condition will be applied.
  #' @param cond MaskCondition. The condition to be applied on the dataframe. Can be either a string, a dictionary, or a
  #'             callable function.
  #'
  #' @return DataFrame. Dataframe evaluated at the mask condition.
  #'
  #' @export

  if (class(cond) == "character") {
    return(filter(eval(parse(text = cond))))
  } else if (class(cond) == "list") {
    cond <- paste(paste(names(cond), "==", paste0("'", unlist(cond), "'"), collapse = " & "), collapse = " & ")
    return(filter(eval(parse(text = cond))))
  } else if (inherits(cond, "function")) {
    return(apply(df, 1, cond))
  } else {
    stop("Unsupported condition type")
  }
}

#' Class for Masks
#'
#' @desctiption Class to define masks with conditions and weights to apply to DataFiles



Mask <- R6::R6Class("Mask",

    private = list(
        ..where = NULL,
        ..use = NULL,
        ..weight = NULL,
        ..other = NULL,
        ..comment = NULL

    ),
    public = list(
    #' @description
    #' Create a new mask object
    #' @param where MaskCondition | list[MaskCondition], optional. Where the mask should be applied.
    #' @param use MaskCondition | list[MaskCondition], optional. Condition on where to use the masks.
    #' @param weight Numeric | Character | list[Numeric | Character], optional. Weights to apply.
    #' @param other Numeric, optional.
    #' @param comment Character, optional. Comment.
    initialize = function(where = NULL, use = NULL,weight = NULL, other = NaN, comment = '') {

        # set fields from constructor arguments
        private$..where <- if (is.null(where)){ list() }else{if (typeof(where)=="list"){ where }else{ list(where) }}
        private$..use <- if (is.null(use)){ list() }else{if (typeof(use)=="list"){ use }else{ list(use) }}
        private$..weight <- if(is.null(weight)){ NULL }else{ if (typeof(weight=="list")){lapply(weight, function(x){as.numeric(x)})}else{as.numeric(weight)}}
        private$..other <- other
        private$..comment <- comment

         # perform consistency checks on fields
        if((!is.null(private$..use) && !is.null(private$..weight)) && (length(private$..use) != length(private$..weight))) {
            stop("Must provide same length of 'use' conditions as 'weight' values.")
        }

        # set default weight to 1 if not set otherwise
        if (is.null(private$..weight)){
            private$..weight <- list(length(private$..use) * 1.0)
        }
    },


    #' @description Check if a mask matches a dataframe by verifying if all 'where' conditions match across all rows.
    #'
    #' @param df DataFrame. Dataframe to check for matches.
    #'
    #' @return Logical. If the mask matches the dataframe.
    #' @export
    matches = function(df) {
        for (w in private$..where) {
            if (!all(apply_cond(df, w))){
                return(FALSE)
            }
        }
        return(TRUE)
    },

    #' @description Apply weights to the dataframe
    #'
    #' @param df Dataframe. Dataframe to apply weights on
    #' @return Dataframe. Dataframe with applied weights
    get_weights = function(df, use, weight) {
        ret <- rep(NA, nrow(df))

        # Apply weights where the use condition matches
        for (i in 1:length(use)) {
            cond <- use[[i]]
            w <- weight[i]
            ret[apply_cond(df, cond)] <- w
        }

        # Convert the result to a data frame with the same index as df
        ret <- data.frame(index = rownames(df), weights = ret)

        # return
        return(ret)
     }


  )
)

#' @description Reads YAML files containing mask specifications from multiple databases and returns a list of Mask objects.
#'
#' @param variable Character. Variable to be read.
#'
#' @return List. List with masks for the variable.
#'
#' @export
read_masks <- function(variable) {
    ret <- list()

    for (database_id in names(databases)) {
        fpath <- file.path(databases[[database_id]], 'masks', paste0(paste(unlist(strsplit(variable,split= '\\|')), collapse = '/'), '.yml'))
        if (file.exists(fpath)) {
            if (dir.exists(fpath)) {
                stop(paste("Expected YAML file, but not a file:", fpath))
            }

        ret <- c(ret, lapply(read_yml_file(fpath), function(mask_specs) {Mask$new(mask_specs)}))
        }
    }

  return(ret)
}
