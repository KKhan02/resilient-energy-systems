import importlib.util
from pathlib import Path
import tempfile
import unittest
import csv
import json
import hashlib

SCRIPT = Path(__file__).resolve().parents[1] / 'run_annual_replays.py'
spec = importlib.util.spec_from_file_location('study_a_annual_runner', SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AnnualPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.repo=Path('D:/fake/repository')
        self.out=self.repo/'outputs'/'pvbess_phase_01'

    def jobs(self,**kwargs):
        return module.build_jobs(self.repo,self.out,**kwargs)

    def test_total_annual_case_counts(self):
        self.assertEqual(len(self.jobs(scope='baseline')),48)
        self.assertEqual(len(self.jobs(scope='sensitivities')),384)
        self.assertEqual(len(self.jobs(scope='full')),432)

    def test_every_replay_has_8760_hours(self):
        for j in self.jobs(scope='full'):
            cmd=j['command']
            self.assertEqual(cmd[cmd.index('--hours')+1],'8760')
            self.assertNotIn('24',cmd)
            self.assertEqual(j['output'].parent.name,'annual_ac_replays_v1')

    def test_baseline_all_territories_and_both_dispatches(self):
        jobs=self.jobs()
        self.assertEqual({j['transformer'] for j in jobs},{'94022','106039','113699','85398','92395'})
        self.assertEqual({j['dispatch'] for j in jobs},{'optimized','causal'})
        self.assertEqual({j['variant'] for j in jobs if j['kind']=='ref'},{'A0','A1'})
        self.assertEqual({j['tier'] for j in jobs},{'min_cost','ss90'})

    def test_92395_star_mst_and_A0eqA1_once(self):
        jobs=[j for j in self.jobs() if j['transformer']=='92395']
        self.assertEqual(len(jobs),8) # 2 hardware tiers * 2 topologies * 2 dispatches
        self.assertEqual({j['topology'] for j in jobs},{'star','mst'})
        self.assertEqual({j['variant'] for j in jobs},{'A0'})
        self.assertEqual({j['kind'] for j in jobs},{'four'})

    def test_four_house_new_designs_included(self):
        jobs=[j for j in self.jobs() if j['kind']=='four']
        self.assertEqual(len(jobs),16) # 4+4 A0 territories, 8 92395
        self.assertEqual({j['transformer'] for j in jobs},{'113699','85398','92395'})

    def test_sensitivity_baseline_excluded(self):
        combinations={(j['pf'],j['length']) for j in self.jobs(scope='sensitivities')}
        self.assertEqual(len(combinations),8)
        self.assertNotIn((.98,1.0),combinations)
        self.assertEqual(len({(j['pf'],j['length']) for j in self.jobs(scope='full')}),9)

    def test_unique_output_across_entire_grid(self):
        jobs=self.jobs(scope='full')
        self.assertEqual(len(set(j['output'] for j in jobs)),len(jobs))

    def test_filters_do_not_hardcode_one_cohort(self):
        self.assertEqual(len(self.jobs(transformer='106039',assignment='A0')),4)
        self.assertEqual(len(self.jobs(transformer='113699',assignment='A0')),8)
        self.assertEqual(len(self.jobs(transformer='92395',assignment='A1')),0)
        self.assertEqual(len(self.jobs(cases='refs',dispatch='optimized')),16)
        self.assertEqual(len(self.jobs(cases='new-four',dispatch='causal')),8)

    def test_no_write_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)/'new_checkout'
            # no .git or input manifest: dry-run must still work and write nothing
            status=module.main(['--repo-root',str(repo),'--scope','baseline',
                                '--transformer','92395'])
            self.assertEqual(status,0)
            self.assertFalse(repo.exists())

    def test_signed_existing_output_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'result';out.mkdir()
            j=self.jobs(transformer='94022',assignment='A0',dispatch='optimized')[0].copy()
            j['output']=out
            energy=Path(tmp)/'energy';energy.mkdir()
            (energy/'energy_manifest.json').write_text('{"x":1}',encoding='utf-8')
            j['energy']=energy
            content='timestamp_lst,ac_feasible\n'+'\n'.join(f'2025-01-01 00:00:00,True' for _ in range(8759))
            # Correct first and last date; no need all distinct timestamps for simple count validation
            from datetime import datetime,timedelta
            start=datetime(2025,1,1)
            with (out/'ac_hourly.csv').open('w',encoding='utf-8',newline='') as f:
                writer=csv.writer(f);writer.writerow(['timestamp_lst','ac_feasible'])
                for i in range(8760):
                    writer.writerow([(start+timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'),'True'])
            rec=dict(status='ANNUAL_PVBESS_AC',hours=8760,scenario='A0',
                     transformer='94022',tier='min_cost',topology='mapped',
                     dispatch='optimized',input_manifest_sha256='signed',pf=.98,length_factor=1.,
                     energy_manifest_sha256=module.digest(energy/'energy_manifest.json'),
                     ac_hourly_sha256=module.digest(out/'ac_hourly.csv'),
                     selected_house_ids=['H01'])
            (out/'ac_summary.json').write_text(json.dumps(rec),encoding='utf-8')
            m={'groups':{'A0':{'94022':['H01']}}}
            self.assertTrue(module.verify_completed(j,'signed',m))
            rec['hours']=24
            (out/'ac_summary.json').write_text(json.dumps(rec),encoding='utf-8')
            with self.assertRaises(RuntimeError):module.verify_completed(j,'signed',m)

if __name__=='__main__':unittest.main()

# Addition: standalone resilient energy/causal planner imports the v1.1 source.
import importlib.util as _spec_util
_energy_script=SCRIPT.parent/'run_all_energy_causal.py'
_en_spec=_spec_util.spec_from_file_location('study_a_energy_causal_batch',_energy_script)
_energy_mod=_spec_util.module_from_spec(_en_spec)
_en_spec.loader.exec_module(_energy_mod)

class EnergyCausalBatchTests(unittest.TestCase):
    def test_all_energy_causal_has_44_independent_jobs(self):
        repo=Path('D:/synthetic/repo');o=repo/'outputs'
        rows=_energy_mod.get_jobs(repo,o)
        self.assertEqual(len(rows),44)
        self.assertEqual(len(_energy_mod.get_jobs(repo,o,'energy')),22)
        self.assertEqual(len(_energy_mod.get_jobs(repo,o,'causal')),22)
        self.assertEqual(sum(j['job']=='four_opt' for j in rows),6)
        self.assertEqual(sum(j['job']=='four_causal' for j in rows),6)
        self.assertEqual(len({j['outdir'] for j in rows}),44)

    def test_energy_causal_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)/'new_repo'
            self.assertEqual(_energy_mod.main(['--repo-root',str(repo),'--stage','both']),0)
            self.assertFalse(repo.exists())
