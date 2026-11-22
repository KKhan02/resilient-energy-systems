"""Synthetic tests for Study A 113699 sampled-P equality annual SOC runner.

No PyPSA annual solve, no pandapower, and no private source contents required.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

p = Path(__file__).with_name("matched_hardware_113699_soc_corridor.py")
spec = importlib.util.spec_from_file_location("signed_113699_soc_contracts",p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def group(origin="A0", hour="2025-03-14 19:00:00"):
    values=[]
    for i in range(41):
        values.append({
            "sample_number":i, "status":"CONVERGED",
            "night_reactive_disabled":True, "q_selected_kvar":0.,
            "hardware_origin":origin,"timestamp_lst":hour,
            "ac_feasible":bool(i>0),
            "max_trafo_pct":101.1 if i==0 else 93.9,
            "min_v_pu":.952 if i==0 else .954,
            "max_v_pu":.98, "max_line_pct":11.,
            "p_sample_ac_kw":i*.0705, "demand_kw":2.82,
            "pcc_kva":3.03 if i==0 else 2.82})
    return pd.DataFrame(values)


class AnnualSOCContractTests(unittest.TestCase):
    def test_selected_3rd_ac_sample_is_exact_and_passed(self):
        value=m.target_from_sample(group(),"A0","2025-03-14 19:00:00")
        self.assertEqual(value["sample_index"],3)
        self.assertAlmostEqual(value["fixed_inverter_p_ac_kw"],.2115)
        self.assertTrue(value["sampled_AC_feasible_main_095_105"])
        self.assertFalse(value["sampled_AC_feasible_STRICT_097_103"])

    def test_only_actual_ac_feasible_sample_can_be_used(self):
        bad=group()
        bad.loc[3,"ac_feasible"]=False
        with self.assertRaisesRegex(ValueError,"AC passing"):
            m.target_from_sample(bad,"A0","2025-03-14 19:00:00")

    def test_3_percent_trafo_reserve_is_enforced_at_selected_point(self):
        bad=group()
        bad.loc[3,"max_trafo_pct"]=97.
        with self.assertRaisesRegex(ValueError,"AC passing"):
            m.target_from_sample(bad,"A0","2025-03-14 19:00:00")

    def test_original_zero_p_failure_must_be_reproduced(self):
        bad=group()
        bad.loc[0,"ac_feasible"]=True
        with self.assertRaisesRegex(ValueError,"P=0 overloaded"):
            m.target_from_sample(bad,"A0","2025-03-14 19:00:00")

    def test_source_sample_lost_or_daylight_q_rejected(self):
        bad=group().iloc[1:].copy()
        with self.assertRaisesRegex(ValueError,"Changed or incomplete"):
            m.target_from_sample(bad,"A0","2025-03-14 19:00:00")
        bad=group()
        bad.loc[5,"q_selected_kvar"]=.1
        with self.assertRaisesRegex(ValueError,"nighttime AC"):
            m.target_from_sample(bad,"A0","2025-03-14 19:00:00")

    def test_exact_corridors_have_equal_p_min_and_max(self):
        plan=[m.target_from_sample(group(),"A0","2025-03-14 19:00:00"),
              m.target_from_sample(group("A0","2025-11-30 20:00:00"),
                                   "A0","2025-11-30 20:00:00")]
        corr=m.exact_sampled_corridors(plan)
        self.assertEqual(len(corr),2)
        self.assertTrue(all(lo==hi for lo,hi in corr.values()))
        lo,hi=corr[pd.Timestamp("2025-03-14 19:00:00")]
        self.assertEqual(lo,hi)
        self.assertAlmostEqual(lo,.2115,places=10)

    def test_duplicate_corridor_hour_fails_closed(self):
        plan=[m.target_from_sample(group(),"A0","2025-03-14 19:00:00")]
        with self.assertRaisesRegex(ValueError,"Duplicate/invalid"):
            m.exact_sampled_corridors(plan+plan)

    def test_original_equipment_keeps_nameplate_and_loading(self):
        class FakeFixed:
            @staticmethod
            def Hardware(**kwargs):
                return kwargs
        h={"pv_panels":17,"battery_modules":3,"battery_power_dc_kw":4.700939,
           "inverter_kva":5.,"transformer_kva_assumed_or_evidenced":3.}
        summary={"annual_equipment_usd":1413.2,"annual_total_usd":2481.2}
        result=m.source_equipment(FakeFixed,h,summary)
        self.assertEqual(result["panels"],17)
        self.assertEqual(result["battery_modules"],3)
        self.assertEqual(result["inverter_kva"],5.)
        self.assertEqual(result["transformer_kva"],3.)
        self.assertEqual(result["loading_pu"],1.)
        self.assertEqual(result["load_pf"],.98)
        self.assertEqual(result["export_policy"],"zero")

    def test_source_only_preflight_requires_real_git_checkout(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"original repository checkout"):
                m.build_plan(Path(d))

    def test_new_versioned_results_never_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=m.output_path(root,"A0")
            self.assertEqual(a.name,m.RESULT_PREFIX+"A0_v1")
            a.mkdir()
            self.assertEqual(m.output_path(root,"A0").name,m.RESULT_PREFIX+"A0_v2")
            self.assertEqual(m.output_path(root,"A1").name,m.RESULT_PREFIX+"A1_v1")
            with self.assertRaises(FileExistsError):
                m.output_path(root,"A0",a)

    def test_annual_ac_status_is_never_predeclared(self):
        self.assertTrue(m.SWEEP_FOLDER.name.endswith("P_Envelope_v1"))
        self.assertEqual(m.SELECTED_INDEX,3)
        self.assertEqual(m.ORIGINS,("A0","A1"))
        self.assertEqual(len(m.SWEEP_CSV_SIGNED_SHA),64)


if __name__=="__main__":
    unittest.main()
