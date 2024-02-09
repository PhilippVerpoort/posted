source("R/posted/read.R")
source("R/posted/path.R")
source("R/posted/definitions.R")

# Loop over databases
flows <-  list()
techs <- list()
for (database_path in databases) {
  # Read flow types
  flow_types <- read_csv_file(file.path(database_path, 'flow_types.csv'))
  unique_indexes <- distinct(select(flow_types, flow_id))
  unique_column_names <- distinct(select(flow_types, attribute))
  print(unique_indexes$flow_id)
  print(unique_column_names$attribute)
  
  for (flow_id in unique_indexes$flow_id) {
    print(flow_id)
    # print(df$flow_id)
    subset_df <- flow_types[flow_types$flow_id == flow_id,]
    # print(subset_df)
    print(subset_df)

    df_list <- split(subset_df$value, subset_df$attribute)

    # Convert each data frame into a named list
    result_list <- lapply(df_list, setNames, as.list)
    print("result_name")
    print(result_list)

    flow_values <- mapply(setNames, subset_df$attribute, subset_df$value, SIMPLIFY = FALSE)


    # print(flow_values['name'])
   
  }

  flow_types <- pivot_wider(flow_types,names_from=attribute, values_from=value )
  
  print("flow_types")
  print(flow_types)
  flows <- c(flows, flow_types)

  # Read technologies
  tech_types <- read_csv_file(file.path(database_path, 'tech_types.csv'))
  techs <- purrr::modify(techs, purrr::modify_at, tech_types$tech_id, ~ as.list(tech_types))
}

# Loop over databases and read definitions
variables <- list()

for (database_path in databases) {
  # Load variable definitions
  print("flows_techs_config")
  print(flows)
  print(techs)
  variable_definitions <- read_definitions(file.path(database_path, 'definitions', 'variable'), flows, techs)
  print(variable_definitions)
  variables <- purrr::modify(variables, purrr::modify_at, names(variable_definitions), ~ as.list(variable_definitions))
}
