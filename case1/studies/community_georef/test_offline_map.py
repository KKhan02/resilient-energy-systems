import unittest
from pathlib import Path
from render_offline_map import render, HERE

class OfflineMapTests(unittest.TestCase):
    def test_map_self_contained_and_does_not_request_osm_tiles(self):
        h=render()
        self.assertIn("data:image/jpeg;base64,",h)
        self.assertNotIn("tile.openstreetmap.org",h)
        self.assertNotIn("unpkg.com",h)
        self.assertNotIn("<script src=",h)
        self.assertIn("H\"+p.house_id",h)
    def test_all_35_geographic_features(self):
        h=render()
        self.assertEqual(h.count('"house_id":'),41) # 35 estimates + six supplied control records
        self.assertIn('Original 35-point community satellite image',h)
        self.assertIn("electrical supply unknown",h)
