from pathlib import Path

import pandas as pd
from pybtex.database.input import bibtex
from pybtex.plugin import find_plugin

from posted.path import databases


# define format function
def format_sources(bib_data, style, form, exclude_fields = None):
    exclude_fields = exclude_fields or []

    if exclude_fields:
        for entry in bib_data.entries.values():
            for ef in exclude_fields:
                if ef in entry.fields.__dict__['_dict']:
                    del entry.fields.__dict__['_dict'][ef]

    ret = []
    for identifier in bib_data.entries:
        entry = bib_data.entries[identifier]
        fields = entry.fields.__dict__['_dict']
        ret.append({
            'identifier': identifier,
            'citation': next(style.format_entries([entry])).text.render(form),
            'doi': fields['doi'] if 'doi' in fields else '',
            'url': fields['url'] if 'url' in fields else '',
        })

    return ret


# export source to file
def dump_sources(file_path: str | Path):
    # convert string to pathlib.Path if necessary
    if isinstance(file_path, str):
        file_path = Path(file_path)

    # define styles and formats
    style = find_plugin('pybtex.style.formatting', 'apa')()
    # format_html = find_plugin('pybtex.backends', 'html')()
    format_plain = find_plugin('pybtex.backends', 'plaintext')()

    # parse bibtex file
    parser = bibtex.Parser()

    # loop over databases
    formatted = []
    for database_path in databases.values():
        bib_data = parser.parse_file(database_path / 'sources.bib')
        formatted += format_sources(bib_data, style, format_plain)

    # convert to dataframe
    df = pd.DataFrame.from_records(formatted)

    # dump dataframe with pandas to CSV or Excel spreadsheet
    if file_path.suffix == '.csv':
        df.to_csv(Path(file_path))
    elif file_path.suffix in ['.xls', '.xlsx']:
        df.to_excel(Path(file_path))
    else:
        raise Exception('Unknown file suffix!')
