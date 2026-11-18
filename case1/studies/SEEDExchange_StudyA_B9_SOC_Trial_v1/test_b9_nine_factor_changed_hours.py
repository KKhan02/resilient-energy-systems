"""Source-independent regression tests for B9 nine-factor changed-hour screen."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

FILE = Path(__file__).with_name('b9_nine_factor_changed_hours.py')
s = importlib.util.spec_from_file_location('b9_nine_factor', FILE)
module = importlib.util.module_from_spec(s)
s.loader.exec_module(module)


class NineFactorChecks(unittest.TestCase):
    def test_factor_coverage(self):
        self.assertEqual(len(module.FACTORS), 9)
        self.assertEqual(len(set(module.FACTORS)), 9)
        self.assertIn((.95, 1.6), module.FACTORS)
        self.assertEqual(sum(module.NUM_CASE_HOURS.values()) * 2 * len(module.FACTORS), 108)

    def test_ac_strict_limit(self):
        row = dict(status='CONVERGED', min_v_pu=.95, max_v_pu=1.05,
                   max_trafo_pct=100.0, max_line_pct=100.0, ac_feasible=True)
        self.assertTrue(module.ac_metrics(row)['ac_feasible'])
        bad = dict(row, max_trafo_pct=107.431, ac_feasible=False)
        self.assertFalse(module.ac_metrics(bad)['ac_feasible'])
        bad = dict(row, min_v_pu=.949, ac_feasible=False)
        self.assertFalse(module.ac_metrics(bad)['ac_feasible'])

    def test_flag_disagreement_rejected(self):
        row = dict(status='CONVERGED', min_v_pu=.95, max_v_pu=1.05,
                   max_trafo_pct=107.431, max_line_pct=7., ac_feasible=True)
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            module.ac_metrics(row)

    def test_nonconvergence_metrics_remain_reportable(self):
        row = {'status':'DID_NOT_CONVERGE', 'error':'no solution'}
        result = module.ac_metrics(row)
        self.assertFalse(result['ac_feasible'])
        self.assertIsNone(result['max_trafo_pct'])
        self.assertIsNone(module.finite_stat(pd.Series([float('nan')]), 'max'))
        self.assertEqual(module.finite_stat(pd.Series([float('nan'), 97.4]), 'max'), 97.4)

    def test_compare_saved_stress_rejects_mismatch(self):
        sample = pd.DataFrame([dict(case_id='SS_B9', phase='candidate',
            timestamp_lst=pd.Timestamp('2025-11-27 20:00:00'),
            min_v_pu=.954, max_v_pu=.98, max_trafo_pct=99., max_line_pct=7.,
            ac_feasible=True)])
        same = dict(min_v_pu=.954, max_v_pu=.98, max_trafo_pct=99.,
                    max_line_pct=7., ac_feasible=True)
        module.compare_saved_stress(sample, 'SS_B9','candidate',
                                   pd.Timestamp('2025-11-27 20:00:00'), same)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            module.compare_saved_stress(sample, 'SS_B9','candidate',
                pd.Timestamp('2025-11-27 20:00:00'), dict(same, max_trafo_pct=104.))


if __name__ == '__main__':
    unittest.main()
