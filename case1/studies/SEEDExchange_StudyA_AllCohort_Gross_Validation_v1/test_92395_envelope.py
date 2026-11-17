"""No numeric energy or AC solver invoked. Synthetic three-hour screen tests."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

file=Path(__file__).with_name('screen_92395_transformer_only.py')
spec=importlib.util.spec_from_file_location('screen_92395',file)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TransformerEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.ts=pd.date_range('2025-01-01',periods=3,freq='h')
        self.profiles=pd.DataFrame({1:[1.0,2.0,3.0],2:[0.5,1,1.5],3:[0.1,0.2,0.3],4:[1,1,1]}, index=self.ts)
        self.mapping={'H30':1,'H31':2,'H32':3,'H33':4}

    def test_pf_screen_only(self):
        result=mod.build_idealized_envelope(self.profiles,self.mapping,list(self.mapping),.98,5.0)
        self.assertEqual(len(result),3)
        self.assertAlmostEqual(result.gross_demand_kw.sum(),12.6)
        self.assertAlmostEqual(result.ideal_nameplate_loading_pct_no_losses.iloc[0],2.6/.98/5*100)
        self.assertTrue((result.ideal_nameplate_loading_pct_no_losses>0).all())

    def test_no_duplicated_customer(self):
        with self.assertRaises(ValueError):
            mod.build_idealized_envelope(self.profiles,self.mapping,['H30','H30'],.98,5)

    def test_invalid_pf(self):
        with self.assertRaises(ValueError):
            mod.build_idealized_envelope(self.profiles,self.mapping,['H30'],0,5)

    def test_invalid_nameplate(self):
        with self.assertRaises(ValueError):
            mod.build_idealized_envelope(self.profiles,self.mapping,['H30'],.98,-5)


if __name__=='__main__':unittest.main()
