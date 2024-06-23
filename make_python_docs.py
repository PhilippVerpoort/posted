import os
# print(os.listdir())
import yaml



import ast

def has_documentable_function_or_class(file_path):
    """ Checks if a a .py file has a function of class which should be included in the docs

    Parameters
    ----------
    file_path: str
        path of the file to check

    Returns
    -------
    bool
        ture if there is at least one documentable function or class"""
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if ast.get_docstring(node):
                return True
    return False

# Define the path to the directory with the python code
code_dir_path = 'python/posted'
# load mkdocs.yml file
with open('mkdocs.yml', 'r') as file:
    mkdocs = yaml.safe_load(file)

# read in file names of the python code and sort them
code_file_names = os.listdir(code_dir_path)
code_file_names.sort()

# Loop through each file in the directory
for file_name in code_file_names:

    # Construct the full file path
    code_file_path = os.path.join(code_dir_path, file_name)

    # Ensure we are working with a (python) file (not a directory)
    if os.path.isfile(file_path) and file_name.endswith(".py"):
        if file_name == "__init__.py":
            continue

        # process files that have documentable functions or classes
        if has_documentable_function_or_class(file_path):

            modified_name = file_name
            modified_name = modified_name[:-3] # cut of .py suffix


            # Add the documentation of the functions to a markdwon file
            content = f"""::: python.posted.{modified_name}
        """

            # Define the path where to save the markdown file of the module
            doc_folder_path = "docs/python_modules"
            doc_file_path = os.path.join(doc_folder_path, f"docs_{modified_name}.md")

            # Create the folder if it doesn't exist
            os.makedirs(doc_folder_path, exist_ok=True)

            # Write the content to the markdown file
            with open(doc_file_path, "w") as file:
                file.write(content)



            # Check if the "Python" section exists in the mkdocs file:
            for i in range(len(mkdocs["nav"])):
                if "Documentation" in mkdocs["nav"][i]: # go  into Documentation section
                    for k in range(len(mkdocs["nav"][i]["Documentation"])):
                        if "Python" in mkdocs["nav"][i]["Documentation"][k]: # go into python section
                            if mkdocs["nav"][i]["Documentation"][k]["Python"] is None:
                                mkdocs["nav"][i]["Documentation"][k]["Python"] = []

                            exists_counter = False # tracks if file already exists in the navigation tree
                            for l in range(len(mkdocs["nav"][i]["Documentation"][k]["Python"])):

                                # go to the section of the modified_name file and override it
                                if modified_name in mkdocs["nav"][i]["Documentation"][k]["Python"][l]:
                                    #print(True)
                                    mkdocs["nav"][i]["Documentation"][k]["Python"][l] = {modified_name: f'python_modules/docs_{modified_name}.md'}
                                    exists_counter = True
                                    break
                            # if there was no file found with the name, create a new entry in the navigation section
                            if exists_counter is False:
                                mkdocs["nav"][i]["Documentation"][k]["Python"].append({modified_name: f'python_modules/docs_{modified_name}.md'})


# Save the modified YAML file
with open('mkdocs.yml', 'w') as file:
    yaml.dump(mkdocs, file)





