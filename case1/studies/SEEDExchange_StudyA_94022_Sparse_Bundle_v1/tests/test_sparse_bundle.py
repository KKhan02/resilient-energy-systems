import unittest
import sys
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import studya_94022_sparse_bundle_trial as s

class BundleTests(unittest.TestCase):
    def test_source_integrity(self):
        m,h,r=s.source_data()
        self.assertEqual(len(h),2160)
        self.assertEqual(len(r),26)
        self.assertEqual(m['line_count'],26)
    def test_option_membership(self):
        _,_,r=s.source_data()
        o=s.proposed_options(r)
        self.assertEqual(len(o),15)
        self.assertEqual(o['head_reference'],[])
        self.assertEqual(o['service_007_R050'],[7])
        self.assertEqual(set(o['gis_top7_R050']),{14,11,16,18,21,22,17})
        self.assertEqual(set(o['all_LV_R050']),set(r.line_index))
        self.assertEqual(len(o['GIS_only_R050']),16)
        self.assertEqual(len(o['service_only_R050']),10)
    def test_branch_types(self):
        _,_,r=s.source_data()
        self.assertEqual(r.set_index('line_index').loc[7,'kind'],'ASSUMED_SERVICE')
        for i in [14,11,16,18,21,22,17]:
            self.assertEqual(r.set_index('line_index').loc[i,'kind'],'EPM_GIS_LV')
    def test_expected_original_feasible_count(self):
        _,h,_=s.source_data()
        self.assertEqual(h[h.option.eq('head_reference')].ac_feasible.sum(),28)
        self.assertEqual(h[h.option.eq('all_LV_R050')].ac_feasible.sum(),72)
    def test_valid_match(self):
        _,h,_=s.source_data()
        a=h[h.option.isin(['head_reference','all_LV_R050'])].copy()
        n, opts=s.audited_comparison(a,h)
        self.assertEqual(n,144)
        self.assertEqual(len(opts),2)
    def test_invalid_duplicate(self):
        _,h,_=s.source_data()
        a=h[h.option.eq('head_reference')].copy()
        self.assertRaises(ValueError,s.audited_comparison,a.iloc[:-1],h)
    def test_network_identity_guard(self):
        _,_,r=s.source_data()
        s.verify_lines(r,r.copy())
        d=r.copy(); d.loc[d.line_index.eq(7),'line_name']='changed'
        self.assertRaises(ValueError,s.verify_lines,r,d)
    def test_negative_feasibility_drift(self):
        _,h,_=s.source_data()
        a=h[h.option.eq('head_reference')].copy();a['ac_feasible']=~a['ac_feasible']
        self.assertRaises(ValueError,s.audited_comparison,a,h)

if __name__=='__main__':unittest.main()
