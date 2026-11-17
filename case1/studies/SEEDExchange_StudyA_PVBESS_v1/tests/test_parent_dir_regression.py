"""Regression: a new portfolio stage must create only its output parent.

No PyPSA/pandapower or GitLab access is needed for these tests.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('run_portfolio_regression', ROOT / 'run_portfolio.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ParentDirRegression(unittest.TestCase):
    def test_dry_run_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            repo.mkdir()
            outbase = Path(tmp) / 'nested' / 'pvbess_phase_01'
            with patch.object(mod, 'proposed_jobs', return_value=[{
                'job': 'mapped_energy', 'variant': 'A0', 'trafo': '106039',
                'tier': 'min_cost', 'outdir': outbase / 'energy_A0_106039_min_cost_ref',
                'args': ['stub']
            }]):
                self.assertEqual(mod.main(['--repo-root', str(repo), '--outbase', str(outbase),
                                          '--stage', 'mapped-energy']), 0)
            self.assertFalse(outbase.exists())

    def test_run_creates_parent_after_validation_before_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            repo.mkdir()
            outbase = Path(tmp) / 'nested' / 'pvbess_phase_01'
            case = outbase / 'energy_A0_106039_min_cost_ref'
            job = {'job': 'mapped_energy', 'variant': 'A0', 'trafo': '106039',
                   'tier': 'min_cost', 'outdir': case, 'args': ['stub']}
            manifest = {'groups': {'A0': {'106039': ['H11']}}}
            called = []

            def stub_subprocess(args, **kwargs):
                self.assertTrue(outbase.is_dir())
                self.assertFalse(case.exists(), 'Launcher must not create case folder')
                called.append(args)
                return CompletedProcess(args, 0)

            with patch.object(mod, 'proposed_jobs', return_value=[job]), \
                 patch.object(mod, 'secure_context', return_value=(manifest, None, None, None)), \
                 patch.object(mod, 'digest', return_value='signed-hash'), \
                 patch.object(mod, 'check_reuse', side_effect=[False, True]), \
                 patch.object(mod.subprocess, 'run', side_effect=stub_subprocess):
                self.assertEqual(mod.main(['--repo-root', str(repo), '--outbase', str(outbase),
                                          '--stage', 'mapped-energy', '--run']), 0)
            self.assertEqual(called, [['stub']])
            self.assertTrue(outbase.is_dir())
            self.assertFalse(case.exists())

    def test_failed_source_validation_never_creates_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            repo.mkdir()
            outbase = Path(tmp) / 'nested' / 'pvbess_phase_01'
            job = {'job': 'mapped_energy', 'variant': 'A0', 'trafo': '106039',
                   'tier': 'min_cost', 'outdir': outbase / 'case', 'args': ['stub']}
            with patch.object(mod, 'proposed_jobs', return_value=[job]), \
                 patch.object(mod, 'secure_context', side_effect=ValueError('bad manifest')):
                with self.assertRaisesRegex(ValueError, 'bad manifest'):
                    mod.main(['--repo-root', str(repo), '--outbase', str(outbase),
                              '--stage', 'mapped-energy', '--run'])
            self.assertFalse(outbase.exists())

    def test_reject_outside_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'; repo.mkdir()
            outbase = Path(tmp) / 'nested' / 'pvbess_phase_01'
            job = {'job': 'mapped_energy', 'variant': 'A0', 'trafo': '106039',
                   'tier': 'min_cost', 'outdir': Path(tmp) / 'outside', 'args': ['stub']}
            with patch.object(mod, 'proposed_jobs', return_value=[job]), \
                 patch.object(mod, 'secure_context', return_value=({'groups': {}}, None, None, None)), \
                 patch.object(mod, 'digest', return_value='hash'), \
                 patch.object(mod, 'check_reuse', return_value=False):
                with self.assertRaisesRegex(RuntimeError, 'outside the selected output base'):
                    mod.main(['--repo-root', str(repo), '--outbase', str(outbase),
                              '--stage', 'mapped-energy', '--run'])
            self.assertFalse(outbase.exists())

if __name__ == '__main__':
    unittest.main()
