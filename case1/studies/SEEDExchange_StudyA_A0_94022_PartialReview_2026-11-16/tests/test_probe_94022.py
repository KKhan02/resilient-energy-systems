import importlib.util, pathlib, tempfile, unittest, json, pandas as pd
P=pathlib.Path(__file__).resolve().parents[1]/'probe_94022_network_options.py'
spec=importlib.util.spec_from_file_location('probe_94022_under_test',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestProbe(unittest.TestCase):
    def test_standard_factors(self):self.assertEqual(m.scenario_options(False),[(.98,1.0),(.95,1.6)])
    def test_all_nine_factors(self):self.assertEqual(len(set(m.scenario_options(True))),9)
    def test_options_unique(self):self.assertEqual(len({q[0] for q in m.OPTIONS}),5)
    def test_reference_head(self):self.assertEqual(m.OPTIONS[0],('head_reference','head',1.0))
    def test_proxies_not_real_conductors(self):self.assertEqual([o[2] for o in m.OPTIONS],[1.,1.,1.,.75,.5])
    def test_tolerance(self):
        self.assertTrue(m.relative_equal(0.95,0.95015));self.assertFalse(m.relative_equal(0.95,0.952))
    def test_empty_trial_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):m.load_trial(pathlib.Path(tmp))
    def test_bad_trial_status_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp); (p/'TRIAL_MANIFEST.json').write_text(json.dumps({'tested_transformer':'94022','selected_event_count':112,'source_group_count':4,'adopted_shift_count':80,'unresolved_event_count':32,'status':'ALL_PASSED'}))
            with self.assertRaises(ValueError):m.load_trial(p)
if __name__=='__main__':unittest.main()
