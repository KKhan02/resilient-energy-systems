import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from transformer_q_guard import enforce_transformer_limit

class TransformerQGuardTests(unittest.TestCase):
    def test_unconstrained_is_unchanged(self):
        r=enforce_transformer_limit(2.,lambda q: 80.+5*q)
        self.assertEqual(r.status,'REQUEST_ACCEPTED')
        self.assertAlmostEqual(r.q_kvar,2.)
        self.assertTrue(r.can_enforce)

    def test_positive_q_is_reduced_to_thermal_boundary(self):
        r=enforce_transformer_limit(3.,lambda q:80.+10*q)
        self.assertTrue(r.can_enforce)
        self.assertAlmostEqual(r.q_kvar,2.,delta=.001)
        self.assertLessEqual(r.post_loading_pct,100.0001)
        self.assertEqual(r.status,'Q_REDUCED_TO_HOLD_TRAFO_LIMIT')

    def test_negative_q_is_reduced_with_sign_preserved(self):
        r=enforce_transformer_limit(-3.,lambda q:80.-10*q)
        self.assertAlmostEqual(r.q_kvar,-2.,delta=.001)
        self.assertTrue(r.can_enforce)

    def test_inverter_compensation_can_reduce_loading(self):
        r=enforce_transformer_limit(3.,lambda q:120.-10*q)
        self.assertAlmostEqual(r.q_kvar,3.)
        self.assertTrue(r.can_enforce)
        self.assertGreater(r.unity_loading_pct,100)

    def test_nonmonotone_feasible_island(self):
        r=enforce_transformer_limit(2.,lambda q:120.-100*q+60*q*q)
        self.assertTrue(r.can_enforce)
        self.assertGreater(r.q_kvar,.3)
        self.assertLess(r.q_kvar,1.5)
        self.assertLessEqual(r.post_loading_pct,100.0001)

    def test_no_possible_thermal_fix_is_reported(self):
        r=enforce_transformer_limit(4.,lambda q:120.+2*q)
        self.assertFalse(r.can_enforce)
        self.assertEqual(r.status,'NO_FEASIBLE_Q_ON_CONTROL_RAY')
        self.assertAlmostEqual(r.q_kvar,0.)
        self.assertGreater(r.post_loading_pct,100)

    def test_zero_q_can_still_overload(self):
        r=enforce_transformer_limit(0.,lambda q:102.)
        self.assertFalse(r.can_enforce)
        self.assertEqual(r.status,'NO_REACTIVE_ACTION_AND_OVERLOAD')

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):enforce_transformer_limit(2.,lambda q:float('nan'))
        with self.assertRaises(ValueError):enforce_transformer_limit(2.,lambda q:90.,sample_points=2)

if __name__=='__main__':unittest.main()
