import unittest

import pandas as pd

from posted import databases, load_sources, format_sources
from posted.read import read_csv_file


class sources(unittest.TestCase):
    # Load and parse the public BibTeX source file.
    def test_loading(self):
        try:
            load_sources("public")
        except Exception as ex:
            raise Exception(f"Could not load BibTeX file:\n{ex}")

    # Ensure that all source identifiers used in TEDFs have a corresponding entry in BibTeX.
    def test_tedfs_no_undefined(self):
        sources_bibtex = list(load_sources("public").entries)

        for file_path in (databases["public"] / "tedfs").rglob("*.csv"):
            df = read_csv_file(file_path)
            assert "source" in df.columns, "The 'sources' column of a TEDF must be present."
            missing = ~df["source"].isin(sources_bibtex)
            if missing.any():
                raise Exception(f"Source identifiers found in '{file_path.name}' but not in BibTeX:" +
                                ", ".join(df.loc[missing, "source"]))

    # Ensure that all source identifiers in BibTeX occur in TEDFs at least once.
    def test_bibtex_no_unused(self):
        sources_tedfs = pd.concat([
            read_csv_file(file_path)["source"]
            for file_path in (databases["public"] / "tedfs").rglob("*.csv")
        ]).unique()

        sources_bibtex = list(load_sources("public").entries)

        for s in sources_bibtex:
            if not s in sources_tedfs:
                raise Exception("Identifier not used in an TEDF: " + s)

    # Ensure that the entries in the BibTeX file are sorted alphabetically.
    def test_bibtex_sorted(self):
        identifiers = list(load_sources("public").entries)
        identifiers_sorted = sorted(identifiers, key=lambda s: s.lower())
        for id, id_sorted in zip(identifiers, identifiers_sorted):
            assert id == id_sorted, (f"Entries in BibTeX file must be sorted: {id}\n\n" +
                                     "\n".join("{0}\t{1}".format(*x) for x in zip(identifiers, identifiers_sorted)))

    # Format all entries contained in the public BibTeX source file.
    def test_formatting(self):
        format_sources(load_sources("public"))
