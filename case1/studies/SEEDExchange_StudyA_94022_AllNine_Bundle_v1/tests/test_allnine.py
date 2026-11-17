"""Small non-solver tests, never execute 8760-hour numerical work."""
import importlib.util
import pathlib
import unittest
import pandas as pd

MODULE=pathlib.Path(__file__).resolve().parents[1]/'studya_94022_allnine_targeted.py'
spec=importlib.util.spec_from_file_location('a0_allnine_package',MODULE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class SourceAndLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows,cls.summary,cls.branches,cls.manifest=m.read_reference()
    def test_source_and_scope(self):
        self.assertEqual(len(self.rows),1152)
        self.assertFalse(self.manifest['annual_8760_AC_verified'])
        self.assertEqual(len(self.branches),26)
    def test_branch_membership(self):
        self.assertEqual(m.BUNDLES['svc007_004_gis014_011_R050'],[7,4,14,11])
        b=self.branches.set_index('line_index')
        self.assertEqual(b.at[7,'to_model_bus'],'HOUSE_H01')
        self.assertEqual(b.at[4,'to_model_bus'],'HOUSE_H06')
        self.assertAlmostEqual(b.loc[[7,4,14,11],'length_m'].sum(),791.992277737867,places=2)
    def test_exact_control_selfmatch(self):
        n,diffs=m.compare_overlaps(self.rows[self.rows.option.isin(m.BUNDLES)],self.rows)
        self.assertEqual(n,360)
        self.assertEqual(max(diffs.values()),0)
    def test_reject_corrupted_control(self):
        t=self.rows[self.rows.option.isin(m.BUNDLES)].copy()
        t.loc[t.index[0],'minimum_voltage_pu']+=.02
        with self.assertRaises(ValueError):m.compare_overlaps(t,self.rows)
    def test_coverage_shape_uses_nine_factors(self):
        self.assertEqual(len(m.FACTOR_GRID),9)
        self.assertEqual(4*9*9*len(m.BUNDLES),1620)
    def test_synthetic_complete_scenario_validation(self):
        original=self.rows[self.rows.option.isin(m.BUNDLES)].copy()
        data=[original]
        sample=original[(original.pf==.98)&(original.length_factor==1.)].copy()
        for pf,l in m.FACTOR_GRID:
            if (pf,l) in [(.98,1.),(.95,1.6)]:continue
            r=sample.copy();r['pf']=pf;r['length_factor']=l;data.append(r)
        completed=pd.concat(data,ignore_index=True)
        n,diffs=m.validate_rows(completed,self.rows)
        self.assertEqual(n,360)
        self.assertEqual(max(diffs.values()),0)
    def test_reject_missing_annual_factor_selected_scenario(self):
        original=self.rows[self.rows.option.isin(m.BUNDLES)].copy()
        with self.assertRaises(ValueError):m.validate_rows(original,self.rows)

if __name__=='__main__':unittest.main()
