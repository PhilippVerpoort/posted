# source("R/posted/config.R")
source("R/posted/columns.R")
# source("R/posted/path.R")
# source("R/posted/units.R")



TEBase <- R6::R6Class("TEBase",
  private = list(
    ..parent_variable = NULL,
    ..var_specs = NULL
  ),
  public = list(
    # initialise
    initialize = function(parent_variable) {
      # set variable from function argument
      private$..parent_variable <- parent_variable

      # set technology specifications
      var_specs <- lapply(names(variables), function(name) {
        if (startsWith(name, private$..parent_variable)) {
          return(variables[[name]])
        } else {
          return(NULL)
        }
      })
      names(var_specs) <- names(variables)
      var_specs  <- Filter(function(x) !is.null(x), var_specs)
      private$..var_specs <-  var_specs
    }
  ),
  active = list(
    parent_variable = function() {
      return(private$..parent_variable)
    }
  )
)

# Define the TEDF class, inheriting from TEBase
TEDF <- R6::R6Class("TEDF", inherit = TEBase,
  # initialise private fields
  private = list(
    ..df = NULL,
    ..inconsistencies = NULL,
    ..file_path = NULL,
    ..fields = NULL,
    ..columns = NULL

  ),
  public = list(
    # inititalise
    initialize = function(parent_variable, database_id = 'public', file_path = NULL, data = NULL) {
      super$initialize(parent_variable)

      # initialise object fields
      private$..df <- data
      private$..inconsistencies <- list()
      private$..file_path <- if (!is.null(data)) NULL else if (!is.null(file_path)) file_path else file.path(databases[[database_id]], 'tedfs', paste0(paste(unlist(strsplit(parent_variable, '\\|')), collapse = '/'), '.csv'))
      fields_comments <- read_fields(private$..parent_variable)
      private$..fields <- fields_comments$fields
      comments <- fields_comments$comments
      private$..columns <- c( private$..fields, base_columns, comments)

      # reverse order
      reversed_names <- rev(names(private$..columns))
      reversed_values <- rev(private$..columns)

       # delete duplicates
      unique_names <- reversed_names[!duplicated(reversed_names)]
      unique_columns <- reversed_values[match(unique_names, reversed_names)]
      private$..columns <- rev(unique_columns)
    },

    # load TEDataFile (only if it has not been read yet)
    load = function() {
      if (is.null(private$..df)) {
        self$read()
      } else {
        warning('TEDataFile is already loaded. Please execute .read() if you want to load from file again.')
      }
      return(self)
    },

    # read TEDataFile from CSV file
    read = function() {
      if (is.null(private$..file_path)) {
        stop('Cannot read from file, as this TEDataFile object has been created from a dataframe.')
      }

      # read CSV file
      private$..df <- read.csv(private$..file_path, sep = ',', quote = '"', encoding = 'utf-8')

      # Check column IDs match base columns and fields
      if (!all(colnames(private$..df) %in% names(private$..columns)  )) {
        stop(paste("Column IDs used in CSV file do not match columns definition: ",
                  paste(colnames(private$..df), collapse = ", ")))
      }

      # insert missing columns and order via reindexing
      missing_columns <- setdiff(names(private$..columns), names(private$..df))


      for(col_id in missing_columns) {
        col <- private$..columns[[col_id]]
        mode_type  =  private$..columns[[col_id]]$dtype
        if(mode_type == "int") {
        private$..df[,col_id] <- vector(mode = "double")
        } else if((mode_type =="str")| mode_type=="category" ) {
          private$..df[,col_id] <- vector(mode = "character")
        } else {
          stop("dtype of column not allowed")
        }
        private$..df[,col_id] <- col$default
        }

      df_new <- select(private$..df, all_of(names(private$..columns)))
      private$..df <- df_new

    },

    # TODO: has to be checked if it works properly
    # write TEDF to CSV file
    write = function() {
      if (is.null(private$..file_path)) {
        stop('Cannot write to file, as this TEDataFile object has been created from a dataframe. Please first set a file path on this object.')
      }
      write.csv(private$..df, private$..file_path, row.names = FALSE, sep = ',', quote = '"', encoding = 'utf-8', na = '')
    },

    # check that TEDF is consistent
    check = function(raise_exception = TRUE) {
      private$..inconsistencies <- list()

      # check row consistency for each row individually
      for (row_id in seq_along(rownames(private$..df))) {
        self$check_row(row_id, raise_exception = raise_exception)
      }
    },

    # TOD implement check_row function
    # check that row in TEDF is consistent and return all inconsistencies found for row
    check_row = function(row_id, raise_exception = TRUE) {
      stop("Check_row function not implemented yet")
    }


  ),
  active = list(
    file_path = function(file_path) {
      if (missing(file_path)) return(private$..file_path)
      else private$..file_path <- file_path
    },
    data = function() {
      return(private$..df)
    },
    inconistencies = function() {
      return(private$..inconsistencies)
    }
  )

)

# Define the TEDFInconsistencyException class
TEDFInconsistencyException <- R6::R6Class("TEDFInconsistencyException",
  inherit = stop,
  public = list(
    initialize = function(message = "Inconsistency detected", row_id = NULL, col_id = NULL, file_path = NULL) {
      self$message <- message
      self$row_id <- row_id
      self$col_id <- col_id
      self$file_path <- file_path
      message_tokens <- c()
      if (!is.null(file_path)) {
        message_tokens <- c(message_tokens, paste("file", file_path))
      }
      if (!is.null(row_id)) {
        message_tokens <- c(message_tokens, paste("line", row_id))
      }
      if (!is.null(col_id)) {
        message_tokens <- c(message_tokens, paste("in column", col_id))
      }
      exception_message <- message
      if (length(message_tokens) > 0) {
        exception_message <- paste(exception_message, paste(message_tokens, collapse = ", "), sep = "\n    ")
      }
      stop(exception_message)
    }
  )
)