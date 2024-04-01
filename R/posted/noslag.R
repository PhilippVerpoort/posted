source("R/posted/masking.R")
source("R/posted/tedf.R")
source("R/posted/units.R")
library(dplyr)



# get list of TEDFs potentially containing variable
collect_files <- function(parent_variable, include_databases = NULL) {
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
    print(top_path)
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

# Define normalise_units function
normalise_units <- function(df, level, var_units, var_flow_ids) {
  print("normalise_units")
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
      unit_convert(row[[unit_col_id]], row['target_unit'], row['target_flow_id'])
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

  # Drop unnecessary columns
  df_tmp <- df_tmp[, !names(df_tmp) %in% c('target_unit', 'target_flow_id')]

  return(df_tmp)
}

normalise_values <- function(df) {
  print("normalise_values")
  # Calculate reference value
  reference_value <- sapply(1:nrow(df), function(i) {
    if (!is.na(df$reference_value[i])) {
      df$reference_value[i]
    } else {
      1.0
    }
  })

  # Calculate new value
  value_new <- as.numeric(df$value) / reference_value

  # Calculate new uncertainty
  uncertainty_new <- as.numeric(df$uncertainty) / reference_value

  # Calculate new reference value
  reference_value_new <- sapply(1:nrow(df), function(i) {
    if (!is.na(df$reference_value[i])) {
      1.0
    } else {
      NA
    }
  })

  # Assign new values to dataframe
  df$value <- value_new
  df$uncertainty <- uncertainty_new
  df$reference_value <- reference_value_new

  return(df)
}



# Define the R6 class
DataSet <- R6::R6Class("DataSet", inherit=TEBase,
  private = list(
    # Private attributes
    ..df = NULL,
    ..columns = NULL,
    ..fields = NULL,
    ..masks = NULL,

    # Internal method for loading TEDFs
    ..load_files = function(include_databases, file_paths, check_inconsistencies) {
        files <- list()
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
          # private$..masks <- c(private$..masks, read_masks(v))
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

    # Internal method for normalizing data
    ..normalise = function(override) {
      if (is.null(override)) {
        override <- list()
      }

      var_flow_ids <- lapply(names(private$..var_specs), function(var_name) {
        var_specs <- private$..var_specs[[var_name]]
        if ('flow_id'%in% names(var_specs)) {
          return(var_specs[['flow_id']])
        } else {
          return(NULL)
        }
      })
      names(var_flow_ids) <- names(private$..var_specs)

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
      print("call normalise_units")

      normalised <- private$..df %>%
              normalise_units(level = 'reference', var_units = var_units, var_flow_ids = var_flow_ids) %>%
              normalise_values() %>%
              normalise_units(level = 'reported', var_units = var_units, var_flow_ids = var_flow_ids)
      return(list(normalised=normalised, var_units=var_units))
    },

    # Internal method for selecting data
    ..select = function(override, drop_singular_fields, extrapolate_period, ...) {
      field_vals_select <- list(...)
      print("select")
      print(field_vals_select)
      print(override)
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

      # add parent variable as prefix to other variable columns
      selected <- mutate(selected, variable = paste(parent_variable, variable, sep = "|"))
      selected <- mutate(selected, reference_variable = paste(parent_variable, reference_variable, sep = "|"))
      selected <- select(selected, -parent_variable)
      print("selected after drop")
      # print(selected)
      # raise exception if fields listed in arguments that are uknown
      for (field_id in names(field_vals_select)) {

        if (!(field_id %in% names(private$..fields))) {
          stop(paste("Field '", field_id, "' does not exist and cannot be used for selection.", sep = ""))
        }
      }

      # order fields for selection: period must be expanded last due to the interpolation
      print("fields_select 1")
      fields_select <- list()
      for (col_id in names(field_vals_select)) {
        fields_select[[col_id]] <- private$..fields[[col_id]]
      }
      print("fields_select 2")
      for (col_id in names(private$..fields)) {
        if (!(col_id %in% c('period', field_vals_select))) {
          fields_select[[col_id]] <- private$..fields[[col_id]]
        }
      }
      print("fields_select 3")
      fields_select[['period']] <- private$..fields[['period']]
      print("fields_select 4")
      # print(names(fields_select))
      # select and expand fields
      for (col_id in names(fields_select)) {
        print("field")
        field <- fields_select[[col_id]]
        print("field_vals")
        print(col_id %in% names(field_vals_select))
        field_vals <- ifelse(col_id %in% names(field_vals_select), field_vals_select[[col_id]], NA)
        print(field_vals)



        selected <- field$select_and_expand(selected, col_id, field_vals, extrapolate_period=extrapolate_period)
      }
      print("selected and expanded")
      print(selected)
      # drop custom fields with only one value if specified in method argument

      if (drop_singular_fields) {
        selected <- selected %>%
        select(-c(
          names(sapply(self$..fields, function(field) {
            if (inherits(field, "CustomFieldDefinition") && n_distinct(selected[[col_id]]) < 2) {
              return(col_id)
            } else {
              return(NULL)
            }
          }))
        ))

      }

      selected2 <- private$..apply_mappings(selected, var_units)

      print(selected)
      selected_and_var_units <- list(selected=selected, var_units=var_units)
      print("return")
      return(selected_and_var_units)
    },
    ..cleanup = function(df, var_units) {

      # Sort columns and rows
      df_cols <- sapply(names(self$..fields), function(col_id) {
          field <- self$..fields[[col_id]]
          if (inherits(field, "CustomFieldDefinition")) {
            return(col_id)
          } else {
            return(NULL)
          }
        })
        print("df_cols")
        print(df_cols)
      cols_sorted <- c(
                      'source', 'variable', 'region', 'period', 'value')
      cols_sorted <- cols_sorted[cols_sorted %in% names(df)]
      print("cols sorted")
      print(cols_sorted)
      df <- select(df, any_of(cols_sorted))
      print("cols selected")
      df <- df %>%
        arrange_at(vars(intersect(cols_sorted, names(df))[!intersect(cols_sorted, names(df)) != "value"])) %>%
        mutate(row_index = row_number()) %>%
        select(-row_index)
      print("ordered")

      # Round values
      df$value <- ifelse(is.na(df$value), df$value, round(df$value, digits = 4))
      print("rounded")
      # Insert column containing units
      df <- as.data.frame(append(df, list(unit=NaN), after = match("value", names(df))-1))
      print(df)
      if ("reference_variable" %in% colnames(df)) {
        df$unit <- apply(df, 1, function(row) {
          if (!is.na(row["reference_variable"])) {
            combine_units(var_units[row["variable"]], var_units[row["reference_variable"]])
          } else {
            var_units[row["variable"]]
          }
        })
      } else {
        df$unit <- var_units[df$variable]
      }

      print(df)
      return(df)
  },

  ..apply_mappings = function(expanded, var_units) {
    print("apply mappings")
    # Get list of groupable columns
      group_cols <- setdiff(names(expanded), c('variable', 'reference_variable', 'value'))

      # Perform group_by and do not drop NA values


      grouped <- expanded %>% group_split(across(all_of(group_cols)), .drop = FALSE)

      # Create return list
      ret <- list()

      for (i in seq_along(grouped)) {
        rows <- grouped[[i]]
        print(rows, width=Inf)

        # 1. convert FLH to OCF
        cond <- endsWith(rows$variable, '|FLH')
        print("cond1")
        print(cond)

        # Check if any rows satisfy the condition
        if (any(cond)) {
          # Multiply 'value' by conversion factor
          rows$value[cond] <- rows$value[cond] * sapply(rownames(rows)[cond], function(idx) {
            unit_convert(var_units[rows$variable[idx]], 'a')
          })

          # Replace '|FLH' with '|OCF' in 'variable'
          rows$variable[cond] <- gsub("\\|FLH$", "|OCF", rows$variable[cond], fixed = TRUE)
        }

        # 2. convert OPEX Fixed Relative to OPEX Fixed
        print(rows, width=Inf)
        cond <- endsWith(rows$variable, '|OPEX Fixed Relative')
        print("cond2")
        print(cond)

        if (any(cond)) {
        # Define a function to calculate the conversion factor
        calculate_conversion <- function(row) {
          print(row)
          var_units_variable <- gsub("|OPEX Fixed Relative", "|CAPEX", row['variable'], fixed = TRUE)
          var_units_reference <- gsub("|OPEX Fixed Relative", "|OPEX Fixed", row['variable'], fixed = TRUE)
          var_units_dividend <- paste(var_units_variable, '/a', sep = "")
          var_units_df <- subset(rows, variable == var_units_variable)

          return(unit_convert(var_units[row['variable']], 'dimensionless') *
                  unit_convert(var_units_dividend, var_units[var_units_reference]) *
                  var_units_df$value[1])

        }



        # Calculate the conversion factor and update 'value' for rows satisfying the condition
        rows$value[cond] <- apply( rows[cond,], 1, calculate_conversion)

        # Replace '|OPEX Fixed Relative' with '|OPEX Fixed' in 'variable'
        rows$variable[cond] <- gsub("\\|OPEX Fixed Relative$", "|OPEX Fixed", rows$variable[cond], fixed = TRUE)

        # Assign 'reference_variable' based on modified 'variable'
        rows$reference_variable[cond] <- sapply(rownames(rows)[cond], function(idx) {
          var_units_variable <- gsub("\\|OPEX Fixed$", "|CAPEX", rows$variable[idx], fixed = TRUE)
          var_units_df <- subset(rows, variable == var_units_variable)
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
      print(rows, width=Inf)
      # 3. convert OPEX Fixed Specific to OPEX Fixed
      # Find rows where 'variable' ends with '|OPEX Fixed Specific'
      cond <- endsWith(rows$variable, "|OPEX Fixed Specific")
      print("cond3")
      print(cond)

      # Check if any rows satisfy the condition
      if (any(cond)) {
        # Define a function to calculate the conversion factor
        calculate_conversion <- function(row) {
          var_units_variable <- gsub("\\|OPEX Fixed Specific", "|OPEX Fixed", row['variable'], fixed = TRUE)
          var_units_reference <- gsub(r'(Input|Output)', '\\1 Capacity', row['reference_variable'], perl = TRUE)
          var_units_dividend <- paste(var_units_variable, '/a', sep = "")
          var_units_df <- subset(rows, variable == gsub("\\|OPEX Fixed Specific$", "|OCF", row['variable'], fixed = TRUE))
          if (nrow(var_units_df) > 0) {
            return(unit_convert(var_units_dividend, var_units[var_units_reference]) /
                  unit_convert(gsub("\\|OPEX Fixed Specific$", "|OPEX Fixed", row['variable'], fixed = TRUE),
                                var_units[var_units_variable],
                                private$..var_specs[row['reference_variable']]['flow_id']) *
                  var_units_df$value[1])
          } else {
            return(NA)
          }
        }

        # Calculate the conversion factor and update 'value' for rows satisfying the condition
        rows$value[cond] <- mapply(calculate_conversion, rows[cond,])

        # Replace '|OPEX Fixed Specific' with '|OPEX Fixed' in 'variable'
        rows$variable[cond] <- gsub("\\|OPEX Fixed Specific$", "|OPEX Fixed", rows$variable[cond], fixed = TRUE)

        # Update 'reference_variable' by replacing 'Input' or 'Output' with 'Input Capacity' or 'Output Capacity'
        rows$reference_variable[cond] <- gsub(r'(Input|Output)', '\\1 Capacity', rows$reference_variable[cond], perl = TRUE)

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

      print('cond4')
      print(cond1 & cond2)
      if (any(cond1 & cond2)) {
        rows$value[cond] <- 1.0 / rows$value[cond]
        rows$variable_new[cond] <- rows$reference_variable[cond]
        rows$reference_variable[cond] <- rows$variable[cond]
        rows$variable[cond] <- rows$variable_new[cond]
        rows <- rows[!names(rows) %in% c("variable_new")]
      }

      # 5. convert all references to primary output


      print(rows$reference_variable)
      if (any(!is.na(rows$reference_variable))) {
        cond1 <- (grepl("\\|Output(?: Capacity)?\\|", rows$reference_variable) | grepl("\\|Input(?: Capacity)?\\|", rows$reference_variable))
      } else {
        cond1 <- FALSE
      }
      print(rows$variable)
      cond2 <- unlist(lapply(rows$variable, function(var) {
        'default_reference' %in% names(private$..var_specs[[var]])
        }))



      get_default_reference <- function(var) {
        if ('default_reference' %in% names(self$var_specs[[var]])) {
          return(self$var_specs[[var]]$default_reference)
        } else {
          return(NA)
        }
      }

      # Apply the function to each 'variable' in 'rows'
      cond3  <- lapply(rows$variable, get_default_reference) != rows[['reference_variable']]
      print('cond5')
      print(cond1)
      print(cond2)
      print(cond3)
      print(cond1 & cond2 & cond3)

      if (any(cond1 & cond2 & cond3)) {
        regex_find <- "\\|(Input|Output)(?: Capacity)?\\|"
        regex_repl <- "|\\1|"
        rows$reference_variable_new[cond] <- sapply(rows$variable[cond], function(var) {
          self$var_specs[var]$default_reference
        })
        rows$value[cond] <- rows$value[cond] * sapply(seq_len(nrow(rows[cond,])), function(i) {
          row <- rows[cond,]
          unit_convert(paste0(ifelse(grepl("Capacity", row$reference_variable[i]), "a*", ""),
                              var_units[row$reference_variable_new[i]]),
                      var_units[gsub(regex_find, regex_repl, row$reference_variable_new[i])],
                      tail(strsplit(row$reference_variable_new[i], "\\|")[[1]], 1)) /
          unit_convert(paste0(ifelse(grepl("Capacity", row$reference_variable[i]), "a*", ""),
                              var_units[row$reference_variable[i]]),
                      var_units[gsub(regex_find, regex_repl, row$reference_variable[i])],
                      tail(strsplit(row$reference_variable[i], "\\|")[[1]], 1)) *
          rows[grepl(paste0("^", gsub(regex_find, regex_repl, row$reference_variable[i]), "$"),
                    rows$variable) &
              grepl(paste0("^", gsub(regex_find, regex_repl, row$reference_variable_new[i]), "$"),
                    rows$reference_variable), ]$value[1]
        })
        rows$reference_variable[cond] <- rows$reference_variable_new[cond]
        rows <- rows[!names(rows) %in% c("reference_variable_new")]
        if (any(cond & is.na(rows$value))) {
          warning(paste("No appropriate mapping found to convert row reference to primary output:",
                        rows[cond & is.na(rows$value), ]))
        }
      }


        }


  }

  ),
  public = list(
    # Constructor
    initialize = function(parent_variable,
                           include_databases = NULL,
                           file_paths = NULL,
                           check_inconsistencies = FALSE,
                           data = NULL) {

      # Attributes
      print("initialize")
      super$initialize(parent_variable)
      private$..df <- NULL
      private$..columns <- base_columns
      private$..fields <- lapply(private$..columns, function(field) {
        if (inherits(field, "AbstractFieldDefinition")) field else NULL
      })
      private$..masks <- list()

      # Load data if provided, otherwise load from TEDataFiles
      if (!is.null(data)) {
        private$..df <- data.frame(data)
      } else {

        if (!is.null(include_databases)) {
            include_databases <- list(include_databases)
        } else {

            include_databases <- list(names(databases))
        }

        if (is.null(file_paths)){
            file_paths <- list()

        }
        private$..df <- data.frame(private$..load_files(include_databases, file_paths, check_inconsistencies))
      }
      print("private_df_type")
      print(typeof(private$..df))
    },

    normalise = function(override = NULL, inplace = FALSE) {
      normalised <- private$..normalise(override)
      if (inplace) {
        private$..df <- data.frame(normalised$normalised)
      } else {
        return(data.frame(normalised$normalised))
      }
    },

    select = function(override = NULL,
                      drop_singular_fields = TRUE,
                      extrapolate_period = TRUE,
                      ...) {
      selected_and_var_units <- private$..select(override, drop_singular_fields, extrapolate_period, ...)
      selected <- selected_and_var_units[[1]]
      var_units <- selected_and_var_units[[2]]

      # Inserting a new column 'reference_variable' at a specific position in the data frame
      selected <- cbind(selected[, 1:selected$variable - 1],
                        reference_variable = NA,
                        selected[, selected$variable:length(selected)])

      # Mapping values from 'var_references' to the 'reference_variable' column based on 'variable'
      selected$reference_variable <- var_references[selected$variable]


      result <- private$..cleanup(selected, var_units)
      return(result)
    },

    aggregate = function(override=NULL,
            drop_singular_fields=TRUE,
            extrapolate_period=TRUE,
            agg=NULL,
            masks=NULL,
            masks_database=TRUE,
            ... ) {
              stop("aggregate not implemented yet")
            }
  ),
  active = list(
    data = function(df) {
      if (missing(df)) return(private$..df)
      else private$
      ..df <- df
    }
  )



)


