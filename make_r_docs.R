library(devtools)
library(fs)
library(yaml)
library(tools)
library(stringr)



extract_function_titles <- function(r_file) {
  script_content <- readLines(r_file)
  titles <- list()

  current_title <- NULL
  for (line in script_content) {
    if (str_detect(line, "^#' @title")) {
      current_title <- str_replace(line, "^#' @title\\s+(.*)", "\\1")
      titles <- c(titles, current_title)
    }
  }
  return(titles)
}

# Generate R documentation with Roxagen2
document()


# Define the path to the directory

# Directory containing the R scripts
r_dir <- "R"

# List all R files in the directory
r_files <- list.files(r_dir, pattern = "\\.R$", full.names = TRUE)
# print(r_files)

# Extract function titles for each R script
file_titles_list <- lapply(r_files, extract_function_titles)
names(file_titles_list) <- basename(r_files)

# Print the extracted information
print(file_titles_list)

# List all R files in the directory
r_files <- list.files(r_dir, pattern = "\\.R$", full.names = TRUE)

# List all files in the directory for rd files
file_list <- dir_ls("man", type = "file")


# Define the path to the mkdocs.yml file
yaml_file <- "mkdocs.yml"

# Read the YAML file
yaml_content <- read_yaml(yaml_file)


# Loop through each .rd file
for (title_name in names(file_titles_list)) {
  print("title name")
  print(title_name)

  for (name in file_titles_list[[title_name]]) {
    # print(file_list)
    print(name)
    if (!(paste0("man/", name, ".Rd") %in%  file_list) ){
      print("next")
      next
    }
    modified_name <- name
    # convert file to md file and save in docs/R_functions
    system(paste('rd2md man docs/R_functions', modified_name))

    # Find the 'Documentation' section and add the new item to the 'R' subsection
    for (i in seq_along(yaml_content$nav)) {
      item <- yaml_content$nav[[i]]
      if (is.list(item) && "Documentation" %in% names(item)) {
        for (j in seq_along(item$Documentation)) {
          subitem <- item$Documentation[[j]]
          if (is.list(subitem) && "R" %in% names(subitem)) {

            temp_list <- list()
            temp_list[[modified_name]] <- paste0('R_functions/', modified_name, '.md')
            # print("temp list")
            # print(temp_list)
            # print(subitem$R)
            # counter to check if a page with modified_ame already exists
            dir_exists_counter <- FALSE
            for (k in seq_along(subitem$R)) {
              # print("name?")
              if(names(subitem$R[[k]]) == modified_name) {
                  # if the page exists, override the entry with the new version
                  subitem$R[[k]] <- temp_list
                  dir_exists_counter <- TRUE
              }
            }

            # if there is a new file, append it at the end
            if(dir_exists_counter == FALSE) {
              subitem$R[[length(subitem$R) + 1]] <- temp_list
            }
          #   print('after')
          #   print(subitem$R)
            yaml_content$nav[[i]]$Documentation[[j]] <- subitem
            break
          }
        }
      }
    }
  }
}
    # Print the modified content
  # print(yaml_content)



# Write the modified content back to the YAML file
write_yaml(yaml_content, yaml_file)


print("finished writing")
