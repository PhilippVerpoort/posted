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
      # Filtering rows where col_id is in field_vals
      print(df)
      df_filtered <- df %>%
        filter(col_id %in% field_vals)
      print("df asterisk")
      print(df %>% filter(col_id == "*"))
      # Filtering rows where col_id is '*'
      df_asterisk <- df %>%
        filter(col_id == "*") %>%
        select(-all_of(col_id)) %>%
        crossing(data.frame(col_id = field_vals))# %>%
        # select(col_id, everything())  # Putting new_col_id as the first column

# Concatenating the filtered data frames
result <- bind_rows(df_filtered, df_asterisk)
      return(result)
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
    
    
    # TODO: rework select and expand function according to new style
    select_and_expand = function(df, col_id, field_vals = NA, ...) {
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
# TODO: Review and implement functions
#     expand = function(df, col_id, field_vals, ...) {
#       return(dplyr::bind_rows(
#         df[df[[col_id]] != '*', ],
#         dplleft_join(
#           df[df[[col_id]] == '*', ] %>% dplyr::select(-col_id),
#           dplyr::expand_grid(!!col_id := field_vals),
#           by = character()
#         )
#       ) %>% dplyr::mutate({{col_id}} := as.numeric({{col_id}})))
#     },

#     select = function(df, col_id, field_vals, ...) {
#       group_cols <- colnames(df)[!(colnames(df) %in% c(col_id, 'value'))]
#       grouped <- df %>% group_by(!!!syms(group_cols), .drop = FALSE)
#       ret <- list()

#       for (i in 1:n_groups(grouped)) {
#         keys <- grouped$`...1`[[i]]
#         rows <- grouped$data[[i]][[c(col_id, 'value')]]
#         periods_exist <- unique(rows[[col_id]])

#         req_rows <- tibble::tibble({{col_id}} := field_vals,
#                                    {{paste0(col_id, '_upper')}} := purrr::map_dbl(field_vals, ~ min(periods_exist[periods_exist >= .x], na.rm = TRUE)),
#                                    {{paste0(col_id, '_lower')}} := purrr::map_dbl(field_vals, ~ max(periods_exist[periods_exist <= .x], na.rm = TRUE)))

#         req_rows[group_cols] <- as_tibble(keys)

#         cond_match <- req_rows[[col_id]] %in% periods_exist
#         cond_extrapolate <- is.na(req_rows[[paste0(col_id, '_upper')]]) | is.na(req_rows[[paste0(col_id, '_lower')]])

#         rows_match <- dplyr::inner_join(req_rows[cond_match, ], rows, by = col_id)
#         rows_extrapolate <- ifelse(!identical("extrapolate_period", names(list(...))), dplyr::bind_rows(
#           req_rows[!cond_match & cond_extrapolate, ] %>%
#             dplyr::mutate(period_combined = ifelse(!is.na({{paste0(col_id, '_upper')}}), {{paste0(col_id, '_upper')}}, {{paste0(col_id, '_lower')}})),
#           dplyr::inner_join(
#             req_rows[!cond_match & cond_extrapolate, ] %>%
#               dplyr::rename({{col_id}} = {{paste0(col_id, '_combined')}}),
#             rows,
#             by = paste0(col_id, '_combined')
#           )
#         ), tibble())

#         rows_interpolate <- req_rows[!cond_match & !cond_extrapolate, ] %>%
#           dplyr::inner_join(
#             rows %>%
#               dplyr::rename({{paste0(col_id, '_upper')}} = {{col_id}},
#                             {{paste0(col_id, '_lower')}} = {{col_id}}),
#             by = c(paste0(col_id, '_upper'), paste0(col_id, '_lower'))
#           ) %>%
#           dplyr::mutate(value = value_lower + ({{paste0(col_id, '_upper')}} - {{col_id}}) /
#                                           ({{paste0(col_id, '_upper')}} - {{paste0(col_id, '_lower')}}) * (value_upper - value_lower)) %>%
#           dplyr::select(-c({{paste0(col_id, '_upper')}}, {{paste0(col_id, '_lower')}}))

#         rows_to_concat <- dplyr::bind_rows(rows_match, rows_extrapolate, rows_interpolate) %>%
#           dplyr::select(-c(paste0(col_id, '_upper'), paste0(col_id, '_lower'), paste0(col_id, '_combined'), 'value_upper', 'value_lower'))
#         if (nrow(rows_to_concat) > 0) {
#           ret <- c(ret, rows_to_concat)
#         }
#       }

#       if (length(ret) > 0) {
#         return(dplyr::bind_rows(ret) %>% dplyr::ungroup())
#       } else {
#         return(df[integer()])
#       }
#     }
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