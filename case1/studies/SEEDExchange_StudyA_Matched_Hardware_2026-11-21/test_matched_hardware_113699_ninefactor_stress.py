"""Synthetic contract tests for source-signed 113699 PF and length uncertainty sample.

No PyPSA solver or pandapower, no historical result writes.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest
import pandas as pd

source=Path(__file__).with_name("matched_hardware_113699_ninefactor_stress.py")
spec=importlib.util.spec_from_file_location("ninefactor113699_synthetic",source)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def reference_frame(hours=8760):
    ts=pd.date_range("2025-01-01",periods=hours,freq="h").astype(str)
    return pd.DataFrame({
        "timestamp_lst":ts,
        "status":["CONVERGED"]*hours,
        "ac_feasible":[True]*hours,
        "min_v_pu":[.96]*hours,
        "max_v_pu":[1.]*hours,
        "max_trafo_pct":[80.]*hours,
        "max_line_pct":[12.]*hours,
        "pcc_kva":[2.4]*hours,
        "loss_kw":[.08]*hours,
        "gross_demand_kw":[2.2]*hours,
        "inverter_ac_kw":[.2]*hours,
        "q_selected_kvar":[0.]*hours,
        "trafo_over_100":[0]*hours,
        "line_over_100":[0]*hours,
        "voltage_below_095":[0]*hours,
        "voltage_above_105":[0]*hours,
        "voltage_below_097":[1]*hours,
        "voltage_above_103":[0]*hours})

class NineFactorContracts(unittest.TestCase):
    def test_soc_source_dir_owned_by_annual_runner(self):
        from types import SimpleNamespace
        annual=SimpleNamespace(SOURCE_DIRS={
            "A0":Path("source_a0"),"A1":Path("source_a1")})
        self.assertEqual(m.soc_hourly_path(annual,"A0"),
                         Path("source_a0/annual_soc_reoptimized_2025.csv"))
        self.assertEqual(m.soc_hourly_path(annual,"A1"),
                         Path("source_a1/annual_soc_reoptimized_2025.csv"))
        with self.assertRaisesRegex(ValueError,"Unknown original SOC origin"):
            m.soc_hourly_path(annual,"A2")

    def test_source_2025_common_hour_selection(self):
        a=reference_frame()
        b=a.copy()
        a.loc[100,"max_trafo_pct"]=96.
        b.loc[200,"min_v_pu"]=.952
        old=list(a.timestamp_lst[:15])
        selected,reasons=m.choose_stress_hours({"A0":a,"A1":b},old)
        self.assertEqual(len(set(selected)),len(selected))
        self.assertTrue(set(old).issubset(selected))
        self.assertIn(str(a.at[100,"timestamp_lst"]),selected)
        self.assertIn(str(b.at[200,"timestamp_lst"]),selected)
        self.assertTrue(any("MAX_max_trafo_pct" in x for x in reasons[str(a.at[100,"timestamp_lst"])]))
        self.assertLessEqual(len(selected),75)

    def test_source_timebase_mismatch_fails_closed(self):
        a=reference_frame()
        b=a.copy()
        b.loc[5,"timestamp_lst"]="2025-04-04 01:00:00"
        with self.assertRaisesRegex(ValueError,"clocks disagree"):
            m.choose_stress_hours({"A0":a,"A1":b},list(a.timestamp_lst[:15]))

    def test_source_nonconvergence_fails_closed(self):
        a=reference_frame()
        b=a.copy()
        b.loc[13,"status"]="AC_FAILURE"
        with self.assertRaisesRegex(ValueError,"incomplete"):
            m.choose_stress_hours({"A0":a,"A1":b},list(a.timestamp_lst[:15]))

    def test_duplicate_source_15_hours_rejected(self):
        a=reference_frame()
        old=list(a.timestamp_lst[:14])+[a.timestamp_lst[0]]
        with self.assertRaisesRegex(ValueError,"15-hour source roster"):
            m.choose_stress_hours({"A0":a,"A1":a},old)

    def test_factor_grid_is_complete_and_bounded(self):
        self.assertEqual(m.PF,(.95,.98,1.))
        self.assertEqual(m.LENGTH,(1.,1.3,1.6))
        self.assertEqual(len(m.ORIGINS)*len(m.PF)*len(m.LENGTH),18)

    def test_main_screen_can_pass_while_strict_voltage_fails(self):
        sample=reference_frame(15)
        r=m.summary_for_factor(sample,"A0",.98,1.)
        self.assertTrue(r["all_sampled_hours_main_feasible"])
        self.assertFalse(r["all_sampled_hours_strict_voltage"])
        self.assertEqual(r["strict_below_097_hours"],15)
        self.assertFalse(r["annual_AC_verified_for_this_factor"])

    def test_sample_overload_fails_main_screen(self):
        sample=reference_frame(15)
        sample.loc[7,["max_trafo_pct","trafo_over_100","ac_feasible"]]=[106.,1,False]
        r=m.summary_for_factor(sample,"A1",.95,1.6)
        self.assertEqual(r["main_infeasible_hours"],1)
        self.assertEqual(r["trafo_over_100_hours"],1)
        self.assertFalse(r["all_sampled_hours_main_feasible"])

    def test_nonconvergence_stays_distinct_from_overload(self):
        sample=reference_frame(15)
        sample.loc[7,["status","ac_feasible"]]=["AC_FAILURE",False]
        r=m.summary_for_factor(sample,"A1",1.,1.3)
        self.assertEqual(r["nonconverged_hours"],1)
        self.assertEqual(r["main_infeasible_hours"],0)
        self.assertFalse(r["all_sampled_hours_main_feasible"])

    def test_reference_exact_reproduction_enforced(self):
        f=reference_frame(15)
        old=f.set_index("timestamp_lst")
        self.assertEqual(m.verify_reference(f,old),15)
        moved=f.copy()
        moved.loc[3,"max_trafo_pct"]=91.
        with self.assertRaisesRegex(ValueError,"field mismatch"):
            m.verify_reference(moved,old)

    def test_new_result_folder_never_overwrites(self):
        with tempfile.TemporaryDirectory() as location:
            repo=Path(location)
            target=m.next_folder(repo)
            self.assertEqual(target.name,m.RESULT_PREFIX+"1")
            target.mkdir()
            self.assertEqual(m.next_folder(repo).name,m.RESULT_PREFIX+"2")

    def test_pinned_annual_results_both_64_digit_sha(self):
        self.assertEqual(set(m.FULL),{"A0","A1"})
        self.assertTrue(all(len(s)==64 for s in m.MANIFEST_SHA_LF.values()))
        self.assertTrue(all(len(s)==64 for s in m.ANNUAL_AC_SHA_WINDOWS.values()))

if __name__=="__main__":
    unittest.main()
