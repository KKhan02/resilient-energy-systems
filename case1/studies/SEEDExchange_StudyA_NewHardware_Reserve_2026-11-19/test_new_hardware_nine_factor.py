"""Synthetic new-hardware nine-factor screening checks (no pandapower execution)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import pandas as pd

file=Path(__file__).with_name("new_hardware_nine_factor.py")
spec=importlib.util.spec_from_file_location("nh_nine_factor",file)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NineFactorTests(unittest.TestCase):
    def test_factor_grid_is_complete(self):
        self.assertEqual(len(m.FACTORS),9)
        self.assertEqual(m.FACTORS[0],(.95,1.))
        self.assertEqual(m.FACTORS[-1],(1.,1.6))

    def test_accepts_only_named_relative_case_paths(self):
        with tempfile.TemporaryDirectory() as d:
            expected=Path(d)/"MC_B10"/"CHANGED_HOUR_AC.csv"
            self.assertEqual(m.checked_case_path(Path(d),"MC_B10",
                r"MC_B10\CHANGED_HOUR_AC.csv"),expected)
            with self.assertRaisesRegex(ValueError,"Unexpected signed"):
                m.checked_case_path(Path(d),"MC_B10",r"SS_B10\CHANGED_HOUR_AC.csv")
            with self.assertRaisesRegex(ValueError,"Unexpected signed"):
                m.checked_case_path(Path(d),"MC_B10","MC_B10/../escape.csv")

    def test_synthetic_pandapower_feasibility_screen(self):
        r={"status":"CONVERGED","ac_feasible":True,"min_v_pu":.955,
           "max_v_pu":1.02,"max_trafo_pct":99.4,"max_line_pct":7.1,
           "loss_kw":.1,"pcc_kva":4.8}
        self.assertTrue(m.ac_screen(r)["ac_feasible"])
        bad={**r,"ac_feasible":False,"max_trafo_pct":101}
        self.assertFalse(m.ac_screen(bad)["ac_feasible"])

    def test_inconsistent_solver_flag_is_rejected(self):
        r={"status":"CONVERGED","ac_feasible":True,"min_v_pu":.955,
           "max_v_pu":1.02,"max_trafo_pct":102,"max_line_pct":7.1,
           "loss_kw":.1,"pcc_kva":4.8}
        with self.assertRaisesRegex(ValueError,"feasibility flag disagrees"):
            m.ac_screen(r)

    def test_nonconvergent_metrics_are_explicit_not_nan(self):
        rec={"status":"NOT_CONVERGED","ac_feasible":False}
        self.assertFalse(m.ac_screen(rec)["ac_feasible"])
        x=pd.Series([float("nan"),None])
        self.assertIsNone(m.finite_extreme(x,"min"))
        self.assertIsNone(m.finite_extreme(x,"max"))

    def test_stress_hour_numeric_check_rejects_tampering(self):
        saved=pd.DataFrame([{"timestamp_lst":"2025-11-27 20:00:00",
            "old_trafo_pct":107.43117,"new_trafo_pct":92.53,
            "old_min_v_pu":.9542,"new_min_v_pu":.9572,
            "old_loss_kw":.19,"new_loss_kw":.17,
            "old_ac_feasible":False,"new_ac_feasible":True}])
        observed={"max_trafo_pct":90.,"min_v_pu":.9572,
                  "loss_kw":.17,"ac_feasible":True}
        with self.assertRaisesRegex(ValueError,"stress solver mismatch"):
            m.compare_stress_stored(saved,"MC_B10","candidate",
                "2025-11-27 20:00:00",observed)

if __name__=="__main__":
    unittest.main()
