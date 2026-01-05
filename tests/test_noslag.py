import unittest
from re import match


class TestNOSLAGMethods(unittest.TestCase):
    def test_normalise(self):
        # Create a dictionary of erros. This will allow running the full test
        # and asserting at the end.
        errors = []

        # Import public database path and TEDF class.
        from posted import databases, TEDF

        # Discover all TEDFs and loop over them.
        for file_path in (databases["public"] / "tedf").rglob("**/*.csv"):
            # Determine the parent variable for loading.
            parent_variable = match(
                r".*\|database\|tedfs\|(.*).csv",
                str(file_path.resolve()).replace("/", "|").replace("\\", "|"),
            ).group(1)

            # Try loading.
            try:
                tedf = TEDF.load(parent_variable)
            except Exception as ex:
                errors += (parent_variable, "load", ex)
                continue

            # Try normalising.
            try:
                tedf.normalise()
            except Exception as ex:
                errors += (parent_variable, "normalise", ex)
                continue

            # Try selecting.
            try:
                tedf.select()
            except Exception as ex:
                errors += (parent_variable, "select", ex)
                continue

            # Try aggregating.
            try:
                tedf.aggregate()
            except Exception as ex:
                errors += (parent_variable, "aggregate", ex)

        # Assert at the end of the test.
        error_msg = "\n".join(
            f"Error occurred while running {fn} on '{par_var}':\n{ex}"
            for par_var, fn, ex in errors
        )

        assert not error_msg, error_msg
