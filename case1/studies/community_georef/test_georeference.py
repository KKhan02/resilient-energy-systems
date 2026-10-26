"""Offline GIS provenance and deterministic-result tests."""
import json
import unittest
from pathlib import Path
from georeference import HERE,generate,FITTED
from epm_fetch import LAYERS,KEEP,sanitize,bbox_from_features

class CommunityGeorefTests(unittest.TestCase):
    def test_archived_population_not_33_assumption(self):
        geo,rows,diag=generate()
        self.assertEqual(len(rows),35)
        self.assertEqual([r["house_id"] for r in rows],list(range(1,36)))
        self.assertEqual({r["service_transformer"] for r in rows},{"unknown"})

    def test_approved_h25_control_choice(self):
        _,_,d=generate()
        self.assertEqual(d["excluded_ids"],[25])
        self.assertEqual(d["fit_ids"],[1,4,5,6,18])
        self.assertGreater(abs(d["h25_model_lonlat"][0]-d["h25_supplied_lonlat"][0]),0.0001)

    def test_quality_warning_not_removed(self):
        _,_,d=generate()
        self.assertGreater(d["max_held_out_error_m"],75)
        self.assertLess(max(r["m"] for r in d["calibration_residuals_m"]),40)

    def test_committed_35_outputs_equal_rebuild(self):
        geo,_,diag=generate()
        published=json.loads((HERE/"house_points_provisional.geojson").read_text())
        d=json.loads((HERE/"georeferencing_diagnostics.json").read_text())
        for a,b in zip(geo["features"],published["features"]):
            self.assertEqual(a["properties"],b["properties"])
            for x,y in zip(a["geometry"]["coordinates"],b["geometry"]["coordinates"]):
                self.assertLess(abs(x-y),1e-7)
        for a,b in zip(diag["leave_one_out_errors_m"],d["leave_one_out_errors_m"]):
            self.assertLess(abs(a["m"]-b["m"]),.2)

    def test_privacy_and_electrical_boundaries(self):
        self.assertNotIn(4,LAYERS)
        self.assertNotIn("ADDRESS",KEEP)
        fs=[{"type":"Feature","geometry":{"type":"Point","coordinates":[-75,6]},
             "properties":{"CODE":"94022","ADDRESS":"private","NAME":"private","CUSTOMERS":3}}]
        self.assertEqual(sanitize(fs)[0]["properties"],{"CODE":"94022","CUSTOMERS":3})
        self.assertEqual(bbox_from_features(fs,0.01),[-75.01,5.99,-74.99,6.01])

if __name__=="__main__":unittest.main()
