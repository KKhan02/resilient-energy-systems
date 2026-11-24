#!/usr/bin/env python3
"""Source-locked PF0.98 annual reconstruction. Zero new AC solves.

Preserve 8754 prior corrected AC records and replace exactly six with the
signed 50% joint pilot records. Preserve the four March/Nov27 corrections.
Recheck the annual energy/SOC chronology before accepting cached AC evidence.
"""
from __future__ import annotations
import argparse
import json
import math
import traceback
from pathlib import Path

import pandas as pd
import matched16_94022_ss90_mar_nov_annual_ac as annual
import matched16_94022_ss90_remaining3_ac as joint
import matched16_94022_nov_soc_shift_ac as nov

PILOT = Path("StudyA_94022_SS90_Remaining3_Pair_AC_v1")
OUT_PREFIX = "StudyA_94022_SS90_AllFiveEvents_AnnualAC_PF98_v"
FRACTION = 0.5
EXPECTED_NEW = set(joint.SOURCE_TIMES)
MIN_REQUIRED = {
    "timestamp_lst", "status", "ac_feasible", "gross_demand_kw", "inverter_ac_kw",
    "min_v_pu", "max_v_pu", "max_trafo_pct", "max_line_pct", "loss_kw",
    "pcc_kva", "voltage_below_095", "voltage_below_097",
    "voltage_above_105", "voltage_above_103", "trafo_over_100", "line_over_100",
    "q_selected_kvar", "q_controller_status", "night_reactive_disabled",
}


def is_true(x):
    if isinstance(x, bool):
        return x
    if str(x).lower() == "true":
        return True
    if str(x).lower() == "false":
        return False
    raise ValueError("Invalid boolean value in signed AC CSV: " + repr(x))


def full_year_rows(rows):
    expected = [str(x) for x in pd.date_range("2025-01-01", periods=8760, freq="h")]
    times = [r["timestamp_lst"] for r in rows]
    if len(rows) != 8760 or times != expected or len(set(times)) != 8760:
        raise ValueError("Signed PF98 2025 AC baseline must have 8760 unique ordered hours")
    for row in rows:
        if not MIN_REQUIRED.issubset(row):
            raise ValueError("Annual AC archive has missing physical result fields")
        if row["status"] != "CONVERGED":
            raise ValueError("Archived AC baseline has nonconverged hour")
    return rows


def annual_scan(rows):
    typed = [{**r, "ac_feasible": is_true(r["ac_feasible"])} for r in rows]
    return annual.annual_summary(typed)


