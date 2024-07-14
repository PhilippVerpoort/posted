import copy
import warnings
from pathlib import Path
from typing import Literal

from posted.settings import default_currency
from posted.read import read_yml_file


def read_definitions(definitions_dir: Path, flows: dict, techs: dict):
    '''
    Reads YAML files from definitions directory, extracts tags, inserts tags into
    definitions, replaces tokens in definitions, and returns the updated definitions.

    Parameters
    ----------
    definitions_dir : Path
        Path leading to the definitions
    flows : dict
        Dictionary containng the different flow types. Each key represents a flow type, the corresponding
        value is a dictionary containing key value pairs of attributes like denisty, energycontent and their
        values.
    techs : dict
        Dictionary containing information about different technologies. Each key in the
        dictionary represents a unique technology ID, and the corresponding value is a dictionary containing
        various specifications for that technology, like 'description', 'class', 'primary output' etc.

    Returns
    -------
        dict
            Dictionary containing the definitions after processing and replacing tags and tokens
    '''
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
        warnings.warn('Tokens could not be replaced correctly.')
        definitions = {k: v for k, v in definitions.items() if '{' not in k}

    # insert tokens
    tokens = {
        'default currency': lambda def_specs: default_currency,
        'primary output': lambda def_specs: def_specs['primary_output'],
    } | {
        f"default flow unit {unit_component}": unit_token_func(unit_component, flows)
        for unit_component in ('full', 'raw', 'variant')
    }
    for def_key, def_specs in definitions.items():
        for def_property, def_value in def_specs.items():
            for token_key, token_func in tokens.items():
                if isinstance(def_value, str) and f"{{{token_key}}}" in def_value:
                    def_specs[def_property] = def_specs[def_property].replace(
                        f"{{{token_key}}}", token_func(def_specs))

    return definitions


def replace_tags(definitions: dict, tag: str, items: dict[str, dict]):
    '''
    Replaces specified tags in dictionary keys and values with corresponding
    items from another dictionary.

    Parameters
    ----------
    definitions : dict
        Dictionary containing the definitions, where the tags should be replaced by the items
    tag : str
        String to identify where replacements should be made in the definitions. Specifies
        the placeholder that needs to be replaced with actual values from the `items` dictionary.
    items : dict[str, dict]
        Dictionary containing the items from whith to replace the definitions

    Returns
    -------
        dict
            Dictionary containing the definitions with replacements based on the provided tag and items.
    '''

    definitions_with_replacements = {}
    for def_name, def_specs in definitions.items():
        if f"{{{tag}}}" not in def_name:
            definitions_with_replacements[def_name] = def_specs
        else:
            for item_name, item_specs in items.items():
                item_desc = item_specs['description'] if 'description' in item_specs else item_name
                def_name_new = def_name.replace(f"{{{tag}}}", item_name)
                def_specs_new = copy.deepcopy(def_specs)
                def_specs_new |= item_specs

                # replace tags in description
                def_specs_new['description'] = def_specs['description'].replace(
                    f"{{{tag}}}", item_desc)

                # replace tags in other specs
                for k, v in def_specs_new.items():
                    if k == 'description' or not isinstance(v, str):
                        continue
                    def_specs_new[k] = def_specs_new[k].replace(
                        f"{{{tag}}}", item_name)
                    def_specs_new[k] = def_specs_new[k].replace(
                        '{parent variable}', def_name[:def_name.find(f"{{{tag}}}")-1])
                definitions_with_replacements[def_name_new] = def_specs_new

    return definitions_with_replacements


def unit_token_func(unit_component: Literal['full', 'raw', 'variant'], flows: dict):
    '''
    Takes a unit component type and a dictionary of flows, and returns a lambda function
    that extracts the default unit based on the specified component type from the flow
    dictionary.

    Parameters
    ----------
    unit_component : Literal['full', 'raw', 'variant']
        Specifies the type of unit token to be returned.
    flows : dict
        Dictionary containg the flows


    Returns
    -------
        lambda function
            lambda function that takes a dictionary `def_specs` as input. The lambda function
            will return different values based on the `unit_component` parameter and
            the contents of the `flows` dictionary.
    '''
    return lambda def_specs: (
        'ERROR'
        if 'flow_id' not in def_specs or def_specs['flow_id'] not in flows else
        (
            flows[def_specs['flow_id']]['default_unit']
            if unit_component == 'full' else
            flows[def_specs['flow_id']]['default_unit'].split(';')[0]
            if unit_component == 'raw' else
            ';'.join([''] + flows[def_specs['flow_id']]
                     ['default_unit'].split(';')[1:2])
            if unit_component == 'variant' else
            'UNKNOWN'
        )
    )
