"""Synthetic negative and positive checks for the read-only 16-case AC preflight."""
import hashlib
import tempfile
from pathlib import Path
import unittest

import matched16_original_ac_input_preflight as gate


class OriginalACInputPreflightTests(unittest.TestCase):
    def rows(self):
        e = [{"timestamp_lst": "2025-01-01 00:00:00", "demand_kw": "2",
              "inverter_ac_kw": "0", "pv_dc_available_kw": "0"},
             {"timestamp_lst": "2025-01-01 01:00:00", "demand_kw": "3",
              "inverter_ac_kw": "1", "pv_dc_available_kw": ".2"}]
        a = [{"timestamp_lst": x["timestamp_lst"],
              "gross_demand_kw": x["demand_kw"],
              "inverter_ac_kw": x["inverter_ac_kw"], "load_pf": ".98",
              "night_reactive_disabled": "True" if i == 0 else "False",
              "status": "CONVERGED", "q_selected_kvar": "0"}
             for i, x in enumerate(e)]
        return e, a

    def test_matching_original_injections(self):
        e, a = self.rows()
        v = gate.compare_original_inputs(e, a)
        self.assertTrue(v["all_checked_original_AC_inputs_equal"])
        self.assertEqual(v["mismatch_counts"]["inverter_ac_kw"], 0)

    def test_mismatch_detects_hour_and_field(self):
        e, a = self.rows()
        a[1]["inverter_ac_kw"] = "1.5"
        v = gate.compare_original_inputs(e, a)
        self.assertFalse(v["all_checked_original_AC_inputs_equal"])
        self.assertEqual(v["first_mismatch"]["inverter_ac_kw"],
                         "2025-01-01 01:00:00")

    def test_convergence_cannot_be_skipped(self):
        e, a = self.rows()
        a[0]["status"] = "DIVERGED"
        self.assertEqual(gate.compare_original_inputs(e, a)
                         ["mismatch_counts"]["unconverged_source_AC"], 1)

    def test_night_q_cannot_be_assumed(self):
        e, a = self.rows()
        a[0]["q_selected_kvar"] = ".1"
        self.assertEqual(gate.compare_original_inputs(e, a)
                         ["mismatch_counts"]["night_Q_not_zero"], 1)

    def test_invalid_night_flag_fails_closed(self):
        e, a = self.rows()
        a[1]["night_reactive_disabled"] = "unsupported"
        with self.assertRaisesRegex(ValueError, "Invalid night AC"):
            gate.compare_original_inputs(e, a)

    def test_nan_energy_fails_closed(self):
        e, a = self.rows()
        e[1]["inverter_ac_kw"] = "nan"
        with self.assertRaisesRegex(ValueError, "Nonfinite energy"):
            gate.compare_original_inputs(e, a)

    def test_nan_ac_fails_closed(self):
        e, a = self.rows()
        a[1]["q_selected_kvar"] = "nan"
        with self.assertRaisesRegex(ValueError, "Nonfinite AC"):
            gate.compare_original_inputs(e, a)

    def test_clock_mismatch_fails_closed(self):
        e, a = self.rows()
        a[1]["timestamp_lst"] = a[0]["timestamp_lst"]
        with self.assertRaisesRegex(ValueError, "clocks disagree"):
            gate.compare_original_inputs(e, a)

    def test_timestamp_duplicate_rejected(self):
        e, _ = self.rows()
        with self.assertRaisesRegex(ValueError, "timestamp mismatch"):
            gate.validate_year(e + [dict(e[-1])],
                               gate.ENERGY_KEYS, hours=3)

    def test_signed_source_exact_and_lf(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "source.csv"
            f.write_bytes(b"timestamp_lst,x\r\n2025-01-01 00:00:00,1\r\n")
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            self.assertEqual(gate.signed_bytes(f, h), "EXACT")
            f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
            self.assertEqual(gate.signed_bytes(f, h),
                             "GIT_LF_EQUALS_SIGNED_CRLF")

    def test_signed_source_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "source.csv"
            f.write_bytes(b"good\n")
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            f.write_bytes(b"tampered\n")
            with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                gate.signed_bytes(f, h)

    def test_equipment_power_difference_matters(self):
        a = dict(pv_panels=41, battery_modules=8,
                 battery_power_dc_kw=12, inverter_kva=12,
                 transformer_kva_assumed_or_evidenced=5)
        self.assertTrue(gate.same_hardware(a, a))
        b = dict(a, battery_power_dc_kw=12.5)
        self.assertFalse(gate.same_hardware(a, b))

    def test_path_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            gate.relative_file(Path("/tmp"), "../outside.csv")


if __name__ == "__main__":
    unittest.main()
