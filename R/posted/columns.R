source("R/posted/config.R")
source("R/posted/path.R")
source("R/posted/read.R")
source("R/posted/settings.R")
# source("R/posted/units.R")

# Import necessary libraries
library(dplyr)
library(assertthat)
library(GROAN)

is_float <- function(string) {
  # Attempt to convert the string to a numeric value
  # If successful, return TRUE; otherwise, return FALSE
  if (length(as.numeric(string)) == 1 && !is.na(as.numeric(string))) {
    return(TRUE)
  } else {
    return(FALSE)
  }
}

AbstractColumnDefinition <- R6::R6Class("AbstractColumnDefinition",
    private = list(
        ..col_type = NULL,
        ..name = NULL,
        ..description = NULL,
        ..dtype = NULL,
        ..required = NULL
    ),
 
  
  public = list(
    
    initialize = function(col_type, name, description, dtype, required) {
        if (!(col_type %in% list('field', 'variable', 'unit', 'value', 'comment'))) {
            stop(sprintf("Columns must be of type field, variable, unit, value, or comment but found: %s", col_type))
        } 
        if (!is.string(name)) {
            stop(sprintf("The 'name' must be a string but found type %s: %s", typeof(name), name))
        }
        if (!is.string(description)) {
            stop(sprintf("The 'description' must be a string but found type %s: %s", typeof(description), description))
        }
        if (!((is.string(dtype)) && (dtype %in% list('float', 'str', 'category')))) {
            stop(sprintf("The 'dtype' must be a valid data type but found %s", dtype))
        }
        if (!is.logical(required)) {
            stop(sprintf("The 'required' argument must be a bool but found: %s", required))
        }

        private$..col_type <- col_type
        private$..name <- name
        private$..description <- description
        private$..dtype <- dtype
        private$..required <- required


    },

    is_allowed = function(cell) {
      TRUE
    }

  ),
  active = list(
    col_type = function() {
      private$..col_type
    },
    
    name = function() {
      private$..name
    },
    
    description = function() {
      private$..description
    },
    
    dtype = function() {
      private$..dtype
    },
    
    required = function() {
      private$..required
    },
    
    default = function() {
      NA
    }
    
    
  )
)



VariableDefinition <- R6::R6Class("VariableDefinition", inherit = AbstractColumnDefinition,
  public = list(
    initialize = function(name, description, required) {
      super$initialize(col_type = 'variable',
                       name = name,
                       description = description,
                       dtype = 'category',
                       required = required)
    },
    
    is_allowed = function(cell) {
      if (is.na(cell)) {
        return(!private$..required)
      }
      return(is.character(cell) && (cell %in% variables))
    }
  )
)



UnitDefinition <- R6::R6Class("UnitDefinition", inherit = AbstractColumnDefinition,
  public = list(
    initialize = function(name, description, required) {
      super$initialize(col_type = 'unit',
                       name = name,
                       description = description,
                       dtype = 'category',
                       required = required)
    },
    
    is_allowed = function(cell) {
      if (is.na(cell)) {
        return(!private$required)
      }
      if (!is.character(cell)) {
        return(FALSE)
      }
      tokens <- strsplit(cell, ';')[[1]]
      if (length(tokens) == 1) {
        return (tokens[1] %in% ureg)
      } else if (length(tokens) == 2) {
        return (tokens[1] %in% ureg && tokens[2] %in% unit_variants)
      } else {
        return(FALSE)
      }
    }
  )
)

ValueDefinition <- R6::R6Class("ValueDefinition", inherit = AbstractColumnDefinition,
  public = list(
    initialize = function(name, description, required) {
      super$initialize(col_type = 'value',
                       name = name,
                       description = description,
                       dtype = 'float',
                       required = required)
    },
    
    is_allowed = function(cell) {
      if (is.na(cell)) {
        return(!private$required)
      }
      return(is.numeric(cell))
    }
  )
)

CommentDefinition <- R6::R6Class("CommentDefinition", inherit = AbstractColumnDefinition,
  public = list(
    initialize = function(name, description, required) {
      super$initialize(col_type = 'comment',
                       name = name,
                       description = description,
                       dtype = 'str',
                       required = required)
    },
    
    is_allowed = function(cell) {
      TRUE
    }
  )
)


