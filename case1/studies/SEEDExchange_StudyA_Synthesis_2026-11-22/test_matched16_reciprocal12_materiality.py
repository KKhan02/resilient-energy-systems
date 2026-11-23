"""Synthetic source-only materiality tests, without grid or LP solves."""
import unittest
import matched16_reciprocal12_materiality as m


class Reciprocal12MaterialityTests(unittest.TestCase):
    def test_twelve_canonical_family_coverage(self):
        self.assertEqual(len(m.MATCHED),4)
        self.assertEqual(len(m.PRIORITY_DESCRIPTIONS),7)
        self.assertEqual(len(m.ARCHIVE_ANCHORS["94022"]),5)

    def test_night_pf_095_proxy(self):
        # Time-matched 2025-11-27 20:00 source inputs, not annual max gross load.
        # A1 SS90 to A0: import=4.887809301, hourly demand=5.186888959 kW.
        # A0 SS90 to A1: import=demand=4.8438874007 kW.
        cases = (
            (4.887809301, 5.186888959, 5.1765998799),
            (4.8438874007, 4.8438874007, 5.0988288428),
        )
        for grid_import_kw, hourly_gross_demand_kw, expected_kva in cases:
            with self.subTest(grid_import_kw=grid_import_kw):
                val = m.nighttime_proxy(grid_import_kw, hourly_gross_demand_kw, .95)
                self.assertAlmostEqual(val, expected_kva, places=7)

    def test_zero_import_with_reactive_load_is_nonzero(self):
        self.assertGreater(m.nighttime_proxy(0,2,.95),0)

    def test_night_proxy_rejects_invalid_pf(self):
        with self.assertRaises(ValueError):
            m.nighttime_proxy(1,2,0)

    def test_night_proxy_rejects_negative_load(self):
        with self.assertRaises(ValueError):
            m.nighttime_proxy(1,-2,.98)

    def test_source_scalar_rejects_nan(self):
        with self.assertRaisesRegex(ValueError,"Nonfinite"):
            m.scalar({"demand_kw":"nan"},"demand_kw")

    def test_hour_selection_requires_full_year(self):
        with self.assertRaisesRegex(ValueError,"Full 2025 source"):
            m.choose_hours([], "94022")

    def test_duplicate_source_hour_refused(self):
        r={"timestamp_lst":"2025-01-01 00:00:00"}
        with self.assertRaisesRegex(ValueError,"Duplicate source hour"):
            m.choose_hours([r]*8760,"113699")

    def test_priority_register_is_complete_and_evidence_only(self):
        expected={
            ("94022","A0"),("94022","A1"),
            ("113699","A0"),("113699","A1"),
            ("106039","A0"),("106039","A1"),("85398","A1"),
        }
        self.assertEqual(set(m.PRIORITY_DESCRIPTIONS),expected)
        self.assertEqual(m.PRIORITY_DESCRIPTIONS[("113699","A1")][0],"P1")
        self.assertEqual(m.PRIORITY_DESCRIPTIONS[("94022","A0")][0],"P1")
        self.assertEqual(m.PRIORITY_DESCRIPTIONS[("85398","A1")][0],"P2")
        self.assertTrue(all(band in ("P1","P2","P3") and bool(reason)
                            for band,reason in m.PRIORITY_DESCRIPTIONS.values()))

if __name__=="__main__":
    unittest.main()
