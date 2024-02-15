library(dplyr)
library(purrr)
library(tidyr)

source("R/posted/settings.R")
source("R/posted/read.R")
# Assuming you have the necessary functions and libraries loaded

read_definitions <- function(definitions_dir, flows, techs) {
  stopifnot(dir.exists(definitions_dir))
  print("read definitions")
  # read all definitions and tags
  definitions <- list()
  tags <- list()
  file_paths <- list.files(path = definitions_dir, pattern = "\\.yml$", recursive = TRUE, full.names = TRUE)
  
  for (file_path in file_paths) {
    # print(file_path)
    if (grepl("^tag_", basename(file_path))) {
      tags <- c(tags, read_yml_file(file_path))
    } else {
      definitions <- c(definitions, read_yml_file(file_path))
    }
  }
  
  

  # read tags from flows and techs
  tags[['Flow IDs']] <- map(flows, ~list())
  tags[['Tech IDs']] <- map(techs, function(item) {item['primary_output']})
 
  print("replace tags init")
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
  # print("tokens")
  # print(tokens)
  for (def_key in names(definitions)) {
    def_specs <- definitions[[def_key]]
    for (def_property in names(def_specs)) {
      def_value <- def_specs[[def_property]]
      for (token_key in names(tokens)) {
        token_func <- tokens[[token_key]]
        if (is.character(def_values) && grepl(paste0("\\{", token_key, "\\}"),def_value))
          def_specs[[def_property]] <- gsub(paste0("\\{", token_key, "\\}"), token_func(def_specs), def_specs[[def_property]])
      }
    }
  }
  
  return(definitions)
}

replace_tags <- function(definitions, tag, items) {
  # print("replace tags")
  definitions_with_replacements <- list()

  for (def_name in names(definitions)) {
    def_specs <- definitions[[def_name]]
    if (!(grepl(paste0("\\{", tag, "\\}"), def_name))) {
      
      # print("not")
    
      definitions_with_replacements[[def_name]] <- def_specs
    } else {
      # print("is")

      for (item_name in names(items)) {
        item_specs <-  items[[item_name]]
        item_desc <- ifelse('description' %in% names(item_specs), item_specs[['description']], item_name)
        
        def_name_new <- gsub(paste0("\\{", tag, "\\}"), item_name, def_name)
        
        def_specs_new <- def_specs

        def_specs_new <- c(def_specs_new, item_specs)
        def_specs_new <- def_specs_new[unique(names(def_specs_new))]
        # print(def_specs_new)
        def_specs_new$description <- gsub(paste0("\\{", tag, "\\}"), item_desc, def_specs$description)
        
        for (k in names(def_specs_new)) {
          if (k == 'description' || !is.character(def_specs_new[[k]])) {
            next
          }
          def_specs_new[[k]] <- gsub(paste0("\\{", tag, "\\}"), item_name, def_specs_new[[k]])
          def_specs_new[[k]] <- gsub('\\{parent variable\\}', substr(def_name, 1, gregexpr(paste0("\\{", tag, "\\}"), def_name)[[1]] - 1), def_specs_new[[k]])
        }
        # print(def_specs_new)
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
