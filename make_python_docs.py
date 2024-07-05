import os
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
    if os.path.isfile(code_file_path) and file_name.endswith(".py"):
        if file_name == "__init__.py":
            continue

        # process files that have documentable functions or classes
        if has_documentable_function_or_class(code_file_path):

            modified_name = file_name
            modified_name = modified_name[:-3] # cut of .py suffix


            # Add the documentation of the functions to a markdwon file
            content = f"""::: python.posted.{modified_name}
        """

            # Define the path where to save the markdown file of the module
            doc_folder_path = "docs/code/python"
            doc_file_name = f"{modified_name}.md"
            doc_file_path = os.path.join(doc_folder_path, doc_file_name)

            # Create the folder if it doesn't exist
            os.makedirs(doc_folder_path, exist_ok=True)

            # Write the content to the markdown file
            with open(doc_file_path, "w") as file:
                file.write(content)


            code_index = None
            python_index = None

            # find index of Code section in the mkdocs file
            for i in range(len(mkdocs["nav"])):
                if "Code" in mkdocs["nav"][i]:
                    code_index = i

            # if there is no code section, create it
            if code_index is None:
                code_index = len(mkdocs["nav"])
                mkdocs["nav"].append({"Code":[]})


            # if there is a code section, but it has no content, create a list to be filled
            if mkdocs["nav"][code_index]["Code"] is None:
                mkdocs["nav"][code_index]["Code"] = []


            # find index of the python section
            for k in range(len(mkdocs["nav"][code_index]["Code"])):
                if "Python" in mkdocs["nav"][code_index]["Code"][k]: # go into python section
                    python_index = k
            print(python_index)
            # if there is no python section, create it
            if python_index is None:
                python_index = len(mkdocs["nav"][code_index]["Code"])
                mkdocs["nav"][code_index]["Code"].append({"Python":[]})


            print
            # if there is a python section, but it has no content, create a list to be filled
            if mkdocs["nav"][code_index]["Code"][python_index]["Python"] is None:
                mkdocs["nav"][code_index]["Code"][python_index]["Python"] = []

            exists_counter = False # tracks if file already exists in the navigation tree
            for l in range(len(mkdocs["nav"][code_index]["Code"][python_index]["Python"])):

                # go to the section of the modified_name file and override it
                if modified_name in mkdocs["nav"][code_index]["Code"][python_index]["Python"][l]:
                    #print(True)
                    mkdocs["nav"][code_index]["Code"][python_index]["Python"][l] = {modified_name: f'code/python/{doc_file_name}'}
                    exists_counter = True
                    break
            # if there was no file found with the name, create a new entry in the navigation section
            if exists_counter is False:
                mkdocs["nav"][code_index]["Code"][python_index]["Python"].append({modified_name: f'code/python/{doc_file_name}'})


# Save the modified YAML file
with open('mkdocs.yml', 'w') as file:
    yaml.dump(mkdocs, file)

print("made python docs")



