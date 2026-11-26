import unittest
import pandas as pd
import remote_94022_middle_robustness as r

class SampleSelection(unittest.TestCase):
    def fixture(self):
        ix=pd.date_range("2025-01-01",periods=15,freq="h")
        a=pd.DataFrame({k:range(15) for k in ("demand_kw","grid_import_kw","inverter_ac_kw","pv_dc_available_kw","battery_soc_usable_kwh")},index=ix)
        b=a.copy();b.at[ix[7],"inverter_ac_kw"]+=.01
        return ix,a,b
    def test_inclusion(self):
        ix,a,b=self.fixture()
        h=r.select_hours([ix[5]],{ix[6]:(.1,1.)},{"c":a},{"c":b})
        self.assertTrue({ix[5],ix[6],ix[7],ix[0],ix[-1]}.issubset(h))
        self.assertEqual(h,sorted(set(h)))
    def test_chronology_gate(self):
        ix,a,b=self.fixture()
        with self.assertRaisesRegex(ValueError,"Chronology"):
            r.select_hours([],{},{"c":a},{"c":b.iloc[::-1]})
    def test_case_gate(self):
        ix,a,b=self.fixture()
        with self.assertRaisesRegex(ValueError,"Case identity"):
            r.select_hours([],{},{"a":a},{"b":b})
    def test_unknown_timestamp(self):
        ix,a,b=self.fixture()
        with self.assertRaisesRegex(ValueError,"Unknown sample timestamp"):
            r.select_hours([ix[0]-pd.Timedelta(hours=1)],{},{"c":a},{"c":b})

if __name__=="__main__":unittest.main()
