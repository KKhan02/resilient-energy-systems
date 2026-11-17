import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('study_a_pvbess',ROOT/'study_a_pvbess.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Plan(unittest.TestCase):
    def test_exact_portfolio(self):
        self.assertEqual(len(mod.check_portfolio_plan()),22)
    def test_six_new_four_home_milp(self):
        p=mod.create_plan()
        self.assertEqual(sum(x['kind']=='new_four_house_milp' for x in p),6)
    def test_frozen_92395_membership(self):
        m={'groups':{'A0':{'92395':['H30','H31','H32','H33']},
                    'A1':{'92395':['H30','H31','H32','H33']}}}
        self.assertEqual(mod.group_for(m,'A0','92395'), ['H30','H31','H32','H33'])
    def test_new_four_cohort_whitelist(self):
        self.assertEqual(set(mod.FOUR_ONLY),{('A0','113699'),('A0','85398'),('A0','92395')})
    def test_unique_case_slugs(self):
        self.assertNotEqual(mod.case_slug('A0','106039','ss90'),mod.case_slug('A1','106039','ss90'))
    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):mod.out_new(ROOT)
    def test_reject_under_four(self):
        with self.assertRaises(ValueError):mod.group_for({'groups':{'A0':{'85398':['H01','H02','H03']}}},'A0','85398')

if __name__=='__main__':unittest.main()