# Define the AbstractFieldDefinition class
AbstractFieldDefinition <- R6::R6Class("AbstractFieldDefinition", inherit = AbstractColumnDefinition,
  private = list(
    ..field_type = NULL,
    ..coded = NULL,
    ..codes = NULL,

    ..expand = function(df, col_id, field_vals, ...) {
      # expand period rows
      df[df[[col_id]] == "*", col_id] = paste(field_vals, collapse=',')
      result_df <- separate_rows(df, col_id, sep=',')
      
      
      
      return(result_df)


    },
    
    ..select = function(df, col_id, field_vals, ...) {
      df[df[[col_id]] %in% field_vals, , drop = FALSE]
    }

  ),
  public = list(
    initialize = function(field_type, name, description, dtype, coded, codes = NULL) {
      if (!(field_type %in% list('case', 'component'))) {
        stop("Fields must be of type case or component.")
      }
      
     super$initialize(col_type = 'field',
                       name = name,
                       description = description,
                       dtype = dtype,
                       required = TRUE)

      private$..field_type <- field_type
      private$..coded <- coded
      private$..codes <- codes
    },

    
    
    
    is_allowed = function(cell) {
      print(cell)
      if (is.na(cell)) {
        return(FALSE)
      }
      if (private$..coded) {
      
        return(cell %in% names(private$..codes) || cell == '*' ||
               (cell == '#' && private$..col_type == 'component'))
      } else {
        return(TRUE)
      }
    },
    
    
   
    select_and_expand = function(df, col_id, field_vals = NA, ...) {
      print("df_select and expand")
      print("field vals initial")
      print(field_vals)
      if (is.na(field_vals)) {
        if (col_id == 'period') {
          field_vals <- default_periods
        } else if (private$..coded) {
          field_vals <- names(private$..codes)
        } else {
          field_vals <- unique(df[[col_id]][df[[col_id]] != '*'])
        }
      } else {
        if(!(is.list(field_vals))) {
        field_vals <- list(field_vals)}
        print("field_vals_columns")
        print(field_vals)

        for (val in field_vals) {
          print(val)
          if (!self$is_allowed(val)) {
            stop(paste("Invalid type selected for field '", col_id, "': ", val, sep = ""))
          }
        }

        if ("*" %in% field_vals) {
          stop(paste("Selected values for field '", col_id, "' must not contain the asterisk.",
                    "Omit the '", col_id, "' argument to select all entries.", sep = ""))
        }

      }
      
      df <- private$..expand(df, col_id, field_vals, ...)
      df <- private$..select(df, col_id, field_vals, ...)
      print(df)
      return(df)
    }
  ),
  active = list(
    field_type = function() {
      private$..field_type
    },
    
    coded = function() {
      private$..coded
    },
    
    codes = function() {
      private$..codes
    
    },
    
    default = function() {
      if (private$..field_type == 'case') {
        return('*')
      } else {
        return('#')
      }
    }
  )
)
 
RegionFieldDefinition <- R6::R6Class("RegionFieldDefinition", inherit = AbstractFieldDefinition,
  public = list(
    initialize = function(name, description) {
      super$initialize(
        field_type = 'case',
        name = name,
        description = description,
        dtype = 'category',
        coded = TRUE,
        codes = list('World' = 'World')  # TODO: Insert list of country names here.
      )
    }
  )
)



