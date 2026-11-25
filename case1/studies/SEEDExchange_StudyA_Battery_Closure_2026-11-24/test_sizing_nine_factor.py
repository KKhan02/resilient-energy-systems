import unittest
import pandas as pd
from sizing_nine_factor import FACTORS,REF,selection,common_hours
class FactorTests(unittest.TestCase):
    def test_factor_grid(self):
        self.assertEqual(len(set(FACTORS)),9)
        self.assertIn(REF,FACTORS)
    def test_selection(self):
        g={"x":{"cases":["A","B"],"hours":[1,2,3]}}
        self.assertEqual(len(selection(g,["A"],"sample",FACTORS)),9)
        self.assertEqual(selection(g,["B"],"annual",[(.95,1.6)])[0][-1],8760)
    def test_common_union(self):
        i=pd.date_range("2025-01-01",periods=12,freq="h")
        a=pd.DataFrame({k:list(range(12)) for k in ("min_v_pu","max_trafo_pct","max_line_pct","max_v_pu")},index=i)
        f=pd.DataFrame({k:list(range(12)) for k in ("demand_kw","grid_import_kw","inverter_ac_kw","pv_dc_available_kw","battery_soc_usable_kwh")},index=i)
        self.assertEqual(common_hours([i[0]],{"A":a},{"A":f}),list(i))
if __name__=="__main__":unittest.main()
