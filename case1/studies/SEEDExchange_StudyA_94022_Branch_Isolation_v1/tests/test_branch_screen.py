from pathlib import Path
import sys,unittest
import pandas as pd
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import probe_94022_branch_isolation as b

class TestBranch(unittest.TestCase):
    def setUp(self):
        self.data=pd.DataFrame([
            dict(line_index=0,line_name='gis_lv_1',kind='EPM_GIS_LV',length_m=20.0,r_ohm_per_km=1.0,x_ohm_per_km=.1,max_i_ka=.10),
            dict(line_index=1,line_name='assumed_service_1',kind='ASSUMED_SERVICE',length_m=35.0,r_ohm_per_km=2.0,x_ohm_per_km=.1,max_i_ka=.08),
            dict(line_index=2,line_name='gis_lv_2',kind='EPM_GIS_LV',length_m=42.0,r_ohm_per_km=1.0,x_ohm_per_km=.1,max_i_ka=.10)])
    def test_options(self):
        o=b.options(self.data)
        self.assertEqual(o['all_LV_R050'],[0,1,2]);self.assertEqual(o['GIS_only_R050'],[0,2]);self.assertEqual(o['service_only_R050'],[1]);self.assertEqual(o['head_reference'],[])
        self.assertEqual(o['line_001_R050'],[1]);self.assertEqual(len(o),7)
    def test_catalog_consistent(self):
        b.consistent_catalog(self.data,self.data.copy())
        df=self.data.copy();df.loc[0,'length_m']+=1
        with self.assertRaises(ValueError):b.consistent_catalog(self.data,df)
    def test_catalog_unrecognized(self):
        frame=pd.DataFrame([dict(name='other',length_km=.1,r_ohm_per_km=1.,x_ohm_per_km=.1,max_i_ka=.1)])
        class Fake:pass
        fake=Fake();fake.line=frame
        with self.assertRaises(ValueError):b.line_metadata(fake,{'line_ids':[0]})
    def test_ac_feasible(self):
        s={'status':'CONVERGED','minimum_voltage_pu':.96,'maximum_voltage_pu':1.04,'transformer_loading_pct':95.,'line_loading_pct':90.}
        self.assertTrue(b.check_feasible(s))
        for key,value in [('minimum_voltage_pu',.94),('maximum_voltage_pu',1.06),('transformer_loading_pct',101),('line_loading_pct',101)]:
            t=dict(s);t[key]=value;self.assertFalse(b.check_feasible(t))

    def test_bundled_source_probe_integrity(self):
        path=Path(__file__).resolve().parents[1]/'inputs'/'StudyA_A0_94022_Network_Probe_v1.zip'
        manifest,rows,times=b.read_prior_probe(path)
        self.assertEqual(len(rows),360)
        self.assertEqual(len(times),9)
        self.assertTrue(manifest['baseline_head_reproduces_trial_or_original_hourly_AC'])

    def test_head_validation(self):
        rec={'status':'CONVERGED','min_v_pu':.9599,'max_v_pu':1.01,'max_trafo_pct':67.0}
        source={'minimum_voltage_pu':.96,'maximum_voltage_pu':1.01,'transformer_loading_pct':67.0}
        b.check_probe_head(rec,source)
        source['minimum_voltage_pu']=.94
        with self.assertRaises(ValueError):b.check_probe_head(rec,source)

if __name__=='__main__':unittest.main()
