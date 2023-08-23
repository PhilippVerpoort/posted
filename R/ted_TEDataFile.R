library(magrittr)

source("R/ted_TEBase.R")

#' The base class for all TE data file classes.
#' 
#' @description This abstract class defines the basic structure of a TE data file class.
#' @usage (NOT EXPORTED)
TEDataFile = R6::R6Class("TEDataFile",
  inherit = TEBase,
  private = list(
      tid = NULL,
      path = NULL,
      df = NULL
  ),
  public = list(
    #' @description
    #' Create a TEDataFile object
    #' @param tid The technology ID.
    #' @param path The path to the data file.
    initialize = function(tid, path=NULL) {
      # initialise TEBase fields
      super$initialize(tid)
      # initialise object fields
      private$tid <- tid
      if (is.null(path)){
          private$path <- pathOfTEDFile(tid)
      } else {
          private$path <- path
      }
      private$df <- data.frame(NULL)
    },
    #' @description
    #' Checks if the data has been read in, if not reads the data.
    load = function() {
      if (identical(private$df,data.frame(NULL))) {
        self$read()
        return(self)
      }
    },
    #' @description
    #' Reads the data from the data file.
    #' Checks if the data file contains no unknown columns.
    #' Inserts missing columns, reorders via reindexing and updates dtypes.
    read = function() {
      # read CSV file
      print(sprintf("Reading file \"%s\"...", private$path))
      private$df <- read.csv(
          private$path,
          colClasses=mapColnamesDtypes,
          header=TRUE,
          sep=",",
          quote="\"",
          encoding="UTF-8",
          na.strings=""
      )
      # adjust row index to start at 1 instead of 0
      rownames(private$df) <- seq_len(nrow(private$df))

      # make sure the file contains no unknown columns
      dataFormatColIDs <- names(private$dataFormat)
      for (colID in names(private$df)) {
          if (!(colID %in% dataFormatColIDs)) {
              stop(sprintf("Unknown column '%s' in file \"%s\".", colID, private$path))
          }
      }
      
      # insert missing columns and reorder via reindexing and update dtypes
      dfNew <- private$df[, dataFormatColIDs]
      cols <- names(self$getDtypeMapping())
      dtypes <- self$getDtypeMapping()
      for (i in seq_along(cols)) {
          col <- cols[[i]]
          dtype <- dtypes[[i]]
          if (col %in% names(private$df)) {
              next
          }
          dfNew[[col]] <- dfNew[[col]] %>% type.convert(as.is=TRUE)
          dfNew[[col]] <- NA
      }
      private$df <- dfNew
    },
    #' @description
    #' Writes the data back to the data file.
    write = function() {
      write.csv(
          private$df,
          file=private$path,
          row.names=FALSE,
          sep=",",
          qmethod="escape",
          fileEncoding="UTF-8",
          na=""
      )
    },
    #' @description
    #' Get the data.
    #' @return The data frame.
    data = function() {
      private$df
    },
    #' @description
    #' Get the inconsistencies.
    #' @return The inconsistencies.
    getInconsistencies = function() {
      private$inconsistencies
    },
    #' @description
    #' Check the data for inconsistencies.
    #' @param re If TRUE, inconsistencies are checked.
    check = function(re = TRUE) {
      private$inconsistencies <- list()

      # check row consistency for each row individually
      for (rowID in rownames(private$df)){
          checkRow(.Object, rowID, re)
      }
    },
    #' @description
    #' Check the consistency of a single row.
    #' @param rowID The row ID.
    #' @param re If TRUE, inconsistencies are checked.
    checkRow = function(rowID, re = TRUE) {
      row <- private$df[rowID,]
      # consistency checks are not implemented in R for now
      # private$inconsistencies[[rowID]] <- checkRowConsistency(private$tid, row, re, rowID, private$path) # nolint # nolint: line_length_linter.
    }
  )
)