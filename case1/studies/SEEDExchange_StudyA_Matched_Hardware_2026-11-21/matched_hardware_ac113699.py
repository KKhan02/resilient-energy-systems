#!/usr/bin/env python3
"""Source-pinned Study A, 113699 A0/A1 fixed-hardware bounded AC diagnostics.

Replays existing 2025 energy schedules through the preserved v6 pandapower AC
solver. No new PyPSA solve, historical-file edits, or annual AC certification.
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
RECIP = HERE / "reciprocal_hardware_energy.py"
FULL = Path("StudyA_A0_A1_MatchedHardware_Full_v1")
FULL_MANIFEST_LF_SHA = "b07ac43ce5a610bfd3f79ffe7deb0c622da7d582319b81701ef1e3b51c930f1f"
OUT_PREFIX = "StudyA_A0_A1_MatchedHardware_AC113699_Pilot_v"
TRANSFORMER = "113699"
ASSIGNMENTS = ("A0", "A1")
MOVES = {"H03": ("94022", "113699"),
         "H06": ("94022", "113699"),
         "H13": ("106039", "85398")}
ANCHORS = ("2025-01-01 00:00:00", "2025-02-09 12:00:00",
           "2025-06-21 12:00:00", "2025-12-21 19:00:00")
EXTREMES = ("demand_kw", "grid_import_kw", "pcc_kva_proxy",
            "inverter_ac_kw", "pv_dc_available_kw",
            "battery_discharge_dc_kw", "curtailed_pv_dc_kw")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_lf_sha(path):
    raw = Path(path).read_bytes()
    if b"\r" in raw.replace(b"\r\n", b""):
        raise ValueError("Unexpected lone CR in signed manifest")
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def load_recip(repo):
    path = repo / RECIP
    spec = importlib.util.spec_from_file_location("ac113699_signed_recip", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def verify_full(repo, rec, base, pv, m, mapping, profiles, originals):
    p = repo / FULL / "RUN_MANIFEST.json"
    if not p.is_file() or git_lf_sha(p) != FULL_MANIFEST_LF_SHA:
        raise ValueError("Signed full 16-case manifest missing or changed")
    j = json.loads(p.read_text(encoding="utf-8"))
    for k in ("input_manifest_sha256", "solar_sha256", "fixed_solver_sha256",
              "source_roster_sha256", "source_manifest_shas",
              "preexisting_pilot_manifest_sha256",
              "existing_exact_hardware_source_reuse"):
        if j.get(k) != base.get(k):
            raise ValueError("Full run changed historical source lineage: " + k)
    if (j.get("status") != "ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING"
        or j.get("completed_case_count") != 16
        or j.get("expected_new_2025_LP_solves") != 12
        or j.get("new_AC_cases") != 0
        or j.get("matched_portfolio_count") != 8
        or j.get("paired_comparison_count") != 4
        or j.get("main_network_AC_validated") is not False
        or j.get("errors") != {}
        or len(j.get("completed_cases", {})) != 16
        or j.get("verified_reverse_pilot", {}).get("target_energy_sha256")
            != rec.REVERSE_CSV_ORIGINAL_SHA):
        raise ValueError("Full run is not audited energy-only 16-case result")
    rec.checked_bytes(repo / RECIP, j["runner_sha256"])
    rec.verify_reverse_pilot(repo, pv, m, mapping, profiles, originals, base)
    for key, entry in j["completed_cases"].items():
        _, trace = pv.source_trace(m, mapping, profiles,
                                   entry["assignment_for_load"], entry["transformer"])
        rec.ensure_completed_case(repo, repo / FULL, key, entry, originals[key], trace)
    return j


def validate_source_movements(repo, v6, m):
    read, infer, _, _ = v6.repo_modules(repo)
    houses, trafos, lv = read()
    a0 = {x["house"]: x for x in v6.resolve_v4_assignments(houses, trafos, lv, infer, "A0")}
    a1 = {x["house"]: x for x in v6.resolve_v4_assignments(houses, trafos, lv, infer, "A1")}
    if len(a0) != 35 or set(a0) != set(a1) or set(m["changed_houses"]) != set(MOVES):
        raise ValueError("Changed source population or changed-house roster")
    actual = {h for h in a0 if a0[h]["transformer"] != a1[h]["transformer"]}
    if actual != set(MOVES):
        raise ValueError("Unrecorded source household reassignment")
    summary = {}
    for hid, (old, new) in MOVES.items():
        source = m["changed_houses"][hid]
        if (a0[hid]["transformer"] != old or a1[hid]["transformer"] != new
            or source["from"] != old or source["to"] != new
            or str(source["target_segment_id"]) != a1[hid]["segment_id"]
            or abs(float(source["target_service_straight_line_m"]) -
                   float(a1[hid]["gis_proximity_m"])) > .03):
            raise ValueError("Moved-house electrical tap has changed: " + hid)
        summary[hid] = {
            "from": old, "to": new,
            "provisional_segment_id": source["target_segment_id"],
            "straight_line_to_provisional_service_tap_m": source["target_service_straight_line_m"],
            "physical_connection": "NOT_VERIFIED"}
    for hid in m["groups"]["A0"][TRANSFORMER]:
        if a0[hid]["segment_id"] != a1[hid]["segment_id"]:
            raise ValueError("Unmoved original 113699 service differs: " + hid)
    return summary


def make_geometry(repo, v6, m, assignment):
    houses = m["groups"][assignment][TRANSFORMER]
    territory = v6.new_territory(repo, assignment, TRANSFORMER, houses, 1.0)
    if (territory.trafo["identifier"] != TRANSFORMER
        or abs(float(territory.trafo["kva"]) - 3.) > 1e-9):
        raise ValueError("Source 113699 transformer or assumed 3 kVA differs")
    metrics = territory.metrics()
    if not metrics["graph_connected"] or not metrics["tree"]:
        raise ValueError("Source GIS LV circuit disconnected or not radial")
    tap = {x["house"]: x for x in territory.attachments}
    if set(tap) != set(houses):
        raise ValueError("AC topology household bus list differs")
    for hid in ("H03", "H06"):
        if assignment == "A1":
            s = m["changed_houses"][hid]
            if (tap[hid]["segment"] != str(s["target_segment_id"])
                or abs(float(tap[hid]["service_euclidean_m"]) -
                       float(s["target_service_straight_line_m"])) > .03
                or not tap[hid]["assumed"]):
                raise ValueError("Unverified moved-house proposed GIS tap differs: " + hid)
        elif hid in tap:
            raise ValueError("Original A0 includes reassigned A1 house " + hid)
    from run_epm_validation import build_net
    net, meta = build_net(territory, "head")
    if set(meta["loads"]) != set(houses) or meta["node"] != territory.root:
        raise ValueError("Existing pandapower builder output differs")
    evidence = {
        "assignment": assignment, "houses": houses,
        "transformer_kva_PLANNING": 3.0,
        "topology": "EPM_GIS_SECTIONS_PLUS_INFERRED_HOUSE_SERVICES",
        "gis_metrics": metrics,
        "fallback_conductor_categories": meta["fallback_conductors"],
        "attachments": [
            {"house": hid, "fid": tap[hid]["segment"],
             "assumed_service_length_m": tap[hid]["service_length_m"],
             "assumed": tap[hid]["assumed"]} for hid in houses],
        "phase_model": "BALANCED_THREE_PHASE_PROXY",
        "inverter_location": "HEAD",
        "utility_connection_authorized": False}
    return territory, net, meta, evidence


def read_four_energy(repo, rec, pv, m, mapping, profiles, originals, full):
    cases = {}
    for origin in ASSIGNMENTS:
        other = "A1" if origin == "A0" else "A0"
        key = f"{origin}_{TRANSFORMER}_min_cost_to_{other}"
        signed = full["completed_cases"][key]
        original = originals[key]
        if signed["hardware"] != original["hw"]:
            raise ValueError("Origin frozen hardware differs from source")
        for destination in ASSIGNMENTS:
            ids, trace = pv.source_trace(m, mapping, profiles, destination, TRANSFORMER)
            if destination == origin:
                path = repo / rec.BASE_PART / original["slug"] / "energy_hourly_2025.csv"
                expected_sha = original["csv_signed_sha256"]
                metrics = original["metrics"]
                provenance = "ORIGINAL_SIGNED"
            else:
                if signed["target_house_ids"] != ids:
                    raise ValueError("Cross assignment cohort differs")
                path = repo / signed["target_energy_csv"]
                expected_sha = signed["target_energy_sha256"]
                metrics = signed["target_yearly_energy_metrics"]
                provenance = "MATCHED_REUSE_OR_NEW_SIGNED"
            hash_mode = rec.checked_bytes(path, expected_sha)
            frame = pd.read_csv(path, parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
            rec.validate_dispatch(frame, trace, original["hw"], metrics)
            label = origin + "_hardware_on_" + destination
            cases[label] = {
                "origin": origin, "destination": destination, "trace": trace,
                "energy": frame, "hardware": original["hw"], "key": key,
                "source_csv_sha256": expected_sha,
                "source_csv": path.relative_to(repo).as_posix(),
                "source_sha_mode": hash_mode, "source_kind": provenance}
    if len(cases) != 4:
        raise ValueError("Expected exactly four fixed-hardware 113699 energy cases")
    return cases


def select_hours(cases):
    reasons = {}
    def pick(hour, reason):
        reasons.setdefault(hour, set()).add(reason)
    for anchor in ANCHORS:
        pick(pd.Timestamp(anchor), "calendar_anchor")
    for name, case in cases.items():
        frame = case["energy"]
        for field in EXTREMES:
            pick(frame[field].idxmax(), name + ":max_" + field)
        pick(frame.battery_soc_usable_kwh.idxmin(), name + ":min_battery_soc")
    hours = sorted(reasons)
    if not 4 <= len(hours) <= 36:
        raise ValueError("Unexpected number of preselected AC stress hours")
    for case in cases.values():
        if any(t not in case["energy"].index for t in hours):
            raise ValueError("Stress hour outside 2025 chronology")
    return hours, {str(k): sorted(v) for k, v in reasons.items()}


def preflight(repo):
    repo = Path(repo).resolve()
    if not (repo / ".git").exists():
        raise ValueError("Run from your real Git checkout")
    rec = load_recip(repo)
    (pv, v6, m, mapping, profiles, _solar, _roster,
     originals, _shared, _oldpilot, _cross, base) = rec.preflight(repo)
    full = verify_full(repo, rec, base, pv, m, mapping, profiles, originals)
    transfers = validate_source_movements(repo, v6, m)
    cases = read_four_energy(repo, rec, pv, m, mapping, profiles, originals, full)
    geometry = {a: make_geometry(repo, v6, m, a) for a in ASSIGNMENTS}
    hours, reasons = select_hours(cases)
    receipt = {
        "status": "SIGNED_113699_AC_SOURCE_GEOMETRY_PREFLIGHT_NO_SOLVES",
        "full_manifest_lf_sha256": FULL_MANIFEST_LF_SHA,
        "source_gitlab_commit": "120c4e966dfd089eb25116a85c2d5ae027dfd5ca",
        "signed_v6_runner_sha256": m["script_sha256"],
        "source_gis_geojson_sha256": m["gis_geojson_sha256"],
        "source_gis_associations_sha256": m["gis_house_sha256"],
        "moved_house_provisional_taps": transfers,
        "source_networks": {a: geometry[a][3] for a in ASSIGNMENTS},
        "four_fixed_hardware_dispatches": {
            k: {"hardware_origin": x["origin"], "assignment": x["destination"],
                "hardware": x["hardware"], "csv_path": x["source_csv"],
                "signed_csv_sha256": x["source_csv_sha256"],
                "csv_hash_mode": x["source_sha_mode"],
                "source_kind": x["source_kind"]}
            for k, x in cases.items()},
        "household_pf": .98, "service_multiplier": 1.0,
        "daylight_Q_ratio": .25, "night_Q": "OFF",
        "selected_unique_2025_hours": len(hours),
        "expected_powerflow_cases": len(hours) * 10,
        "sampled_timestamps": [
            {"timestamp_lst": str(t), "reasons": reasons[str(t)]} for t in hours],
        "annual_AC_feasible": False,
        "new_powerflow_solves": 0,
        "real_EPM_approval": False}
    return v6, cases, geometry, hours, reasons, receipt


def choose_out(repo, supplied=None):
    if supplied is not None:
        p = supplied if supplied.is_absolute() else repo / supplied
        p = p.resolve()
        if p.exists() or p.parent != repo:
            raise FileExistsError("Output must be an unused repo-root directory")
        return p
    for n in range(1, 1000):
        p = repo / (OUT_PREFIX + str(n))
        if not p.exists():
            return p
    raise FileExistsError("No available pilot output version")


def summaries(frame, hours):
    result = []
    for (assignment, origin, mode), group in frame.groupby(
            ["assignment", "hardware_origin", "operation"], sort=True):
        good = group[group.status == "CONVERGED"]
        result.append({
            "assignment": assignment, "hardware_origin": origin,
            "operation": mode, "selected_hours": hours,
            "converged_hours": len(good),
            "nonconverged_hours": len(group) - len(good),
            "main_band_feasible_hours": int(good.ac_feasible.eq(True).sum()),
            "main_band_infeasible_hours": int(good.ac_feasible.eq(False).sum()),
            "strict_low_voltage_hours": int(good.voltage_below_097.sum()) if len(good) else 0,
            "strict_high_voltage_hours": int(good.voltage_above_103.sum()) if len(good) else 0,
            "min_voltage_pu": float(good.min_v_pu.min()) if len(good) else None,
            "max_voltage_pu": float(good.max_v_pu.max()) if len(good) else None,
            "max_transformer_pct": float(good.max_trafo_pct.max()) if len(good) else None,
            "max_line_pct": float(good.max_line_pct.max()) if len(good) else None,
            "sample_losses_kw_sum_NOT_ANNUAL": float(good.loss_kw.sum()) if len(good) else None})
    return result


def diagnostic_plots(frame, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path.mkdir(exist_ok=False)
    names = []
    for col, ylabel, filename, limit in (
        ("min_v_pu", "Minimum household voltage (pu)", "sampled_voltage.png", .95),
        ("max_trafo_pct", "Transformer loading (%)", "sampled_transformer.png", 100.)):
        fig, ax = plt.subplots(figsize=(11, 5))
        for (a, o, op), v in frame.groupby(
                ["assignment", "hardware_origin", "operation"], sort=True):
            if v.status.eq("CONVERGED").sum() == 0:
                continue
            v = v.sort_values("timestamp_lst")
            valid = v.status.eq("CONVERGED")
            ax.plot(pd.to_datetime(v.loc[valid, "timestamp_lst"]), v.loc[valid, col],
                    marker=".", linewidth=1, label=a + "/" + o + "/" + op)
        ax.axhline(limit, linewidth=.8, linestyle="--", label="Research screen")
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Selected 2025 local timestamps (noncontiguous)")
        ax.set_title("113699 bounded A0/A1 AC, PF .98, length factor 1.0")
        ax.grid(alpha=.3)
        ax.legend(fontsize=7, ncol=2)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(path / filename, dpi=160)
        plt.close(fig)
        names.append(filename)
    return names


def pilot(repo, out=None, preflight_only=False):
    repo = Path(repo).resolve()
    v6, cases, geo, hours, reasons, receipt = preflight(repo)
    if preflight_only:
        return receipt
    import pandapower as pp
    folder = choose_out(repo, out)
    folder.mkdir(parents=True)
    manifest_file = folder / "RUN_MANIFEST.json"
    manifest = dict(receipt, status="INCOMPLETE_113699_BOUNDED_AC",
                    new_powerflow_solves=0, output_folder=str(folder))
    manifest_file.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n",
                             encoding="utf-8")
    try:
        rows = []
        for assignment in ASSIGNMENTS:
            terr, net, meta, _evidence = geo[assignment]
            source_trace = cases["A0_hardware_on_" + assignment]["trace"]
            for ts in hours:
                raw = v6.solve_ac_hour(net, meta, terr, ts, source_trace.loc[ts],
                    .98, 0., 0., 0., 0., 9, "gross", pp)
                rows.append({"assignment": assignment, "hardware_origin": "NONE",
                             "operation": "load_only", "timestamp_lst": str(ts),
                             "hour_selection": ";".join(reasons[str(ts)]), **raw})
            for origin in ASSIGNMENTS:
                case = cases[origin + "_hardware_on_" + assignment]
                for name, ratio in (("q_off", 0.), ("daylight_q025", .25)):
                    for ts in hours:
                        hour = case["energy"].loc[ts]
                        raw = v6.solve_ac_hour(net, meta, terr, ts, case["trace"].loc[ts],
                            .98, float(hour.inverter_ac_kw),
                            float(case["hardware"]["inverter_kva"]),
                            float(hour.pv_dc_available_kw), ratio, 9, "pvbess", pp)
                        rows.append({
                            "assignment": assignment, "hardware_origin": origin,
                            "operation": name, "timestamp_lst": str(ts),
                            "hour_selection": ";".join(reasons[str(ts)]),
                            "energy_case_key": case["key"],
                            "source_energy_sha256": case["source_csv_sha256"], **raw})
                    print("Completed bounded AC", assignment, origin, name, flush=True)
        frame = pd.DataFrame(rows)
        if (len(frame) != receipt["expected_powerflow_cases"]
            or frame.duplicated(["assignment", "hardware_origin", "operation",
                                  "timestamp_lst"]).any()):
            raise ValueError("Expected selected-hour scenario combinations not saved")
        csv = folder / "BOUNDED_AC_HOURLY.csv"
        frame.to_csv(csv, index=False, float_format="%.10f")
        manifest["ac_csv_sha256"] = sha(csv)
        manifest["sampled_case_summaries"] = summaries(frame, len(hours))
        figures = diagnostic_plots(frame, folder / "figures_diagnostic")
        manifest["diagnostic_png_sha256"] = {
            f: sha(folder / "figures_diagnostic" / f) for f in figures}
        manifest["new_powerflow_solves"] = len(frame)
        manifest["converged_case_hours"] = int(frame.status.eq("CONVERGED").sum())
        manifest["nonconverged_case_hours"] = int(frame.status.ne("CONVERGED").sum())
        manifest["sampled_infeasible_case_hours"] = int(
            (frame.status.eq("CONVERGED") & frame.ac_feasible.eq(False)).sum())
        manifest["status"] = (
            "BOUNDED_AC_NONCONVERGENCE_RECORDED_ANNUAL_PENDING"
            if manifest["nonconverged_case_hours"] else
            "BOUNDED_AC_VIOLATIONS_RECORDED_ANNUAL_PENDING"
            if manifest["sampled_infeasible_case_hours"] else
            "BOUNDED_AC_NO_SAMPLED_VIOLATIONS_ANNUAL_PENDING")
        manifest["annual_AC_feasible"] = False
        manifest_file.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n",
                                 encoding="utf-8")
        return {"status": manifest["status"], "output": str(folder),
                "sampled_hours": len(hours), "powerflow_cases": len(frame),
                "nonconverged": manifest["nonconverged_case_hours"],
                "sampled_infeasible": manifest["sampled_infeasible_case_hours"],
                "annual_AC_feasible": False}
    except Exception as exc:
        manifest["status"] = "INCOMPLETE_AC_DIAGNOSTIC_DO_NOT_CLAIM"
        manifest["error"] = {"type": type(exc).__name__, "message": str(exc),
                             "traceback": traceback.format_exc()}
        manifest_file.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n",
                                 encoding="utf-8")
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    print(json.dumps(pilot(args.repo_root, args.out, args.preflight_only),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
