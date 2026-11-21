"""Isolated contract tests: saved failed-hour selection and P sampling, no AC solves."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import pandas as pd

source = Path(__file__).with_name("matched_hardware_ac113699_p_envelope.py")
spec = importlib.util.spec_from_file_location("ac113699_night_p_test", source)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    times = [str(pd.Timestamp("2025-01-01") + pd.Timedelta(hours=i)) for i in range(11)]
    times += ["2025-03-14 19:00:00", "2025-09-11 20:00:00",
              "2025-10-06 19:00:00", "2025-11-30 20:00:00"]
    frames = []
    for assignment in ("A0", "A1"):
        for origin, op in [("NONE", "load_only"), ("A0", "q_off"),
                           ("A0", "daylight_q025"), ("A1", "q_off"),
                           ("A1", "daylight_q025")]:
            for ts in times:
                isfail = (assignment == "A1" and
                    ((origin == "NONE" and ts in (
                        "2025-03-14 19:00:00", "2025-09-11 20:00:00",
                        "2025-10-06 19:00:00", "2025-11-30 20:00:00"))
                    or (origin == "A0" and ts in m.EXPECTED_FAILURES["A0"])
                    or (origin == "A1" and ts in m.EXPECTED_FAILURES["A1"])))
                frames.append({
                    "assignment": assignment, "hardware_origin": origin,
                    "operation": op, "timestamp_lst": ts,
                    "status": "CONVERGED", "ac_feasible": not isfail})
    return pd.DataFrame(frames)


class NightPEnvelopeContractTests(unittest.TestCase):
    def test_expected_failure_roster_three_distinct_hardware_case_hours(self):
        data = fixture()
        found = m.expected_failing_rows(data)
        self.assertEqual(sum(map(len, found.values())), 3)
        self.assertEqual([x["timestamp_lst"] for x in found["A0"]],
                         list(m.EXPECTED_FAILURES["A0"]))
        self.assertEqual([x["timestamp_lst"] for x in found["A1"]],
                         list(m.EXPECTED_FAILURES["A1"]))

    def test_wrong_failure_hour_refused(self):
        data = fixture()
        ix = data.index[(data.assignment == "A1") &
                        (data.hardware_origin == "A1") &
                        (data.operation == "q_off") &
                        (data.timestamp_lst == "2025-11-30 20:00:00")][0]
        data.loc[ix, "ac_feasible"] = True
        with self.assertRaisesRegex(ValueError, "Changed original number"):
            m.expected_failing_rows(data)

    def test_tampered_source_timestamp_duplicates_refused(self):
        data = fixture()
        data.loc[1, "timestamp_lst"] = data.loc[0, "timestamp_lst"]
        with self.assertRaisesRegex(ValueError, "150 valid AC records"):
            m.expected_failing_rows(data)

    def test_night_battery_sweep_does_not_use_illegal_power_or_export(self):
        hw = {"battery_modules":3, "battery_power_dc_kw":4.7, "inverter_kva":5.}
        self.assertAlmostEqual(m.max_night_battery_p_ac(2.8, hw), 2.8)
        self.assertAlmostEqual(m.max_night_battery_p_ac(8., hw), .95 * 4.7)
        hw["inverter_kva"] = 2.
        self.assertAlmostEqual(m.max_night_battery_p_ac(8., hw), 2.)

    def test_no_battery_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Missing installed"):
            m.max_night_battery_p_ac(2., {
                "battery_modules":0, "battery_power_dc_kw":0,
                "inverter_kva":5.})

    def test_consecutive_feasible_points_not_promoted_to_guaranteed_continuum(self):
        vals = [False, True, True, False, True]
        data = [
            {"status":"CONVERGED", "ac_feasible":bool(ok),
             "p_sample_ac_kw":float(i) * .1} for i, ok in enumerate(vals)]
        bands = m.contiguous_feasible_points(data)
        self.assertEqual(len(bands), 2)
        self.assertAlmostEqual(bands[0]["first_sample_kw"], .1)
        self.assertAlmostEqual(bands[0]["last_sample_kw"], .2)
        self.assertEqual(bands[0]["inter_sample_AC_feasibility"], "NOT_PROVEN")

    def test_nonconvergence_breaks_feasible_sample_band(self):
        data = [
            {"status":"CONVERGED", "ac_feasible":True, "p_sample_ac_kw":0.},
            {"status":"AC_FAILURE", "ac_feasible":False, "p_sample_ac_kw":.1},
            {"status":"CONVERGED", "ac_feasible":True, "p_sample_ac_kw":.2}]
        self.assertEqual(len(m.contiguous_feasible_points(data)), 2)

    def test_crlf_normalization_is_exact_or_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/"a.csv"
            p.write_bytes(b"a,b\r\n1,2\r\n")
            s = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(m.signed_text_mode(p, s), "ORIGINAL_EXACT")
            p.write_bytes(b"a,b\n1,2\n")
            self.assertEqual(m.signed_text_mode(p, s),
                             "GIT_LF_MATCHES_SIGNED_CRLF")
            p.write_bytes(b"a,b\n1,3\n")
            with self.assertRaisesRegex(ValueError, "differs"):
                m.signed_text_mode(p, s)

    def test_output_versioning_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            first = m.select_out(root)
            self.assertEqual(first.name, m.OUT_PREFIX + "1")
            first.mkdir()
            self.assertEqual(m.select_out(root).name, m.OUT_PREFIX + "2")
            with self.assertRaises(FileExistsError):
                m.select_out(root, first)


if __name__ == "__main__":
    unittest.main()
