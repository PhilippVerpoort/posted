# source("R/posted/read.R")
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

  new_df <- data.frame(matrix(ncol=length(unique_column_names$attribute)+1, nrow=length(unique_indexes$flow_id)))
  colnames(new_df) <-c("index", unique_column_names$attribute)

  new_df$index <- unique_indexes$flow_id
  for (index in unique_indexes$flow_id) {

    subset_df <- flow_types[flow_types$flow_id == index,]

    temp <- list()
    for (i in subset_df$attribute) {
      temp[[i]] <- subset_df[subset_df$attribute==i, 'value']
    }
    flows[[index]] <- temp
  }

  tech_types = read_csv_file(file.path(database_path, 'tech_types.csv'))
  techs <- apply(tech_types, 1, function(row) {
     temp <- list()
    for (i in 2:length(row)) {
         temp[[names(row[i])]] <- row[[i]]
    }
    return(temp)
  })
}
names(techs) <- tech_types$tech_id



# Loop over databases and read definitions
variables <- list()

for (database_path in databases) {
  # Load variable definitions

  variables <-  c(variables, read_definitions(file.path(database_path, 'definitions', 'variable'), flows, techs))


}

# # Define a global variable to store the cached value
# cached_variables <- NULL

# # Function to load the variable from file or retrieve it from cache
# load_or_retrieve_variable <- function() {
#   if (!is.null(cached_variables)) {
#     # If the variable is already cached, return it
#     return(cached_variables)
#   } else {
#     for (database_path in databases) {
#     # Load variable definitions

#     cached_variables <-  c(variables, read_definitions(file.path(database_path, 'definitions', 'variable'), flows, techs))


# }
#     return(cached_variables)
#   }
# }

# # Function to access the variable
# access_variables <- function() {
#   variable <- load_or_retrieve_variable()
#   # Use the variable as needed
#   return(variable)
# }

# # Example usage
# # variables <- access_variable()

