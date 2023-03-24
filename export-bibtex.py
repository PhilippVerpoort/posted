#!/usr/bin/env python3


import csv

from pybtex.database.input import bibtex
from pybtex.database import parse_string
from pybtex.plugin import find_plugin


# define format function
def formatEntries(bib_data, style, form, exclude_fields = None):
    exclude_fields = exclude_fields or []

    if exclude_fields:
        for entry in bib_data.entries.values():
            for ef in exclude_fields:
                if ef in entry.fields.__dict__['_dict']:
                    del entry.fields.__dict__['_dict'][ef]

    ret = []
    for identifier in bib_data.entries:
        entry = bib_data.entries[identifier]
        ret.append({
            'identifier': identifier,
            'citation': next(style.format_entries([entry])).text.render(form),
            'doi': entry.fields.__dict__['_dict']['doi'],
            'url': entry.fields.__dict__['_dict']['url'],
        })

    return ret


# define styles and formats
style = find_plugin('pybtex.style.formatting', 'apa')()
format_html = find_plugin('pybtex.backends', 'html')()
format_plain = find_plugin('pybtex.backends', 'plaintext')()


# parse bibtex file
parser = bibtex.Parser()
bib_data = parser.parse_file('references.bib')


# call format function
formatted = formatEntries(bib_data, style, format_plain)


# output to file
with open('references-formatted.csv', 'w', newline='') as csvfile:
    fieldnames = ['identifier', 'citation', 'doi', 'url']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for row in formatted:
        writer.writerow(row)
