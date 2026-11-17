"""Tests for the read-only annual output export utility (standard library only)."""
import csv
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
import zipfile

SCRIPT = pathlib.Path(__file__).parents[1] / 'export_selected_annual_results.py'
spec = importlib.util.spec_from_file_location('annual_export', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class TestAnnualExport(unittest.TestCase):
    def prepare(self, repo, cid):
        ac = repo / mod.SOURCE_AC / cid / mod.SCENARIO
        energy = repo / mod.SOURCE_ENERGY / cid
        ac.mkdir(parents=True)
        energy.mkdir(parents=True)
        hourly = ('hour_index,ac_feasible\n' + ''.join(f'{i},True\n' for i in range(8760))).encode()
        trajectory = b'hour_index,pu\n0,1\n'
        (ac / 'annual_ac_hours.csv').write_bytes(hourly)
        (energy / 'fixed_hardware_manufacturer_soc_baseline.csv').write_bytes(trajectory)
        (energy / 'pilot_manifest.json').write_text(json.dumps({
            'candidate_id':cid, 'source_trajectory_sha256':sha(trajectory),
            'manufacturer_soc_baseline_annual_total_usd': 4500.0,
        }))
        (ac / 'annual_ac_summary.json').write_text(json.dumps({
            'candidate_id':cid, 'hours_checked':8760, 'all_8760_evaluated':True,
            'ac_feasible_full_year':True, 'source_trajectory_sha256':sha(trajectory),
            'load_pf':.98, 'service_factor':1.0,
        }))
        (ac / 'ac_checkpoint.json').write_text(json.dumps({
            'status':'COMPLETE', 'hours_saved':8760,
            'annual_ac_hours_sha256':sha(hourly),
            'signature':{'candidate_id':cid,'trajectory_sha256':sha(trajectory)},
        }))

    def test_two_candidate_export_and_zip(self):
        with tempfile.TemporaryDirectory() as root:
            repo = pathlib.Path(root)
            for cid in mod.CANDIDATES:
                self.prepare(repo, cid)
            out = repo / 'case1/studies/ac_aware_redispatch_v1/outputs/exports/two_01'
            result = mod.build_export(repo, out)
            self.assertEqual(len(result['candidates']), 2)
            self.assertTrue(all(r['source_integrity'] == 'VERIFIED' for r in result['candidates']))
            with zipfile.ZipFile(result['zip']) as archive:
                self.assertIn('comparison.csv', archive.namelist())
                self.assertEqual(len([n for n in archive.namelist() if n.endswith('/annual_ac_hours.csv')]),2)
            with self.assertRaises(FileExistsError):
                mod.build_export(repo, out)

    def test_missing_candidate_reported_without_claiming_pass(self):
        with tempfile.TemporaryDirectory() as root:
            repo = pathlib.Path(root)
            self.prepare(repo,mod.CANDIDATES[0])
            result = mod.build_export(repo,repo/'case1/studies/ac_aware_redispatch_v1/outputs/exports/two_02')
            self.assertEqual(result['candidates'][1]['status'],'AC_NOT_FOUND')
            self.assertEqual(result['candidates'][1]['source_integrity'],'NOT_VERIFIED')

    def test_wrong_ac_hash_detected(self):
        with tempfile.TemporaryDirectory() as root:
            repo = pathlib.Path(root)
            self.prepare(repo, mod.CANDIDATES[0])
            ac_path = repo / mod.SOURCE_AC / mod.CANDIDATES[0] / mod.SCENARIO / 'annual_ac_hours.csv'
            ac_path.write_text('tampered')
            result = mod.build_export(repo,repo/'case1/studies/ac_aware_redispatch_v1/outputs/exports/two_03')
            self.assertEqual(result['candidates'][0]['source_integrity'],'NOT_VERIFIED')
            self.assertIn('SHA256 mismatch',result['candidates'][0]['issues'])

    def test_refuse_path_outside_repo(self):
        with tempfile.TemporaryDirectory() as root:
            repo = pathlib.Path(root)/'repo'
            (repo / mod.SOURCE_AC).mkdir(parents=True)
            with self.assertRaises(ValueError):
                mod.build_export(repo, pathlib.Path(root)/'outside')

if __name__ == '__main__':
    unittest.main()
