source("R/config_config.R")

#' The base class for all TE classes.
#' 
#' @description This abstract class defines the basic structure of a TE class.
#' This includes tid, data format, technology specifications, and dtype mapping.
#' @usage (NOT EXPORTED)
TEBase = R6::R6Class("TEBase",
  private = list(
    tid = NULL,
    tspecs = NULL,
    dataFormat = NULL,
    caseFields = NULL,
    dtypeMapping = NULL,
    setDataFormat = function() {
      # generate data format from base format and technology case fields
      private$dataFormat <- list()
      #slot(.Object, "dataFormat") <- list()
      for (key in names(baseFormat)) {
          private$dataFormat[[key]] <- baseFormat[[key]]

          # insert case fields after flow_type column
          if (key == "flow_type") {
              private$dataFormat <- c(private$dataFormat, private$tspecs$case_fields)
          }
        }
        private$caseFields <- list(names(private$tspecs$case_fields))
    }
  ),

  public = list(
    #' @description
    #' Create a TEBase object
    #' @param tid The technology ID.
    initialize = function(tid = "") {
      private$tid <- tid
      private$tspecs <- techs[[private$tid]]
      private$dtypeMapping <- list(NULL)
      private$setDataFormat()
    },
    #' @description
    #' Get the data format.
    #' @return A list of data format specifications.
    getDataFormat = function() {
      private$dataFormat
    },
    #' @description
    #' Get the default reference unit.
    #' @return The default reference unit.
    refUnit = function() {
      flowTypes[self$refFlow()][["default_unit"]]
    },
    #' @description
    #' Get the reference flow.
    #' @return The reference flow.
    refFlow = function() {
      private$tspecs[["reference_flow"]]
    },
    #' @description
    #' Get the default data type (data type mapping).
    #' @return The default data type.
    getDtypeMapping = function() {
      if (is.null(private$dtypeMapping[[1]])) {
          private$dtypeMapping <- list()
          for (colName in names(private$dataFormat)) {
              private$dtypeMapping[[colName]] <- private$dataFormat[[colName]][["dtype"]]
          }
      }
      return(private$dtypeMapping)
    }
  )
)