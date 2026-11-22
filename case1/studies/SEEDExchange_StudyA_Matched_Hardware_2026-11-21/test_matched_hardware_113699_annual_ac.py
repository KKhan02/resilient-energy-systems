"""Regression contracts for signed 113699 full-year AC replays.

Synthetic data only, no annual pandapower solves or PyPSA optimizations.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

script = Path(__file__).with_name("matched_hardware_113699_annual_ac.py")
spec = importlib.util.spec_from_file_location("matched113699ac2025_tests", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fake_ac(hours=8760):
    index = pd.date_range("2025-01-01", periods=hours, freq="h")
    frame = pd.DataFrame({
        "timestamp_lst": index.astype(str),
        "status": ["CONVERGED"]*hours,
        "ac_feasible": [True]*hours,
        "min_v_pu": [.96]*hours,
        "max_v_pu": [1.]*hours,
        "max_trafo_pct": [50.]*hours,
        "max_line_pct": [10.]*hours,
        "loss_kw": [.01]*hours,
        "trafo_over_100": [0]*hours,
        "line_over_100": [0]*hours,
        "voltage_below_095": [0]*hours,
        "voltage_above_105": [0]*hours,
        "voltage_below_097": [1]*hours,
        "voltage_above_103": [0]*hours,
        "gross_demand_kw": [1.]*hours,
        "inverter_ac_kw": [.5]*hours,
        "q_selected_kvar": [0.]*hours,
        "pcc_kva": [.55]*hours,
    })
    return frame


class Annual113699ACContracts(unittest.TestCase):
    def test_annual_pass_keeps_strict_voltage_failure_separate(self):
        frame = fake_ac()
        j = mod.annual_summary(frame,"A0")
        self.assertEqual(j["hourly_records"],8760)
        self.assertEqual(j["converged_hours"],8760)
        self.assertEqual(j["model_main_band_feasible_hours"],8760)
        self.assertTrue(j["annual_AC_all_hours_pass_main_research_screen"])
        self.assertFalse(j["strict_097_103_research_screen_pass"])
        self.assertEqual(j["optional_strict_voltage_under_097_hours"],8760)
        self.assertAlmostEqual(j["annual_model_ac_losses_kwh"],87.6)
        self.assertFalse(j["field_verified"])

    def test_one_transformer_failure_blocks_annual_ac_pass(self):
        frame=fake_ac()
        frame.loc[123,["ac_feasible","max_trafo_pct","trafo_over_100"]]=[False,101.,1]
        j=mod.annual_summary(frame,"A1")
        self.assertEqual(j["model_trafo_over_100_hours"],1)
        self.assertEqual(j["model_main_band_infeasible_hours"],1)
        self.assertEqual(j["model_main_band_feasible_hours"],8759)
        self.assertFalse(j["annual_AC_all_hours_pass_main_research_screen"])
        self.assertEqual(len(j["worst_main_band_failed_timestamps_first_100"]),1)

    def test_nonconvergence_blocks_annual_claim_and_loss_total(self):
        frame=fake_ac()
        frame.loc[0,["status","ac_feasible"]]=["AC_FAILURE",False]
        j=mod.annual_summary(frame,"A1")
        self.assertEqual(j["nonconverged_hours"],1)
        self.assertEqual(j["model_main_band_infeasible_hours"],0)
        self.assertFalse(j["annual_model_losses_valid"])
        self.assertIsNone(j["annual_model_ac_losses_kwh"])
        self.assertFalse(j["annual_AC_all_hours_pass_main_research_screen"])

    def test_source_15_time_selection_must_be_exact(self):
        a=fake_ac(15)
        p={"sampled_timestamps":[{"timestamp_lst":t} for t in a.timestamp_lst]}
        self.assertEqual(mod.exact_source_15_ac_check(a,p),list(a.timestamp_lst))
        a.loc[0,"ac_feasible"]=False
        with self.assertRaisesRegex(ValueError,"not the approved source"):
            mod.exact_source_15_ac_check(a,p)

    def test_15_ac_replay_must_match_original_source(self):
        a=fake_ac(15)
        self.assertIsNone(mod.validate_replay_15(a,a.copy()))
        altered=a.copy()
        altered.loc[3,"max_trafo_pct"]=65.
        with self.assertRaisesRegex(ValueError,"AC rerun differs"):
            mod.validate_replay_15(altered,a)

    def test_output_names_do_not_overwrite_old_results(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)
            a=mod.selected_output(base,"A0")
            self.assertEqual(a.name,mod.RESULT_STEM+"A0_v1")
            a.mkdir()
            self.assertEqual(mod.selected_output(base,"A0").name,mod.RESULT_STEM+"A0_v2")
            self.assertEqual(mod.selected_output(base,"A1").name,mod.RESULT_STEM+"A1_v1")
            with self.assertRaises(FileExistsError):
                mod.selected_output(base,"A0",a)

    def test_signed_sha_is_strict_and_preserves_source_ending(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"f.csv"
            p.write_bytes(b"x,y\r\n1,2\r\n")
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(mod.verified_crlf_source(p,digest),"EXACT_SIGNED")
            p.write_bytes(b"x,y\n1,2\n")
            self.assertEqual(mod.verified_crlf_source(p,digest),
                             "GIT_LF_EQUALS_SIGNED_CRLF")
            p.write_bytes(b"x,y\n1,3\n")
            with self.assertRaisesRegex(ValueError,"differs"):
                mod.verified_crlf_source(p,digest)

    def test_sources_have_pinned_both_annual_soc_manifests(self):
        self.assertEqual(set(mod.SOURCE_MANIFEST_GIT_SHA),{"A0","A1"})
        self.assertTrue(all(len(x)==64 for x in mod.SOURCE_MANIFEST_GIT_SHA.values()))
        self.assertTrue(all(len(x)==64 for x in mod.SOURCE_ANNUAL_CRLF_SHA.values()))
        self.assertTrue(all(len(x)==64 for x in mod.SOURCE_15H_CRLF_SHA.values()))
        self.assertEqual(mod.REQUIRED_HOURS,8760)

    def test_no_git_checkout_rejected_before_full_replay(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"genuine original Git"):
                mod.preflight(root)


if __name__ == "__main__":
    unittest.main()
