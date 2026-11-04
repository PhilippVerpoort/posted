"""Tests for field selection and expansion."""

import unittest


class TestsFields(unittest.TestCase):
    """Tests for field selection and expansion."""

    def setUp(self):
        """Create a non-coded case field and a small test frame."""
        import pandas as pd

        from posted._columns.fields import CustomFieldDefinition

        self.field = CustomFieldDefinition(
            name="Plant size",
            description="Plant size",
            type="case",
            coded=False,
        )
        self.df = pd.DataFrame(
            {
                "size": ["1 MW", "1 MW, 100 MW", "*", "N/S", "5 MW"],
                "value": [0.0, 1.0, 2.0, 3.0, 4.0],
            }
        )

    def _sizes(self, df, value):
        return sorted(df.loc[df["value"] == value, "size"])

    def test_expand_all(self):
        """Test expansion when no field values are selected."""
        out = self.field.select_and_expand(self.df.copy(), "size", None)

        # Comma-separated cells are split into individual rows.
        self.assertEqual(self._sizes(out, 1.0), ["1 MW", "100 MW"])

        # Asterisk expands to all individual values, but not to N/S or
        # to the unsplit comma-separated strings.
        self.assertEqual(self._sizes(out, 2.0), ["1 MW", "100 MW", "5 MW"])

        # N/S rows are kept as they are.
        self.assertEqual(self._sizes(out, 3.0), ["N/S"])

        # Unchanged single values remain.
        self.assertEqual(self._sizes(out, 0.0), ["1 MW"])
        self.assertEqual(self._sizes(out, 4.0), ["5 MW"])

    def test_expand_selected(self):
        """Test expansion when explicit field values are selected."""
        out = self.field.select_and_expand(self.df.copy(), "size", ["1 MW"])
        self.assertEqual(sorted(out["size"].unique()), ["1 MW"])
        self.assertEqual(sorted(out["value"]), [0.0, 1.0, 2.0])

        # Explicit lists may contain N/S, which the asterisk then expands to.
        out = self.field.select_and_expand(
            self.df.copy(), "size", ["5 MW", "N/S"]
        )
        self.assertEqual(self._sizes(out, 2.0), ["5 MW", "N/S"])
        self.assertEqual(sorted(out["value"]), [2.0, 2.0, 3.0, 4.0])

    def test_asterisk_not_selectable(self):
        """Test that the asterisk cannot be selected explicitly."""
        with self.assertRaises(Exception):
            self.field.select_and_expand(self.df.copy(), "size", ["*"])
