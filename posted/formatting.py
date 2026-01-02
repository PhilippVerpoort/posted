from typing import Optional
import re

from pybtex.plugin import find_plugin
from pybtex.database import BibliographyData


def format_sources(
        bib_data: BibliographyData,
        style: str = 'alpha',
        form: str = 'plaintext',
        exclude_fields: Optional[list] = None):
    """
    Takes a citation style, a citation format, and (optionally) excluded
    fields, and returns a formatted list of sources based on the specified
    style and format. The sources are loaded from 'references-data.bib' file.

    Parameters
    ----------
    style
        Specifies the formatting style for the bibliography entries.
    form
        Specifies the format in which the citation should be rendered.
        It determines how the citation information will be displayed or
        structured in the final output. This can be 'plaintext' or 'html'.
    exclude_fields
        Specifies a list of fields that should be excluded from the
        final output. These fields will be removed from the entries
        before formatting and returning the citation data.

    Returns
    -------
        list[dict]
            A list of dictionaries containing the identifier, citation,
            and URL information for each entry in the bibliography
            data, formatted according to the specified style and form,
            with any excluded fields removed.
    """
    # set exclude_fields to an empty list if provided as None
    exclude_fields = exclude_fields or []

    # load pybtext styles and formats based on arguments
    pyb_style = find_plugin('pybtex.style.formatting', style)()
    pyb_format = find_plugin('pybtex.backends', form)()

    # exclude undesired fields
    if exclude_fields:
        for entry in bib_data.entries.values():
            for ef in exclude_fields:
                if ef in entry.fields.__dict__['_dict']:
                    del entry.fields.__dict__['_dict'][ef]

    # loop over entries and format accordingly
    ret = {}
    for identifier in bib_data.entries:
        try:
            entry = bib_data.entries[identifier]
            fields = entry.fields.__dict__['_dict']

            cite_auth = ' '.join(entry.persons.get("author", [])[0].last_names).replace('{', '').replace('}', '')
            cite_year = entry.fields.get("year", "n.d.")

            doi = entry.fields.get("doi", None)
            url = entry.fields.get("url", None)
            pdf = entry.fields.get("pdf", None)
            url_doi = f"https://doi.org/{doi}" if doi else None

            if doi:
                del entry.fields["doi"]
            if url:
                del entry.fields["url"]
            if pdf:
                del entry.fields["pdf"]

            ret[identifier] = {
                "cite_auth": cite_auth,
                "cite_year": cite_year,
                "cite": f"{cite_auth} ({cite_year})",
                "citep": f"({cite_auth}, {cite_year})",
                "bib": next(pyb_style.format_entries([entry])).text.render(pyb_format),
                "doi": doi,
                "url_doi": url_doi,
                "url": url or url_doi,
                "pdf": pdf,
            }
        except Exception as ex:
            raise Exception(f"Error occurred while parsing '{identifier}':\n{ex}")

    # return dict(sorted(ret.items(), key=lambda item: (item[1]['cite_auth'], item[1]['cite_year'])))
    return ret


def insert_citations(text: str, citations: dict[str], link: None | str = None):
    """
    Inserts citations into a text passed as a string.

    Parameters
    ----------
    text
        Text that contains replacement patterns for citations.
    citations
        Formatted citations for each identifier.

    Returns
    -------
        str
            The updated text, which has the patterns replaced with citations.
    """
    return re.sub(
        r'{{(cite|citep):([^}]+)}}',
        lambda m: (
            (f"<a href=\"{link}#{m.group(2)}\">" if link else '') + 
            citations.get(m.group(2), {}).get(m.group(1), m.group(0)) + 
            ('</a>' if link else '')
        ),
        text,
    )