def merge_six(original_corrected, selected, source_candidate):
    if len(original_corrected) != 8760 or set(selected) != EXPECTED_NEW:
        raise ValueError("Annual merge must replace exactly six specified November hours")
    index = {r["timestamp_lst"]: i for i, r in enumerate(original_corrected)}
    if len(index) != 8760 or any(t not in index for t in EXPECTED_NEW):
        raise ValueError("Annual original corrected archive has missing/duplicate hours")
    if len(source_candidate) != 8760:
        raise ValueError("Candidate is not a complete signed 2025 chronology")
    merged = [dict(r) for r in original_corrected]
    detail = []
    for stamp in joint.SOURCE_TIMES:
        old = original_corrected[index[stamp]]
        new = selected[stamp]
        if not MIN_REQUIRED.issubset(new) or not MIN_REQUIRED.issubset(old):
            raise ValueError("Missing required new or old AC fields at " + stamp)
        if new["timestamp_lst"] != stamp or new["status"] != "CONVERGED" or not is_true(new["ac_feasible"]):
            raise ValueError("Selected joint hour not converged/AC feasible: " + stamp)
        t = pd.Timestamp(stamp)
        expected_p = float(source_candidate.at[t, "inverter_ac_kw"])
        expected_load = float(source_candidate.at[t, "demand_kw"])
        if (abs(float(new["inverter_ac_kw"]) - expected_p) > 1e-6 or
                abs(float(new["gross_demand_kw"]) - expected_load) > 1e-5):
            raise ValueError("Selected AC point differs from source annual P/load at " + stamp)
        if (abs(float(old["gross_demand_kw"]) - expected_load) > 1e-5 or
                abs(float(old["load_pf"]) - 0.98) > 1e-9 or
                abs(float(new["load_pf"]) - 0.98) > 1e-9):
            raise ValueError("Original or new AC source load or PF changed at " + stamp)
        updated = dict(old)
        for key in MIN_REQUIRED | {"ac_evaluations", "error", "load_pf", "q_requested_kvar"}:
            if key not in new or key not in updated:
                raise ValueError("New AC output missing original comparable field: " + key)
            updated[key] = new[key]
        updated["source_grid_import_kw"] = str(source_candidate.at[t, "grid_import_kw"])
        updated["scenario"] = "corrected_five_event_source_locked"
        merged[index[stamp]] = updated
        detail.append({
            "timestamp_lst": stamp, "pf": 0.98, "fraction": FRACTION,
            "original_old_corrected_inverter_ac_kw": float(old["inverter_ac_kw"]),
            "new_corrected_inverter_ac_kw": float(updated["inverter_ac_kw"]),
            "old_corrected_min_v_pu": float(old["min_v_pu"]),
            "new_corrected_min_v_pu": float(updated["min_v_pu"]),
            "old_corrected_trafo_pct": float(old["max_trafo_pct"]),
            "new_corrected_trafo_pct": float(updated["max_trafo_pct"]),
            "old_corrected_loss_kw": float(old["loss_kw"]),
            "new_corrected_loss_kw": float(updated["loss_kw"]),
            "loss_delta_kw": float(updated["loss_kw"]) - float(old["loss_kw"]),
        })
    if any(merged[i] != original_corrected[i] for i in range(8760)
           if original_corrected[i]["timestamp_lst"] not in EXPECTED_NEW):
        raise ValueError("Unchanged 8754 annual AC hours were altered")
    return merged, detail


