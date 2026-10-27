"""Offline source-only check of user-supplied coordinates and EPM transformer identity."""
import csv
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def csvdata(file):
    with (ROOT/file).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

class FieldReviewEvidenceChecks(unittest.TestCase):
    def test_unique_complete_geographic_register(self):
        rows=csvdata("houses_field_review.csv")
        self.assertEqual([r["house_id"] for r in rows],[f"H{i:02d}" for i in range(1,36)])
        for r in rows:
            self.assertTrue(6.23<float(r["latitude"])<6.26)
            self.assertTrue(-75.03<float(r["longitude"])<-74.99)
            self.assertGreaterEqual(float(r["distance_from_prior_m"]),0)

    def test_geojson_matches_register_not_transformer_assignments(self):
        rows=csvdata("houses_field_review.csv")
        js=json.loads((ROOT/"houses_field_review.geojson").read_text())
        self.assertEqual(js["type"],"FeatureCollection")
        self.assertEqual(len(js["features"]),35)
        for row,f in zip(rows,js["features"]):
            lon,lat=f["geometry"]["coordinates"]
            self.assertAlmostEqual(float(row["latitude"]),lat)
            self.assertAlmostEqual(float(row["longitude"]),lon)
            self.assertFalse(f["properties"]["service_territory_verified"])

    def test_transformers_distinct_nodes_and_correct_units(self):
        rows=csvdata("epm_transformer_register.csv")
        self.assertEqual(len(rows),7)
        nodes={r["epm_node"]:r for r in rows}
        self.assertEqual(len(nodes),7)
        self.assertEqual(nodes["923848"]["trafo_number"],"92395")
        self.assertEqual(nodes["931076"]["trafo_number"],"94022")
        self.assertEqual(nodes["823002"]["portal_nominal_kw"],"3")
        self.assertEqual(nodes["241054"]["portal_nominal_kw"],"3")
        self.assertEqual(nodes["823002"]["separate_archived_kva"],"")
        self.assertEqual(nodes["241054"]["mv_circuit_or_portal_label"],"221-13")
        self.assertEqual(nodes["NOT_CONFIRMED"]["separate_archived_kva"],"25")

    def test_uncertainty_and_known_user_assignments_preserved(self):
        rows={r["house_id"]:r for r in csvdata("houses_field_review.csv")}
        self.assertEqual({k:rows[k]["candidate_epm_nodes"] for k in ("H12","H17","H30")},{"H12":"900607","H17":"923494","H30":"923848"})
        self.assertTrue(all(rows[k]["assignment_confidence"]=="user_definite" for k in ("H12","H17","H30")))
        self.assertEqual(rows["H10"]["candidate_epm_nodes"],"923494|823002")
        self.assertEqual(rows["H29"]["candidate_epm_nodes"],"931076|923848")
        self.assertEqual(rows["H02"]["candidate_epm_nodes"],"")
        self.assertEqual(rows["H01"]["candidate_epm_nodes"],"")
        self.assertEqual(rows["H14"]["assignment_confidence"],"unverifiable")
        self.assertEqual(rows["H15"]["assignment_confidence"],"unverifiable")
        self.assertEqual(len([r for r in rows.values() if r["position_source"]=="new_user_map_point_2026_10_27"]),19)

    def test_issues_and_noncertified_service(self):
        d=json.loads((ROOT/"review_findings.json").read_text())
        self.assertEqual(d["stats"]["total"],35)
        self.assertEqual(d["stats"]["definite"],["H12","H17","H30"])
        self.assertFalse("utility_verified_assignments" in d)

if __name__=="__main__":
    unittest.main()
