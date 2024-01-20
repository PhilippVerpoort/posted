source("R/posted/config.R")
source("R/posted/fields.R")
# source("R/posted/masking.R")
source("R/posted/path.R")
source("R/posted/read.R")
# source("R/posted/units.R")


read_fields <- function(variable) {
  ret <- list()
  
  for (database_id in names(databases)) {
    print(strsplit(variable, split="\\|"))
    fpath <- file.path(databases[[database_id]], 'fields', paste0(paste(unlist(strsplit(variable, split= "\\|")), collapse = '/'), '.yml'))
    if (file.exists(fpath)) {
      if (!file_test("-f", fpath)) {
        stop(paste("Expected YAML file, but not a file:", fpath))
      }


      fields <- read_yml_file(fpath)
      for (field_id in names(fields)) {

        field_specs <- fields[[field_id]]
        
        custom_field <- CustomFieldDefinition$new(field_id = field_id, field_specs = field_specs)
        ret <- c(ret, list(custom_field))
      }

      }
    }
    return(ret)
  }





# Define the TEBase class
TEBase <- R6::R6Class("TEBase",

  public = list(
    parent_variable = NULL,
    var_specs = NULL,
    initialize = function(parent_variable) {
      self$parent_variable <- parent_variable
      self$var_specs <- variables[grepl(paste0("^", parent_variable), names(variables))]
    }
  )
)

