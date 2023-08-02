library("R6")
source("R/config/config.R")

TEBase = R6Class("TEBase",
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
    initialize = function(tid = "") {
      private$tid <- tid
      private$tspecs <- techs[[private$tid]]
      private$dtypeMapping <- list(NULL)
      private$setDataFormat()
    },
    getDataFormat = function() {
      private$dataFormat
    },
    refUnit = function() {
      flowTypes[self$refFlow()][["default_unit"]]
    },
    refFlow = function() {
      private$tspecs[["reference_flow"]]
    },
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