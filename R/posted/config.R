source("R/posted/read.R")
source("R/posted/path.R")
source("R/posted/definitions.R")


# Define data paths
DATA_PATH <- BASE_PATH  # Replace with the actual path to your data directory
config_path <- file.path(DATA_PATH, 'config')
base_format_path <- file.path(config_path, 'base_format.yml')

# Read data format and dtypes
base_format <- read_yml_file(base_format_path)
base_dtypes <- sapply(base_format, function(col_specs) col_specs$dtype)

# Default selection options
default_periods <- c(2030, 2040, 2050)

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