def signed_inputs(repo):
    repo = repo.resolve()
    receipt, item, _v6 = joint.preflight(repo)
    old_manifest = nov.gate.read_json(repo / joint.BASELINE / "RUN_MANIFEST.json")
    pilot_manifest = nov.gate.read_json(repo / PILOT / "RUN_MANIFEST.json")
    if (old_manifest.get("status") != "ANNUAL_94022_SS90_MARCH50_NOV98_PF98_COMPLETE_VIOLATIONS_RECORDED"
            or old_manifest.get("pf") != 0.98
            or old_manifest.get("corrected_annual_summary", {}).get("main_band_infeasible_hours") != 3
            or old_manifest.get("new_original_AC_case_hours") != 8760
            or old_manifest.get("new_corrected_AC_case_hours") != 4
            or old_manifest.get("original_energy_csv_sha256") != receipt["frozen_energy_source_sha256"]
            or old_manifest.get("AC_solver_state_independent_flat_reset_source_confirmed") is not True):
        raise ValueError("Original March/Nov annual source manifest differs from signed source")
    if (pilot_manifest.get("status") != "REMAINING3_94022_SS90_JOINT_AC_SAMPLED_60_COMPLETE_NOT_ANNUAL"
            or pilot_manifest.get("new_AC_hours_executed") != 60
            or pilot_manifest.get("AC_converged_casehours") != 60
            or pilot_manifest.get("all_selected_20of20_pass_candidates") != 1
            or pilot_manifest.get("new_12of12_AC_pass_candidates") != 1
            or pilot_manifest.get("annual_2025_corrected_AC_verified") is not False
            or pilot_manifest.get("original_pf98_annual_AC_source") != receipt["original_pf98_annual_AC_source"]
            or pilot_manifest.get("frozen_energy_source_sha256") != receipt["frozen_energy_source_sha256"]):
        raise ValueError("New pilot source, completeness or selected candidate mismatched")
    selected = [r for r in pilot_manifest["candidate_summary"]
                if r["20of20_selected_AC_pass"] is True]
    if len(selected) != 1 or abs(float(selected[0]["fraction"]) - FRACTION) > 1e-12:
        raise ValueError("Unique joint successful 50% candidate was not signed")
    files = {
        "original": (joint.BASELINE / "ORIGINAL_2025_8760_AC.csv", old_manifest["outputs_sha256"]["ORIGINAL_2025_8760_AC.csv"]),
        "prior_corrected": (joint.BASELINE / "CORRECTED_2025_8760_AC.csv", old_manifest["outputs_sha256"]["CORRECTED_2025_8760_AC.csv"]),
        "new_ac": (PILOT / "REMAINING3_DONOR_TARGET_60_AC_CASEHOURS.csv", pilot_manifest["ac_csv_sha256"]),
        "candidates": (PILOT / "JOINT_CANDIDATES_5.csv", pilot_manifest["candidate_csv_sha256"]),
    }
    sig, saved = {}, {}
    for key, (rel, sha) in files.items():
        sig[key] = nov.gate.signed_bytes(repo / rel, sha)
        saved[key] = nov.gate.read_csv(repo / rel)
    initial = full_year_rows(saved["original"])
    previous = full_year_rows(saved["prior_corrected"])
    if len(saved["new_ac"]) != 60 or len(saved["candidates"]) != 5:
        raise ValueError("New pilot or candidate CSV population differs from signed manifest")
    winners = [r for r in saved["candidates"] if is_true(r["20of20_selected_AC_pass"])]
    if len(winners) != 1 or float(winners[0]["fraction"]) != FRACTION:
        raise ValueError("Candidate CSV does not identify unique 50% passing schedule")
    seen = set()
    winning, zeropct, selected_both_pf = {}, {}, []
    for r in saved["new_ac"]:
        key = (float(r["fraction"]), float(r["pf"]), r["timestamp_lst"])
        if key in seen or key[0] not in joint.SAMPLES or key[1] not in joint.PF or key[2] not in EXPECTED_NEW:
            raise ValueError("Pilot AC candidate-time duplicates or invalid grid")
        seen.add(key)
        if (r["case"] != joint.CASE or r["frozen_source_energy_sha256"] != receipt["frozen_energy_source_sha256"]
                or r["source_pf98_original_annual_AC_SHA"] != receipt["original_pf98_annual_AC_source"]
                or abs(float(r["load_pf"]) - key[1]) > 1e-9):
            raise ValueError("Pilot case or source hash/PF mismatch")
        if key[0] == FRACTION:
            selected_both_pf.append(r)
            if key[1] == 0.98:
                winning[key[2]] = r
        if key[0] == 0.0 and key[1] == 0.98:
            zeropct[key[2]] = r
    if len(seen) != 60 or len(winning) != 6 or len(zeropct) != 6:
        raise ValueError("Pilot does not cover exactly 60 distinct signed AC cases")
    if len(selected_both_pf) != 12 or any(r["status"] != "CONVERGED" or not is_true(r["ac_feasible"]) for r in selected_both_pf):
        raise ValueError("Selected joint schedule failed a sampled PF .98/.95 AC hour")
    orig_map = {r["timestamp_lst"]: r for r in initial}
    prior_map = {r["timestamp_lst"]: r for r in previous}
    for t in EXPECTED_NEW:
        annual.exact_ac_regression(zeropct[t], orig_map[t], "Original PF98 pilot regression " + t)
        for k in ("inverter_ac_kw", "gross_demand_kw", "min_v_pu", "max_v_pu", "loss_kw"):
            if abs(float(prior_map[t][k]) - float(orig_map[t][k])) > 1e-10:
                raise ValueError("Prior four-hour correction already changed residual source hour " + t)
    candidate = item["frames"][FRACTION]
    merged, changed = merge_six(previous, winning, candidate)
    # Check every cached AC row against the matching full-year candidate P and load.
    for old, prior, new in zip(initial, previous, merged):
        t = pd.Timestamp(new["timestamp_lst"])
        for row, frame in ((old, item["source"]), (prior, item["base"]), (new, candidate)):
            for ac_field, energy_field, tol in (
                ("inverter_ac_kw", "inverter_ac_kw", 1e-6),
                ("gross_demand_kw", "demand_kw", 1e-5),
                ("source_grid_import_kw", "grid_import_kw", 1e-6),
            ):
                if abs(float(row[ac_field])-float(frame.at[t, energy_field])) > tol:
                    raise ValueError("Cached annual input mismatch: " + str(t) + " " + ac_field)
            if abs(float(row["load_pf"]) - .98) > 1e-9:
                raise ValueError("Unexpected annual AC load PF")
    actual = {b["timestamp_lst"] for a,b in zip(initial,merged)
              if abs(float(a["inverter_ac_kw"])-float(b["inverter_ac_kw"])) > 1e-7}
    if actual != (set(annual.CHANGED) | EXPECTED_NEW):
        raise ValueError("Expected exactly ten changed annual P hours")
    original_sum = annual_scan(initial)
    old_sum = annual_scan(previous)
    new_sum = annual_scan(merged)
    if (original_sum["main_band_infeasible_hours"] != 5
            or old_sum["main_band_infeasible_hours"] != 3
            or abs(old_sum["minimum_voltage_pu"] - old_manifest["corrected_annual_summary"]["minimum_voltage_pu"]) > 1e-10):
        raise ValueError("Independent annual source count or old summary does not reproduce")
    loss_change = sum(r["loss_delta_kw"] for r in changed)
    if not math.isclose(new_sum["annual_ac_network_losses_kwh"] - old_sum["annual_ac_network_losses_kwh"],
                        loss_change, abs_tol=1e-6, rel_tol=0):
        raise ValueError("Annual AC network loss delta differs from six replacements")
    report = {
        "status": "SIGNED_94022_SS90_FIVE_EVENTS_ANNUAL_REUSE_PREFLIGHT_NO_NEW_AC",
        "annual_2025_pf": 0.98, "year": 2025, "source": joint.CASE,
        "transformer": "94022", "assumed_trafo_kva": 5.0,
        "load_assignment": "A0", "battery_modules": 6,
        "prior_march_fraction": 0.5, "prior_nov27_fraction": 0.98,
        "new_joint_fraction": FRACTION,
        "old_original_annual_hour_count": 8760, "old_corrected_annual_hour_count": 8760,
        "new_ac_solved_in_this_reconstruction": 0, "cached_new_ac_replaced_hours": 6,
        "old_corrected_ac_reused_hours": 8754, "unique_changed_P_hours_vs_frozen_original": 10,
        "old_original_annual_summary": original_sum,
        "prior_four_hour_corrected_annual_summary": old_sum,
        "new_five_event_corrected_annual_summary": new_sum,
        "delta_network_losses_kwh_vs_prior": loss_change,
        "annual_model_main_band_pass": bool(new_sum["all_2025_model_main_band_pass"]),
        "annual_AC_verified": bool(new_sum["all_2025_model_main_band_pass"]),
        "annual_AC_reconstructed_from_cached_stateless_AC": True,
        "original_AC_solver_state_independent_flat_reset": True,
        "PF95_annual_AC_verified": False,
        "strict_research_097_103_annual_pass": new_sum["optional_under_097_hours"] == 0 and new_sum["optional_above_103_hours"] == 0,
        "field_EPM_verified": False, "actual_utility_nameplate_and_phase_verified": False,
        "manufacturer_nighttime_reactive_capability_verified": False,
        "grid_import_and_economic_objective_reoptimized_for_losses": False,
        "source_frozen_energy_sha256": receipt["frozen_energy_source_sha256"],
        "source_old_corrected_annual_sha256": files["prior_corrected"][1],
        "source_pilot_new_ac_sha256": files["new_ac"][1], "source_modes": sig,
    }
    return report, initial, previous, merged, changed


