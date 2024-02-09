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
  # print(tech_types)

  
  techs <- apply(tech_types, 1, function(row) {
     temp <- list()
     
    for (i in 2:length(row)) {
      
     
      temp[[names(row[i])]] <- row[[i]]
     
      
   

    }
 
    return(temp)
  })
   
   


  


# Set names of the list elements
names(techs) <- tech_types$tech_id
print(techs$'MEOH-2-OLEF')


#   # Read technologies
#   tech_types <- read_csv_file(file.path(database_path, 'tech_types.csv'))
#   techs <- purrr::modify(techs, purrr::modify_at, tech_types$tech_id, ~ as.list(tech_types))
 }

 print("assigned flows")

# Loop over databases and read definitions
variables <- list()

for (database_path in databases) {
  # Load variable definitions
  print("flows_techs_config")
  #print(flows)
 # print(techs)
  variable_definitions <- read_definitions(file.path(database_path, 'definitions', 'variable'), flows, techs)
  #print(variable_definitions)
  variables <- purrr::modify(variables, purrr::modify_at, names(variable_definitions), ~ as.list(variable_definitions))
}
