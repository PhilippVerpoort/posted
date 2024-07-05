library(dplyr)
library(purrr)
library(tidyr)
library(stringr)

#' @title read_definitions
#'
#' @description Reads YAML files from definitions directory, extracts tags, inserts tags into
#' definitions, replaces tokens in definitions, and returns the updated definitions.
#'
#' @param definitions_dir Character. Path leading to the definitions.
#' @param flows List. Dictionary containing the different flow types. Each key represents a flow type, the corresponding
#'              value is a dictionary containing key value pairs of attributes like density, energy content and their
#'              values.
#' @param techs List. Dictionary containing information about different technologies. Each key in the
#'              dictionary represents a unique technology ID, and the corresponding value is a dictionary containing
#'              various specifications for that technology, like 'description', 'class', 'primary output' etc.
#'
#' @return List. Dictionary containing the definitions after processing and replacing tags and tokens.
#'
#' @export
read_definitions <- function(definitions_dir, flows, techs) {


  # chek that variables exists and is a directory
  if(!dir.exists(definitions_dir)) {
    stop(paste0("Should be a directory but is not: ", definitions_dir))
  }

  # read all definitions and tags
  definitions <- list()
  tags <- list()

  file_paths <- list.files(path = definitions_dir, pattern = "\\.yml$", recursive = TRUE, full.names = TRUE)
  for (file_path in file_paths) {
    if (grepl("^tag_", basename(file_path))) {
      tags <- c(tags, read_yml_file(file_path))
    } else {
      definitions <- c(definitions, read_yml_file(file_path))
    }
  }

  # read tags from flows and techs
  tags[['Flow IDs']] <- map(flows, ~list())
  tags[['Tech IDs']] <- map(techs, function(item) {item['primary_output']})

  # instert tags
  for (tag in names(tags)) {
    definitions <- replace_tags(definitions, tag, tags[[tag]])
  }

  # remove definitions where tags could not been replaced
  if (any(sapply(definitions, function(x) "\\{" %in% names(x)))) {
    warning('Tokens could not be replaced correctly.')
    definitions <- purrr::keep(definitions, ~ !any(sapply(.x, function(x) "{" %in% names(x))))
  }

  # insert tokens
  tokens <- list(
    'default currency' = function(def_specs) default_currency,
    'primary output' = function(def_specs) def_specs$primary_output
  ) %>%
   c(set_names(
        lapply(c('full', 'raw', 'variant'), function(unit_component) {
          unit_token_func(unit_component, flows)
        }),
        sprintf('default flow unit %s', c('full', 'raw', 'variant'))
      ))
  for (def_key in names(definitions)) {
    for (def_property in names(definitions[[def_key]])) {
      def_value <- definitions[[def_key]][[def_property]]

      for (token_key in names(tokens)) {
        token_func <- tokens[[token_key]]
        if (is.character(def_value) && grepl(paste0("\\{", token_key, "\\}"), def_value)) {
          definitions[[def_key]][[def_property]] <- gsub(paste0("\\{", token_key, "\\}"), token_func(definitions[[def_key]]), definitions[[def_key]][[def_property]])

      }
    }
  }
  }
  return(definitions)
}



#' @title replace_tags
#'
#' @description Replaces specified tags in dictionary keys and values with corresponding
#' items from another dictionary.
#'
#' @param definitions List. Dictionary containing the definitions, where the tags should be replaced by the items.
#' @param tag Character. String to identify where replacements should be made in the definitions. Specifies
#'            the placeholder that needs to be replaced with actual values from the \code{items} dictionary.
#' @param items List. Dictionary containing the items from which to replace the definitions.
#'
#' @return List. Dictionary containing the definitions with replacements based on the provided tag and items.
#'
#' @export
replace_tags <- function(definitions, tag, items) {


  definitions_with_replacements <- list()

  # Precompute regular expressions for tag replacement
  tag_regex <- paste0("\\{", tag, "\\}")

  for (def_name in names(definitions)) {
    def_specs <- definitions[[def_name]]

    if (grepl(tag_regex, def_name)) {
      for (item_name in names(items)) {
        item_specs <- items[[item_name]]
        item_desc <- ifelse('description' %in% names(item_specs), item_specs[['description']], item_name)

        def_name_new <- gsub( paste0("\\{", tag, "\\}"), item_name, def_name)
        def_specs_new <- c(def_specs, item_specs)
        def_specs_new <- def_specs_new[!duplicated(names(def_specs_new))]

        # Replace tags in description
        def_specs_new$description <- gsub( paste0("\\{", tag, "\\}"), item_desc, def_specs$description)

        # Replace tags in other specs
        def_specs_new <- lapply(def_specs_new, function(spec) {
          if (is.character(spec) && !identical(names(def_specs_new)[which(def_specs_new == spec)], 'description')) {
            spec <- gsub( paste0("\\{", tag, "\\}"), item_name, spec)
            spec <- gsub('\\{parent variable\\}', substr(def_name, 1, gregexpr( paste0("\\{", tag, "\\}"), def_name)[[1]] - 2), spec)
          }
          return(spec)
        })
        definitions_with_replacements[[def_name_new]] <- def_specs_new
      }
    } else {
      definitions_with_replacements[[def_name]] <- def_specs
    }
  }
  return(definitions_with_replacements)
}


#' @title unit_token_func
#'
#' @description Takes a unit component type and a dictionary of flows, and returns a lambda function
#' that extracts the default unit based on the specified component type from the flow
#' dictionary.
#'
#' @param unit_component Character. Specifies the type of unit token to be returned. Possible values are 'full', 'raw', 'variant'.
#' @param flows List. Dictionary containing the flows.
#'
#' @return Function. Lambda function that takes a dictionary \code{def_specs} as input. The lambda function
#' will return different values based on the \code{unit_component} parameter.
#'
#' @export
unit_token_func <- function(unit_component, flows) {
  return(function(def_specs) {
    if (!('flow_id' %in% names(def_specs)) || !(def_specs$flow_id %in% names(flows))) {
      return('ERROR')
    } else {
      if (unit_component == 'full') {
        return(flows[[def_specs$flow_id]]$default_unit)
      } else if (unit_component == 'raw') {
        return(strsplit(flows[[def_specs$flow_id]]$default_unit, ';')[[1]][1])
      } else if (unit_component == 'variant') {
        if (paste0(';', strsplit(flows[[def_specs$flow_id]]$default_unit, ';')[[1]][2])==";NA") {
          return ("")
        } else {
        return(paste0(';', strsplit(flows[[def_specs$flow_id]]$default_unit, ';')[[1]][2]))}
      } else {
        return('UNKNOWN')
      }
    }
  })
}
