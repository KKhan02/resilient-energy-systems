"""Independent synthetic checks for the four-family input gate."""
import unittest
import matched16_four_family_input_gate as subject


class FourFamilyInputGateTests(unittest.TestCase):
    def source(self):
        return [{"timestamp_lst": "2025-01-01 00:00:00",
                 "demand_kw": "2", "pv_dc_available_kw": "0",
                 "inverter_ac_kw": "0", "grid_export_kw": "0", "unserved_kw": "0"},
                {"timestamp_lst": "2025-01-01 01:00:00",
                 "demand_kw": "3", "pv_dc_available_kw": "0",
                 "inverter_ac_kw": "2", "grid_export_kw": "0", "unserved_kw": "0"}]

    def test_all_four_distinct_cases(self):
        self.assertEqual(len(subject.FAMILIES), 4)
        self.assertEqual(len(set(v[0] for v in subject.FAMILIES.values())), 4)

    def test_factors_nine(self):
        self.assertEqual(len(subject.FACTOR_SET), 9)

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            subject.numeric({"q":"nan"}, "q")

    def test_coverage_detects_duplicate(self):
        hours = ["2025-01-01 19:00:00"]
        x = [{"pf": p, "length_factor": l, "timestamp_lst": hours[0]}
             for p,l in subject.FACTOR_SET]
        self.assertEqual(subject.factor_coverage(x, hours), 9)
        with self.assertRaisesRegex(ValueError, "coverage incomplete"):
            subject.factor_coverage(x[:-1]+[x[0]], hours)

    def test_coverage_detects_missing_hour(self):
        with self.assertRaisesRegex(ValueError, "coverage incomplete"):
            subject.factor_coverage([], ["2025-01-01 19:00:00"])

    def test_validation_requires_full_year(self):
        with self.assertRaisesRegex(ValueError, "Incomplete annual"):
            subject.annual_deltas(self.source(), self.source())

    def test_missing_field_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Non-numeric or absent"):
            subject.numeric({}, "power")

    def test_bad_finite_year_hypothesis(self):
        rows = [{"timestamp_lst": "2025-01-01 00:00:00"}]
        with self.assertRaisesRegex(ValueError, "Incomplete annual"):
            subject.annual_deltas(rows, rows)


if __name__ == "__main__":
    unittest.main()
