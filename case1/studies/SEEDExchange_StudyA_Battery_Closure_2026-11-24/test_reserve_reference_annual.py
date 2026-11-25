import unittest
import pandas as pd
from reserve_reference_annual import reference_benchmarks

class ReferenceBenchmarksTest(unittest.TestCase):
    def setUp(self):
        self.ts=pd.date_range("2025-01-01",periods=17,freq="h")
        self.f=pd.DataFrame({"inverter_ac_kw":1.,"demand_kw":2.},index=self.ts)
        self.a=pd.DataFrame(dict(case="x",pf=.98,length_factor=1.,timestamp_lst=self.ts,
            status="CONVERGED",ac_feasible=True,source_sha256="old",new_energy_sha256="new",
            inverter_ac_kw=1.,gross_demand_kw=2.))
    def check(self,a):
        return reference_benchmarks(a,"x","old","new",self.f,self.ts)
    def test_exact(self):
        self.assertEqual(len(self.check(self.a)),17)
    def test_wrong_hash(self):
        self.a.loc[0,"new_energy_sha256"]="other"
        with self.assertRaises(ValueError):self.check(self.a)
    def test_changed_p(self):
        self.a.loc[0,"inverter_ac_kw"]=1.1
        with self.assertRaises(ValueError):self.check(self.a)
    def test_duplicate_timestamp(self):
        self.a.loc[1,"timestamp_lst"]=self.a.loc[0,"timestamp_lst"]
        with self.assertRaises(ValueError):self.check(self.a)
    def test_failed_ac(self):
        self.a.loc[0,"ac_feasible"]=False
        with self.assertRaises(ValueError):self.check(self.a)

if __name__=="__main__":
    unittest.main()
