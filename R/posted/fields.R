# Import necessary libraries
library(dplyr)

# Define the AbstractFieldDefinition class
AbstractFieldDefinition <- R6Class("AbstractFieldDefinition",
  public = list(
    field_id = NULL,
    initialize = function(field_id) {
      self$field_id <- field_id
    },

    id = function() {
      return(self$field_id)
    },

    type = function() {
      stop("This method must be implemented in subclasses.")
    },

    is_coded = function() {
      return(FALSE)
    },

    codes = function() {
      return(NULL)
    },

    allowed_types = function() {
      stop("This method must be implemented in subclasses.")
    },

    is_allowed = function(value) {
      if (self$is_coded()) {
        return(value %in% c(self$codes(), '*', '#'))
      } else {
        return(TRUE)
      }
    },

    select_and_expand = function(df, field_vals) {
      stop("This method must be implemented in subclasses.")
    }
  )
)

# Define the PeriodFieldDefinition class
PeriodFieldDefinition <- R6Class("PeriodFieldDefinition",
  inherit = AbstractFieldDefinition,
  public = list(
    initialize = function() {
      super$initialize('period')
    },

    type = function() {
      return('cases')
    },

    allowed_types = function() {
      return(union('numeric', 'character'))
    },

    select_and_expand = function(df, field_vals) {
      df <- bind_rows(
        df[df$period != '*', ],
        df[df$period == '*', ] %>%
          select(-period) %>%
          merge(data.frame(period = field_vals), by = NULL, all = TRUE, allow.cartesian = TRUE)
      ) %>%
        mutate(period = as.numeric(period))

      group_cols <- setdiff(names(df), c('period', 'value'))
      grouped <- df %>% group_by(across(all_of(group_cols)), .drop = FALSE)

      ret <- list()

      for (i in seq_along(grouped$data)) {
        rows <- grouped$data[[i]]
        periods_exist <- unique(rows$period)
        req_rows <- data.frame(period = field_vals,
                               period_upper = sapply(field_vals, function(p) min(periods_exist[periods_exist >= p], na.rm = TRUE)),
                               period_lower = sapply(field_vals, function(p) max(periods_exist[periods_exist <= p], na.rm = TRUE)))

        req_rows[group_cols] <- grouped$group_keys[[i]]

        cond_match <- req_rows$period %in% periods_exist
        cond_extrapolate <- is.na(req_rows$period_upper) | is.na(req_rows$period_lower)

        rows_match <- req_rows[cond_match, ] %>%
          left_join(rows, by = 'period')

        rows_extrapolate <- req_rows[!cond_match & cond_extrapolate, ] %>%
          mutate(period_combined = ifelse(!is.na(period_upper), period_upper, period_lower)) %>%
          left_join(rows, by = c('period_combined' = 'period'))

        rows_interpolate <- req_rows[!cond_match & !cond_extrapolate, ] %>%
          left_join(rows %>% rename_with(~paste0(., '_upper'), everything()), by = c('period_upper' = 'period')) %>%
          left_join(rows %>% rename_with(~paste0(., '_lower'), everything()), by = c('period_lower' = 'period_lower')) %>%
          mutate(value = value_lower + (period_upper - period) / (period_upper - period_lower) * (value_upper - value_lower))

        rows_append <- bind_rows(rows_match, rows_extrapolate, rows_interpolate) %>%
          select(-period_upper, -period_lower, -period_combined, -value_upper, -value_lower)

        ret[[i]] <- rows_append
      }

      return(bind_rows(ret))
    }
  )
)

# Define the SourceFieldDefinition class
SourceFieldDefinition <- R6Class("SourceFieldDefinition",
  inherit = AbstractFieldDefinition,
  public = list(
    initialize = function() {
      super$initialize('source')
    },

    type = function() {
      return('cases')
    },

    allowed_types = function() {
      return('character')
    }
  )
)

# Define the CustomFieldDefinition class
CustomFieldDefinition <- R6::R6Class("CustomFieldDefinition",
  inherit = AbstractFieldDefinition,
  public = list(
    field_specs = NULL,
    initialize = function(field_id, field_specs) {
      super$initialize(field_id)
      self$field_specs <- field_specs
     

      stopifnot('name' %in% names(field_specs) && is.character(field_specs$name))
      stopifnot('type' %in% names(field_specs) && is.character(field_specs$type))
      if (field_specs$type != 'comment') {
        stopifnot('coded' %in% names(field_specs) && is.logical(field_specs$coded))
        if (field_specs$coded) {
          stopifnot('codes' %in% names(field_specs) && is.list(field_specs$codes) && all(sapply(field_specs$codes, is.character)))
        }
      }
    },

    type = function() {
      return(self$field_specs$type)
    },

    is_coded = function() {
      return(self$field_specs$coded)
    },

    codes = function() {
      return(names(self$field_specs$codes))
    },

    allowed_types = function() {
      return('character')
    }
  )
)
