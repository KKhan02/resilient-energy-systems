"""Non-numerical regression tests for Windows MAX_PATH boundary fix."""
import importlib.util
from pathlib import Path
from unittest import TestCase, mock
import unittest

HERE=Path(__file__).resolve().parents[1]
if not (HERE/'SEEDExchange_StudyA_PVBESS_v1'/'study_a_pvbess.py').is_file():
    HERE=HERE.parent
SCRIPTS=[
    HERE/'SEEDExchange_StudyA_PVBESS_v1'/'study_a_pvbess.py',
    HERE/'SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1'/'run_annual_replays.py',
    HERE/'SEEDExchange_StudyA_AC_Recovery_v1'/'studya_recover_ac_summaries.py',
]

class WindowsMaxPathTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mods=[]
        for i,path in enumerate(SCRIPTS):
            spec=importlib.util.spec_from_file_location(f'winpath_patch_mod_{i}',path)
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls.mods.append(mod)

    def test_original_failure_boundary(self):
        folder=r'D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems\case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\annual_ac_replays_v1\A0_106039_min_cost_ref_mapped_optimized_pf095_length13_annual8760'
        self.assertEqual(len(folder),244)
        self.assertEqual(len(folder+r'\ac_hourly.csv'),258)
        self.assertEqual(len(folder+r'\ac_summary.json'),260)

    def test_linux_paths_not_modified(self):
        for mod in self.mods:
            with self.subTest(script=mod.__file__):
                with mock.patch.object(mod.sys, 'platform', 'linux'):
                    x=Path('/tmp/project/output/ac_summary.json')
                    self.assertEqual(mod.windows_extended_path(x),x)

    def test_windows_prefixed_path_idempotence(self):
        for mod in self.mods:
            with self.subTest(script=mod.__file__):
                with mock.patch.object(mod.sys, 'platform', 'win32'):
                    res=mod.windows_extended_path(Path('/tmp/study/output'))
                    self.assertTrue(str(res).startswith('\\\\?\\'))
                    self.assertEqual(mod.windows_extended_path(res),res)

    @unittest.skipUnless(__import__('sys').platform=='win32', 'actual Windows filesystem only')
    def test_real_windows_long_file_write_read(self):
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            long_dir=root/('a'*90)/('b'*90)/('c'*70)
            for mod in self.mods:
                extended=mod.windows_extended_path(long_dir)
                extended.mkdir(parents=True,exist_ok=True)
                output=extended/'ac_summary.json'
                self.assertGreater(len(str(long_dir/'ac_summary.json')),260)
                output.write_text('test',encoding='utf8')
                self.assertEqual(output.read_text(encoding='utf8'),'test')
                output.unlink()
            # Remove nested directory using the extended prefix before cleanup.
            shutil.rmtree(str(self.mods[0].windows_extended_path(long_dir)))

    def test_yearly_scope_unchanged(self):
        mod=self.mods[1]
        self.assertEqual(len(list(mod.yearly_combinations('baseline'))),1)
        self.assertEqual(len(list(mod.yearly_combinations('sensitivities'))),8)
        self.assertEqual(len(list(mod.yearly_combinations('full'))),9)

    def test_annual_workload_unchanged(self):
        mod=self.mods[1]
        repo=Path('/synthetic/repo'); base=repo/'results'
        self.assertEqual(len(mod.build_jobs(repo,base,'baseline')),48)
        self.assertEqual(len(mod.build_jobs(repo,base,'sensitivities')),384)

    def test_recovery_is_read_only_by_default(self):
        src=SCRIPTS[2].read_text(encoding='utf8')
        self.assertIn('if not repair:',src)
        self.assertIn("with target.open('x',encoding='utf-8')",src)

if __name__=='__main__':unittest.main()
