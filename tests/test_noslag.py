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
