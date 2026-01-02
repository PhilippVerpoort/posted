"""Tests for TEDFs."""

import unittest
from re import match


class TestsTEDFs(unittest.TestCase):
    """Tests for TEDFs."""

    def test_tedfs_validity(self):
        """Test TEDFs contain valid entries.

        Perform validation of all TEDFs.
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

            # Load TEDF from source.
            tedf = TEDF.load(parent_variable)

            # Run validation.
            tedf.validate()

            # Print validation results.
            if not tedf.validated.all().all():
                bad_rows = ~tedf.validated.all(axis=1)

                df_bad = tedf.raw.loc[bad_rows]
                val_bad = ~tedf.validated.loc[bad_rows]

                # Mark invalid cells.
                display_df = df_bad.astype(str).copy()

                for col in tedf.raw.columns:
                    display_df.loc[val_bad[col], col] = (
                        "!! " + display_df.loc[val_bad[col], col]
                    )

                errors.append((parent_variable, display_df.to_string()))

        # Assert at the end of the test.
        error_msg = "\n".join(
            f"Validation errors for '{par_var}':\n{ex}"
            for par_var, ex in errors
        )

        assert not error_msg, error_msg
