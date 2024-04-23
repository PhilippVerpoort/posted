source("R/posted/path.R")
source("R/posted/read.R")


apply_cond <- function(df, cond) {
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


Mask <- R6::R6Class("Mask",
    private = list(
        ..where = NULL,
        ..use = NULL,
        ..weight = NULL,
        ..other = NULL
        ..comment = NULL

    )
  public = list(
    where = NULL,
    use = NULL
    weight = NULL,
    other = NaN,
    comment = '',

    initialize = function(field_specs) {
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
        if is.null(private$..weight)
            private$..weight <- list(length(private$..use) * 1.0)
    }

    # check if a mask mateches a dataframe (all 'when' conditions match across all rows)
    matches = function(df) {
        for (w in private$..where) {
            if (!all(apply_cond(df, w))){
                return(FALSE)
            }
        }
        return(TRUE)
    }

    # return a dataframe with weights applied
    get_weights <- function(df, use, weight) {
        ret <- rep(NA, nrow(df))

        # Apply weights where the use condition matches
        for (i in 1:length(use)) {
            cond <- use[[i]]
            w <- weight[i]
            ret[apply_cond(df, cond)] <- w
        }

        # Convert the result to a data frame with the same index as df
        ret <- data.frame(index = rownames(df), weights = ret)
        return(ret)
        }


  )
)

read_masks <- function(variable) {
  ret <- list()

  for (database_id in databases) {
    fpath <- file.path(databases[[database_id]], 'masks', paste(unlist(strsplit(variable, '\\|')), collapse = '/'), '.yml')
    if (file.exists(fpath)) {
      if (!file.info(fpath)$isfile) {
        stop(paste("Expected YAML file, but not a file:", fpath))
      }

      ret <- c(ret, lapply(read_yaml_file(fpath), function(mask_specs) Mask(mask_specs)))
    }
  }

  return(ret)
}
