"""Tests for NOSLAG framework."""

import unittest
from re import match


class TestsNOSLAG(unittest.TestCase):
    """Tests for NOSLAG framework."""

    def test_noslag_workflow(self):
        """Test NOSLAG workflow.

        Test that normalise, select, and aggregate method works for all TEDFs.
        """
        # Create a dictionary of erros. This will allow running the full test
        # and asserting at the end.
        errors = []

        # Import public database path and TEDF class.
        from posted import TEDF, databases

        # Discover all TEDFs and loop over them.
        for file_path in (databases["public"] / "tedfs").rglob("**/*.csv"):
            # Determine the parent variable for loading.
            parent_variable = match(
                r".*\|database\|tedfs\|(.*).csv",
                str(file_path.resolve()).replace("/", "|").replace("\\", "|"),
            ).group(1)

            # Try loading.
            try:
                tedf = TEDF.load(parent_variable)
            except Exception as ex:
                errors.append((parent_variable, "aggregate", ex))
                continue

            # Try normalising.
            try:
                tedf.normalise()
            except Exception as ex:
                errors.append((parent_variable, "aggregate", ex))
                continue

            # Try selecting.
            try:
                tedf.select()
            except Exception as ex:
                errors.append((parent_variable, "aggregate", ex))
                continue

            # Try aggregating.
            try:
                tedf.aggregate()
            except Exception as ex:
                errors.append((parent_variable, "aggregate", ex))

        # Assert at the end of the test.
        error_msg = "\n".join(
            f"Error occurred while running {fn} on '{par_var}':\n{ex}"
            for par_var, fn, ex in errors
        )

        assert not error_msg, error_msg

    def test_expand_not_specified(self):
        """Test that `N/S` field values are expanded only when requested."""
        from posted import TEDF

        # The electrolysis TEDF contains `N/S` entries in the size field.
        tedf = TEDF.load("Tech|Electrolysis")

        # By default, `N/S` is expanded to all other values of the field.
        selected = tedf.select()
        self.assertNotIn("N/S", selected["size"].unique())

        # When disabled, `N/S` is kept as a separate field value.
        selected = tedf.select(expand_not_specified=False)
        self.assertIn("N/S", selected["size"].unique())

        # Expansion can be restricted to specific fields.
        selected = tedf.select(expand_not_specified=["subtech"])
        self.assertIn("N/S", selected["size"].unique())
        with self.assertRaises(Exception):
            tedf.select(expand_not_specified=["nonexistent"])
