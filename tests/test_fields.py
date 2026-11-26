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


class TestsPeriodSelect(unittest.TestCase):
    """Tests for period selection with interpolation and extrapolation."""

    def setUp(self):
        """Create a period field and a small test frame."""
        import numpy as np
        import pandas as pd

        from posted._columns.fields import PeriodFieldDefinition

        self.np = np
        self.field = PeriodFieldDefinition(name="Period", description="Period")
        self.df = pd.DataFrame(
            {
                "var": ["a", "a", "a", "b", "b", "c", "c"],
                "period": [2020, 2025, 2030, 2020, 2030, 2020, 2030],
                "value": [1.0, 2.0, 4.0, 10.0, 20.0, 1.0, np.nan],
            }
        )

    def _select(self, periods, mode):
        """Select periods, returning the resulting frame."""
        out = self.field._select(
            self.df.copy(), "period", periods, period_mode=mode
        )
        return {
            (var, period): value
            for var, period, value in zip(
                out["var"], out["period"], out["value"]
            )
        }

    def test_match_interpolation_extrapolation(self):
        """Test that periods are matched, interpolated and extrapolated."""
        from posted._columns.fields import PeriodMode

        values = self._select(
            [2015, 2025, 2035], PeriodMode.INTER_AND_EXTRAPOLATION
        )
        # Exact matches pass through, out-of-range periods take the value
        # of the nearest observed period.
        self.assertEqual(values[("a", 2015)], 1.0)
        self.assertEqual(values[("a", 2025)], 2.0)
        self.assertEqual(values[("a", 2035)], 4.0)
        # Unobserved periods between observed ones are interpolated
        # linearly.
        self.assertEqual(values[("b", 2025)], 15.0)
        # Periods with missing values count as not observed: they are
        # interpolated or extrapolated across like any missing period.
        self.assertEqual(values[("c", 2015)], 1.0)
        self.assertEqual(values[("c", 2025)], 1.0)
        self.assertEqual(values[("c", 2035)], 1.0)

    def test_interpolation_only(self):
        """Test that out-of-range periods are dropped without extrapolation."""
        from posted._columns.fields import PeriodMode

        values = self._select([2015, 2025, 2035], PeriodMode.INTERPOLATE)
        self.assertEqual(sorted(values), [("a", 2025), ("b", 2025)])
        self.assertEqual(values[("a", 2025)], 2.0)
        self.assertEqual(values[("b", 2025)], 15.0)

    def test_extrapolation_only(self):
        """Test that interior gaps are dropped without interpolation."""
        from posted._columns.fields import PeriodMode

        values = self._select([2015, 2025, 2035], PeriodMode.EXTRAPOLATE)
        self.assertEqual(
            sorted(values),
            [
                ("a", 2015),
                ("a", 2025),
                ("a", 2035),
                ("b", 2015),
                ("b", 2035),
                ("c", 2015),
                ("c", 2025),
                ("c", 2035),
            ],
        )
        self.assertEqual(values[("a", 2015)], 1.0)
        self.assertEqual(values[("a", 2035)], 4.0)
        self.assertEqual(values[("b", 2015)], 10.0)
        self.assertEqual(values[("b", 2035)], 20.0)

    def test_row_order(self):
        """Test that rows come per group in the order of the requests."""
        from posted._columns.fields import PeriodMode

        out = self.field._select(
            self.df.copy(),
            "period",
            [2015, 2025, 2035],
            period_mode=PeriodMode.INTER_AND_EXTRAPOLATION,
        )
        self.assertEqual(
            list(zip(out["var"], out["period"])),
            [
                (var, period)
                for var in ["a", "b", "c"]
                for period in [2015, 2025, 2035]
            ],
        )

    def test_duplicate_periods_raise(self):
        """Test that duplicate periods within a group raise an error."""
        from posted import POSTEDException

        df = self.df.copy()
        df.loc[0, ["var", "period"]] = ["b", 2020]  # duplicate (b, 2020)
        with self.assertRaises(POSTEDException):
            self.field._select(df, "period", [2025], period_mode=None)
