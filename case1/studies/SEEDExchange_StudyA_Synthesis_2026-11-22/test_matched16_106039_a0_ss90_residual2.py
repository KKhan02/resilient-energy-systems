"""Selection and annual chronology guards, no AC solver."""
import unittest
import matched16_106039_a0_ss90_residual2 as a
class Contract(unittest.TestCase):
    def test_event_population(self):
        self.assertEqual(len(a.EVENTS),2)
        self.assertEqual(len(a.CHANGED),4)
        self.assertEqual(len(a.EVENTS)*len(a.FRACTIONS)*len(a.PF)*2,40)
    def test_smallest_passing(self):
        rows=[{"donor_time":d,"target_time":t,"fraction":f,"pair_4of4_AC_screen_pass":f>=.25} for d,t,_ in a.EVENTS for f in (.5,0,.25)]
        self.assertEqual([r["fraction"] for r in a.select_choices(rows)],[.25,.25])
    def test_missing_event_rejected(self):
        d,t,_=a.EVENTS[0]
        self.assertIsNone(a.select_choices([{"donor_time":d,"target_time":t,"fraction":.25,"pair_4of4_AC_screen_pass":True}]))
    def test_incomplete_year(self):
        with self.assertRaisesRegex(ValueError,"ordered 2025"):a.year_index([])
if __name__=="__main__":unittest.main()
