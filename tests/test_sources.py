"""Tests for sources."""

import unittest

import pandas as pd

from posted import databases
from posted._read import read_tedf_from_csv
from posted.sources import format_sources, load_sources


class TestsSources(unittest.TestCase):
    """Tests for sources."""

    def test_loading(self):
        """Load and parse the public BibTeX source file."""
        try:
            load_sources("public")
        except Exception as ex:
            raise Exception(f"Could not load BibTeX file:\n{ex}")

    def test_tedfs_no_undefined(self):
        """Check validity of source identifiers in TEDFs.

        Ensure that all source identifiers used in TEDFs have a corresponding
        entry in BibTeX.
        """
        sources_bibtex = list(load_sources("public").entries)

        for file_path in (databases["public"] / "tedfs").rglob("*.csv"):
            df = read_tedf_from_csv(file_path)
            assert "source" in df.columns, (
                "The 'sources' column of a TEDF must be present."
            )
            missing = ~df["source"].isin(sources_bibtex)
            if missing.any():
                raise Exception(
                    f"Source identifiers found in '{file_path.name}' but not "
                    f"in BibTeX:" + ", ".join(df.loc[missing, "source"])
                )

    def test_bibtex_no_unused(self):
        """Check validity of source identifiers in TEDFs.

        Ensure that all source identifiers in BibTeX occur in at least one
        TEDF.
        """
        sources_tedfs = pd.concat(
            [
                read_tedf_from_csv(file_path)["source"]
                for file_path in (databases["public"] / "tedfs").rglob("*.csv")
            ]
        ).unique()

        sources_bibtex = list(load_sources("public").entries)

        sources_not_used = [
            s for s in sources_bibtex if s not in sources_tedfs
        ]
        if sources_not_used:
            raise Exception(
                "Identifier not used in an TEDF: "
                + ", ".join(sources_not_used)
            )

    def test_bibtex_sorted(self):
        """Check BibTeX file is sorted.

        Ensure that the entries in the BibTeX file are sorted alphabetically.
        """
        identifiers = list(load_sources("public").entries)
        identifiers_sorted = sorted(identifiers, key=lambda s: s.lower())
        for id, id_sorted in zip(identifiers, identifiers_sorted):
            assert id == id_sorted, (
                f"Entries in BibTeX file must be sorted: {id}\n\n"
                + "\n".join(
                    "{0}\t{1}".format(*x)
                    for x in zip(identifiers, identifiers_sorted)
                )
            )

    # Format all entries contained in the public BibTeX source file.
    def test_formatting(self):
        """Check that all sources can be formatted correctly."""
        format_sources(load_sources("public"))
