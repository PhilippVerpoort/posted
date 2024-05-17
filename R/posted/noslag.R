source("R/posted/masking.R")
source("R/posted/tedf.R")
source("R/posted/units.R")
library(dplyr)
library(Deriv)



# get list of TEDFs potentially containing variable
collect_files <- function(parent_variable, include_databases = NULL) {
  #' collect_files
  #' Takes a parent variable and optional list of databases to include,
  #' checks for their existence, and collects files and directories based on the parent variable.
  #'
  #' @param parent_variable Character. Variable to collect files on.
  #' @param include_databases Optional list[Character]. List of Database IDs to collect files from.
  #'
  #' @return List of tuples. List of tuples containing the parent variable and the
  #' database ID for each file found in the specified directories.
  #'
  #' @examples
  #' # Example usage:
  #' collect_files("variable_name", c("db1", "db2"))
  #'
  #' @export

  if (parent_variable == "") {
    stop("Variable may not be empty.")
  }

  # check that the requested database to include can be found
  if (!is.null(include_databases)) {
    for (database_id in include_databases) {
      if (!(database_id %in% names(databases) && file.exists(databases[[database_id]]))) {
        stop(paste("Could not find database '", database_id, "'.", sep = ""))
      }
    }


  }

  ret <- list()
  for (database_id in names(databases)) {
    # skip ted paths not requested to include
    if (!is.null(include_databases) && !(database_id %in% include_databases)) next

    # find top-level file and directory
    top_path <- paste(unlist(strsplit(parent_variable, '\\|')), collapse = '/')
    top_file <- file.path(databases[[database_id]], 'tedfs', paste(top_path, '.csv', sep = ''))
    top_directory <- file.path(databases[[database_id]], 'tedfs', top_path)

    # add top-level file if it exists
    if (file.exists(top_file) && !dir.exists(top_file)) {
      ret <- c(ret, list(list(parent_variable, database_id)))
    }

    # add all files contained in top-level directory
    if (file.exists(top_directory) && dir.exists(top_directory)) {
      sub_files <- list.files(top_directory, pattern = '\\.csv$', full.names = TRUE, recursive = TRUE)
      for (sub_file in sub_files) {
        sub_variable <- paste(parent_variable, '|', tools::file_path_sans_ext(file.path(top_directory, sub_file)), sep = '')
        ret <- c(ret, list(list(sub_variable, database_id)))
      }
    }

    # loop over levels
    levels <- unlist(strsplit(parent_variable, '|'))
    for (l in seq_along(levels)) {
      # find top-level file and directory
      top_path <- paste(levels[seq_len(l)], collapse = '/')
      parent_file <- file.path(databases[[database_id]], 'tedfs', paste(top_path, '.csv', sep = ''))

      # add parent file if it exists
      if (file.exists(parent_file) && file.isFile(parent_file)) {
        parent_variable <- paste(levels[seq_len(l)], collapse = '|')
        ret <- c(ret, list(list(parent_variable, database_id)))
      }
    }
  }
  return(ret)
}

# normalise units
normalise_units <- function(df, level, var_units, var_flow_ids) {
  #' normalise_units
  #'
  #' Takes a DataFrame with reported or reference data, along with
  #' dictionaries mapping variable units and flow IDs, and normalizes the units of the variables in the
  #' DataFrame based on the provided mappings.
  #'
  #' @param df DataFrame. Dataframe to be normalized.
  #' @param level Character. Specifies whether the data should be normalized on the reported or reference values. Possible values are 'reported' or 'reference'.
  #' @param var_units List. Dictionary that maps a combination of parent variable and variable to its corresponding unit. The keys in the dictionary are in the format "{parent_variable}|{variable}", and the values are the units associated with that variable.
  #' @param var_flow_ids List. Dictionary that maps a combination of parent variable and variable to a specific flow ID. This flow ID is used for unit conversion in the \code{normalize_units} function.
  #'
  #' @return DataFrame. Normalized dataframe.
  #'
  #' @examples
  #' # Example usage:
  #' normalize_dataframe(df, "reported", var_units, var_flow_ids)
  #'
  #' @export

  prefix <- ifelse(level == 'reported', '', 'reference_')
  var_col_id <- paste0(prefix, 'variable')
  value_col_id <- paste0(prefix, 'value')
  unit_col_id <- paste0(prefix, 'unit')

  target_unit <- apply(df, 1, function(row) {
    tryCatch({
    ifelse((is.character(row[var_col_id]) && (!(row[var_col_id] == ""))),
            var_units[[paste0(row['parent_variable'], "|", row[var_col_id])]], NA)}, error=function(e){NA})
            })

  # TODO: make this try catch nicer
  target_flow_id <- apply(df, 1, function(row) {

    tryCatch({
    ifelse((is.character(row[var_col_id]) && (!(row[var_col_id] == ""))),
            var_flow_ids[[paste0(row['parent_variable'], "|", row[var_col_id])]], NA)}, error=function(e){NA}, warning=function(w){NA})
            })

  df_tmp <- df
  df_tmp$target_unit <- target_unit
  df_tmp$ target_flow_id <- target_flow_id


  # Apply unit conversion
  conv_factor <- apply(df_tmp, 1, function(row) {
    if (!is.na(row[value_col_id])) {

      unit_convert(row[[unit_col_id]], row[['target_unit']], row[['target_flow_id']])
    } else {
      return(1.0)
    }
  })

  # Update value column with conversion factor
  df_tmp[[value_col_id]] <- as.numeric(df_tmp[[value_col_id]]) * conv_factor

  # If level is 'reported', update uncertainty column with conversion factor
  if (level == 'reported') {
    df_tmp[['uncertainty']] <- df_tmp[['uncertainty']] * conv_factor
  }

  # Update unit column
  df_tmp[[unit_col_id]] <- df_tmp[['target_unit']]

  # Drop unnecessary columns and return
  return(df_tmp[, !names(df_tmp) %in% c('target_unit', 'target_flow_id')])
}

