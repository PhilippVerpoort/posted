from pybtex.database.input import bibtex
from pybtex.database import BibliographyData

from .. import databases


def load_sources(database_id: str) -> BibliographyData:
    """
    Load sources from BibTeX files in database(s).

    Parameters
    ----------
    database_id: str | None
        The ID of the database, which should be contained in the public `databases` property of the `posted` package.

    Returns
    -------
    BibliographyData
        An object containing bibliographic data. This object is typically best passed on to `format_sources` from
        `posted.formatting`. Alternatively, the data can manually be processed with the `pybtex` package.
    """
    sources_file_path = databases[database_id] / "sources.bib"
    with sources_file_path.open("r") as file_stream:
        return bibtex.Parser().parse_file(file_stream)
