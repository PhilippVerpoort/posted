library(devtools)
library(fs)
library(yaml)
library(tools)
library(stringr)


# function to extract the function titles from an R file
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

# Generate R documentation with Roxygen2
document()

# define the Directory containing the R scripts
r_dir <- "R"
# Define the path to the mkdocs.yml file
yaml_file <- "mkdocs.yml"
# define the path for the r module files
module_file_path <- "docs/R_modules/"
# define the path for the r function files
function_file_path <- "docs/R_functions/"


# Check if the module path exists
if (!dir.exists(module_file_path)) {
  # If it doesn't exist, create the directories
  dir.create(module_file_path, recursive = TRUE)
  cat("Directory created:", module_file_path, "\n")
} else {
  cat("Directory already exists:", module_file_path, "\n")
}

# Check if the function path exists
if (!dir.exists(function_file_path)) {
  # If it doesn't exist, create the directories
  dir.create(function_file_path, recursive = TRUE)
  cat("Directory created:", function_file_path, "\n")
} else {
  cat("Directory already exists:", function_file_path, "\n")
}


# List all R files in the directory
r_files <- list.files(r_dir, pattern = "\\.R$", full.names = TRUE)


# Extract function titles for each R script
file_titles_list <- lapply(r_files, extract_function_titles)
names(file_titles_list) <- basename(r_files)
print("file_titles_list")
print(file_titles_list)

# list of all .Rd files in the man/ directory
rd_file_list <- dir_ls("man", type = "file")


# convert all documented functions that are stored in the man/ directory as .Rd files
# to .md files stored in docs/R_functions. Adjust the formatting of those files for later processing
for (rd_file in rd_file_list) {
  # remove the man/ prefix and the .Rd
  name <- sub("^man/(.*)\\.Rd$", "\\1", rd_file)
  system(paste('rd2md man docs/R_functions', name))

  # read in the markdown file of the function/class
  function_markdown <- readLines(paste0("docs/R_functions/", name, ".md"))

  # add title line to all R6 classes (because somehow this is not done by default, contrary to functions)
  if (length(function_markdown) == 0 || function_markdown[1] != paste0("# `", name, "`")) {

  # Add "# class_name" as the first line
  function_markdown <- c(paste0("# `", name, "`"), function_markdown)
  }

  # Go down one layer of navigation by adding an additional # to each title line
  # this is to conform with navigation standards in mkdocs, otherwise there would be no good navigation
  # in the documentation
  function_markdown <- sapply(function_markdown, function(line) {
  if (startsWith(line, "#")) {
    return(paste0("#", line))
  } else {
    return(line)
  }
  })

  # Write the modified lines back to the .md file
  writeLines(function_markdown, paste0("docs/R_functions/", name, ".md"))
}

print(".Rd processing complete")


# Read the YAML file
yaml_content <- read_yaml(yaml_file)

# Loop through all R modules. title name is the name of the R file
# add module to the navigation section of the mkdocs.yml file
# create markdown files whith snippets linking to all functions/classes belonging to this module
for (title_name in names(file_titles_list)) {
  print("start loop")
  print(title_name)
  # check if there is at least one documentable function in the file, if not, skip.
  if(length(file_titles_list[[title_name]]) == 0) {
    next
  }

  print(typeof(file_titles_list[[title_name]]))
  print(file_titles_list[[title_name]])

  mod_title_name <- substr(title_name, 1, nchar(title_name) - 2) # remove .R suffix


  # generate markdown file for R module which includes all functions/classes in a file
  markdown_file_content <- ""
  for (name in file_titles_list[[title_name]]) {

    # add snippet for each function/class to the module file
    markdown_file_content <- c(markdown_file_content,
      paste0('--8<-- "R_functions/', name,'.md"') #
    )
  }
  # write the markdown file
  writeLines(markdown_file_content, paste0(module_file_path, "docs_", mod_title_name, ".md"))

  # Find the 'Documentation' section in the mkdocs.yml file and add the new item to the 'R' subsection
  for (i in seq_along(yaml_content$nav)) {
    item <- yaml_content$nav[[i]]
    if (is.list(item) && "Documentation" %in% names(item)) {
      for (j in seq_along(item$Documentation)) {
        subitem <- item$Documentation[[j]]

        if (is.list(subitem) && "R" %in% names(subitem)) {
          # print(subitem$R)
          temp_list <- list()
          temp_list[[mod_title_name]] <- paste0('R_modules/docs_', mod_title_name, '.md')

          # counter to check if a page with modified_name already exists
          dir_exists_counter <- FALSE

          # loop through directory and override file with modified_name with the new version
          for (k in seq_along(subitem$R)) {
            print(k)
            print(names(subitem$R[[k]]))
            if(names(subitem$R[[k]]) == mod_title_name) {
                print("override")

                # if the page exists, override the entry with the new version
                subitem$R[[k]] <- temp_list
                dir_exists_counter <- TRUE
            }
          }
          print("after loop")
          # if there was no file to override add a new entry with the new file
          if(dir_exists_counter == FALSE) {
            subitem$R[[length(subitem$R) + 1]] <- temp_list
          }

          yaml_content$nav[[i]]$Documentation[[j]] <- subitem
          break
        }
      }
    }
  }
}





# Write the modified content back to the YAML file
write_yaml(yaml_content, yaml_file)


print("finished writing")
