"""Source-evidence regression tests. No electrical simulation."""
import unittest
from studies.spatial_electrical_reconciliation.audit_sources import audit

class SourceReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=audit()

    def test_asset_identifier(self):
        self.assertEqual(self.data["asset_94022"]["node"],"931076")
        self.assertEqual(self.data["asset_94022"]["kva"],5.)

    def test_house_mapping_is_pixel_only(self):
        self.assertEqual(self.data["houses"]["image_ids"],35)
        self.assertEqual(self.data["houses"]["georeferenced_lat_lon"],0)

    def test_preserve_conflicting_lv_lengths(self):
        d=self.data["line_traces_m"]
        self.assertAlmostEqual(d["lv"]["derived_length_m"],324.452085283,places=4)
        self.assertEqual(d["lv_geometry_register_m"],328.8)
        self.assertGreater(d["lv_difference_register_vs_trace_m"],4.)

    def test_groupings_cover_all_35_and_are_hypothetical(self):
        expected={"4":9,"5":7,"6":6,"7":5,"8":5}
        for key,count in expected.items():
            x=self.data["groupings"][key]
            self.assertEqual(x["candidate_transformers"],count)
            self.assertEqual(x["house_count"],35)

    def test_original_gitlab_notebooks_are_not_uploaded_v18_v5(self):
        n=self.data["gitlab_original_notebooks"]
        self.assertIn("v17",n["pypsa"]["heading"])
        self.assertEqual(n["pandapower"]["cells"],37)
