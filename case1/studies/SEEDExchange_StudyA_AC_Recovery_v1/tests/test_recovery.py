import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recover',HERE/'studya_recover_ac_summaries.py')
r=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.ac=self.root/'ac';self.en=self.root/'energy';self.ca=self.root/'causal'
        for p in (self.ac,self.en,self.ca):p.mkdir()
        self.job={'output':self.ac,'energy':self.en,'causal':self.ca,
                 'variant':'A0','transformer':'106039','tier':'min_cost',
                 'topology':'mapped','dispatch':'optimized','pf':.98,'length':1.0}
        self.manifest={'groups':{'A0':{'106039':['H11','H13']}}}
        self.sha='source_sha_test'
        self.times=pd.date_range('2025-01-01',periods=8760,freq='h')
        df=pd.DataFrame({'timestamp_lst':self.times.strftime('%Y-%m-%d %H:%M:%S'),
            'gross_demand_kw':1.0,'inverter_ac_kw':0.5,
            'load_pf':.98,'status':'CONVERGED','ac_feasible':True,
            'min_v_pu':0.98,'max_v_pu':.99,'max_trafo_pct':40.0,
            'max_line_pct':2.0,'loss_kw':.001,
            'voltage_below_095':0,'voltage_above_105':0,
            'trafo_over_100':0,'line_over_100':0})
        self.df=df
        self._write_case()
    def tearDown(self):self.tmp.cleanup()
    def _write_case(self):
        self.df.to_csv(self.ac/'ac_hourly.csv',index=False)
        source=pd.DataFrame({'timestamp_lst':self.times.strftime('%Y-%m-%d %H:%M:%S'),
            'demand_kw':[1.]*8760,'inverter_ac_kw':[.5]*8760})
        source.to_csv(self.en/'energy_hourly_2025.csv',index=False)
        meta={'input_manifest_sha256':self.sha,
             'selected_house_ids':['H11','H13'],
             'hardware_selection_tier':'min_cost',
             'energy_csv_sha256':r.digest(self.en/'energy_hourly_2025.csv')}
        (self.en/'energy_manifest.json').write_text(json.dumps(meta))
    def test_valid_csv_generates_identical_source_summary_fields(self):
        q=r.check_and_reconstruct(self.job,self.manifest,self.sha)
        self.assertEqual(q['hours'],8760)
        self.assertEqual(q['converged_hours'],8760)
        self.assertEqual(q['AC_infeasible_hours'],0)
        self.assertEqual(q['min_voltage_pu'],.98)
        self.assertIn('recovery_provenance',q)
    def test_rejects_changed_energy_input(self):
        self.df.loc[500,'gross_demand_kw']=4.0
        self.df.to_csv(self.ac/'ac_hourly.csv',index=False)
        with self.assertRaisesRegex(ValueError,'differs from source dispatch'):
            r.check_and_reconstruct(self.job,self.manifest,self.sha)
    def test_rejects_failed_hour(self):
        self.df.loc[30,'status']='AC_FAILURE'
        self.df.to_csv(self.ac/'ac_hourly.csv',index=False)
        with self.assertRaisesRegex(ValueError,'AC failure statuses'):
            r.check_and_reconstruct(self.job,self.manifest,self.sha)
    def test_rejects_misreported_violation(self):
        self.df.loc[26,'min_v_pu']=0.94
        self.df.to_csv(self.ac/'ac_hourly.csv',index=False)
        with self.assertRaisesRegex(ValueError,'feasible flags'):
            r.check_and_reconstruct(self.job,self.manifest,self.sha)
    def test_rejects_nonfinite(self):
        self.df.loc[99,'min_v_pu']=np.nan
        self.df.to_csv(self.ac/'ac_hourly.csv',index=False)
        with self.assertRaisesRegex(ValueError,'null/non-finite'):
            r.check_and_reconstruct(self.job,self.manifest,self.sha)
    def test_rejects_incomplete_year(self):
        self.df.iloc[:-1].to_csv(self.ac/'ac_hourly.csv',index=False)
        with self.assertRaisesRegex(ValueError,'not 8760'):
            r.check_and_reconstruct(self.job,self.manifest,self.sha)
    def test_rejects_existing_summary(self):
        (self.ac/'ac_summary.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'already exists'):
            r.check_and_reconstruct(self.job,self.manifest,self.sha)

if __name__=='__main__':unittest.main()
