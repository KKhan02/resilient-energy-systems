"""No numerical simulations. Check sweep coverage, immutable output checks and preflight."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('run_gross_sensitivity',HERE/'run_gross_sensitivity.py')
import sys
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)

class PlanTests(unittest.TestCase):
    def test_72_unique_configs_with_eight_existing_baselines(self):
        main=module.planned_cases('main')
        extra=module.planned_cases('interactions')
        baseline={(a,t,.98,1.) for a in ('A0','A1') for t in ('94022','106039','113699','85398')}
        planned={(c.assignment,c.transformer,c.pf,c.length) for c in main+extra}
        self.assertEqual((len(main),len(extra),len(planned)),(32,32,64))
        self.assertFalse(planned.intersection(baseline))
        self.assertEqual(len(planned.union(baseline)),72)
        self.assertFalse(any(c.transformer=='92395' for c in main+extra))

    def test_labels_unique_and_immutable_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            one=module.planned_cases('main')[0]
            d1=module.result_dir(root,one,24)
            d2=module.result_dir(root,one,8760)
            self.assertNotEqual(d1,d2)
            self.assertFalse(module.check_output(d1,one,24,module.EXPECTED_SHA))
            d1.mkdir()
            with self.assertRaises(RuntimeError):module.check_output(d1,one,24,module.EXPECTED_SHA)

    def test_genuine_manifest_and_original_runner_hash(self):
        manifest=Path('/mnt/data/input_manifest_v6_2.json')
        patched=Path('/mnt/data/SEEDExchange_StudyA_v6_2_Patch.zip')
        if not manifest.exists() or not patched.exists():self.skipTest('Turn-local source unavailable')
        with tempfile.TemporaryDirectory() as folder:
            repo=Path(folder);(repo/'.git').mkdir()
            mp=repo/module.MANIFEST_REL
            mp.parent.mkdir(parents=True);mp.write_bytes(manifest.read_bytes())
            script=repo/module.RUNNER_REL
            with zipfile.ZipFile(patched) as archive:
                script.write_bytes(archive.read('SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py'))
            m=module.preflight(repo,mp,script)
            self.assertEqual(m['groups']['A1']['92395'],['H30','H31','H32','H33'])
            self.assertEqual(module.sha256(script),m['script_sha256'])

if __name__=='__main__':unittest.main()
