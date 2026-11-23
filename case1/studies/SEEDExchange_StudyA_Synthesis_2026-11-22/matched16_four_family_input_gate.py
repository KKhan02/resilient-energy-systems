#!/usr/bin/env python3
"""Four-family read-only AC source and saved SOC-shift input audit (2025).

Validates the existing source receipts, not an independently recomputed AC solve.
Do not infer actual EPM phase, service, transformer, or corrected AC certification.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import matched16_original_ac_input_preflight as base

FAMILIES = {
    "A0_106039_min_cost_to_A1": ("A1_106039_min_cost_ref", "A1"),
    "A1_106039_min_cost_to_A0": ("A0_106039_min_cost_ref", "A0"),
    "A1_85398_min_cost_to_A0": ("A0_85398_min_cost_ref", ""),
    "A1_85398_ss90_to_A0": ("A0_85398_ss90_ref", ""),
}
TRIAL_A0 = Path("StudyA_A0_106039_Sequenced_Trial_v1")
TRIAL_A1 = Path("StudyA_A1_106039_Redispatch_Trial_v1")
SOURCE_V1 = Path("StudyA_Matched16_OriginalAC_InputPreflight_v1")
OUTPUT_PREFIX = "StudyA_Matched16_FourFamily_InputGate_v"
FACTOR_SET = {(p, l) for p in (.95, .98, 1.) for l in (1., 1.3, 1.6)}


def numeric(row, col):
    try:
        value = float(row[col])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Non-numeric or absent " + col) from exc
    if not math.isfinite(value):
        raise ValueError("Nonfinite " + col)
    return value


def annual_deltas(original, corrected):
    """Detect changes only in inverter P; household load and PV remain fixed."""
    base.validate_year(original, base.ENERGY_KEYS)
    base.validate_year(corrected, base.ENERGY_KEYS)
    diff, p_sum = [], 0.
    for src, dst in zip(original, corrected):
        if src["timestamp_lst"] != dst["timestamp_lst"]:
            raise ValueError("Corrected chronology changed")
        for col in ("demand_kw", "pv_dc_available_kw"):
            if abs(numeric(src, col) - numeric(dst, col)) > 1e-8:
                raise ValueError("Corrected load/PV input changed: " + col)
        for col in ("grid_export_kw", "unserved_kw"):
            if abs(numeric(dst, col)) > 1e-6:
                raise ValueError("Corrected zero-export/no-ENS policy changed")
        delta = numeric(dst, "inverter_ac_kw") - numeric(src, "inverter_ac_kw")
        if abs(delta) > 1e-8:
            diff.append(src["timestamp_lst"])
        p_sum += delta
    if abs(p_sum) > 1e-4:
        raise ValueError("Annual AC P sum differs after supposedly neutral shift")
    return diff, p_sum


def factor_coverage(records, hours):
    """Exactly one accepted report for each changed timestamp and each factor."""
    expected = {(p, l, ts) for p, l in FACTOR_SET for ts in hours}
    found = [(numeric(x, "pf"), numeric(x, "length_factor"), x["timestamp_lst"])
             for x in records]
    if len(found) != len(expected) or set(found) != expected:
        raise ValueError("Nine-factor changed-hour AC coverage incomplete")
    return len(found)


def source_baseline(repo, case, family, groups):
    assignment = case["assignment_for_load"]
    tr, tier = str(case["transformer"]), case["tier"]
    native = repo / base.ARCHIVED / ("energy_" + family)
    em = base.read_json(native / "energy_manifest.json")
    if (em["scenario"] != assignment or em["transformer"] != tr
            or em["hardware_selection_tier"] != tier
            or em["selected_house_ids"] != groups[assignment][tr]
            or em["selected_house_ids"] != case["target_house_ids"]
            or not base.same_hardware(case["hardware"], em["hardware"])
            or case["target_energy_sha256"] != em["energy_csv_sha256"]):
        raise ValueError("Target source equipment/household/energy mismatch: " + family)
    base.signed_bytes(native / "energy_hourly_2025.csv", em["energy_csv_sha256"])
    srcfile = base.relative_file(repo, case["target_energy_csv"])
    base.signed_bytes(srcfile, case["target_energy_sha256"])
    energy = base.read_csv(srcfile)
    base.validate_year(energy, base.ENERGY_KEYS)
    folder = repo / base.ARCHIVED / "annual_ac_replays_v1" / (
        family + "_mapped_optimized_pf098_length10_annual8760")
    meta = base.read_json(folder / "ac_summary.json")
    if (meta["status"] != "ANNUAL_PVBESS_AC"
            or meta["scenario"] != assignment or str(meta["transformer"]) != tr
            or meta["tier"] != tier or meta["topology"] != "mapped"
            or meta["dispatch"] != "optimized"
            or meta["selected_house_ids"] != case["target_house_ids"]
            or int(meta["hours"]) != 8760 or int(meta["converged_hours"]) != 8760
            or abs(numeric(meta, "pf") - .98) > 1e-8
            or abs(numeric(meta, "length_factor") - 1.) > 1e-8
            or abs(numeric(meta, "q_ratio_daylight") - .25) > 1e-8
            or meta["night_q_disabled"] is not True
            or meta["input_manifest_sha256"] != base.INPUT_SHA):
        raise ValueError("Archived original AC source metadata mismatch: " + family)
    base.signed_bytes(native / "energy_manifest.json", meta["energy_manifest_sha256"])
    base.signed_bytes(folder / "ac_hourly.csv", meta["ac_hourly_sha256"])
    ac = base.read_csv(folder / "ac_hourly.csv")
    base.validate_year(ac, base.AC_KEYS)
    checks = base.compare_original_inputs(energy, ac)
    if not checks["all_checked_original_AC_inputs_equal"]:
        raise ValueError("Original 2025 AC source inputs differ: " + family)
    fails = sum(row["ac_feasible"] == "False" for row in ac)
    if fails != int(meta["AC_infeasible_hours"]):
        raise ValueError("Original AC infeasible-hour count does not match source")
    return em, meta, energy, fails


def check_v1(repo, original_cases):
    m = base.read_json(repo / SOURCE_V1 / "RUN_MANIFEST.json")
    base.signed_bytes(repo / SOURCE_V1 / "CASE_INPUT_GATE.csv",
                      m["case_gate_csv_sha256"])
    tab = base.read_csv(repo / SOURCE_V1 / "CASE_INPUT_GATE.csv")
    if (m["status"] != "ORIGINAL_AC_INPUTS_CHECKED_NO_AC_SOLVES"
            or m["cases"] != 16 or len(original_cases) != 16 or len(tab) != 16
            or {x["case"] for x in tab} != set(original_cases)
            or m["original_AC_candidate_cases"] != 2
            or m["original_AC_checked_hours"] != 17520
            or m["source_energy_hours_verified"] != 140160
            or m["SOC_corrected_AC_certified_reuse_hours"] != 0
            or m["source_input_manifest_sha256"] != base.INPUT_SHA):
        raise ValueError("Saved 16-case v1 receipt is missing or inconsistent")
    return m


def check_saved_overlay(repo, kind, source, baseline_meta, expected_sha):
    """Return source-reconciled schedule and archived AC report metadata."""
    if kind == "A0":
        folder = repo / TRIAL_A0
        report = base.read_json(folder / "TRIAL_MANIFEST.json")
        if (report["tested_transformer"] != "106039"
                or report["status"] != "ALL_SELECTED_A0_PILOT_GROUPS_PASSED"
                or report["mode"] !=
                    "A0_SEQUENTIAL_EXPLORATORY_SHIFT_TRIAL_NOT_JOINT_OPTIMUM"):
            raise ValueError("A0 correction trial provenance mismatch")
        recs = [x for x in report["candidate_files"]
                if x["case"] == "A0_106039_min_cost_ref"
                and x["dispatch"] == "optimized"]
        if len(recs) != 1 or recs[0]["input_energy_sha256"] != expected_sha:
            raise ValueError("A0 correction original energy signature changed")
        rec = recs[0]
        candidate_path = folder / rec["candidate_file"]
        candidate_sha = rec["sha256"]
        all_ac = base.read_csv(folder / "CHANGED_HOURS_FINAL_AC.csv")
        changed_ac = [x for x in all_ac
                      if x["case"] == "A0_106039_min_cost_ref"
                      and x["dispatch"] == "optimized"]
        screens = [x for x in base.read_csv(folder / "NINE_FACTOR_ANNUAL_REUSE.csv")
                   if x["case"] == "A0_106039_min_cost_ref"
                   and x["dispatch"] == "optimized"]
        has_PQ_columns = False
    else:
        folder = repo / TRIAL_A1
        report = base.read_json(folder / "trial_manifest.json")
        if (report["status"] != "ALL_NINE_PF_LENGTH_CASES_FEASIBLE"
                or report["mode"] != "SOC_CONSISTENT_FIXED_SCHEDULE_SHIFT"
                or report["territory"] != "A1_106039"
                or report["source_annual_signatures"]["min_cost_ref"]
                    != baseline_meta["energy_manifest_sha256"]):
            raise ValueError("A1 correction trial provenance mismatch")
        rec = report["candidate_annual_files"]["min_cost_ref"]
        candidate_path = folder / rec["path"]
        candidate_sha = rec["sha256"]
        all_ac = base.read_csv(folder / "changed_hour_ac_checks.csv")
        changed_ac = [x for x in all_ac
                      if x["tier"] == "min_cost_ref" and x["change"] == "candidate"]
        screens = [x for x in report["screens"] if x["tier"] == "min_cost_ref"]
        has_PQ_columns = True
    base.signed_bytes(candidate_path, candidate_sha)
    candidate = base.read_csv(candidate_path)
    changes, delta_sum = annual_deltas(source, candidate)
    if len(changes) != (39 if kind == "A0" else 4):
        raise ValueError("Saved correction schedule has unexpected changed hours")
    count = factor_coverage(changed_ac, changes)
    if len(screens) != 9:
        raise ValueError("Incomplete nine-factor annual overlay")
    factors = {(numeric(s, "pf"), numeric(s, "length_factor")) for s in screens}
    if factors != FACTOR_SET:
        raise ValueError("Annual overlay PF/length combinations changed")
    original_sha_key = ("source_ac_sha256" if kind == "A0"
                        else "original_ac_sha256")
    baseline = next(s for s in screens if
                    numeric(s, "pf") == .98 and
                    numeric(s, "length_factor") == 1.)
    if baseline[original_sha_key] != baseline_meta["ac_hourly_sha256"]:
        raise ValueError("Trial references a different original AC baseline source")
    bad_key = "trial_bad_hours" if kind == "A0" else "candidate_bad_hours"
    for screen in screens:
        if int(screen[bad_key]) != 0:
            raise ValueError("Saved correction did not clear a nine-factor violation")
        if kind == "A0" and int(screen["annual_hours_accounted_for"]) != 8760:
            raise ValueError("A0 saved annual accounting incomplete")
        if kind == "A1" and screen["all_8760_hours_accounted_for"] is not True:
            raise ValueError("A1 saved annual accounting incomplete")
    if any(x["ac_feasible"] != "True" for x in changed_ac):
        raise ValueError("Corrected changed-hour AC reports non-feasibility")
    if kind == "A1":
        indexed = {x["timestamp_lst"]: x for x in candidate}
        for x in changed_ac:
            at = indexed[x["timestamp_lst"]]
            if (x["status"] != "CONVERGED"
                    or abs(numeric(x, "inverter_ac_kw") -
                           numeric(at, "inverter_ac_kw")) > 1e-6
                    or abs(numeric(x, "gross_demand_kw") -
                           numeric(at, "demand_kw")) > 1e-6
                    or (x["night_reactive_disabled"] == "True") !=
                       (numeric(at, "pv_dc_available_kw") <= 1e-9)):
                raise ValueError("A1 changed-hour replay P/demand/daylight differs")
            numeric(x, "q_selected_kvar")
    if kind == "A0" and any("q_selected_kvar" in x or "inverter_ac_kw" in x
                             for x in changed_ac):
        raise ValueError("A0 AC report is not the recorded compact format")
    return {"changed_hours": len(changes), "unchanged_hours": 8760-len(changes),
            "changed_AC_factor_records": count, "annual_P_delta_sum_kwh": delta_sum,
            "changed_AC_has_recorded_PQ": has_PQ_columns,
            "saved_nine_factor_zero_violations": True,
            "schedule_type": "SAVED_ENERGY_NEUTRAL_SOC_SHIFT",
            "correction_source_sha": candidate_sha}


def inspect(repo):
    original = base.read_json(repo / base.SOURCE_MANIFEST)["completed_cases"]
    check_v1(repo, original)
    base.signed_bytes(repo / base.INPUT_MANIFEST, base.INPUT_SHA)
    groups = base.read_json(repo / base.INPUT_MANIFEST)["groups"]
    rows = []
    for key, (family, correction) in FAMILIES.items():
        case = original[key]
        em, ac, source, fails = source_baseline(repo, case, family, groups)
        row = {"reciprocal_case": key, "target_assignment": case["assignment_for_load"],
               "transformer": case["transformer"], "tier": case["tier"],
               "original_family": family, "source_AC_checked_hours": 8760,
               "source_AC_infeasible_pf098_length1": fails,
               "original_energy_and_AC_input_match": True,
               "corrected_AC_reuse_certified_hours": 0,
               "field_verified": False}
        if correction:
            row.update(check_saved_overlay(repo, correction, source, ac,
                                          em["energy_csv_sha256"]))
            row["status"] = "SAVED_SHIFT_AC_REPORT_COVERED_NOT_INDEPENDENT_SOLVER"
        else:
            row.update({"schedule_type": "ORIGINAL_UNMODIFIED_NO_SHIFT_FILE",
                        "changed_hours": 0, "unchanged_hours": 8760,
                        "changed_AC_factor_records": 0,
                        "changed_AC_has_recorded_PQ": False,
                        "status": "ORIGINAL_AC_ONLY_NO_NEW_CORRECTION"})
        rows.append(row)
    return {"status": "FOUR_FAMILY_SOURCE_AND_SAVED_SHIFT_INPUT_AUDIT",
            "source_verified_original_cases": 4,
            "original_AC_input_hours_checked": 35040,
            "source_SOC_shifted_cases": 2,
            "cases_without_original_source_family": 12,
            "certified_corrected_AC_reuse_hours": 0,
            "field_AC_certified": False,
            "new_AC_solves": 0, "results": rows}


def run(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo-root", type=Path, default=Path("."))
    cli.add_argument("--dry-run", action="store_true")
    args = cli.parse_args(argv)
    repo = args.repo_root.resolve()
    data = inspect(repo)
    if args.dry_run:
        print(json.dumps({k:v for k,v in data.items() if k!="results"}, indent=2))
        return 0
    folder = next((repo/(OUTPUT_PREFIX+str(i)) for i in range(1,1000)
                   if not (repo/(OUTPUT_PREFIX+str(i))).exists()), None)
    if folder is None:
        raise ValueError("All versioned output folders used")
    folder.mkdir(parents=False)
    cols = ("reciprocal_case", "target_assignment", "transformer", "tier",
            "original_family", "source_AC_checked_hours",
            "source_AC_infeasible_pf098_length1", "original_energy_and_AC_input_match",
            "schedule_type", "changed_hours", "unchanged_hours",
            "changed_AC_factor_records", "changed_AC_has_recorded_PQ",
            "corrected_AC_reuse_certified_hours", "field_verified", "status")
    with (folder/"FOUR_FAMILY_GATES.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data["results"])
    data["gate_csv_sha256"] = base.sha256((folder/"FOUR_FAMILY_GATES.csv").read_bytes())
    (folder/"RUN_MANIFEST.json").write_text(
        json.dumps(data, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"status": data["status"], "output": str(folder),
                      "source_cases": 4, "original_ac_hours": 35040,
                      "new_AC_solves": 0, "corrected_AC_reuse_certified_hours": 0},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
