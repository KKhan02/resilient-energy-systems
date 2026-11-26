import unittest
import pandas as pd
import remote_94022_A1_annual as r

class AnnualGate(unittest.TestCase):
    def test_plan(self):
        r.check_plan()
        self.assertEqual(len(r.SELECTED)*len(r.FACTORS)*8760,52560)
        self.assertEqual(len(r.EXPECTED),9)
    def test_regression(self):
        r.sample_regression({"strict_failures":0,"minimum_voltage_pu":.951000001},{"strict_failures":0,"minimum_voltage_pu":.951})
    def test_failure_gate(self):
        with self.assertRaisesRegex(ValueError,"strict_failures"):
            r.sample_regression({"strict_failures":1},{"strict_failures":0})
    def test_voltage_gate(self):
        with self.assertRaisesRegex(ValueError,"minimum_voltage_pu"):
            r.sample_regression({"minimum_voltage_pu":.950},{"minimum_voltage_pu":.951})
    def test_stats(self):
        a=pd.DataFrame(dict(strict_feasible=[True,False],night_reactive_disabled=[False,True],
            min_v_pu=[.99,.949],max_v_pu=[1.,1.],max_trafo_pct=[50.,60.],max_line_pct=[10.,20.]))
        out=r.stats(a)
        self.assertEqual(out["strict_failures"],1)
        self.assertEqual(out["night_failures"],1)
        self.assertEqual(out["minimum_voltage_pu"],.949)
        self.assertEqual(out["optional_under_097_hours"],1)

if __name__=="__main__":unittest.main()