def diagnostic_figures(original, previous, corrected, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    folder = out / "figures_diagnostic"
    folder.mkdir(exist_ok=False)
    stamps = pd.date_range("2025-01-01", periods=8760, freq="h")
    series = [np.asarray([float(r["min_v_pu"]) for r in frame])
              for frame in (original, previous, corrected)]
    labels = ["Original annual", "Prior March50 + Nov27 98%", "Five-event corrected, joint 50%"]
    fig, ax = plt.subplots(figsize=(12, 5))
    for y, label in zip(series, labels):
        ax.plot(stamps, y, lw=0.7, label=label)
    ax.axhline(.95, color="black", ls="--", lw=1, label="Research minimum 0.95 pu")
    ax.set(title="94022 A0, PF 0.98: annual minimum house voltage, cached AC",
           xlabel="2025 model local time", ylabel="Minimum voltage [pu]")
    ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.autofmt_xdate(); fig.tight_layout()
    a = folder / "annual_min_voltage_three_schedules.png"
    fig.savefig(a, dpi=160); plt.close(fig)
    chosen = tuple(sorted(set(annual.CHANGED) | EXPECTED_NEW))
    places = {str(t): i for i,t in enumerate(stamps)}
    ind = [places[t] for t in chosen]
    xx = np.arange(len(ind))
    fig, ax = plt.subplots(figsize=(13, 5))
    for j,(y,label) in enumerate(zip(series,labels)):
        ax.bar(xx+(j-1)*.25, y[ind], .23, label=label)
    ax.axhline(.95,color="black",ls="--",lw=1)
    ax.set_xticks(xx,[t[5:16] for t in chosen],rotation=35,ha="right")
    ax.set_ylim(.94,max(1.0,max(y[ind].max() for y in series)+.01))
    ax.set(title="All ten changed P hours",ylabel="Minimum house voltage [pu]")
    ax.legend(fontsize=8); ax.grid(axis="y",alpha=.2); fig.tight_layout()
    b = folder / "ten_changed_hours_voltage.png"
    fig.savefig(b,dpi=160); plt.close(fig)
    return {a.name:annual.sha(a),b.name:annual.sha(b)}


def save_new_version(repo, report, initial, previous, merged, changed):
    out = next((repo / f"{OUT_PREFIX}{k}" for k in range(1,101)
                if not (repo / f"{OUT_PREFIX}{k}").exists()),None)
    if out is None:
        raise FileExistsError("No unused corrected annual result directory")
    out.mkdir()
    manifest = out / "RUN_MANIFEST.json"
    doc = dict(report,status="INCOMPLETE_94022_FIVE_EVENT_ANNUAL_REUSE_DO_NOT_CLAIM")
    def save():
        manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save()
    try:
        path=out/"CORRECTED_2025_8760_AC.csv"
        ledger=out/"SIX_NEW_CHANGED_AC_HOURS.csv"
        annual.save_csv(path,merged); annual.save_csv(ledger,changed)
        plot_sha=diagnostic_figures(initial,previous,merged,out)
        doc.update(status=("REUSED_ANNUAL_94022_SS90_PF98_MAIN_BAND_PASS_NOT_FIELD"
                           if report["annual_model_main_band_pass"] else
                           "REUSED_ANNUAL_94022_SS90_PF98_VIOLATIONS_RECORDED"),
                   outputs_sha256={path.name:annual.sha(path),ledger.name:annual.sha(ledger)},
                   diagnostics_sha256=plot_sha,output_folder=str(out))
        save()
        return doc
    except Exception as exc:
        doc["failure"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
        save()
        raise


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path.cwd())
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument("--preflight-only",action="store_true")
    mode.add_argument("--run-local",action="store_true")
    args=ap.parse_args(argv)
    if not (args.repo_root/".git").is_dir():
        raise FileNotFoundError("Use the actual GitLab checkout as --repo-root")
    report,initial,previous,merged,changed=signed_inputs(args.repo_root)
    if args.run_local:
        result=save_new_version(args.repo_root,report,initial,previous,merged,changed)
        print(json.dumps({"status":result["status"],"folder":result["output_folder"],
                          "annual":result["new_five_event_corrected_annual_summary"]},indent=2,allow_nan=False))
    else:
        print(json.dumps(report,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
