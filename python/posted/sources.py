from pathlib import Path

import pandas as pd
from pybtex.database.input import bibtex
from pybtex.plugin import find_plugin

from posted.path import databases


def format_sources(bib_data, style, form, exclude_fields = None):
    '''
    Takes bibliographic data, a citation style, a citation form, and
    optional excluded fields, and returns a formatted list of sources based on the specified style and
    form.

    Parameters
    ----------
    bib_data
        Contains bibliographic information, such as author, title, references or citations.
    style
        Specifies the formatting style for the bibliography entries.
    form
        Specifies the format in which the citation should be rendered. It determines how the citation information will be displayed or
        structured in the final output.
    exclude_fields
        Specifies a list of fields that should be excluded from the final output. These fields will be removed from the entries before
    formatting and returning the citation data.

    Returns
    -------
        list[dict]
            A list of dictionaries containing the identifier, citation, DOI, and URL information for each entry
            in the bibliography data, formatted according to the specified style and form, with any excluded
            fields removed.

    '''
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



def dump_sources(file_path: str | Path):
    '''Parses BibTeX files, formats the data, and exports it into a CSV or Excel
    file using pandas.

    Parameters
    ----------
    file_path : str | Path
        Path to the file where the formatted sources should be exported to.
         It can be either a string representing the file path or a `Path` object
        from the `pathlib` module.

    '''
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