# Define the TEDF class, inheriting from TEBase
TEDF <- R6::R6Class("TEDF",
  inherit = TEBase,
  public = list(
    df = NULL,
    inconsistencies = NULL,
    file_path = NULL,
    fields = NULL,
    
    initialize = function(parent_variable, database_id = 'public', file_path = NULL, data = NULL) {
      super$initialize(parent_variable)
      self$df <- data
      self$inconsistencies <- list()
      self$file_path <- if (!is.null(data)) NULL else if (!is.null(file_path)) file_path else file.path(databases[[database_id]], 'tedfs', paste0(paste(unlist(strsplit(parent_variable, '\\|')), collapse = '/'), '.csv'))
      
      self$fields <- read_fields(self$parent_variable)
    },

    load = function() {
      if (is.null(self$df)) {
        self$read()
      } else {
        warning('TEDataFile is already loaded. Please execute .read() if you want to load from file again.')
      }
      return(self)
    },
    # read TEDataFile from CSV file
    read = function() {
      if (is.null(self$file_path)) {
        stop('Cannot read from file, as this TEDataFile object has been created from a dataframe.')
      }

      # read CSV file
      self$df <- read.csv(self$file_path, sep = ',', quote = '"', encoding = 'utf-8')
    
      # create data format and dtypes from base format
      data_format_cols <- names(base_format)
   
      data_format_cols <- c(setdiff(names(self$df), data_format_cols), data_format_cols)
      
      data_dtypes <- base_dtypes
     
      for (c in data_format_cols) {
        if (!(c %in% names(data_dtypes))) {
          data_dtypes[c] <- 'category'
        }
      }

      # add missing columns from data_format_cols to self$df
      missing_columns <- setdiff(data_format_cols, names(self$df))
      self$df[,missing_columns] <- NA
      df_new <- select(self$df, all_of(data_format_cols))

     
      for (col in names(data_dtypes)) {
        if (col %in% names(self$df)) {
          next
        }
  
        df_new[, col] <- as(self$df[, col], data_dtypes[col])
     
        df_new[, col] <- NA
      }
  
      self$df <- df_new

    },

    write = function() {
      if (is.null(self$file_path)) {
        stop('Cannot write to file, as this TEDataFile object has been created from a dataframe. Please first set a file path on this object.')
      }
      write.csv(self$df, self$file_path, row.names = FALSE, sep = ',', quote = '"', encoding = 'utf-8', na = '')
    },

    data = function() {
      return(self$df)
    },

    get_inconsistencies = function() {
      return(self$inconsistencies)
    },

    check = function(raise_exception = TRUE) {
      stop("Check not implemented yet")
      self$inconsistencies <- list()
      for (row_id in seq_along(rownames(self$df))) {
        self$check_row(row_id, raise_exception = raise_exception)
      }
    },

    check_row = function(row_id, raise_exception = TRUE) {
      stop("Check not implemented yet")
      row <- self$df[row_id, ]
      inconsistencies <- check_row_consistency(
        parent_variable = self$parent_variable,
        fields = self$fields,
        row = row,
        row_id = row_id,
        file_path = self$file_path,
        raise_exception = raise_exception
      )
      self$inconsistencies[[as.character(row_id)]] <- inconsistencies
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
# # TODO: Review this code and implement checks
# # Define the new_inconsistency function
# new_inconsistency <- function(raise_exception, ...) {

#   exception <- TEDFInconsistencyException$new(...)
#   if (raise_exception) {
#     stop(exception)
#   } else {
#     return(exception)
#   }
# }

# # Define the check_row_consistency function
# check_row_consistency <- function(parent_variable, fields, row, row_id, file_path, raise_exception) {
#   ret <- list()
#   ikwargs <- list(row_id = row_id, file_path = file_path, raise_exception = raise_exception)

#   # Check whether fields are among those defined in the technology specs
#   for (col_id in names(row)[!(names(row) %in% names(base_format))]) {
#     if (!any(col_id == sapply(fields, function(field) field$id))) {
#       ret <- c(ret, new_inconsistency(
#         message = paste("Invalid field ID:", col_id),
#         col_id = col_id,
#         ...,
#       ))
#     } else {
#       cell <- row[col_id]
#       field <- fields[[which(sapply(fields, function(f) f$id == col_id))]]
#       if (field$type == 'comment') {
#         next
#       }
#       if (field$type == 'cases' && cell == '#') {
#         ret <- c(ret, new_inconsistency(
#           message = paste("Case fields may not contain hash keys."),
#           col_id = col_id,
#           ...,
#         ))
#       }
#       if (field$type == 'components' && cell == '*') {
#         ret <- c(ret, new_inconsistency(
#           message = paste("Component fields may not contain asterisks."),
#           col_id = col_id,
#           ...,
#         ))
#       }
#       if (is.na(cell) || (field$is_coded && !field$is_allowed(cell))) {
#         ret <- c(ret, new_inconsistency(
#           message = paste("Invalid field value", cell),
#           col_id = col_id,
#           ...,
#         ))
#       }
#     }
#   }

#   # Period may not be empty
#   if (is.na(row['period'])) {
#     ret <- c(ret, new_inconsistency(
#       message = "Period cell is empty.",
#       col_id = 'period',
#       ...,
#     ))
#   } else if (!(is.numeric(row['period']) || is.character(row['period']) && (is.numeric(as.character(row['period'])) || row['period'] == '*'))) {
#     ret <- c(ret, new_inconsistency(
#       message = paste("Period is not a valid entry:", row['period']),
#       col_id = 'period',
#       ...,
#     ))
#   }

#   # Variable may not be empty
#   reported_subvariable <- row['reported_variable']
#   reference_subvariable <- row['reference_variable']
#   if (!is.character(reported_subvariable)) {
#     ret <- c(ret, new_inconsistency(
#       message = "Empty reported variable.",
#       col_id = 'reported_variable',
#       ...,
#     ))
#     return(ret)
#   }

#   # If the variable is not empty, check whether variable is among the allowed variables
#   reported_variable <- paste(parent_variable, '|', reported_subvariable, sep = '')
#   reference_variable <- paste(parent_variable, '|', reference_subvariable, sep = '')
#   if (!(reported_variable %in% names(variables))) {
#     ret <- c(ret, new_inconsistency(
#       message = paste("Invalid reported variable", reported_variable),
#       col_id = 'reported_variable',
#       ...,
#     ))
#     return(ret)
#   }
#   if (!(reference_variable %in% names(variables)) && 'default_reference' %in% variables[[reported_variable]]) {
#     ret <- c(ret, new_inconsistency(
#       message = paste("Invalid reference variable", reference_variable),
#       col_id = 'reference_variable',
#       ...,
#     ))
#     return(ret)
#   }

#   # Check that reported and reference units match variable definition
#   for (level in c('reported', 'reference')) {
#     if (is.na(reference_subvariable)) {
#       next
#     }
#     var_specs <- variables[[paste(level, '_variable', sep = '')]]
#     col_id <- paste(level, '_unit', sep = '')
#     unit <- row[col_id]
#     if (!('dimension' %in% names(var_specs))) {
#       if (!is.na(unit)) {
#         ret <- c(ret, new_inconsistency(
#           message = paste("Unexpected unit", unit, "for", col_id),
#           col_id = col_id,
#           ...,
#         ))
#       }
#       next
#     }
#     dimension <- var_specs$dimension
#     flow_id <- ifelse('flow_id' %in% names(var_specs), var_specs$flow_id, NULL)
#     allowed <- unit_allowed(unit, flow_id = flow_id, dimension = dimension)
#     if (!allowed) {
#       ret <- c(ret, new_inconsistency(
#         message = allowed$message,
#         col_id = col_id,
#         ...,
#       ))
#     }
#   }

#   return(ret)
# }

# is_float <- function(string) {
#   suppressWarnings(!is.na(as.numeric(string)))
# }


print("test0")
tedf <- TEDF$new("tech|ELH2")
print("initialized")

# print(tedf$parent_variable)
# print(tedf$file_path)
tedf$load()

print(tedf$df)
