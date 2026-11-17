from pathlib import Path
import csv
import hashlib
import json
import sys
import tempfile
from unittest import TestCase, mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_study_a as a

class IntegratedFakeCheckout(TestCase):
    def test_complete_user_run_dry_gis_skip_under_project(self):
        positions={
            '94022':(6.24695,-75.00621), '106039':(6.24284,-75.00481),
            '113699':(6.24343,-75.00813), '85398':(6.23778,-75.00292),
            '92395':(6.24706,-75.001), '98380':(6.23709,-75.0126),
        }
        original={}
        for h in a.CORE7 + a.CORE9_MORE:original[h]='94022'
        for h in a.CORE12:original[h]='106039'
        for n in range(1,36):
            h=f'H{n:02d}'
            original.setdefault(h,'113699' if n in (4,5,7,10) else '85398' if n in (9,12,14,15) else '92395' if n in (30,31,32,33) else '98380' if n==8 else '94022')
        with tempfile.TemporaryDirectory(prefix='seed_a_smoketest_') as temporary:
            repo=Path(temporary)/'repo'
            (repo/'.git').mkdir(parents=True)
            (repo/a.HOUSES).parent.mkdir(parents=True)
            with (repo/a.HOUSES).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['house_id','latitude','longitude','transformer_number','assignment_status'])
                w.writeheader()
                for hid,t in sorted(original.items()):
                    lat,lon=positions[a.CANDIDATE_MOVES.get(hid,t)]
                    w.writerow({'house_id':hid,'latitude':lat,'longitude':lon,'transformer_number':t,'assignment_status':'possible'})
            with (repo/a.TRAFOS).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['transformer_number','latitude','longitude','kva'])
                w.writeheader()
                for k,(lat,lon) in positions.items():w.writerow({'transformer_number':k,'latitude':lat,'longitude':lon,'kva':3 if k in ('113699','98380') else 5})
            (repo/a.GEOJSON).write_text('{"type":"FeatureCollection","features":[]}',encoding='utf-8')
            fake_hashes={str(key):a.digest(repo/key) for key in (a.HOUSES,a.TRAFOS,a.GEOJSON)}
            out=repo/'case1'/'studies'/'trial_01'
            with mock.patch.dict(a.EXPECTED_SHA,fake_hashes),mock.patch.object(sys,'argv',['prepare_study_a.py','--repo-root',str(repo),'--outdir',str(out),'--skip-gis']):
                a.main()
            meta=json.loads((out/'preflight_summary.json').read_text())
            self.assertEqual(meta['status'],'COMPLETED_LOAD_ONLY_LOCAL_PREFLIGHT_NOT_AC')
            self.assertEqual(meta['historical_original_20_profile_check']['status'],'MISSING_IN_LOCAL_CHECKOUT')
            self.assertEqual(meta['scenario_house_counts']['A0_original']['94022'],10)
            self.assertEqual(meta['scenario_house_counts']['A1_nearest_point']['94022'],8)
            with (out/'gross_load_pf_sensitivity.csv').open(newline='') as f:self.assertEqual(len(list(csv.DictReader(f))),72)
            self.assertFalse((repo/'case1'/'studies'/'trial_02').exists())
