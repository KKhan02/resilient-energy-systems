import csv
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'collect_studya_pvbess_results_v2.py'
spec=importlib.util.spec_from_file_location('studya_collector2',MODULE)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CollectorTests(unittest.TestCase):
    def create_case(self,root,invalid=False):
        basedir=root/c.BASE/'annual_ac_replays_v1'
        basedir.mkdir(parents=True,exist_ok=True)
        manifest=root/c.MANIFEST_REL
        manifest.parent.mkdir(parents=True,exist_ok=True)
        manifest.write_text('{}')
        case=basedir/'A0_106039_min_cost_ref_mapped_optimized_pf098_length10_annual8760'
        case.mkdir()
        hourly=case/'ac_hourly.csv'
        with hourly.open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f)
            writer.writerow(['timestamp_lst','dummy'])
            for i,t in enumerate(c.HOUR_LABELS):
                writer.writerow([t if not (invalid and i==500) else '2025-01-01 00:00:00','1'])
        sha=hashlib.sha256(hourly.read_bytes()).hexdigest()
        m={'status':'ANNUAL_PVBESS_AC','scenario':'A0','transformer':'106039',
           'tier':'min_cost','topology':'mapped','dispatch':'optimized','pf':.98,
           'length_factor':1.,'hours':8760,'converged_hours':8760,
           'nonconverged_hours':0,'selected_house_ids':['H01','H02','H03','H04'],
           'AC_infeasible_hours':1,'voltage_below_095_hours':1,
           'transformer_overload_hours':0,'min_voltage_pu':.948,
           'max_transformer_loading_pct':81.2,'annual_or_sample_losses_kwh':130.,
           'input_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
           'ac_hourly_sha256':sha}
        (case/'ac_summary.json').write_text(json.dumps(m))
        return case

    def test_signed_full_year(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.create_case(root)
            result=c.run(root,root/'audit.zip',progress=0)
            self.assertEqual(result['signed_chronology_verified']['ac'],1)
            self.assertEqual(result['issues'],[])

    def test_tampered_chronology_detected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.create_case(root,invalid=True)
            result=c.run(root,root/'audit.zip',progress=0)
            self.assertEqual(result['signed_chronology_verified']['ac'],0)
            self.assertIn('NOT_EXACT_2025_CHRONOLOGY',result['issues'][0]['issue'])

    def test_missing_summary_detected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);case=self.create_case(root)
            (case/'ac_summary.json').unlink()
            result=c.run(root,root/'audit.zip',progress=0)
            self.assertEqual(result['signed_chronology_verified']['ac'],0)
            self.assertIn('SUMMARY_MISSING',result['issues'][0]['issue'])

    def test_name_and_hash_parse(self):
        self.assertEqual(len(c.HOUR_LABELS),8760)
        self.assertEqual(c.HOUR_LABELS[0],'2025-01-01 00:00:00')
        self.assertEqual(c.HOUR_LABELS[-1],'2025-12-31 23:00:00')
        self.assertEqual(c.EXPECT['ac'],432)

if __name__=='__main__':unittest.main()
