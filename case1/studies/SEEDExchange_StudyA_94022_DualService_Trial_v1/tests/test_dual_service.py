import importlib.util
import sys
import unittest
from pathlib import Path
import pandas as pd

p=Path(__file__).resolve().parents[1]/'studya_94022_dual_service_trial.py'
spec=importlib.util.spec_from_file_location('dual_service',p)
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)

class DualServiceTests(unittest.TestCase):
    def test_input_hash_and_coverage(self):
        rows,summary,branches,manifest=module.read_source()
        self.assertEqual(len(rows),1080)
        self.assertEqual(len(summary),15)
        self.assertEqual(len(branches),26)
        self.assertEqual(len(set(rows['option'])),15)
    def test_service_mapping_exact(self):
        _,_,br,_=module.read_source()
        self.assertEqual(br.set_index('line_index').loc[7,'to_model_bus'],'HOUSE_H01')
        self.assertEqual(br.set_index('line_index').loc[4,'to_model_bus'],'HOUSE_H06')
    def test_group_unique_and_sensitivities(self):
        self.assertEqual(len(module.OPTIONS),16)
        self.assertIn('all_LV_R050',module.OPTIONS)
        self.assertIn('head_reference',module.OPTIONS)
        self.assertEqual(module.OPTIONS['svc007_004_gis014_011_R050'],[7,4,14,11])
        for k,ids in module.OPTIONS.items():
            if isinstance(ids,list):self.assertEqual(len(ids),len(set(ids)),k)
    def test_feasibility_threshold(self):
        base=dict(minimum_voltage_pu=[.95001,.94999,.96,.96,.96],
                  maximum_voltage_pu=[1,1,1.05001,1,1],
                  transformer_loading_pct=[98,98,98,100.001,98],
                  line_loading_pct=[20,20,20,20,100.001],status=['CONVERGED']*5)
        self.assertEqual(module.feasible(pd.DataFrame(base)).tolist(),[True,False,False,False,False])
    def test_source_option_flags_consistent(self):
        r,_,_,_=module.read_source()
        self.assertTrue((module.feasible(r)==r.ac_feasible).all())
    def test_controls_integrity(self):
        r,_,_,_=module.read_source()
        controls={'head_reference','svc007_gis014_011_R050','svc007_gis_top9_R050','GIS_only_R050','service_only_R050','all_LV_R050'}
        limited=r[r.option.isin(controls)]
        n,opts,err=module.compare_controls(limited,r)
        self.assertEqual(n,6*72)
        self.assertEqual(err,0)
    def test_controls_cannot_omit_baseline(self):
        r,_,_,_=module.read_source()
        with self.assertRaises(ValueError):module.compare_controls(r[r.option.ne('head_reference')],r)
    def test_results_incomplete_detected(self):
        r,sm,br,_=module.read_source()
        with self.assertRaises(ValueError):module.validate_output(r,r,br,sm)
    def test_previous_source_dimension_counts(self):
        r,_,_,_=module.read_source()
        self.assertTrue(r.groupby('option').size().eq(72).all())
        self.assertEqual(r.timestamp_lst.nunique(),9)
        self.assertEqual(len(r[['case','dispatch']].drop_duplicates()),4)

if __name__=='__main__':unittest.main()
