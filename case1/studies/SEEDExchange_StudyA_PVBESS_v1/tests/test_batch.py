import unittest
from pathlib import Path
import importlib.util
p=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('run_portfolio',p/'run_portfolio.py')
# Script imports study_a_pvbess from same dir
import sys
sys.path.insert(0,str(p))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class Batch(unittest.TestCase):
    def test_all_energy(self):
        self.assertEqual(len(mod.proposed_jobs(Path('/tmp/repo'),Path('/tmp/results'),'all-energy')),22)
    def test_all_causal(self):
        self.assertEqual(len(mod.proposed_jobs(Path('/tmp/repo'),Path('/tmp/results'),'all-causal')),22)
    def test_single_106039(self):
        cases=mod.proposed_jobs(Path('/tmp/repo'),Path('/tmp/results'),'mapped-energy','106039','A0')
        self.assertEqual({x['tier'] for x in cases},{'min_cost','ss90'})
    def test_92395_only_dedicated_milps(self):
        cases=mod.proposed_jobs(Path('/tmp/repo'),Path('/tmp/results'),'all-energy','92395')
        self.assertEqual(len(cases),2)
        self.assertTrue(all(x['job']=='four_opt' for x in cases))
    def test_no_mixing_output_dirs(self):
        jobs=mod.proposed_jobs(Path('/tmp/repo'),Path('/tmp/results'),'all')
        self.assertEqual(len({str(x['outdir']) for x in jobs}),44)
if __name__=='__main__':unittest.main()
