"""No-solver regression checks for the six-event thermal screen."""
import unittest
import matched16_reciprocal_p1_thermal_ac as t
class Contract(unittest.TestCase):
    def test_six_events(self):
        self.assertEqual(len(t.EVENTS),4)
        self.assertEqual(len(t.event_keys()),6)
        self.assertEqual(len(t.event_keys())*len(t.FRACTIONS)*len(t.PF)*2,120)
    def test_register(self):
        r=[{"case":c,"best_donor_hour":d,"event":e} for c,d,e in t.event_keys()]
        self.assertEqual(len(t.check_register(r)),6)
        with self.assertRaisesRegex(ValueError,"identities changed"):t.check_register(r+[r[0]])
    def test_choice_minimum_and_missing(self):
        c="A0_113699_min_cost_to_A1";rows=[]
        for d,e in t.EVENTS[c]:
            for f in (.75,.25,.5):
                rows.append({"case":c,"target_time":e,"fraction":f,"pair_4of4_AC_screen_pass":f>=.5})
        self.assertEqual([r["fraction"] for r in t.choose_combined(rows,c)],[.5,.5])
        self.assertIsNone(t.choose_combined(rows[:3],c))
    def test_overlap_rejected(self):
        from unittest.mock import patch
        rows=[{"donor_time":"2025-01-01 17:00:00","target_time":"2025-01-01 20:00:00","moved_dc_kw":1},{"donor_time":"2025-01-01 19:00:00","target_time":"2025-01-01 21:00:00","moved_dc_kw":1}]
        with patch.object(t.nov,"transfer",return_value=None):
            with self.assertRaisesRegex(ValueError,"overlap"):t.combined_frame(None,rows)
if __name__=="__main__":unittest.main()
