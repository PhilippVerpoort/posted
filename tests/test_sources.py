import unittest

from pybtex.database.input import bibtex
from pybtex.plugin import find_plugin

from posted.path import databases
from posted.sources import format_sources


class sources(unittest.TestCase):
    # parse all sources bibtex files
    def test_parse(self):
        parser = bibtex.Parser()
        for database_path in databases.values():
            parser.parse_file(database_path / 'sources.bib')

    # format all entries in bibtex files
    def test_format(self):
        parser = bibtex.Parser()
        style = find_plugin('pybtex.style.formatting', 'apa')()
        format_plain = find_plugin('pybtex.backends', 'plaintext')()
        for database_path in databases.values():
            bib_data = parser.parse_file(database_path / 'sources.bib')
            format_sources(bib_data, style, format_plain)
