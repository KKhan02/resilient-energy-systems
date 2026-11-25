import unittest
import pandas as pd
from sizing_ac_sample import pick_hours,summarize,FACTORS

class SampleTest(unittest.TestCase):
    def test_union_includes_all_benchmarks(self):
        idx=pd.date_range("2025-01-01",periods=10,freq="h")
        f=pd.DataFrame({k:range(10) for k in ("demand_kw","grid_import_kw","inverter_ac_kw","pv_dc_available_kw","battery_soc_usable_kwh")},index=idx)
        result=pick_hours({"a":f},[idx[4]])
        self.assertEqual(result,list(idx[[0,1,2,4,7,8,9]]))
    def test_common_union_multiple_designs(self):
        idx=pd.date_range("2025-01-01",periods=10,freq="h")
        keys=("demand_kw","grid_import_kw","inverter_ac_kw","pv_dc_available_kw","battery_soc_usable_kwh")
        f=pd.DataFrame({k:range(10) for k in keys},index=idx)
        g=f.copy();g.loc[idx[4],"grid_import_kw"]=100
        self.assertIn(idx[4],pick_hours({"a":f,"b":g},[]))
    def test_factors(self):
        self.assertEqual(FACTORS,((.98,1.),(.95,1.6)))
    def test_summary_does_not_claim_annual(self):
        r=dict(case="a",pf=.98,length_factor=1.,status="CONVERGED",ac_feasible=False,
            min_v_pu=.94,max_v_pu=1.,max_trafo_pct=80.,max_line_pct=20.)
        s=summarize([r])[0]
        self.assertEqual(s["infeasible"],1)
        self.assertFalse(s["annual_AC_verified"])

if __name__=="__main__":
    unittest.main()
