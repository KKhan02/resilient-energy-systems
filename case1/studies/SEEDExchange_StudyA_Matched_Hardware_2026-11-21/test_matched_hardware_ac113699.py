"""Synthetic 113699 matched-hardware AC source checks. No numerical solver."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

path = Path(__file__).with_name("matched_hardware_ac113699.py")
spec = importlib.util.spec_from_file_location("ac113699_testmodule", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MatchedAC113699Tests(unittest.TestCase):
    def test_manifests_accept_only_same_git_lf_data(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "signed.json"
            f.write_bytes(b'{"ok":true}\r\n')
            expected = hashlib.sha256(b'{"ok":true}\n').hexdigest()
            self.assertEqual(mod.git_lf_sha(f), expected)
            f.write_bytes(b'{"ok":true}\n')
            self.assertEqual(mod.git_lf_sha(f), expected)

    def test_bare_carriage_return_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "signed.json"
            f.write_bytes(b"tamper\rbytes")
            with self.assertRaisesRegex(ValueError, "lone CR"):
                mod.git_lf_sha(f)

    def test_missing_full_signed_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "missing or changed"):
                mod.verify_full(Path(d), None, {}, None, None, None, None, None)

    def test_three_known_moves_only(self):
        self.assertEqual(set(mod.MOVES), {"H03", "H06", "H13"})
        self.assertEqual(mod.MOVES["H03"], ("94022", "113699"))
        self.assertEqual(mod.MOVES["H06"], ("94022", "113699"))
        self.assertEqual(mod.MOVES["H13"], ("106039", "85398"))

    def test_scenarios_and_device_families_are_fixed(self):
        self.assertEqual(mod.ASSIGNMENTS, ("A0", "A1"))
        self.assertEqual(mod.TRANSFORMER, "113699")
        self.assertEqual(mod.FULL.name, "StudyA_A0_A1_MatchedHardware_Full_v1")

    def test_auto_numbered_output_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first = mod.choose_out(root)
            self.assertEqual(first.name, mod.OUT_PREFIX + "1")
            first.mkdir()
            self.assertEqual(mod.choose_out(root).name, mod.OUT_PREFIX + "2")
            with self.assertRaises(FileExistsError):
                mod.choose_out(root, first)

    def test_same_stress_hours_across_all_four_dispatches(self):
        idx = pd.date_range("2025-01-01", periods=8760, freq="h")
        cases = {}
        for origin in mod.ASSIGNMENTS:
            for load in mod.ASSIGNMENTS:
                cols = {k: np.ones(8760) for k in mod.EXTREMES}
                cols["battery_soc_usable_kwh"] = np.ones(8760)
                frame = pd.DataFrame(cols, index=idx)
                frame.loc[idx[200], "demand_kw"] = 4.
                cases[origin+"_hardware_on_"+load] = {"energy": frame}
        picked, reasons = mod.select_hours(cases)
        self.assertLessEqual(len(picked), 36)
        self.assertEqual(len(picked), len(set(picked)))
        self.assertIn(idx[200], picked)
        self.assertIn(pd.Timestamp(mod.ANCHORS[0]), picked)
        self.assertTrue(any(x.endswith(":max_demand_kw") for x in reasons[str(idx[200])]))

    def test_nonconvergence_is_not_a_valid_ac_hour(self):
        data = pd.DataFrame([
            {"assignment":"A1", "hardware_origin":"A0", "operation":"q_off",
             "status":"CONVERGED", "ac_feasible":False,
             "voltage_below_097":1, "voltage_above_103":0, "min_v_pu":.949,
             "max_v_pu":1., "max_trafo_pct":98., "max_line_pct":30., "loss_kw":.01},
            {"assignment":"A1", "hardware_origin":"A0", "operation":"q_off",
             "status":"AC_FAILURE", "ac_feasible":False,
             "voltage_below_097":None, "voltage_above_103":None, "min_v_pu":None,
             "max_v_pu":None, "max_trafo_pct":None, "max_line_pct":None,
             "loss_kw":None},
        ])
        summary = mod.summaries(data, 2)[0]
        self.assertEqual(summary["converged_hours"], 1)
        self.assertEqual(summary["nonconverged_hours"], 1)
        self.assertEqual(summary["main_band_feasible_hours"], 0)
        self.assertEqual(summary["main_band_infeasible_hours"], 1)
        self.assertEqual(summary["strict_low_voltage_hours"], 1)
        self.assertAlmostEqual(summary["sample_losses_kw_sum_NOT_ANNUAL"], .01)


if __name__ == "__main__":
    unittest.main()
