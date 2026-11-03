import math, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from coordinated_q_control import (ACLimits,ACPoint,choose_q,build_ratio_grid,feasible)

class TestCoordinatedQ(unittest.TestCase):
    def test_sweep_grid_contains_special_values(self):
        v=build_ratio_grid(0,.6,.1,(.25,.48))
        self.assertEqual(v[0],0.)
        self.assertEqual(v[-1],.6)
        self.assertIn(.25,v)
        self.assertIn(.48,v)

    def test_good_q_different_from_hil_request(self):
        # Positive Q raises min voltage but increases trafo loading;
        # negative Q reduces overvoltage but harms low voltage.
        def mock(q):
            return ACPoint(q,.965+.02*q,1.015+.008*q,92+20*abs(q),15,.3+q*q,3.3)
        result=choose_q(mock,1.,0.,ACLimits(),grid_points=31,refine=2)
        self.assertTrue(result.feasible)
        self.assertGreater(result.point.q_kvar,.24)
        self.assertLessEqual(result.point.trafo_pct,100.0001)
        self.assertEqual(result.status,'AC_FEASIBLE_Q')

    def test_no_feasible_q_is_honest(self):
        def mock(q):return ACPoint(q,.89,1.08,120.,40.,1.,8.)
        choice=choose_q(mock,1.,.5)
        self.assertFalse(choice.feasible)
        self.assertEqual(choice.status,'NO_SAMPLED_AC_FEASIBLE_Q_AT_FIXED_P')

    def test_negative_q_controls_overvoltage(self):
        def mock(q):return ACPoint(q,.985+.005*q,1.055+.06*q,85+10*abs(q),15,.2,4.0)
        choice=choose_q(mock,1.,0.)
        self.assertTrue(choice.feasible)
        self.assertLess(choice.point.q_kvar,-.4)

    def test_zero_reactive_headroom(self):
        def mock(q):return ACPoint(q,.98,1.02,70,12,.2,3.)
        choice=choose_q(mock,0.,0.)
        self.assertTrue(choice.feasible)
        self.assertEqual(choice.evaluations,1)

    def test_limit_validator(self):
        with self.assertRaises(ValueError):ACLimits(min_v=1.02)
        with self.assertRaises(ValueError):build_ratio_grid(0,.6,0)
        with self.assertRaises(ValueError):choose_q(lambda q: ACPoint(q,1,1,0,0,0,0),-1,0)

if __name__=='__main__':unittest.main()
