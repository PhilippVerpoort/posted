source("R/posted/read.R")
source("R/posted/path.R")
source("R/posted/definitions.R")

# Loop over databases
flows <- techs <- list()

for (database_path in databases) {
  # Read flow types
  flow_types <- read_csv_file(file.path(database_path, 'flow_types.csv'))
  flow_types <- reshape2::dcast(flow_types, flow_id ~ attribute, value.var = 'value')
  flows <- purrr::modify(flows, purrr::modify_at, names(flow_types), ~ as.list(flow_types))

  # Read technologies
  tech_types <- read_csv_file(file.path(database_path, 'tech_types.csv'))
  techs <- purrr::modify(techs, purrr::modify_at, tech_types$tech_id, ~ as.list(tech_types))
}

# Loop over databases and read definitions
variables <- list()

for (database_path in databases) {
  # Load variable definitions
  variable_definitions <- read_definitions(file.path(database_path, 'definitions', 'variable'), flows, techs)
  variables <- purrr::modify(variables, purrr::modify_at, names(variable_definitions), ~ as.list(variable_definitions))
}
