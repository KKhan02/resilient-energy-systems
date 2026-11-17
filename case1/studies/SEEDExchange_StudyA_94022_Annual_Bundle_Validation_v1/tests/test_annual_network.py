import importlib.util
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

SCRIPT=Path(__file__).resolve().parents[1]/'validate_94022_annual_bundle.py'
spec=importlib.util.spec_from_file_location('annual_bundle_for_tests',SCRIPT)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

class AnnualBundleTests(unittest.TestCase):
    def test_verified_source_zip(self):
        src,manifest=mod.load_target()
        self.assertEqual(len(src),1620)
        self.assertEqual(src.option.nunique(),5)
        self.assertEqual(src.groupby('option').size().tolist(),[324]*5)
        self.assertFalse(manifest['annual_8760_ac_validated'])
    def test_all_three_bundles_pass_source(self):
        src,_=mod.load_target()
        for name,opt in mod.OPTION_NAMES.items():
            d=src[src.option.eq(opt)]
            self.assertEqual(int(d.ac_feasible.sum()),324)
            self.assertGreaterEqual(d.minimum_voltage_pu.min(),.95)
    def test_full_target_reproduction_keys(self):
        src,_=mod.load_target()
        for bundle,opt in mod.OPTION_NAMES.items():
            d=mod.select_checks(src,'A0_94022_min_cost_ref','causal',.95,1.6,opt)
            self.assertEqual(len(d),9)
            self.assertTrue(d.index.is_unique)
    def test_correct_bundles(self):
        self.assertEqual(mod.BUNDLES['four'],[7,4,14,11])
        self.assertEqual(mod.BUNDLES['five'],[7,4,14,11,16])
        self.assertEqual(mod.BUNDLES['six'],[7,4,14,11,16,18])
    def test_modes(self):
        fake={'candidate_files':[{'case':f'case{i}','dispatch':'optimized'} for i in range(4)]}
        self.assertEqual(len(mod.make_plan(fake,'pilot','five')),4)
        self.assertEqual(len(mod.make_plan(fake,'reference','five')),4)
        self.assertEqual(len(mod.make_plan(fake,'all-nine','five')),36)
        with self.assertRaises(ValueError):mod.make_plan(fake,'unknown','five')
    def test_feasibility_recomputed(self):
        df=pd.DataFrame({'status':['CONVERGED']*4,
           'min_v_pu':[.95,.949,1.,.96],'max_v_pu':[1.,1.,1.051,1.],
           'max_trafo_pct':[95.,95.,95.,100.1],'max_line_pct':[50.]*4})
        self.assertEqual(mod.physical_feasible(df).tolist(),[True,False,False,False])
    def test_selected_control_detects_corruption(self):
        src,_=mod.load_target()
        s=mod.select_checks(src,'A0_94022_min_cost_ref','causal',.95,1.6,mod.OPTION_NAMES['five'])
        frame=pd.DataFrame({'timestamp_lst':s.index,
           'min_v_pu':s.minimum_voltage_pu.values,'max_v_pu':s.maximum_voltage_pu.values,
           'max_trafo_pct':s.transformer_loading_pct.values,'max_line_pct':s.line_loading_pct.values,
           'ac_feasible':s.ac_feasible.values})
        self.assertLess(max(mod.assert_control(frame,s).values()),1e-12)
        frame.loc[0,'min_v_pu']+=.02
        with self.assertRaises(ValueError):mod.assert_control(frame,s)
    def test_record_annual_strict_criterion(self):
        dates=pd.Series(pd.date_range('2025-01-01',periods=8760,freq='h'))
        self.assertTrue(dates.equals(pd.Series(pd.date_range('2025-01-01',periods=8760,freq='h'))))

if __name__=='__main__':unittest.main()
