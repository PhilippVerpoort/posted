from pathlib import Path


class AbstractVariableDefinition:
    """
    Abstract class to define variables

    Parameters
    ----------
    name: str
        Name of the column
    description: str
        Description of the column
    dtype:
        Data type of the column
    required: bool
        Bool that specifies if the column is required

    Methods
    -------
        is_allowed
            Check if cell is allowed
    """
    pass


def read_variables(definitions_dir: Path, flows: dict, techs: dict):
    """
    Reads YAML files

    Parameters
    ----------
    definitions_dir : Path
        Path leading to the definitions
    flows : dict
        Dictionary containng the different flow types. Each key
        represents a flow type, the corresponding value is a dictionary
        containing key value pairs of attributes like denisty,
        energycontent and their values.
    techs : dict
        Dictionary containing information about different technologies.
        Each key in the dictionary represents a unique technology ID,
        and the corresponding value is a dictionary containing various
        specifications for that technology, like 'description', 'class',
        'primary output' etc.

    Returns
    -------
        dict
            Dictionary containing the definitions after processing and
            replacing tags and tokens
    """
    # check that variables exists and is a directory
    if not definitions_dir.exists():
        return {}
    if not definitions_dir.is_dir():
        raise Exception(f"Should be a directory but is not: {definitions_dir}")

    # read all definitions and tags
    definitions = {}
    tags = {}
    for file_path in definitions_dir.rglob('*.yml'):
        if file_path.name.startswith('tag_'):
            tags |= read_yml_file(file_path)
        else:
            definitions |= read_yml_file(file_path)

    # read tags from flows and techs
    tags['Flow IDs'] = {
        flow_id: {}
        for flow_id, flow_specs in flows.items()
    }
    tags['Tech IDs'] = {
        tech_id: {
            k: v
            for k, v in tech_specs.items()
            if k in ['primary_output']
        }
        for tech_id, tech_specs in techs.items()
    }

    # insert tags
    for tag, items in tags.items():
        definitions = replace_tags(definitions, tag, items)

    # remove definitions where tags could not been replaced
    if any('{' in key for key in definitions):
        warnings.raise_warnings('Tokens could not be replaced correctly.')
        definitions = {k: v for k, v in definitions.items() if '{' not in k}

    # insert tokens
    tokens = {
        'default currency': lambda def_specs: default_currency,
        'primary output': lambda def_specs: def_specs['primary_output'],
    } | {
        f"default flow unit {unit_component}": unit_token_func(unit_component,
                                                               flows)
        for unit_component in ('full', 'raw', 'variant')
    }
    for def_key, def_specs in definitions.items():
        for def_property, def_value in def_specs.items():
            for token_key, token_func in tokens.items():
                if (isinstance(def_value, str) and
                    f"{{{token_key}}}" in def_value):
                    def_specs[def_property] = (
                        def_specs[def_property].replace(f"{{{token_key}}}",
                                                        token_func(def_specs))
                    )

    return definitions
