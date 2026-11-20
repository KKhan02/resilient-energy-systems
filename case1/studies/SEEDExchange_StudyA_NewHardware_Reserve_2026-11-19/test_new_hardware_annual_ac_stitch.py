"""Annual source-stitch checks that do not execute pandapower or rewrite history."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

source=Path(__file__).with_name("new_hardware_annual_ac_stitch.py")
spec=importlib.util.spec_from_file_location("nh_source_stitch",source)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class AnnualSourceStitchTests(unittest.TestCase):
    def test_exact_pair_reuse_and_outlier_screen(self):
        idx=pd.date_range("2025-01-01",periods=8760,freq="h")
        ref=pd.DataFrame({"inverter_ac_kw":np.ones(8760),
                          "pv_dc_available_kw":np.zeros(8760)},index=idx)
        cand=ref.copy()
        cand.iloc[157,cand.columns.get_loc("inverter_ac_kw")]=1.0000000001
        cand.iloc[160,cand.columns.get_loc("pv_dc_available_kw")]=.1
        mask=m.exact_source_mask(cand,ref,{"inverter_kva":12},{"inverter_kva":12})
        self.assertEqual(int(mask.sum()),8758)
        self.assertFalse(mask[157])
        self.assertFalse(mask[160])
        self.assertTrue(mask[161])

    def test_mismatched_inverter_rating_blocks_reuse(self):
        idx=pd.date_range("2025-01-01",periods=8760,freq="h")
        a=pd.DataFrame({"inverter_ac_kw":np.ones(8760),
                       "pv_dc_available_kw":np.ones(8760)},index=idx)
        with self.assertRaisesRegex(ValueError,"different inverter"):
            m.exact_source_mask(a,a,{"inverter_kva":20},{"inverter_kva":12})

    def test_changed_hour_source_metrics_detect_tamper(self):
        r={"status":"CONVERGED","ac_feasible":True,"min_v_pu":.96,
           "max_v_pu":1.0,"max_trafo_pct":99.,"max_line_pct":8.,
           "loss_kw":.12,"pcc_kva":4.1}
        m.compare_saved(r,pd.Series(r))
        invalid=dict(r,max_trafo_pct=94.)
        with self.assertRaisesRegex(ValueError,"mismatches source"):
            m.compare_saved(invalid,pd.Series(r))

    def test_comparison_rejects_status_or_flag_drift(self):
        r={"status":"CONVERGED","ac_feasible":True,"min_v_pu":.96,
           "max_v_pu":1.0,"max_trafo_pct":99.,"max_line_pct":8.,
           "loss_kw":.12,"pcc_kva":4.1}
        with self.assertRaisesRegex(ValueError,"Solver status differs"):
            m.compare_saved(dict(r,status="AC_FAILURE"),pd.Series(r))
        with self.assertRaisesRegex(ValueError,"feasibility flag mismatch"):
            m.compare_saved(dict(r,ac_feasible=False),pd.Series(r))

    def test_ac_fill_preserves_other_hours(self):
        i=pd.date_range("2025-01-01",periods=3,freq="h")
        df=pd.DataFrame({"inverter_ac_kw":[1.,1.,1.],
                         "status":["CONVERGED"]*3,
                         "ac_feasible":[True]*3,
                         "error":[np.nan]*3},index=i)
        m.fill_ac(df,i[1],{"inverter_ac_kw":2.,"status":"CONVERGED",
                             "ac_feasible":True,"error":""})
        self.assertEqual(df.inverter_ac_kw.tolist(),[1.,2.,1.])
        self.assertEqual(df.at[i[1],"error"],"")
        self.assertEqual(float(df.at[i[0],"inverter_ac_kw"]),1.)

    def test_daily_2025_all_nine_factor_identity(self):
        self.assertEqual(len(m.FACTORS),9)
        self.assertEqual(len(m.BASE_REF),3)
        self.assertEqual(m.SCOPE_PILOT,{("MC_B10",.95,1.0)})
        self.assertEqual(m.factor_tag("MC_B10",.95,1.6),"MC_B10_pf095_l16")

    def test_compact_immutable_case_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            row={"case_id":"MC_B10","pf":.95,"length_factor":1.0,
                 "corrected":{"year_hours":8760,"ac_failed_hours":0}}
            data=pd.DataFrame({"timestamp_lst":["2025-10-13 20:00:00"],
                               "phase":["candidate_reserve_correction"],
                               "max_trafo_pct":[92.5]})
            name=m.commit_case_result(out,row,data)
            self.assertEqual(name,"MC_B10_pf095_l10")
            self.assertTrue((out/name/"CASE_RECEIPT.json").is_file())
            self.assertTrue((out/name/"AC_NEW_SOLVED_HOURS.csv").is_file())
            self.assertEqual(m.sha(out/row["new_ac_delta_file"]),row["new_ac_delta_sha256"])
            with self.assertRaises(FileExistsError):
                m.commit_case_result(out,row,data)

    def test_does_not_accept_nonfinite_converged_year(self):
        idx=pd.date_range("2025-01-01",periods=8760,freq="h")
        df=pd.DataFrame({"status":["CONVERGED"]*8760,
                         "ac_feasible":[True]*8760,
                         "min_v_pu":[.96]*8760,
                         "max_v_pu":[1.0]*8760,
                         "max_trafo_pct":[99.]*8760,
                         "max_line_pct":[8.]*8760,
                         "loss_kw":[.12]*8760,
                         "pcc_kva":[4.1]*8760},index=idx)
        b9=SimpleNamespace(validated_ac_mask=lambda f,d:d.ac_feasible)
        self.assertEqual(m.validate_year(None,b9,df)["converged_hours"],8760)
        df.at[idx[100],"loss_kw"]=np.nan
        with self.assertRaisesRegex(ValueError,"Nonfinite AC metrics"):
            m.validate_year(None,b9,df)

if __name__=="__main__":
    unittest.main()