PeriodFieldDefinition <- R6::R6Class("PeriodFieldDefinition", inherit = AbstractFieldDefinition,
  private = list(


    ..expand = function(df, col_id, field_vals, ...) {
      
      # expand period rows
      df[df[[col_id]] == "*", col_id] = paste(field_vals, collapse=',')
      result_df <- separate_rows(df, col_id, sep=',')
      
      # Convert 'period' column to float
      result_df[[col_id]] <- as.numeric(result_df[[col_id]])
      
      return(result_df)
    },




    ..select = function(df, col_id, field_vals, ...) {
      kwargs <- list(...)
      
      # Get list of groupable columns
      group_cols <- setdiff(names(df), c(col_id, 'value'))
     
      # Perform group_by and do not drop NA values
      
      
      grouped <- df %>% group_split(across(all_of(group_cols)), .drop = FALSE)
    
      # Create return list

      
      ret <- list()
      
   


      # Loop over groups
      for (i in seq_along(grouped)) {
        group_df <- grouped[[i]]
      
        # Get rows in group
        rows <- group_df %>%
          select(col_id, value)
    
        # Get a list of periods that exist
        periods_exist <- unique(rows[[col_id]])
       
        # Create dataframe containing rows for all requested periods
        req_rows <- data.frame()
       
     
        req_rows <-setNames(data.frame(field_vals[[1]]),col_id )
        req_rows[[paste0(col_id, "_upper")]] <- sapply(field_vals, function(p) {
            filtered_values <- periods_exist[periods_exist >= p]
            if (length(filtered_values) == 0 || all(is.na(filtered_values))) {
              return(NaN)
            } else {
              return(min(filtered_values, na.rm = TRUE))
            }
          })
                        
        req_rows[[paste0(col_id, "_lower")]] <- sapply(field_vals, function(p) {
            filtered_values <- periods_exist[periods_exist <= p]
            if (length(filtered_values) == 0 || all(is.na(filtered_values))) {
              return(NaN)
            } else {
              return(max(filtered_values, na.rm = TRUE))
            }
          })
       
        
        # Set missing columns from group
        req_rows[group_cols] <- group_df%>% slice(1) %>% select(all_of(group_cols))
        
        # check case
        cond_match <- req_rows[[col_id]] %in% periods_exist
        cond_extrapolate <- is.na(req_rows[[paste0(col_id, "_upper")]]) | is.na(req_rows[[paste0(col_id, "_lower")]])

        
        # Match
        rows_match <- req_rows[cond_match, ] %>%
            merge(rows, by = col_id)
        
      
        # Extrapolate

       
        if (!("extrapolate_period" %in% names(kwargs)) || kwargs$extrapolate_period) {
         
          rows_extrapolate <- req_rows[!cond_match & cond_extrapolate, ] %>% mutate(period_combined = ifelse(!is.na(!!sym(paste0(col_id, "_upper"))), !!sym(paste0(col_id, "_upper")), !!sym(paste0(col_id, "_lower"))))
          rows_ext <- rows %>% rename(!!paste0(col_id, "_combined") := !!sym(col_id))

          # Merge the data frames
          rows_extrapolate <- left_join(rows_extrapolate, rows_ext, by = paste0(col_id, "_combined"))
        } else {
          rows_extrapolate <- data.frame()
        }
        
      
       
        rows_interpolate <- req_rows %>%
          filter(!(.data[[col_id]] %in% periods_exist) & (!is.na(!!sym(paste0(col_id, "_upper"))) & !is.na(!!sym(paste0(col_id, "_lower"))))) %>%
          inner_join(rename(rows, !!paste0(col_id, "_upper") := !!sym(col_id), !!paste0("value_upper") := value), by = paste0(col_id, "_upper")) %>%
          inner_join(rename(rows, !!paste0(col_id, "_lower") := !!sym(col_id), !!paste0("value_lower") := value), by = paste0(col_id, "_lower")) %>%
          mutate(value = value_lower + ((!!sym(paste0(col_id, "_upper")) - !!sym(col_id)) / (!!sym(paste0(col_id, "_upper")) - !!sym(paste0(col_id, "_lower")))) * (value_upper - value_lower))
       
        # Combine into one dataframe and drop unused columns
        rows_to_concat <- list(rows_match, rows_extrapolate, rows_interpolate)
        rows_to_concat <- Filter(function(x) !is.data.frame(x) || nrow(x) > 0, rows_to_concat)
        if (length(rows_to_concat) > 0) {
          rows_append <- bind_rows(rows_to_concat) 
        
          rows_append <- rows_append %>%  select(-any_of(c(paste0(col_id, "_upper"),
                  paste0(col_id, "_lower"),
                  paste0(col_id, "_combined"),
                  "value_upper",
                  "value_lower")))
        
          # Add to return list
          ret[[i]] <- rows_append
        }
      }
   
      # Convert return list to dataframe and return
      if (length(ret) > 0) {
        return(bind_rows(ret))
        
      } else {
        return(df[FALSE, ])  # Empty data frame
      }
    }

  ),
  
  public = list(
    initialize = function(name, description) {
      super$initialize(
        field_type = 'case',
        name = name,
        description = description,
        dtype = 'float',
        coded = FALSE
      )
    },

    is_allowed = function(cell) {
      return(is_float(cell) || cell == '*')
    }

    
  )
)




# Define the SourceFieldDefinition class
SourceFieldDefinition <- R6::R6Class("SourceFieldDefinition",
  inherit = AbstractFieldDefinition,
  public = list(
    initialize = function(name, description) {
      super$initialize(
        field_type = 'case',
        name= name,
        description = description,
        dtype = 'category',
        coded = FALSE # TODO: Insert list of BibTeX identifiers here.
        ) 
    }
    ) 
)  

