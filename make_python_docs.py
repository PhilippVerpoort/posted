import os
# print(os.listdir())
import yaml
# Define the path to the directory
dir_path = 'python/posted'


import ast

def has_documentable_function_or_class(file_path):
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if ast.get_docstring(node):
                return True
    return False



with open('mkdocs.yml', 'r') as file:
    mkdocs = yaml.safe_load(file)

file_names = os.listdir(dir_path)
print(file_names)
file_names.sort()
print(file_names)
# Loop through each file in the directory
for file_name in file_names:

    # Construct the full file path
    file_path = os.path.join(dir_path, file_name)
    print(file_path)
    # Ensure we are working with a file (not a directory)
    if os.path.isfile(file_path) and file_name.endswith(".py"):
        if file_name == "__init__.py":
            continue
        if has_documentable_function_or_class(file_path):

            # Remove the "man/" prefix and ".rd" suffix
            modified_name = file_name
            modified_name = modified_name[:-3]

            # # Print the modified name
            # print(modified_name)


            # Define the content of the markdown file
            content = f"""::: python.posted.{modified_name}
        """

            # Define the path of the folder and file
            folder_path = "docs/python_modules"
            file_path = os.path.join(folder_path, f"docs_{modified_name}.md")

            # Create the folder if it doesn't exist
            os.makedirs(folder_path, exist_ok=True)

            # Write the content to the markdown file
            with open(file_path, "w") as file:
                file.write(content)

            # print(f"Markdown file created and saved at: {file_path}")

            # Check if the "Python" section exists
            for i in range(len(mkdocs["nav"])):
                if "Documentation" in mkdocs["nav"][i]:
                    for k in range(len(mkdocs["nav"][i]["Documentation"])):
                        if "Python" in mkdocs["nav"][i]["Documentation"][k]:
                            if mkdocs["nav"][i]["Documentation"][k]["Python"] is None:
                                mkdocs["nav"][i]["Documentation"][k]["Python"] = []
                            exists_counter = False
                            for l in range(len(mkdocs["nav"][i]["Documentation"][k]["Python"])):
                                #print(mkdocs["nav"][i]["Documentation"][k]["Python"][l])
                                #print(modified_name)
                                if modified_name in mkdocs["nav"][i]["Documentation"][k]["Python"][l]:
                                    #print(True)
                                    mkdocs["nav"][i]["Documentation"][k]["Python"][l] = {modified_name: f'python_modules/docs_{modified_name}.md'}
                                    exists_counter = True
                                    break
                            if exists_counter is False:
                                mkdocs["nav"][i]["Documentation"][k]["Python"].append({modified_name: f'python_modules/docs_{modified_name}.md'})


# Save the modified YAML file
with open('mkdocs.yml', 'w') as file:
    yaml.dump(mkdocs, file)