normalise_values <- function(df) {
  #' normalise_values
  #'
  #' Takes a DataFrame as input, normalizes the 'value' and 'uncertainty'
  #' columns by the reference value, and updates the 'reference_value' column accordingly.
  #'
  #' @param df DataFrame. Dataframe to be normalized.
  #'
  #' @return DataFrame. Returns a modified DataFrame where the 'value' column has been
  #' divided by the 'reference_value' column (or 1.0 if 'reference_value' is null), the 'uncertainty'
  #' column has been divided by the 'reference_value' column, and the 'reference_value' column has been
  #' replaced with 1.0 if it was not null.
  #'
  #' @examples
  #' # Example usage:
  #' normalized_df <- normalize_values(df)
  #'
  #' @export

  # Calculate reference value
  reference_value <- sapply(1:nrow(df), function(i) {
    if (!is.na(df$reference_value[i])) {
      df$reference_value[i]
    } else {
      1.0
    }
  })

  # Calculate new value, reference value and uncertainty
  value_new <- as.numeric(df$value) / reference_value
  uncertainty_new <- as.numeric(df$uncertainty) / reference_value
  reference_value_new <- sapply(1:nrow(df), function(i) {
    if (!is.na(df$reference_value[i])) {
      1.0
    } else {
      NA
    }
  })

  # Assign new values to dataframe and return
  df$value <- value_new
  df$uncertainty <- uncertainty_new
  df$reference_value <- reference_value_new
  return(df)
}

combine_units <- function(numerator, denominator) {
  #' Combine fraction of two units into an updated unit string
  #'
  #' @param numerator Character. Numerator of the fraction.
  #' @param denominator Character. Denominator of the fraction.
  #'
  #' @return Character. Updated unit string after simplification.
  #'
  #' @examples
  #' # Example usage:
  #' combine_units("m", "s")
  #'
  #' @export

  ret = Simplify(paste0("(", numerator, ")/(", denominator, ")"))
  # check if ret is numeric, e.g. dimensionless, if not return ret, else return the explicit quotient
  if (!grepl("^-?\\d+\\.?\\d*$", ret)) {
    return(ret)
  } else {
    if (grepl('/', denominator)) {
      return(paste0(numerator, "/(", denominator, ")"))
    } else {
      return(paste0(numerator, "/", denominator))
    }
}
}


#' @title DataSet
#'
#' @description This class provides methods to store, normalize, select, and aggregate DataSets.
#'
#' @param parent_variable Character. Variable to collect Data on.
#' @param include_databases Optional list[Character] | tuple[Character], optional. Databases to load from.
#' @param file_paths Optional list[Character], optional. Paths to load data from.
#' @param check_inconsistencies Logical, optional. Whether to check for inconsistencies.
#' @param data Optional DataFrame, optional. Specific data to include in the dataset.
#'
#' @section Attributes:
#' \describe{
#'   \item{data}{DataFrame. The dataset stored in the object.}
#' }
#'
#' @section Methods:
#' \describe{
#'   \item{\code{normalize()}}{Normalizes the dataset.}
#'   \item{\code{select()}}{Selects specific data from the dataset.}
#'   \item{\code{aggregate()}}{Aggregates the dataset.}
#' }
#'
#' @export

