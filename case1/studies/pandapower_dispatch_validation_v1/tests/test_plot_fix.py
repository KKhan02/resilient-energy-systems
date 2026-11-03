"""Regression test: worst-hour groupby label is a timestamp, not row index."""
import sys
import tempfile
from pathlib import Path
import unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_validation import make_plots


class TestPlotFix(unittest.TestCase):
    def test_worst_timestamp_plot(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            summary = pd.DataFrame([
                {'households': 7, 'siting': 'lv_head', 'load_allocation': 'equal',
                 'load_pf': .98, 'lowest_lv_pu': .955, 'max_trafo_pct': 105,
                 'max_lv_line_pct': 12},
            ])
            # Intentionally use a RangeIndex. idxmin() of groupby returns a timestamp.
            profiles = pd.DataFrame([
                {'timestamp_lst':'2025-01-01 00:00:00', 'households':7,
                 'siting':'lv_head', 'load_allocation':'equal', 'load_pf':.98,
                 'distance_m':0, 'vm_pu':1.0},
                {'timestamp_lst':'2025-01-01 00:00:00', 'households':7,
                 'siting':'lv_head', 'load_allocation':'equal', 'load_pf':.98,
                 'distance_m':324.5, 'vm_pu':.99},
                {'timestamp_lst':'2025-11-29 20:00:00', 'households':7,
                 'siting':'lv_head', 'load_allocation':'equal', 'load_pf':.98,
                 'distance_m':0, 'vm_pu':1.0},
                {'timestamp_lst':'2025-11-29 20:00:00', 'households':7,
                 'siting':'lv_head', 'load_allocation':'equal', 'load_pf':.98,
                 'distance_m':324.5, 'vm_pu':.955},
            ])
            make_plots(summary, profiles, root)
            self.assertTrue((root/'7_homes_worst_lv_profile.png').exists())
            self.assertTrue((root/'min_voltage_by_household.png').exists())
            self.assertTrue((root/'transformer_loading_by_household.png').exists())
            self.assertTrue((root/'lv_conductor_loading_by_household.png').exists())

if __name__ == '__main__':
    unittest.main()
