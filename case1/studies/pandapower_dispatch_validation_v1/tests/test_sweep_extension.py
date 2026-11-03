import sys
import unittest
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from run_validation import siting_tap_index
from export_missing_dispatch import selected_designs

class TestSiting(unittest.TestCase):
    def test_placements(self):
        for taps in [2,3,4,5,6,8]:
            self.assertEqual(siting_tap_index(taps,'lv_head'),0)
            self.assertEqual(siting_tap_index(taps,'far_end'),taps)
            self.assertTrue(1<=siting_tap_index(taps,'middle')<=taps)
        self.assertEqual(siting_tap_index(6,'middle'),3)
        self.assertEqual(siting_tap_index(5,'middle'),3)
    def test_invalid(self):
        with self.assertRaises(ValueError):siting_tap_index(6,'unknown')

class TestExport(unittest.TestCase):
    def test_pick_best_fixed_pv(self):
        d=pd.DataFrame([
            dict(houses=5,kva=5.,status='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER',
                 task='fixed_PV_economic',annual_total_usd=500.,panels=15,area_max_panels=82,case='5_homes'),
            dict(houses=5,kva=5.,status='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER',
                 task='fixed_PV_economic',annual_total_usd=400.,panels=17,area_max_panels=82,case='5_homes')])
        self.assertEqual(selected_designs(d,[5])[0]['panels'],17)

if __name__=='__main__':unittest.main()
