import json
import unittest
from pathlib import Path
from render_evidence_overlay import render,HERE

class OverlayValidation(unittest.TestCase):
    def test_offline_and_numbered_35(self):
        x=render()
        self.assertIn("data:image/jpeg;base64,",x)
        self.assertNotIn("tile.openstreetmap.org",x)
        self.assertNotIn("<script src=",x)
        self.assertIn("Corrected house locations",x)
        self.assertEqual(x.count('"status":"user_definite"'),3)
    def test_only_two_known_transformer_coordinates_and_no_fabrication(self):
        x=render()
        self.assertIn("94022 / node 931076",x)
        self.assertIn("Northern 25 kVA candidate",x)
        self.assertNotIn('"name":"923494"',x)
        self.assertNotIn('"name":"823002"',x)
    def test_committed_html_matches_offline_renderer_structure(self):
        generated=render()
        committed=(HERE/"satellite_epm_review_overlay.html").read_text(encoding="utf-8")
        for item in ('data:image/jpeg;base64,','id="referenceOverlay"','reviewMarkers',
                     '94022 / node 931076','Northern 25 kVA candidate'):
            self.assertIn(item,generated)
            self.assertIn(item,committed)
        self.assertEqual(generated.count('"candidates":'),35)
        self.assertEqual(committed.count('"candidates":'),35)
        self.assertLess(committed.index('id="referenceOverlay"'),committed.index('id="satview"'))