# Define the CustomFieldDefinition class
CustomFieldDefinition <- R6::R6Class("CustomFieldDefinition",
  inherit = AbstractFieldDefinition,
  public = list(
    field_specs = NULL,
    initialize = function(field_specs) {

    if (!('type' %in% names(field_specs) && is.string(field_specs$type) && field_specs$type %in% c('case', 'component'))) {
    stop("Field type must be provided and equal to 'case' or 'component'.")
    }

    if (!('name' %in% names(field_specs) && is.string(field_specs$name))) {
    stop("Field name must be provided and of type string.")
    }

    if (!('description' %in% names(field_specs) && is.string(field_specs$description))) {
    stop("Field description must be provided and of type string.")
    }

    if (!('coded' %in% names(field_specs) && is.logical(field_specs$coded))) {
    stop("Field coded must be provided and of type bool.")
    }

    if (field_specs$coded && !('codes' %in% names(field_specs) && is.list(field_specs$codes))) {
    stop("Field codes must be provided and contain a list of possible codes.")
    }
    if ('codes' %in% names(field_specs)) {    
        x <- field_specs$codes
    } else {
        x <- NULL
    }
    

    super$initialize(
        field_type=field_specs$type,
        name=field_specs$name,
        description=field_specs$description,
        dtype='category',
        coded=field_specs$coded,
        codes= x
    )
  
      self$field_specs <- field_specs
    
    }
  )
)



base_columns <- list(
  'region' = RegionFieldDefinition$new(
    name = 'Region',
    description = 'The region that this value is reported for.'
  ),
  'period' = PeriodFieldDefinition$new(
    name = 'Period',
    description = 'The period that this value is reported for.'
  ),
  'variable' = VariableDefinition$new(
    name = 'Variable',
    description = 'The reported variable.',
    required = TRUE
  ),
  'reference_variable' = VariableDefinition$new(
    name = 'Reference Variable',
    description = 'The reference variable. This is used as an addition to the reported variable to clear, simplified, and transparent data reporting.',
    required = FALSE
  ),
  'value' = ValueDefinition$new(
    name = 'Value',
    description = 'The reported value.',
    required = TRUE
  ),
  'uncertainty' = ValueDefinition$new(
    name = 'Uncertainty',
    description = 'The reported uncertainty.',
    required = FALSE
  ),
  'unit' = UnitDefinition$new(
    name = 'Unit',
    description = 'The reported unit that goes with the reported value.',
    required = TRUE
  ),
  'reference_value' = ValueDefinition$new(
    name = 'Reference Value',
    description = 'The reference value. This is used as an addition to the reported variable to clear, simplified, and transparent data reporting.',
    required = FALSE
  ),
  'reference_unit' = UnitDefinition$new(
    name = 'Reference Unit',
    description = 'The reference unit. This is used as an addition to the reported variable to clear, simplified, and transparent data reporting.',
    required = FALSE
  ),
  'comment' = CommentDefinition$new(
    name = 'Comment',
    description = 'A generic free text field commenting on this entry.',
    required = FALSE
  ),
  'source' = SourceFieldDefinition$new(
    name = 'Source',
    description = 'A reference to the source that this entry was taken from.'
  ),
  'source_detail' = CommentDefinition$new(
    name = 'Source Detail',
    description = 'Detailed information on where in the source this entry can be found.',
    required = TRUE
  )
)





read_fields <- function(variable) {
  fields <- list()
  comments <- list()

  
  for (database_id in names(databases)) {
    fpath <- file.path(databases[[database_id]], 'fields', paste0(paste(unlist(strsplit(variable, split= "\\|")), collapse = '/'), '.yml'))
    if (file.exists(fpath)) {
      if (!file_test("-f", fpath)) {
        stop(paste("Expected YAML file, but not a file:", fpath))
      }


      fpathfile <- read_yml_file(fpath) 
      for (pair in names(fpathfile)) {
        col_id <- pair
        field_specs <- fpathfile[[pair]]
        if (field_specs['type'] %in% list('case', 'component')) {
      
            fields[[col_id]] <- CustomFieldDefinition$new(field_specs)
        } else if (field_specs['type'] == 'comment') {
            comments[[col_id]] <- CommentDefinition(, required =False)
        }  else {
            stop(sprintf("Unknown field type: %s", col_id))
        }
    
      }
    #   for (col_id %in% fields):
    #     if (col_id %in% base_columns):
    #         stop(sprintf("Field ID cannot be equal to a base column ID: %s", col_id))
    
      }
    }
    return(list(fields= fields, comments= comments))
  }