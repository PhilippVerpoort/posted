library(dplyr)
library(purrr)
library(tidyr)

source("R/posted/settings.R")
source("R/posted/read.R")
# Assuming you have the necessary functions and libraries loaded

read_definitions <- function(definitions_dir, flows, techs) {
  stopifnot(dir.exists(definitions_dir))
  
  # read all definitions and tags
  definitions <- list()
  tags <- list()
  file_paths <- list.files(path = definitions_dir, pattern = "\\.yml$", recursive = TRUE, full.names = TRUE)
  
  for (file_path in file_paths) {
    if (grepl("^tag_", basename(file_path))) {
      tags <- union(tags, read_yml_file(file_path))
    } else {
      definitions <- union(definitions, read_yml_file(file_path))
    }
  }
  
  # read tags from flows and techs
  tags[['Flow IDs']] <- map(flows, ~list())
  tags[['Tech IDs']] <- map(techs, ~select(.x, primary_output = primary_output))
  
  # insert tags
  definitions <- replace_tags(definitions, tags)
  
  # remove definitions where tags could not been replaced
  if (any(sapply(definitions, function(x) "{" %in% names(x)))) {
    warning('Tokens could not be replaced correctly.')
    definitions <- purrr::keep(definitions, ~ !any(sapply(.x, function(x) "{" %in% names(x))))
  }
  
  # insert tokens
  tokens <- list(
    'default currency' = function(def_specs) default_currency(),
    'primary output' = function(def_specs) def_specs$primary_output
  ) %>% 
    union(
      set_names(
        lapply(c('full', 'raw', 'variant'), function(unit_component) {
          unit_token_func(unit_component, flows)
        }),
        sprintf('default flow unit %s', c('full', 'raw', 'variant'))
      )
    )
  
  definitions <- map(definitions, ~{
    def_specs <- .x
    map(def_specs, ~{
      def_property <- .y
      def_value <- def_specs[[def_property]]
      for (token_key in names(tokens)) {
        if (grepl(paste0("{", token_key, "}"), def_value)) {
          def_specs[[def_property]] <<- gsub(paste0("{", token_key, "}"), tokens[[token_key]](def_specs), def_value)
        }
      }
    })
    return(def_specs)
  })
  
  return(definitions)
}

replace_tags <- function(definitions, tags) {
  definitions_with_replacements <- list()
  
  for (def_name in names(definitions)) {
    def_specs <- definitions[[def_name]]
    
    if (!(paste0("{", tag, "}") %in% names(def_name))) {
      definitions_with_replacements[[def_name]] <- def_specs
    } else {
      for (item_name in names(tags)) {
        item_specs <- tags[[item_name]]
        item_desc <- ifelse('description' %in% names(item_specs), item_specs$description, item_name)
        def_name_new <- gsub(paste0("{", tag, "}"), item_name, def_name)
        def_specs_new <- dplyr::copy_to(def_specs)
        def_specs_new <- union(def_specs_new, item_specs)
        def_specs_new$description <- gsub(paste0("{", tag, "}"), item_desc, def_specs$description)
        
        for (k in names(def_specs_new)) {
          if (k == 'description' || !is.character(def_specs_new[[k]])) {
            next
          }
          def_specs_new[[k]] <- gsub(paste0("{", tag, "}"), item_name, def_specs_new[[k]])
          def_specs_new[[k]] <- gsub('{parent variable}', substr(def_name, 1, gregexpr(paste0("{", tag, "}"), def_name)[[1]] - 1), def_specs_new[[k]])
        }
        
        definitions_with_replacements[[def_name_new]] <- def_specs_new
      }
    }
  }
  
  return(definitions_with_replacements)
}

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
        return(paste0('', strsplit(flows[[def_specs$flow_id]]$default_unit, ';')[[1]][2]))
      } else {
        return('UNKNOWN')
      }
    }
  })
}
