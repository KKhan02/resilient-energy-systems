#!/usr/bin/env python3
"""A1 113699: bounded nighttime P-envelope test of independently audited AC failures.

This is a sampled, fixed-geometry static AC diagnostic. It does NOT edit the
original 8760h PV/BESS schedules, change installed hardware, solve SOC, or
establish annual AC feasibility.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

import numpy as np
import pandas as pd

HERE = Path("case1/studies/SEEDExchange_StudyA_Matched_Hardware_2026-11-21")
PREVIOUS_RUNNER = HERE / "matched_hardware_ac113699.py"
OLD_PILOT = Path("StudyA_A0_A1_MatchedHardware_AC113699_Pilot_v1")
MANIFEST_LF_SHA = "b17333788978555471d7ee0760ad11b5e4c267106fcc22c4f4dae2967cbbe947"
ORIGINAL_CSV_SHA = "908ce6a602e1e317288ce8d4028084b207790753fa8edc0e8ad943ffd0af180a"
OUT_PREFIX = "StudyA_A0_A1_MatchedHardware_AC113699_P_Envelope_v"
EXPECTED_FAILURES = {
    "A0": ("2025-03-14 19:00:00", "2025-11-30 20:00:00"),
    "A1": ("2025-11-30 20:00:00",),
}
DEFAULT_SAMPLES = 41
ETA_INVERTER = .95
AC_COMPARE_TOL = 2e-4


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def git_lf_sha(path):
    raw = Path(path).read_bytes()
    if b"\r" in raw.replace(b"\r\n", b""):
        raise ValueError("Unexpected lone CR in source")
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def signed_text_mode(path, expected_sha):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() == expected_sha:
        return "ORIGINAL_EXACT"
    if b"\r" not in raw and b"\n" in raw:
        if hashlib.sha256(raw.replace(b"\n", b"\r\n")).hexdigest() == expected_sha:
            return "GIT_LF_MATCHES_SIGNED_CRLF"
    raise ValueError("Prior bounded AC CSV differs from signed source: " + str(path))


def load_previous(repo):
    path = repo / PREVIOUS_RUNNER
    spec = importlib.util.spec_from_file_location("ac113699_p_envelope_source", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expected_failing_rows(frame):
    if (len(frame) != 150 or len(frame.timestamp_lst.unique()) != 15
        or frame.duplicated(["assignment", "hardware_origin", "operation",
                             "timestamp_lst"]).any()
        or frame.status.ne("CONVERGED").any()):
        raise ValueError("Original pilot no longer has its 150 valid AC records")
    if frame.ac_feasible.astype(str).str.lower().eq("false").sum() != 10:
        raise ValueError("Changed original number of 113699 infeasible AC cases")
    selected = frame.loc[(frame.assignment == "A1") & (frame.operation == "q_off")
                         & frame.hardware_origin.isin(("A0", "A1"))].copy()
    if len(selected) != 30:
        raise ValueError("Missing original A1 Q-off records")
    selected["failed"] = selected.ac_feasible.astype(str).str.lower().eq("false")
    fail = selected[selected.failed]
    observed = {}
    for origin, times in EXPECTED_FAILURES.items():
        observed_times = sorted(fail[fail.hardware_origin == origin].timestamp_lst)
        if observed_times != sorted(times):
            raise ValueError("Unexpected A1 AC failure roster for frozen " + origin)
        observed[origin] = [
            fail[(fail.hardware_origin == origin) &
                 (fail.timestamp_lst == when)].iloc[0].to_dict()
            for when in times]
    if len(fail) != sum(len(x) for x in EXPECTED_FAILURES.values()):
        raise ValueError("Unexpected extra A1 source AC failures")
    return observed


def max_night_battery_p_ac(load_kw, hardware, eta=ETA_INVERTER):
    load_kw = float(load_kw)
    if load_kw <= 0:
        raise ValueError("Need positive gross demand for night feeder screening")
    if (hardware["battery_modules"] <= 0 or hardware["battery_power_dc_kw"] <= 0
        or hardware["inverter_kva"] <= 0):
        raise ValueError("Missing installed energy equipment")
    result = min(load_kw, float(hardware["inverter_kva"]),
                 eta * float(hardware["battery_power_dc_kw"]))
    if not 0 < result <= load_kw + 1e-9:
        raise ValueError("Invalid no-export sampled P upper limit")
    return result


def contiguous_feasible_points(rows):
    """Group only adjacent AC-feasible samples; NOT an interval AC proof."""
    bands, run = [], []
    for row in rows:
        if bool(row["ac_feasible"]) and row["status"] == "CONVERGED":
            run.append(row)
        elif run:
            bands.append(run)
            run = []
    if run:
        bands.append(run)
    return [{"first_sample_kw": float(r[0]["p_sample_ac_kw"]),
             "last_sample_kw": float(r[-1]["p_sample_ac_kw"]),
             "sample_count": len(r),
             "inter_sample_AC_feasibility": "NOT_PROVEN"} for r in bands]


def select_out(repo, path=None):
    if path is not None:
        target = path if path.is_absolute() else repo / path
        target = target.resolve()
        if target.exists() or target.parent != repo:
            raise FileExistsError("Only a new repo-root result directory is permitted")
        return target
    for i in range(1, 1000):
        candidate = repo / (OUT_PREFIX + str(i))
        if not candidate.exists():
            return candidate
    raise FileExistsError("Exhausted output versions")



def verify_previous_manifest_fields(manifest, source):
    """Report the precise failed signed-source field, never relax a gate."""
    if len(ORIGINAL_CSV_SHA) != 64 or any(
            c not in "0123456789abcdef" for c in ORIGINAL_CSV_SHA):
        raise ValueError("The runner's pinned AC CSV SHA-256 is incomplete or invalid")
    expected = {
        "status": "BOUNDED_AC_VIOLATIONS_RECORDED_ANNUAL_PENDING",
        "ac_csv_sha256": ORIGINAL_CSV_SHA,
        "sampled_infeasible_case_hours": 10,
        "converged_case_hours": 150,
        "nonconverged_case_hours": 0,
        "new_powerflow_solves": 150,
        "annual_AC_feasible": False,
        "full_manifest_lf_sha256": source["full_manifest_lf_sha256"],
    }
    for field, value in expected.items():
        observed = manifest.get(field)
        if type(observed) is not type(value) or observed != value:
            raise ValueError(
                f"Original bounded AC source manifest field {field} mismatch: "
                f"expected {value!r}, saved {observed!r}")



def preflight(repo, samples=DEFAULT_SAMPLES):
    repo = Path(repo).resolve()
    if not (repo / ".git").exists():
        raise ValueError("Require the actual GitLab checkout")
    if samples != DEFAULT_SAMPLES:
        raise ValueError("First controlled test is pinned to 41 samples")
    previous = load_previous(repo)
    v6, cases, geometry, hours, reasons, source = previous.preflight(repo)
    if (source["status"] != "SIGNED_113699_AC_SOURCE_GEOMETRY_PREFLIGHT_NO_SOLVES"
        or source["expected_powerflow_cases"] != 150
        or len(hours) != 15 or source["annual_AC_feasible"] is not False):
        raise ValueError("Prior signed 113699 energy/GIS preflight changed")
    folder = repo / OLD_PILOT
    manifest_path = folder / "RUN_MANIFEST.json"
    csv_path = folder / "BOUNDED_AC_HOURLY.csv"
    if not manifest_path.exists() or git_lf_sha(manifest_path) != MANIFEST_LF_SHA:
        raise ValueError("Original bounded AC pilot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_previous_manifest_fields(manifest, source)
    mode = signed_text_mode(csv_path, ORIGINAL_CSV_SHA)
    frame = pd.read_csv(csv_path)
    if frame.timestamp_lst.dtype != object:
        raise ValueError("Unexpected previous AC local timestamps")
    observed = expected_failing_rows(frame)
    failed_case_rows = []
    for origin, known in observed.items():
        energy = cases[origin + "_hardware_on_A1"]
        for row in known:
            hour = str(row["timestamp_lst"])
            t = pd.Timestamp(hour)
            old = energy["energy"].loc[t]
            if (abs(float(old.inverter_ac_kw)) > 1e-7
                or abs(float(old.pv_dc_available_kw)) > 1e-7
                or abs(float(row["q_selected_kvar"])) > 1e-7
                or abs(float(row["inverter_ac_kw"])) > 1e-7
                or float(old.grid_export_kw) > 1e-7 or float(old.unserved_kw) > 1e-7):
                raise ValueError("Selected failed hour not an original Q-off, zero-P night")
            hw = energy["hardware"]
            floor = hw["battery_modules"] * (17.3 / 4 - .8 * 5.12)
            if float(old.battery_soc_usable_kwh) < floor - 1e-6:
                raise ValueError("Original night discharge violates manufacturer SOC")
            limit = max_night_battery_p_ac(float(old.demand_kw), hw)
            failed_case_rows.append({
                "hardware_origin": origin, "assignment": "A1",
                "timestamp_lst": hour,
                "gross_demand_kw": float(old.demand_kw),
                "original_AC_pcc_kva": float(row["pcc_kva"]),
                "original_AC_min_v_pu": float(row["min_v_pu"]),
                "original_AC_transformer_pct": float(row["max_trafo_pct"]),
                "original_energy_PCC_proxy_kva": float(old.pcc_kva_proxy),
                "original_inverter_ac_kw": float(old.inverter_ac_kw),
                "original_battery_soc_usable_kwh": float(old.battery_soc_usable_kwh),
                "manufacturer_SOC_usable_floor_kwh": floor,
                "maximum_sweep_ac_kw": limit,
                "P_grid_samples": samples,
                "source_energy_csv_sha256": energy["source_csv_sha256"]})
    if len(failed_case_rows) != 3:
        raise ValueError("First experiment must be exactly the 3 failed case-hours")
    receipt = {
        "status": "SOURCE_PINNED_113699_FAILED_HOUR_P_ENVELOPE_NO_SOLVES",
        "previous_result_commit": "e211d601314b2b34dbfceba5a224622e618b005f",
        "original_ac_manifest_lf_sha256": MANIFEST_LF_SHA,
        "original_ac_csv_signed_sha256": ORIGINAL_CSV_SHA,
        "original_ac_csv_signed_representation": mode,
        "signed_energy_source_manifest_lf_sha256": source["full_manifest_lf_sha256"],
        "transformer": "113699", "territory": "A1",
        "phase_model": "BALANCED_THREE_PHASE_PROXY",
        "transformer_kva_assumed": 3.,
        "individual_load_pf": .98,
        "service_multiplier": 1.0,
        "night_q": "OFF",
        "hardware_changed": False, "SOC_schedule_changed": False,
        "new_ac_solver_calls": 0,
        "failure_case_hours": failed_case_rows,
        "sample_points_per_case": samples,
        "planned_AC_powerflow_calls": 3 * samples,
        "annual_AC_feasible": False,
        "interpretation": "Sampled static AC P operating points, not yet chronological SOC or proven interval feasibility"}
    return v6, cases, geometry, observed, receipt


def make_plots(frame, folder):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder.mkdir(exist_ok=False)
    results = {}
    for metric, ylab, bound, name in (
        ("max_trafo_pct", "Transformer loading (%)", 100., "sampled_transformer_vs_P.png"),
        ("min_v_pu", "Lowest customer bus voltage (pu)", .95, "sampled_voltage_vs_P.png")):
        fig, ax = plt.subplots(figsize=(9.5, 5.5))
        for (origin, hour), grp in frame.groupby(["hardware_origin", "timestamp_lst"], sort=True):
            grp = grp.sort_values("sample_number")
            ok = grp.status.eq("CONVERGED")
            ax.plot(grp.loc[ok, "p_sample_ac_kw"], grp.loc[ok, metric],
                    marker=".", linewidth=1.5, label=origin + " / " + hour[5:16])
            bad = grp.ac_feasible.astype(str).str.lower().eq("false") & ok
            if bad.any():
                ax.scatter(grp.loc[bad, "p_sample_ac_kw"], grp.loc[bad, metric],
                           marker="x", zorder=3)
        ax.axhline(bound, linestyle="--", linewidth=.8, label="Research limit")
        ax.set_title("A1 113699 original 3 kVA assumed transformer, Q=0 at night")
        ax.set_xlabel("Hypothetical inverter AC active power (kW), source SOC unchanged")
        ax.set_ylabel(ylab)
        ax.grid(alpha=.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        path = folder / name
        fig.savefig(path, dpi=160)
        plt.close(fig)
        results[name] = sha(path)
    return results


def run(repo, out=None, preflight_only=False, samples=DEFAULT_SAMPLES):
    repo = Path(repo).resolve()
    v6, cases, geometry, old_failures, receipt = preflight(repo, samples)
    if preflight_only:
        return receipt
    import pandapower as pp
    path = select_out(repo, out)
    path.mkdir(parents=True)
    metadata = dict(receipt, status="INCOMPLETE_P_ENVELOPE_DO_NOT_CLAIM", new_ac_solver_calls=0)
    manifest_path = path / "RUN_MANIFEST.json"
    manifest_path.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    try:
        territory, net, meta, _evidence = geometry["A1"]
        records, bands = [], []
        for case in receipt["failure_case_hours"]:
            origin = case["hardware_origin"]
            t = pd.Timestamp(case["timestamp_lst"])
            e = cases[origin + "_hardware_on_A1"]
            demand = e["trace"].loc[t]
            if abs(float(demand.sum()) - case["gross_demand_kw"]) > 1e-6:
                raise ValueError("Original individual load profile changed")
            sample_set = []
            for k, p in enumerate(np.linspace(0., case["maximum_sweep_ac_kw"], samples)):
                raw = v6.solve_ac_hour(
                    net, meta, territory, t, demand, .98, float(p),
                    float(e["hardware"]["inverter_kva"]), 0., 0., 9, "pvbess", pp)
                if k == 0:
                    original = old_failures[origin][
                        list(EXPECTED_FAILURES[origin]).index(str(t))]
                    if raw["status"] != "CONVERGED" or bool(raw["ac_feasible"]):
                        raise ValueError("Original failed AC case was not reproduced")
                    for field in ("min_v_pu", "max_v_pu", "max_trafo_pct",
                                  "max_line_pct", "loss_kw", "pcc_kva"):
                        if abs(float(raw[field]) - float(original[field])) > AC_COMPARE_TOL:
                            raise ValueError("Original AC source mismatch at P=0 for " + field)
                row = {
                    "hardware_origin": origin, "assignment": "A1",
                    "timestamp_lst": str(t), "sample_number": k,
                    "p_sample_ac_kw": float(p),
                    "p_max_from_battery_kw": case["maximum_sweep_ac_kw"],
                    "demand_kw": case["gross_demand_kw"],
                    "original_source_soc_kwh": case["original_battery_soc_usable_kwh"],
                    "SOC_chronology_reoptimized": False,
                    **raw}
                sample_set.append(row)
                records.append(row)
            available = contiguous_feasible_points(sample_set)
            bands.append({
                "hardware_origin": origin, "timestamp_lst": str(t),
                "total_sample_points": samples,
                "converged_sample_points": sum(x["status"] == "CONVERGED" for x in sample_set),
                "AC_feasible_sample_points": sum(bool(x["ac_feasible"]) for x in sample_set),
                "candidate_sample_bands": available,
                "first_feasible_sample_kw": (available[0]["first_sample_kw"] if available else None),
                "unresolved_no_feasible_sample": len(available) == 0,
                "inter_sample_AC_feasibility": "NOT_PROVEN",
                "annual_SOC_feasibility": "NOT_TESTED"})
            print("Screened failure", origin, str(t), "AC feasible P samples",
                  bands[-1]["AC_feasible_sample_points"], "/", samples, flush=True)
        df = pd.DataFrame(records)
        if (len(df) != receipt["planned_AC_powerflow_calls"]
            or df.duplicated(["hardware_origin", "timestamp_lst", "sample_number"]).any()):
            raise ValueError("Missing or duplicate P-sample outputs")
        csv = path / "AC_P_SWEEP_SAMPLES.csv"
        df.to_csv(csv, index=False, float_format="%.10f")
        metadata["sampled_hour_results"] = bands
        metadata["ac_samples_sha256"] = sha(csv)
        metadata["diagnostic_figure_sha256"] = make_plots(df, path / "figures_diagnostic")
        metadata["new_ac_solver_calls"] = len(df)
        metadata["nonconverged_sample_points"] = int(df.status.ne("CONVERGED").sum())
        metadata["unresolved_case_hours"] = int(sum(x["unresolved_no_feasible_sample"] for x in bands))
        metadata["status"] = (
            "SAMPLED_AC_P_HAS_UNRESOLVED_HOURS_SOC_AND_ANNUAL_PENDING"
            if metadata["unresolved_case_hours"] else
            "SAMPLED_AC_P_CANDIDATES_FOUND_SOC_AND_ANNUAL_PENDING")
        metadata["annual_AC_feasible"] = False
        manifest_path.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return {"status": metadata["status"], "output": str(path),
                "cases": len(bands), "sampled_powerflows": len(df),
                "unresolved_case_hours": metadata["unresolved_case_hours"],
                "annual_AC_feasible": False}
    except Exception as exc:
        metadata["status"] = "INCOMPLETE_P_ENVELOPE_DO_NOT_CLAIM"
        metadata["failure"] = {"type": type(exc).__name__, "message": str(exc),
                               "traceback": traceback.format_exc()}
        manifest_path.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    print(json.dumps(run(args.repo_root, args.out, args.preflight_only),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
