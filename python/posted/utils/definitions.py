import copy
import itertools
import warnings
from pathlib import Path
from typing import Literal

from posted.settings import default_currency
from posted.utils.read import read_yml_file


def read_definitions(directory_path: Path, flows: dict, techs: dict):
    assert directory_path.is_dir()

    # read all definitions and tags
    definitions = {}
    tags = {}
    for file_path in directory_path.rglob('*.yml'):
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
        tech_id: {key: val for key, val in tech_specs.items() if key in ['reference_flow_id', 'case_fields']}
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
    } | {
        f"default {subtype} flow unit {unit_component}": unit_token_func(subtype, unit_component, flows)
        for subtype in ('reported', 'reference')
        for unit_component in ('full', 'raw', 'variant')
    }
    for def_key, def_specs in definitions.items():
        for def_property, def_value in def_specs.items():
            for token_key, token_func in tokens.items():
                if f"{{{token_key}}}" in def_value:
                    def_specs[def_property] = def_specs[def_property].replace(f"{{{token_key}}}", token_func(def_specs))

    return definitions


def list_cases(case_fields: dict):
    cases = []
    for case_field_combinations in itertools.chain.from_iterable(itertools.combinations(case_fields.values(), r) for r in range(len(case_fields)+1)):
        cases.extend([' '.join(list(e)) for e in itertools.product(*case_field_combinations)])

    return cases


def replace_tags(definitions: dict, tag: str, items: dict[str]):
    definitions_with_replacements = {}
    for def_name, def_specs in definitions.items():
        if f"{{{tag}}}" not in def_name:
            definitions_with_replacements[def_name] = def_specs
        else:
            for item_name, item_specs in items.items():
                cases = [''] if 'case_fields' not in item_specs else list_cases(item_specs['case_fields'])
                for case_name in cases:
                    item_name_case = item_name if not case_name else f"{item_name} {case_name}"
                    item_desc = item_specs['description'] if 'description' in item_specs else item_name_case
                    def_name_new = def_name.replace(f"{{{tag}}}", item_name_case)
                    def_specs_new = copy.deepcopy(def_specs)
                    def_specs_new |= item_specs
                    def_specs_new['description'] = def_specs['description'].replace(f"{{{tag}}}", item_desc)
                    for k, v in def_specs_new.items():
                        if k == 'description' or not isinstance(v, str):
                            continue
                        def_specs_new[k] = v.replace(f"{{{tag}}}", item_name_case)
                    definitions_with_replacements[def_name_new] = def_specs_new

    return definitions_with_replacements


def unit_token_func(subtype: Literal['reported', 'reference'], unit_component: Literal['full', 'raw', 'variant'], flows: dict):
    return lambda def_specs: (
        'ERROR'
        if f"{subtype}_flow_id" not in def_specs or def_specs[f"{subtype}_flow_id"] not in flows else
        (
            flows[def_specs[f"{subtype}_flow_id"]]['default_unit']
            if unit_component == 'full' else
            flows[def_specs[f"{subtype}_flow_id"]]['default_unit'].split(';')[0]
            if unit_component == 'raw' else
            ';'.join([''] + flows[def_specs[f"{subtype}_flow_id"]]['default_unit'].split(';')[1:2])
            if unit_component == 'variant' else
            'UNKNOWN'
        )
    )
