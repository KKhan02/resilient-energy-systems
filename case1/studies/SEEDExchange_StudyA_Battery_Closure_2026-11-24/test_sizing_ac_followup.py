import unittest
from sizing_ac_followup import choose_grid_interval,power_ceiling,NEW_113

class FollowupTests(unittest.TestCase):
    def test_contiguous_upper_segment(self):
        self.assertEqual(choose_grid_interval([(0,False),(1,True),(2,False),(3,True),(4,True)]),(3,4,2))
    def test_ceiling_failure(self):
        self.assertIsNone(choose_grid_interval([(0,True),(1,False)]))
    def test_all_pass(self):
        self.assertEqual(choose_grid_interval([(0,True),(1,True)]),(0,1,None))
    def test_cap(self):
        self.assertAlmostEqual(power_ceiling(5.,{"inverter_kva":8.,"battery_power_dc_kw":4.}),3.8)
        self.assertEqual(power_ceiling(3.,{"inverter_kva":8.,"battery_power_dc_kw":8.}),3.)
    def test_full_roster(self):
        self.assertEqual(len(set(NEW_113)),5)

if __name__=="__main__":
    unittest.main()
