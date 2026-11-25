import unittest
import pandas as pd
from sizing_nine_factor import FACTORS,REF,selection,common_hours,check_receipt_hash,SMALL_HASHES,FULL_AC_HASH,FULL_ENERGY_HASH,CORRIDOR_HASH
class FactorTests(unittest.TestCase):
    def test_pinned_sha256_format_and_receipt(self):
        pins=[*SMALL_HASHES.values(),*FULL_AC_HASH.values(),*FULL_ENERGY_HASH.values(),CORRIDOR_HASH]
        for pin in pins:
            check_receipt_hash("source.csv",pin,pin)
        with self.assertRaisesRegex(ValueError,"Malformed pinned SHA256"):
            check_receipt_hash("source.csv","a"*62,"a"*64)
        with self.assertRaisesRegex(ValueError,"receipt SHA256 mismatch"):
            check_receipt_hash("source.csv","a"*64,"b"*64)
        self.assertEqual(FULL_AC_HASH["A1_94022_min_cost_to_A0"],
                         "659f0627fa9fa7e9b9b4e8e77f7c6efccc538119eb6f93c61f9d8fb28c680f22")
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
