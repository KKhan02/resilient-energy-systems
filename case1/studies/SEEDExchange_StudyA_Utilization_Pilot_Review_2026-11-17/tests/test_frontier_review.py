import importlib.util
import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

BASE=Path(__file__).resolve().parents[1]
def load(module,file):
    s=importlib.util.spec_from_file_location(module,BASE/file)
    obj=importlib.util.module_from_spec(s);sys.modules[module]=obj;s.loader.exec_module(obj);return obj
ac=load('frontier_validation_unit','validate_frontier_ac.py')

class TestScopeAndControls(unittest.TestCase):
    def test_stress_count(self):
        self.assertEqual(ac.case_plan('SS_B9,MC_B9','stress'),[('SS_B9',.95,1.6),('MC_B9',.95,1.6)])
    def test_all_nine(self):
        self.assertEqual(len(ac.case_plan('SS_B9,MC_B9','all-nine')),18)
    def test_no_invalid_case(self):
        with self.assertRaises(ValueError):ac.case_plan('SS_B9,WHAT','stress')
    def test_no_duplicate_case(self):
        with self.assertRaises(ValueError):ac.case_plan('SS_B9,SS_B9','reference')
    def test_no_invalid_mode(self):
        with self.assertRaises(ValueError):ac.case_plan('SS_B9','other')
    def test_electrical_screen(self):
        d=pd.DataFrame([{'timestamp_lst':'2025-01-01','status':'CONVERGED','ac_feasible':True,'min_v_pu':.956,'max_v_pu':1.01,'max_trafo_pct':90,'max_line_pct':50},
                       {'timestamp_lst':'2025-01-02','status':'CONVERGED','ac_feasible':False,'min_v_pu':.94,'max_v_pu':1.01,'max_trafo_pct':90,'max_line_pct':50},
                       {'timestamp_lst':'2025-01-03','status':'CONVERGED','ac_feasible':False,'min_v_pu':.956,'max_v_pu':1.01,'max_trafo_pct':101,'max_line_pct':50}])
        self.assertEqual(ac.valid_ac(d).tolist(),[True,False,False])
    def test_q_control_screen_missing_measure(self):
        with self.assertRaises(ValueError):ac.valid_ac(pd.DataFrame([{'status':'CONVERGED'}]))

if __name__=='__main__':unittest.main()
