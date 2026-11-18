import importlib.util
import sys
import unittest
import hashlib
import json
import tempfile
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

    def test_new_frontier_case_names(self):
        names=('SS_P45_B9','MC_B10','SS_B9_POWER16','MC_P33')
        self.assertEqual(ac.case_plan(','.join(names),'stress'),
                         [(name,.95,1.6) for name in names])
        self.assertEqual(len(ac.case_plan('SS_P45_B9,MC_B10,SS_B10','all-nine')),27)

    def test_git_line_endings_match_signed_bytes_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'energy_hourly_2025.csv'
            signed=b'timestamp_lst,demand_kw\r\n2025-01-01 00:00:00,4\r\n'
            expected=hashlib.sha256(signed).hexdigest()
            f.write_bytes(signed)
            self.assertEqual(ac.signed_csv_line_endings(f,expected),'SIGNED_BYTES_MATCH')
            f.write_bytes(signed.replace(b'\r\n',b'\n'))
            self.assertEqual(ac.signed_csv_line_endings(f,expected),'EXACT_GIT_LF_TO_SIGNED_CRLF')
            f.write_bytes(signed.replace(b'4\r\n',b'5\n').replace(b'\r\n',b'\n'))
            with self.assertRaisesRegex(ValueError,'differs'):
                ac.signed_csv_line_endings(f,expected)

    def test_git_normalized_energy_requires_original_households_and_exact_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            idx=pd.date_range('2025-01-01',periods=8760,freq='h')
            load=np.full(8760,4.0)
            energy=pd.DataFrame({'timestamp_lst':idx,'demand_kw':load,'inverter_ac_kw':np.zeros(8760),
                 'pv_dc_available_kw':np.zeros(8760),'grid_export_kw':np.zeros(8760),
                 'unserved_kw':np.zeros(8760),'battery_soc_usable_kwh':np.full(8760,2.061)})
            raw=energy.to_csv(index=False,lineterminator='\n').encode()
            signed=hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest()
            (d/'energy_hourly_2025.csv').write_bytes(raw)
            manifest=d/'original_manifest.json';manifest.write_text('source')
            (d/'energy_manifest.json').write_text(json.dumps({
                'energy_csv_sha256':signed,'input_manifest_sha256':ac.sha(manifest),
                'case_id':'SS_P45_B9','transformer':'106039','scenario':'A1',
                'selected_house_ids':['H11'],'hardware':{'inverter_kva':20}}))
            ctx={'m':{},'mp':manifest,'houses':['H11'],
                 'trace':pd.DataFrame({'H11':load},index=idx)}
            class SignedValidator:
                @staticmethod
                def validated_energy_directory(*_):
                    raise AssertionError('Direct signed validator cannot accept Git-normalized CSV')
            actual,m=ac.energy_from_signed_or_git_normalized(SignedValidator,d,ctx)
            self.assertEqual(len(actual),8760)
            self.assertEqual(m['case_id'],'SS_P45_B9')
            ctx['houses']=['WRONG_HOUSE']
            with self.assertRaisesRegex(ValueError,'metadata differs'):
                ac.energy_from_signed_or_git_normalized(SignedValidator,d,ctx)

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