DataSet <- R6::R6Class("DataSet", inherit=TEBase,
  private = list(
    # Private attributes
    ..df = NULL,
    ..columns = NULL,
    ..fields = NULL,
    ..masks = NULL,

    # load TEDFs and compile into NSHASataSet
    ..load_files = function(include_databases, file_paths, check_inconsistencies) {
        files <- list()

        # collect TEDF and append to list
        collected_files = collect_files(parent_variable = private$..parent_variable, include_databases = include_databases)

        for (i in 1:length(collected_files)) {
          file_variable <- collected_files[[i]][[1]]
          file_database_id <- collected_files[[i]][[2]]
          files <- append(files, TEDF$new(parent_variable = file_variable, database_id = file_database_id ))
        }
        for (file_path in file_paths) {
          files <- apend(files, TEDF$new(parent_variable=private$..parent_variable, file_path=file_path))
        }

        # raise exception if no TEDF can be loaded
        if (length(files) == 0) {
          stop(sprintf("NO TEDF to load for variabele '%s'.", private$..parent_variable))
        }

        # get fields and masks from databases
        files_vars = as.vector(unique(sapply(files, function(f) f$parent_variable)))

        for (v in files_vars) {
          new_fields_comments = read_fields(v)
          new_fields = new_fields_comments$fields
          new_comments = new_fields_comments$comments
          for (col_id in names(c(new_fields, new_comments))) {


            if (col_id %in% private$..columns) {
              stop(sprintf("Cannot load TEDFs due to multiple columns with same ID defined : %s", col_id))
            }

          private$..fields <- c(new_fields, private$..fields)
          private$..columns <- c(new_fields, private$..columns, new_comments)
          private$..masks <- c(private$..masks, read_masks(v))
          }
        }

        # load all TEDFs: load from file, check for inconsistencies (if requested), expand cases and variables
        file_dfs <- list()
        for (f in files) {
          # load
          f$load()
          #check for inconsistencies
          if (check_inconsistencies) {
            f$check()
          }

          # obtain dataframe and insert column parent_variable
          df_tmp = f$data
          df_tmp <- df_tmp <- cbind(parent_variable = f$parent_variable, df_tmp)

          # append to dataframe list
          file_dfs <- append(file_dfs, df_tmp)
        }

        # compile dataset from the dataframes loaded from the individual files
        data <- do.call(cbind, file_dfs)

        # Query relevant variables
        data <- as.data.frame(data) %>% filter(parent_variable == private$..parent_variable)

        # Drop entries with unknown variables and warn
        for (var_type in c('variable', 'reference_variable')) {
          cond <- (!is.na(data[[var_type]]) & (data[[var_type]] != "") &
            apply(data, 1, function(row) {
              !paste(row[["parent_variable"]], row[[var_type]], sep = "|") %in% names(private$..var_specs)
            }))

          if (any(cond)) {
            warning(paste("Unknown", var_type, "so dropping rows:\n", data[cond, var_type]))
            data <- data[!cond, ]
          }
        }

        # return
        return(as.data.frame(data))
    },

    ..normalise = function(override) {
      if (is.null(override)) {
        override <- list()
      }

      # get overridden var specs
      var_flow_ids <- lapply(names(private$..var_specs), function(var_name) {
        var_specs <- private$..var_specs[[var_name]]
        if ('flow_id'%in% names(var_specs)) {
          return(var_specs[['flow_id']])
        } else {
          return(NULL)
        }
      })
      names(var_flow_ids) <- names(private$..var_specs)
      var_flow_ids <- var_flow_ids[order(names(var_flow_ids))]

      var_units <- lapply(names(private$..var_specs), function(var_name) {
        var_specs <- private$..var_specs[[var_name]]
          return(var_specs[['default_unit']])

      })
      names(var_units) <- names(private$..var_specs)
      var_units <- Filter(function(x) !is.null(x), var_units)

      # Get the names common to both var_units and override
      common_names <- intersect(names(var_units), names(override))

      # Replace values in var_units with values from override for common names
      var_units[common_names] <- override[common_names]
      var_units <- var_units[order(names(var_units))]

      # normalise reference units, normalise reference values, and normalise reported units
      normalised <- private$..df %>%
              normalise_units(level = 'reference', var_units = var_units, var_flow_ids = var_flow_ids) %>%
              normalise_values() %>%
              normalise_units(level = 'reported', var_units = var_units, var_flow_ids = var_flow_ids)

      # return normalised data and variable units
      return(list(normalised=normalised, var_units=var_units))
    },


    ..select = function(override, drop_singular_fields, extrapolate_period, ...) {
      field_vals_select <- list(...)

      # start from normalised data
      normalised_units <- private$..normalise(override)
      selected <- normalised_units$normalised
      var_units <- normalised_units$var_units

      # drop unit columns and reference falue column
      selected <- selected %>% select( -unit, -reference_unit, -reference_value)

      # drop columns containing comments and uncertaindty field (which is currently unsupported)
      comment_columns <- Filter(function(col_id) {(private$..columns[[col_id]]$col_type == "comment")}, names(private$..columns))
      selected <- selected %>%
        select(-uncertainty,  -any_of(comment_columns))

      reference_variable_temp <- selected$reference_variable

      # add parent variable as prefix to other variable columns
      selected <- mutate(selected, variable = paste(parent_variable, variable, sep = "|"))
      selected <- mutate(selected, reference_variable = ifelse((is.na(reference_variable_temp) | (reference_variable_temp =="")), NA, paste(parent_variable, reference_variable_temp, sep = "|")))
      selected <- select(selected, -parent_variable)

      # raise exception if fields listed in arguments that are uknown
      for (field_id in names(field_vals_select)) {

        if (!(field_id %in% names(private$..fields))) {
          stop(paste("Field '", field_id, "' does not exist and cannot be used for selection.", sep = ""))
        }
      }

      # order fields for selection: period must be expanded last due to the interpolation
      fields_select <- list()
      for (col_id in names(field_vals_select)) {
        fields_select[[col_id]] <- private$..fields[[col_id]]
      }

      for (col_id in names(private$..fields)) {
        if (!(col_id %in% c('period', field_vals_select))) {
          fields_select[[col_id]] <- private$..fields[[col_id]]
        }
      }
      fields_select[['period']] <- private$..fields[['period']]

      # select and expand fields
      for (col_id in names(fields_select)) {
        field <- fields_select[[col_id]]
        field_vals <- if (col_id %in% names(field_vals_select)) { field_vals_select[[col_id]]} else {NULL}
        selected <- field$select_and_expand(selected, col_id, field_vals, extrapolate_period=extrapolate_period)
      }

      # drop custom fields with only one value if specified in method argument
      df_cols <- sapply(names(private$..fields), function(col_id) {
          field <- private$..fields[[col_id]]

          if (inherits(field, "CustomFieldDefinition")) {
            return(col_id)
          } else {
            return(NULL)
          }
        })
      if (drop_singular_fields) {
        columns_to_drop <- c(
          sapply(names(private$..fields), function(col_id) {
            field <- private$..fields[[col_id]]
            if (inherits(field, "CustomFieldDefinition") && n_distinct(selected[[col_id]]) < 2) {
              return(col_id)
            } else {
              return(NULL)
            }
          })
        )
        names(columns_to_drop )<- NULL
        columns_to_drop <- unlist(unique( Filter(Negate(is.null), columns_to_drop)))
        selected <- selected %>%
        select(-any_of(columns_to_drop))

      }
      # apply mappings
      selected <- private$..apply_mappings(selected, var_units)

      # drop rows with failed mappings
      selected <- selected[!is.na(selected$value), , drop = FALSE]

      # get map of variable references
      var_references <- selected %>%
                  select(variable, reference_variable) %>%
                  distinct() %>%
                  mutate(variable = as.character(variable)) %>%
                  distinct()

      # Check for multiple reference variables per reported variable
      if (duplicated(list(var_references$variable))) {
        stop("Multiple reference variables per reported variable found")
      }
      var_references <- setNames(var_references$reference_variable, var_references$variable)

      # Remove 'reference_variable' column
      selected <- selected %>%
                    select(-reference_variable)
      selected <- selected[order(selected$source),]

      # strip off unit variants
      var_units <- lapply(var_units, function(unit) {
        unlist(strsplit(unit, ";"))[1]
      })

      # return
      selected_var_units_and_references <- list(selected=selected, var_units=var_units, var_references=var_references)
      return(selected_var_units_and_references)
    },

    # apply mappings between entry types
    ..apply_mappings = function(expanded, var_units) {

      #list of columns to group by
      group_cols <- setdiff(names(expanded), c('variable', 'reference_variable', 'value'))

      # Perform group_by and do not drop NA values
      grouped <- expanded %>% group_split(across(all_of(group_cols)), .drop = FALSE)

      # Create return list
      ret <- list()

      # loop over groups
      for (i in seq_along(grouped)) {
        # get rows in group
        rows <- grouped[[i]]

        # 1. convert FLH to OCF
        cond <- endsWith(rows$variable, '|FLH')
        if (any(cond)) {

          # Multiply 'value' by conversion factor
          rows$value[cond] <- rows$value[cond] * apply(rows[cond,], 1, function(row) {
            return(unit_convert(var_units[[row[['variable']]]], 'a'))})

          # Replace '|FLH' with '|OCF' in 'variable'
          rows$variable[cond] <- gsub("|FLH", "|OCF", rows$variable[cond], fixed = TRUE)
        }

          # 2. convert OPEX Fixed Relative to OPEX Fixed
          cond <- endsWith(rows$variable, '|OPEX Fixed Relative')
          if (any(cond)) {
          # Define a function to calculate the conversion factor
          calculate_conversion <- function(row) {
            variable <- gsub("|OPEX Fixed Relative", "|CAPEX", row[['variable']], fixed = TRUE)
            var_units_reference <- var_units[[gsub("|OPEX Fixed Relative", "|OPEX Fixed", row[['variable']], fixed = TRUE)]]
            var_units_dividend <- paste(var_units[[variable]], '/a', sep = "")
            filter_condition <- rows$variable == variable
            var_units_df <-  filter(rows,  filter_condition)

            return(unit_convert(var_units[row['variable']], 'dimensionless') *
                    unit_convert(var_units_dividend,var_units_reference) *
                    var_units_df$value[1])
          }

          # Calculate the conversion factor and update 'value' for rows satisfying the condition
          rows$value[cond] <- rows$value[cond] * apply( rows[cond,], 1, calculate_conversion)
          # Replace '|OPEX Fixed Relative' with '|OPEX Fixed' in 'variable'
          rows$variable[cond] <- gsub("|OPEX Fixed Relative", "|OPEX Fixed", rows$variable[cond], fixed = TRUE)

          # Assign 'reference_variable' based on modified 'variable'
          rows$reference_variable[cond] <- apply(rows[cond,],1, function(row) {
            var_units_variable <- gsub("|OPEX Fixed", "|CAPEX", row[['variable']], fixed = TRUE)
            filter_condition <- rows$variable == var_units_variable
            var_units_df <-  filter(rows,  filter_condition)
            if (nrow(var_units_df) > 0) {
              return(var_units_df$reference_variable[1])
            } else {
              return(NA)
            }
          })

          # Check if there are rows with null 'value' after the operation
          if (any(cond & is.na(rows$value))) {
            warning("No CAPEX value matching an OPEX Fixed Relative value found.")
          }
        }

        # 3. convert OPEX Fixed Specific to OPEX Fixed
        cond <- endsWith(rows$variable, "|OPEX Fixed Specific")
        if (any(cond)) {

          # Define a function to calculate the conversion factor
          calculate_conversion <- function(row) {
            unit_conversion_1_from <- paste(var_units[[row[['variable']]]], '/a', sep = "")
            unit_conversion_1_to<- gsub("|OPEX Fixed Specific", "|OPEX Fixed", row[['variable']], fixed = TRUE)

            unit_conversion_2_from <- paste(var_units[[row['reference_variable']]], '/a', sep = "")
            unit_conversion_2_to <- var_units[[gsub("(Input|Output)", "\\1 Capacity", row['reference_variable'], perl=TRUE)]]
            unit_conversion_2_flow_type <- if ('flow_id' %in% private$..var_specs[[row['reference_variable']]]) {
              private$..var_specs[[row['reference_variable']]]$flow_id
            } else {
              NaN
            }
            var_units_df <- subset(rows, variable == gsub("|OPEX Fixed Specific", "|OCF", row['variable'], fixed = TRUE))

            if (nrow(var_units_df) > 0) {
              return(unit_convert(unit_conversion_1_from, unit_conversion_1_to) /
                    unit_convert(unit_conversion_2_from, unit_conversion_2_to, unit_conversion_2_flow_type) *
                    var_units_df$value[1])
            } else {
              return(NA)
            }
          }

          # Calculate the conversion factor and update 'value' for rows satisfying the condition
          rows$value[cond] <- rows$value[cond] * apply(rows[cond,],1,calculate_conversion)

          # Replace '|OPEX Fixed Specific' with '|OPEX Fixed' in 'variable'
          rows$variable[cond] <- gsub("|OPEX Fixed Specific", "|OPEX Fixed", rows$variable[cond], fixed = TRUE)

          # Update 'reference_variable' by replacing 'Input' or 'Output' with 'Input Capacity' or 'Output Capacity'
          rows$reference_variable[cond] <- gsub('(Input|Output)', '\\1 Capacity', rows$reference_variable[cond], perl = TRUE)

          # Check if there are rows with null 'value' after the operation
          if (any(cond & is.na(rows$value))) {
            warning("No OCF value matching an OPEX Fixed Specific value found.")
          }
        }

        # 4. convert efficiencies (Output over Input) to demands (Input over Output)
        cond1 <- grepl("\\|Output(?: Capacity)?\\|", rows$variable)
        if (any(!is.na(rows$reference_variable))) {
          cond2 <- grepl("\\|Input(?: Capacity)?\\|", rows$reference_variable)
                        } else {
          cond2 <- FALSE}
        cond <- cond1 & cond2

        if (any(cond)) {
          rows$value[cond] <- 1.0 / rows$value[cond]
          rows$variable_new <- NaN
          rows$variable_new[cond] <- rows$reference_variable[cond]
          rows$reference_variable[cond] <- rows$variable[cond]
          rows$variable[cond] <- rows$variable_new[cond]
          rows <- rows[!names(rows) %in% c("variable_new")]
        }

        # 5. convert all references to primary output
        if (any(!is.na(rows$reference_variable))) {
          cond1 <- (grepl("\\|Output(?: Capacity)?\\|", rows$reference_variable) | grepl("\\|Input(?: Capacity)?\\|", rows$reference_variable))
        } else {
          cond1 <- FALSE
        }
        cond2 <- unlist(lapply(rows$variable, function(var) {
          'default_reference' %in% names(private$..var_specs[[var]])
          }))

        # define helper function for cond3
        get_default_reference <- function(var) {
          if ('default_reference' %in% names(self$var_specs[[var]])) {
            return(self$var_specs[[var]]$default_reference)
          } else {
            return(NA)
          }
        }
        cond3  <- lapply(rows$variable, get_default_reference) != rows[['reference_variable']]

        cond <- cond1 & cond2 & cond3
        if (any(cond)) {
          regex_find <- "\\|(Input|Output)(?: Capacity)?\\|"
          regex_repl <- "|\\1|"
          rows$reference_variable_new <- NaN
          rows$reference_variable_new[cond] <- sapply(rows$variable[cond], function(var) {

            private$..var_specs[[var]]$default_reference
          })
          calculate_conversion <- function(row) {
            reference_variable_new <- gsub(regex_find, regex_repl, row['reference_variable_new'][[1]])
            if(grepl("Capacity", row['reference_variable'][[1]])) {
              if (grepl( "/a", var_units[[row['reference_variable_new'][[1]]]])) {
                row_reference_variable_new <- sub("/a", "", var_units[[row['reference_variable_new'][[1]]]])
              } else {
                row_reference_variable_new <- paste0("a*", var_units[[row['reference_variable_new'][[1]]]])

              }
            } else {
              row_reference_variable_new <- var_units[[row['reference_variable'][[1]]]]
            }

            var_units_reference_variable_new <- var_units[[reference_variable_new]]
            tail_reference_variable_new <-  tail(strsplit(row['reference_variable_new'][1], "\\|")[[1]], 1)

            reference_variable <- gsub(regex_find, regex_repl, row['reference_variable'][[1]] )
            if(grepl("Capacity", row['reference_variable'][[1]])) {
              if (grepl( "/a",var_units[[row['reference_variable'][[1]]]])) {
                row_reference_variable <- sub("/a", "", var_units[[row['reference_variable'][[1]]]])
              } else {
                row_reference_variable<- paste0("a*", var_units[[row['reference_variable'][[1]]]])

              }
            } else {
              row_reference_variable <- var_units[[row['reference_variable'][[1]]]]
            }

            var_units_reference_variable <- var_units[[reference_variable]]
            tail_reference_variable <-  tail(strsplit(row['reference_variable'][1], "\\|")[[1]], 1)

            rows_cond1 <-  rows$variable == reference_variable
            rows_cond2 <-  rows$reference_variable == reference_variable_new
            var_units_df <-  filter(rows, rows_cond2 & rows_cond2)

            return(unit_convert(row_reference_variable_new, var_units_reference_variable_new, tail_reference_variable_new) /
                        unit_convert(row_reference_variable, var_units_reference_variable, tail_reference_variable) *
                            var_units_df$value[1])

            }
          # Calculate the conversion factor and update 'value' for rows satisfying the condition
          rows$value[cond] <- rows$value[cond] * apply( rows[cond,], 1, calculate_conversion)

          rows$reference_variable[cond] <- rows$reference_variable_new[cond]
          rows <- rows[!names(rows) %in% c("reference_variable_new")]
          if (any(cond & is.na(rows$value))) {
            warning(paste("No appropriate mapping found to convert row reference to primary output:",
                          rows[cond & is.na(rows$value), ]))

          }
        }

        # add to return list
        ret <- append(ret, list(rows))
      }
      # convert return list to dataframe and return
      return(bind_rows(ret))
    },

  # clean up: sort columns and rows, round values, insert units
  ..cleanup = function(df, var_units) {
      # Sort columns and rows
      df_cols <- sapply(names(private$..fields), function(col_id) {
          field <- private$..fields[[col_id]]

          if (inherits(field, "CustomFieldDefinition")) {
            return(col_id)
          } else {
            return(NULL)
          }
        })
      names(df_cols) <- NULL
      cols_sorted <- unlist(unique(c(df_cols, 'source', 'variable', 'reference_variable', 'region', 'period', 'value')))
      cols_sorted <- cols_sorted[cols_sorted %in% names(df)]
      df <- select(df, any_of(cols_sorted))
      cols_sorted <- cols_sorted[-which(cols_sorted == "value")]
      df <- df[do.call(order, df[cols_sorted]), ]

      # Round values
      df$value <- ifelse(is.na(df$value), df$value, signif(df$value, digits = 4))

      # Insert column containing units
      df <- as.data.frame(append(df, list(unit=NaN), after = match("value", names(df))-1))
      if ("reference_variable" %in% colnames(df)) {
        df$unit <- apply(df, 1, function(row) {
          if (!is.na(row["reference_variable"])) {
            combine_units(var_units[[row["variable"]]], var_units[[row["reference_variable"]]])
          } else {
            var_units[row["variable"]]
          }
        })
      } else {
        df$unit <- var_units[df$variable]
      }
      return(df)
    },

  ),

  public = list(

    #' initialise
    #'
    #' Initialise parent class and fields, load data from specified databases and files'''
    initialize = function(parent_variable,
                           include_databases = NULL,
                           file_paths = NULL,
                           check_inconsistencies = FALSE,
                           data = NULL) {
      super$initialize(parent_variable)

      # initialise fields
      private$..df <- NULL
      private$..columns <- base_columns
      private$..fields <- lapply(private$..columns, function(field) {
        if (inherits(field, "AbstractFieldDefinition")) field else NULL
      })
      private$..fields <- Filter(Negate(is.null), private$..fields)
      private$..masks <- list()

      # Load data if provided, otherwise load from TEDataFiles
      if (!is.null(data)) {
        private$..df <- data.frame(data)
      } else {
        # read TEDataFiles and combine into dataset
        if (!is.null(include_databases)) {
            include_databases <- list(include_databases)
        } else {
            include_databases <- list(names(databases))
        }

        # in no file paths are given, set to empty list
        if (is.null(file_paths)){
            file_paths <- list()
        }
        private$..df <- data.frame(private$..load_files(include_databases, file_paths, check_inconsistencies))
      }
    },

    #' @description Normalize data: default reference units, reference value equal to 1.0, default reported units
    #'
    #' @param override Optional list[Character]. Dictionary with key, value pairs of variables to override.
    #' @param inplace Logical, optional. Whether to do the normalization in place.
    #'
    #' @return DataFrame. If \code{inplace} is \code{FALSE}, returns normalized dataframe.
    #'
    #' @examples
    #' # Example usage:
    #' dataset$normalize(override = list("variable1" = "value1"), inplace = FALSE)
    #'
    #' @export
    normalise = function(override = NULL, inplace = FALSE) {
      normalised <- private$..normalise(override)
      if (inplace) {
        private$..df <- data.frame(normalised$normalised)
      } else {
        return(data.frame(normalised$normalised))
      }
    },

    #' @description Select desired data from the dataframe
    #'
    #' @param override Optional list[Character]. Dictionary with key, value pairs of variables to override.
    #' @param drop_singular_fields Logical, optional. If \code{TRUE}, drop custom fields with only one value.
    #' @param extrapolate_period Logical, optional. If \code{TRUE}, extrapolate values if no value for this period is given.
    #' @param ... IDs of values to select.
    #'
    #' @return DataFrame. DataFrame with selected values.
    #'
    #' @examples
    #' # Example usage:
    #' dataset$select(override = list("variable1" = "value1"), drop_singular_fields = TRUE, extrapolate_period = FALSE, field1 = "value1")
    #'
    #' @export
    select = function(override = NULL,
                      drop_singular_fields = TRUE,
                      extrapolate_period = TRUE,
                      ...) {
      selected_var_units_and_references <- private$..select(override, drop_singular_fields, extrapolate_period, ...)
      selected <- selected_var_units_and_references$selected
      var_units <- selected_var_units_and_references$var_units
      var_references <- selected_var_units_and_references$var_references




      # Inserting a new column 'reference_variable' at a specific position in the data frame

      selected <- as.data.frame(append(selected, list(reference_variable=NA), after=match("variable", names(selected))-1))


      # Mapping values from 'var_references' to the 'reference_variable' column based on 'variable'
      selected$reference_variable <- var_references[selected$variable]

      result <- private$..cleanup(selected, var_units)
      return(result)
    },

    #' @description Aggregates data based on specified parameters, applies masks,
    #' and cleans up the resulting DataFrame.
    #'
    #' @param override Optional list[Character]. Dictionary with key, value pairs of variables to override.
    #' @param drop_singular_fields Logical, optional. If \code{TRUE}, drop custom fields with only one value.
    #' @param extrapolate_period Logical, optional. If \code{TRUE}, extrapolate values if no value for this period is given.
    #' @param agg Optional Character | list[Character] | tuple[Character]. Specifies which fields to aggregate over.
    #' @param masks Optional list[Mask]. Specifies a list of Mask objects that will be applied to the data during aggregation. These masks can be used to filter or weight the data based on certain conditions defined in the Mask objects.
    #' @param masks_database Logical, optional. Determines whether to include masks from databases in the aggregation process. If \code{TRUE}, masks from databases will be included along with any masks provided as function arguments. If \code{FALSE}, only the masks provided as function arguments will be applied.
    #'
    #' @return DataFrame. The \code{aggregate} method returns a pandas DataFrame that has been cleaned up and aggregated based on the specified parameters and input data. The method performs aggregation over component fields and case fields, applies weights based on masks, drops rows with NaN weights, aggregates with weights, inserts reference variables, sorts columns and rows, rounds values, and inserts units before returning the final cleaned and aggregated DataFrame.
    #'
    #' @examples
    #' # Example usage:
    #' dataset$aggregate(override = list("variable1" = "value1"), drop_singular_fields = TRUE, extrapolate_period = FALSE, agg = "field", masks = list(mask1, mask2), masks_database = TRUE)
    #'
    #' @export
    aggregate = function(override=NULL,
            drop_singular_fields=TRUE,
            extrapolate_period=TRUE,
            agg=NULL,
            masks=NULL,
            masks_database=TRUE,
            ... ) {
      # get selection
      selected_var_units_and_references <- private$..select(override, extrapolate_period, drop_singular_fields, ...)
      selected <- selected_var_units_and_references[[1]]
      var_units <- selected_var_units_and_references[[2]]
      var_references <- selected_var_units_and_references[[3]]

      # compile masks from databases and function argument into one list
      if (!is.null(masks) && any(!sapply(masks, function(m) inherits(m, "Mask")))) {
        stop("Function argument 'masks' must contain a list of posted.masking.Mask objects.")
      }
      masks <- c(if (masks_database) {private$..masks} else {list()}, if(!is.null(masks)) {masks} else {list()} )

      # aggregation
      component_fields <- names(Filter(function(field) field$field_type == 'component', private$..fields))
      if (is.null(agg)) {
        agg <- c(component_fields, 'source')
      } else {
        if (!is.list(agg)) {
          agg <- list(agg)
        }
        for (a in agg) {
          if (!is.character(a)) {
            stop(sprintf("Field ID in argument 'agg' must be a string but found: %s", a))
          }
          if (!any(a %in% names(private$..fields))) {
            stop(sprintf("Field ID in argument 'agg' is not a valid field: %s", a))
          }
        }
      }

      # aggregate over component fields
      group_cols <- subset(names(selected), !(names(selected) == 'value' | (names(selected) %in% agg & names(selected) %in% component_fields)))
      aggregated <- selected %>%
          group_by_at(vars(group_cols)) %>%
          summarise(value = sum(value), .groups = 'drop') %>%
          ungroup()

      # aggregate over cases fields
      group_cols <- subset(names(selected), !(names(selected) == 'value' | (names(selected) %in% agg)))
      grouped <- aggregated %>% group_split(across(all_of(group_cols)), .drop = FALSE)

      ret <- list()
      for (i in seq_along(grouped)) {
        rows <- grouped[[i]]
        # set default weights to 1.0
        rows$weight <- 1.0

        # update weights by applying masks
        for (mask in masks) {
          if (mask$matches(rows)) {
            rows$weight <- rows$weight * mask$get_weights(rows)
          }
        }

        # Drop all rows with missing values in the 'weight' column
        rows <- rows[!is.na(rows$weight), , drop = FALSE]

        if (!is_empty(rows)) {
          # Aggregate with weighted average
          out <- rows %>%
            group_by_at(vars(group_cols)) %>%
            summarise(value = weighted.mean(value, w = weight), .groups ='drop') %>%
            ungroup()
          # Add to return list

          ret <- append(ret, list(out))
        }
      }
      aggregated <- bind_rows(ret)

      # insert reference variable
      unique_vars <- unique(aggregated$variable)

      # Filter out NULL and NA values and extract corresponding var_references
      var_ref_unique <- unique(lapply(unique_vars, function(var) ifelse(!is.null(var_references[var]), var_references[var], NULL)))
      var_ref_unique <- Filter(function(x) !is.null(x) & !is.na(x), var_ref_unique)

      agg_append <- list()
      for (ref_var in var_ref_unique) {
        df <- data.frame(variable = ref_var, value = 1.0)
        col_ids <- names(private$..fields)[names(private$..fields) %in% names(aggregated)]
        col_ids <- setdiff(col_ids, names(df))
        for (col_id in col_ids) {
          df[col_id] <- '*'
        }
        agg_append <- append(agg_append, list(df))
      }

      if (length(agg_append) > 0) {
        agg_append <- bind_rows(agg_append)
        agg_append <- agg_append[order(rownames(agg_append)), ]  # Sort rows
        for (col_id in names(private$..fields)) {
          field <- private$..fields[[col_id]]
          if (!(col_id %in% names(aggregated))) {
            next
          }
          unique_values <- unique(aggregated[[col_id]])
          agg_append <- field$select_and_expand(agg_append,col_id, as.list(unique(aggregated[[col_id]])))
        }
      } else {
        agg_append <- NULL
      }
    # convert return list to dataframe, reset index and clean up
    return(private$..cleanup(bind_rows(list(aggregated, agg_append)), var_units))

    }
     ),
  active = list(
    # access dataframe
    data = function(df) {
      if (missing(df)) return(private$..df)
      else private$..df <- df
    }
  )



)


