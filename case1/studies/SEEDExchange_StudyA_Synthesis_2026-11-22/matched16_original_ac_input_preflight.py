#!/usr/bin/env python3
"""Read-only exact-hour original AC source-input screening for 16 reciprocal cases.

This program NEVER runs a power flow. Even exact 8760-hour original AC source
input agreement is not a certificate of SOC-corrected AC reuse or field approval.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path

HOME = Path("case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22")
SOURCE_MANIFEST = Path("StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json")
INPUT_MANIFEST = Path("case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json")
ARCHIVED = Path("case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01")
OUTPUT_STEM = "StudyA_Matched16_OriginalAC_InputPreflight_v"
INPUT_SHA = "2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69"
HARDWARE_KEYS = ("pv_panels", "battery_modules", "battery_power_dc_kw",
                 "inverter_kva", "transformer_kva_assumed_or_evidenced")
ENERGY_KEYS = ("timestamp_lst", "demand_kw", "inverter_ac_kw",
               "pv_dc_available_kw")
AC_KEYS = ("timestamp_lst", "gross_demand_kw", "inverter_ac_kw", "load_pf",
           "night_reactive_disabled", "q_selected_kvar", "status")
HOURS = 8760
TOL = 1e-8




def windows_extended_string(value: str, windows: bool | None = None) -> str:
    """Form a Win32 extended path without weakening source checks.

    Pure string logic is separately testable on non-Windows.
    """
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return value
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    if not ntpath.isabs(value):
        raise ValueError("Windows extended source path must be absolute")
    return "\\\\?\\" + value


def io_path(path: Path) -> Path:
    """Only filesystem access is normalized; saved source references stay exact."""
    if os.name != "nt":
        return path
    return Path(windows_extended_string(os.path.abspath(os.fspath(path))))


def required_file(path: Path) -> Path:
    """Require the original local file even when Windows paths exceed MAX_PATH."""
    candidate = io_path(path)
    if not candidate.is_file():
        raise FileNotFoundError(
            "Required signed source not present in local checkout: "
            + str(path) + ". Verify the relative path with git ls-files "
                          "and Windows core.longpaths; no source was substituted.")
    return candidate

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signed_bytes(path: Path, expected: str) -> str:
    """Accept exact bytes or only Git-normalized LF form of a signed CRLF CSV."""
    data = required_file(path).read_bytes()
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("Missing or invalid signed source SHA: " + str(path))
    if sha256(data) == expected:
        return "EXACT"
    if b"\r" not in data and b"\n" in data:
        if sha256(data.replace(b"\n", b"\r\n")) == expected:
            return "GIT_LF_EQUALS_SIGNED_CRLF"
    raise ValueError("Signed source SHA mismatch: " + str(path))


def read_json(path: Path) -> dict:
    value = json.loads(required_file(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required: " + str(path))
    return value


def read_csv(path: Path) -> list[dict]:
    with required_file(path).open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("Missing or duplicate CSV headers: " + str(path))
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values())
           for row in rows):
        raise ValueError("Malformed CSV source: " + str(path))
    return rows


def validate_year(rows: list[dict], columns: tuple[str, ...],
                  hours: int = HOURS) -> None:
    """Fail closed for unordered, duplicate, missing or non-2025 local hours."""
    if len(rows) != hours:
        raise ValueError("Incomplete annual source: " + str(len(rows)))
    if any(not set(columns).issubset(row) for row in rows):
        raise ValueError("Required input column absent")
    expected = datetime(2025, 1, 1)
    for row in rows:
        if row["timestamp_lst"] != expected.strftime("%Y-%m-%d %H:%M:%S"):
            raise ValueError("2025 hourly source timestamp mismatch: "
                             + row["timestamp_lst"])
        expected += timedelta(hours=1)


def same_hardware(a: dict, b: dict, tol: float = TOL) -> bool:
    return all(abs(float(a[k]) - float(b[k])) <= tol for k in HARDWARE_KEYS)


def compare_original_inputs(energy: list[dict], ac: list[dict],
                            pf: float = .98, tol: float = TOL) -> dict:
    """Compare fields used to create the original AC operating point.

    Gross demand is only the sum of loads. The per-house spatial load mapping
    must also be independently pinned by source manifests.
    """
    if len(energy) != len(ac):
        raise ValueError("Source annual clocks disagree")
    diffs = {"gross_demand_kw": 0, "inverter_ac_kw": 0,
             "night_from_pv_availability": 0, "load_pf": 0,
             "unconverged_source_AC": 0, "night_Q_not_zero": 0}
    first = {}
    greatest = {"gross_demand_kw": 0.0, "inverter_ac_kw": 0.0}
    for e, a in zip(energy, ac):
        stamp = str(e["timestamp_lst"])
        for key in ("demand_kw", "inverter_ac_kw", "pv_dc_available_kw"):
            try:
                number = float(e[key])
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError("Invalid energy input at " + stamp + "/" + key) from exc
            if not math.isfinite(number):
                raise ValueError("Nonfinite energy input at " + stamp + "/" + key)
        for key in ("gross_demand_kw", "inverter_ac_kw", "load_pf",
                    "q_selected_kvar"):
            try:
                number = float(a[key])
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError("Invalid AC input at " + stamp + "/" + key) from exc
            if not math.isfinite(number):
                raise ValueError("Nonfinite AC input at " + stamp + "/" + key)
        if stamp != a["timestamp_lst"]:
            raise ValueError("Source annual clocks disagree at " + stamp)
        for left, right in (("demand_kw", "gross_demand_kw"),
                            ("inverter_ac_kw", "inverter_ac_kw")):
            delta = abs(float(e[left]) - float(a[right]))
            greatest[right] = max(greatest[right], delta)
            if delta > tol:
                diffs[right] += 1
                first.setdefault(right, stamp)
        night = float(e["pv_dc_available_kw"]) <= 1e-9
        night_token = str(a["night_reactive_disabled"]).strip().lower()
        if night_token not in ("true", "false"):
            raise ValueError("Invalid night AC policy at " + stamp)
        source_night = night_token == "true"
        if night != source_night:
            diffs["night_from_pv_availability"] += 1
            first.setdefault("night_from_pv_availability", stamp)
        if abs(float(a["load_pf"]) - pf) > tol:
            diffs["load_pf"] += 1
            first.setdefault("load_pf", stamp)
        if a["status"] != "CONVERGED":
            diffs["unconverged_source_AC"] += 1
            first.setdefault("unconverged_source_AC", stamp)
        if source_night and abs(float(a["q_selected_kvar"])) > tol:
            diffs["night_Q_not_zero"] += 1
            first.setdefault("night_Q_not_zero", stamp)
    return {"mismatch_counts": diffs, "first_mismatch": first,
            "max_abs_difference": greatest,
            "all_checked_original_AC_inputs_equal": all(v == 0 for v in diffs.values())}


def relative_file(repo: Path, value: str) -> Path:
    """Disallow absolute/escaping paths in signed source receipt."""
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Unsafe relative source path")
    return repo / p


def inspect(repo: Path, only_preflight: bool = False) -> dict:
    source = read_json(repo / SOURCE_MANIFEST)
    inputs_path = repo / INPUT_MANIFEST
    signed_bytes(inputs_path, INPUT_SHA)
    inputs = read_json(inputs_path)
    if inputs.get("2025_hours") != HOURS:
        raise ValueError("2025 source manifest hour count changed")
    cases = source.get("completed_cases")
    if (not isinstance(cases, dict) or len(cases) != 16
            or source.get("status") != "ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING"):
        raise ValueError("Unexpected reciprocal 16-case source manifest")
    inventory = []
    for case_id in sorted(cases):
        c = cases[case_id]
        if c.get("source_case") != case_id or c.get("AC_verified") is not False:
            raise ValueError("Original AC claim or case identity changed: " + case_id)
        target = c["assignment_for_load"]
        tr = str(c["transformer"])
        tier = c["tier"]
        ids = c["target_house_ids"]
        if ids != inputs["groups"][target][tr]:
            raise ValueError("Target feeder household identities differ: " + case_id)
        native = next((x for x in cases.values()
                       if x["assignment_for_hardware"] == target
                       and str(x["transformer"]) == tr and x["tier"] == tier), None)
        if native is None:
            raise ValueError("Missing target-own original hardware: " + case_id)
        equal = same_hardware(c["hardware"], native["hardware"])
        path = relative_file(repo, c["target_energy_csv"])
        energy_signature = signed_bytes(path, c["target_energy_sha256"])
        energy = read_csv(path)
        validate_year(energy, ENERGY_KEYS)
        for row in energy:
            for col in ("demand_kw", "inverter_ac_kw", "pv_dc_available_kw"):
                if row[col] in ("", None):
                    raise ValueError("Incomplete hourly energy data: " + case_id)
                try:
                    value = float(row[col])
                except (ValueError, TypeError) as exc:
                    raise ValueError("Invalid annual energy input: " + case_id) from exc
                if not math.isfinite(value):
                    raise ValueError("Nonfinite annual energy input: " + case_id)
        item = {
            "case": case_id, "transformer": tr, "tier": tier,
            "hardware_origin": c["assignment_for_hardware"],
            "target_assignment": target, "households": len(ids),
            "target_2025_energy_hours_verified": len(energy),
            "target_energy_signature_mode": energy_signature,
            "target_native_same_tier_hardware_equal": equal,
            "original_AC_source_candidate": False,
            "source_original_AC_checked_hours": 0,
            "reusable_SOC_corrected_AC_hours_CERTIFIED": 0,
            "field_verified": False, "source_AC_violating_hours": None,
            "source_AC_case": "",
            "status": ("NATIVE_HARDWARE_EQUAL_AC_INPUT_CHECK_PENDING"
                       if equal else "NATIVE_HARDWARE_DIFFERS_ALT_ARCHIVE_UNSEARCHED")
        }
        if equal and not only_preflight:
            if tr != "106039" or tier != "min_cost":
                raise ValueError("Unexpected new AC source-candidate hardware: " + case_id)
            family = native["origin_source_family"]
            if not family.startswith(target + "_" + tr + "_" + tier + "_"):
                raise ValueError("Target-native source family changed")
            native_dir = repo / ARCHIVED / ("energy_" + family)
            em = read_json(native_dir / "energy_manifest.json")
            if (em["selected_house_ids"] != ids
                    or em["hardware_selection_tier"] != tier
                    or not same_hardware(em["hardware"], c["hardware"])
                    or em["energy_csv_sha256"] != c["target_energy_sha256"]):
                raise ValueError("Target original signed energy not identical")
            signed_bytes(native_dir / "energy_hourly_2025.csv", em["energy_csv_sha256"])
            dirname = family + "_mapped_optimized_pf098_length10_annual8760"
            ac_dir = repo / ARCHIVED / "annual_ac_replays_v1" / dirname
            ac_summary = read_json(ac_dir / "ac_summary.json")
            if (ac_summary["status"] != "ANNUAL_PVBESS_AC"
                    or ac_summary["scenario"] != target
                    or ac_summary["transformer"] != tr
                    or ac_summary["tier"] != tier
                    or ac_summary["topology"] != "mapped"
                    or ac_summary["dispatch"] != "optimized"
                    or ac_summary["selected_house_ids"] != ids
                    or int(ac_summary["hours"]) != HOURS
                    or int(ac_summary["converged_hours"]) != HOURS
                    or abs(float(ac_summary["pf"]) - .98) > TOL
                    or abs(float(ac_summary["length_factor"]) - 1.) > TOL
                    or abs(float(ac_summary["q_ratio_daylight"]) - .25) > TOL
                    or ac_summary["night_q_disabled"] is not True
                    or ac_summary["energy_manifest_sha256"] is None):
                raise ValueError("Original AC source metadata differs: " + case_id)
            for factor in ("pf", "length_factor", "q_ratio_daylight"):
                if not math.isfinite(float(ac_summary[factor])):
                    raise ValueError("Nonfinite original AC factor " + factor)
            signed_bytes(native_dir / "energy_manifest.json",
                         ac_summary["energy_manifest_sha256"])
            if ac_summary.get("input_manifest_sha256") != INPUT_SHA:
                raise ValueError("Original AC GIS input manifest differs")
            ac_csv = ac_dir / "ac_hourly.csv"
            signed_bytes(ac_csv, ac_summary["ac_hourly_sha256"])
            ac = read_csv(ac_csv)
            validate_year(ac, AC_KEYS)
            comparison = compare_original_inputs(energy, ac)
            fail_counts = sum(str(row["ac_feasible"]).strip().lower() == "false"
                              for row in ac)
            if fail_counts != int(ac_summary["AC_infeasible_hours"]):
                raise ValueError("Original source AC failure summary differs")
            item["source_AC_case"] = dirname
            item["source_original_AC_checked_hours"] = HOURS
            item["source_AC_violating_hours"] = int(ac_summary["AC_infeasible_hours"])
            item["original_AC_source_candidate"] = comparison["all_checked_original_AC_inputs_equal"]
            item.update(comparison)
            item["status"] = ("ORIGINAL_AC_INPUT_MATCH_NOT_CORRECTED_REUSE"
                              if item["original_AC_source_candidate"] else
                              "ORIGINAL_AC_INPUT_MISMATCH_NO_REUSE")
        inventory.append(item)
    if len(inventory) != 16:
        raise ValueError("Reciprocal inventory incomplete")
    return {
        "status": ("SIGNED_ENERGY_16_PREFLIGHT_NO_AC_REPLAY"
                   if only_preflight else "ORIGINAL_AC_INPUTS_CHECKED_NO_AC_SOLVES"),
        "matched_hardware_source_status": source["status"],
        "year": 2025, "cases": 16,
        "source_energy_hours_verified": sum(x["target_2025_energy_hours_verified"]
                                            for x in inventory),
        "original_AC_candidate_cases": sum(bool(x["original_AC_source_candidate"])
                                           for x in inventory),
        "original_AC_checked_hours": sum(x["source_original_AC_checked_hours"]
                                         for x in inventory),
        "SOC_corrected_AC_certified_reuse_hours": 0,
        "field_AC_certified": False,
        "source_input_manifest_sha256": INPUT_SHA,
        "results": inventory,
        "interpretation": ("Original AC input equivalence is a necessary condition "
                           "only. Corrected dispatch, per-house electrical mapping "
                           "and true utility network remain separate evidence gates.")
    }


def output_folder(repo: Path) -> Path:
    for n in range(1, 1000):
        candidate = repo / (OUTPUT_STEM + str(n))
        if not candidate.exists():
            return candidate
    raise ValueError("No available versioned result folder")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    result = inspect(repo, args.preflight_only)
    if args.preflight_only:
        print(json.dumps({k: v for k, v in result.items() if k != "results"}, indent=2))
        return 0
    dest = output_folder(repo)
    dest.mkdir(parents=False)
    columns = ("case", "transformer", "tier", "hardware_origin",
               "target_assignment", "households", "target_2025_energy_hours_verified",
               "target_energy_signature_mode", "target_native_same_tier_hardware_equal",
               "original_AC_source_candidate", "source_original_AC_checked_hours",
               "source_AC_violating_hours", "reusable_SOC_corrected_AC_hours_CERTIFIED",
               "source_AC_case", "status")
    with (dest / "CASE_INPUT_GATE.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["results"])
    result["case_gate_csv_sha256"] = sha256((dest / "CASE_INPUT_GATE.csv").read_bytes())
    (dest / "RUN_MANIFEST.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(dest),
                      "cases": result["cases"],
                      "candidate_cases": result["original_AC_candidate_cases"],
                      "original_AC_checked_hours": result["original_AC_checked_hours"],
                      "certified_corrected_reuse_hours": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
