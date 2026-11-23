"""Synthetic source-only materiality tests, without grid or LP solves."""
import unittest
import matched16_reciprocal12_materiality as m


class Reciprocal12MaterialityTests(unittest.TestCase):
    def test_twelve_canonical_family_coverage(self):
        self.assertEqual(len(m.MATCHED),4)
        self.assertEqual(len(m.PRIORITY_DESCRIPTIONS),7)
        self.assertEqual(len(m.ARCHIVE_ANCHORS["94022"]),5)

    def test_night_pf_095_proxy(self):
        val=m.nighttime_proxy(4.887809301, 5.7703076217, .95)
        self.assertAlmostEqual(val,5.1765998799,places=7)

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
        with self.assertRaisesRegex(ValueError,"Full 2025 source"):
            m.choose_hours([r,r],"113699")

    def test_target_priority_nameplate_not_a_certificate(self):
        self.assertEqual(m.PRIORITY_DESCRIPTIONS[("113699","A1")][0],"P1")
        self.assertTrue(all("EPM" in m.PRIORITY_DESCRIPTIONS[k][1] or
                            "PF" in m.PRIORITY_DESCRIPTIONS[k][1] or
                            "original" in m.PRIORITY_DESCRIPTIONS[k][1] or
                            "SS90" in m.PRIORITY_DESCRIPTIONS[k][1] or
                            "H13" in m.PRIORITY_DESCRIPTIONS[k][1] or
                            "Four-home" in m.PRIORITY_DESCRIPTIONS[k][1]
                            for k in m.PRIORITY_DESCRIPTIONS))

if __name__=="__main__":
    unittest.main()
