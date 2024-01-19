import copy
import warnings
from pathlib import Path
from typing import Literal

from posted.settings import default_currency
from posted.read import read_yml_file


def read_definitions(definitions_dir: Path, flows: dict, techs: dict):
    assert definitions_dir.is_dir()

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
                    def_specs[def_property] = def_specs[def_property].replace(f"{{{token_key}}}", token_func(def_specs))

    return definitions


def replace_tags(definitions: dict, tag: str, items: dict[str, dict]):
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
                def_specs_new['description'] = def_specs['description'].replace(f"{{{tag}}}", item_desc)
                for k, v in def_specs_new.items():
                    if k == 'description' or not isinstance(v, str):
                        continue
                    def_specs_new[k] = def_specs_new[k].replace(f"{{{tag}}}", item_name)
                    def_specs_new[k] = def_specs_new[k].replace('{parent variable}', def_name[:def_name.find(f"{{{tag}}}")-1])
                definitions_with_replacements[def_name_new] = def_specs_new

    return definitions_with_replacements


def unit_token_func(unit_component: Literal['full', 'raw', 'variant'], flows: dict):
    return lambda def_specs: (
        'ERROR'
        if 'flow_id' not in def_specs or def_specs['flow_id'] not in flows else
        (
            flows[def_specs['flow_id']]['default_unit']
            if unit_component == 'full' else
            flows[def_specs['flow_id']]['default_unit'].split(';')[0]
            if unit_component == 'raw' else
            ';'.join([''] + flows[def_specs['flow_id']]['default_unit'].split(';')[1:2])
            if unit_component == 'variant' else
            'UNKNOWN'
        )
    )
