#!/usr/bin/env python3
"""A1 106039: source-verified evening BESS reserve trial for 3 NEW hardware cases.

The original 8760-hour PyPSA fixed-hardware energy schedules and annual
pandapower stress replays are read-only. Re-solve ONLY altered hours in the
original v6.2 pandapower network at PF=.95, service factor=1.6. This is a
stress-only experiment, never a nine-factor or field feasibility certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback

import numpy as np
import pandas as pd

CASES = ("MC_B10", "SS_B10", "SS_P45_B9")
# Exact source-specific proposals, not copied AC outcomes from another design.
PLAN = {
    "MC_B10": (
        ("2025-10-13 17:00:00", "2025-10-13 20:00:00", 0.60),
        ("2025-11-27 18:00:00", "2025-11-27 20:00:00", 0.80)),
    "SS_B10": (("2025-11-27 18:00:00", "2025-11-27 20:00:00", 0.80),),
    "SS_P45_B9": (("2025-11-27 18:00:00", "2025-11-27 20:00:00", 0.80),),
}
KNOWN_BASELINE_FAILURES = {
    "MC_B10": {"2025-10-13 20:00:00", "2025-11-27 20:00:00"},
    "SS_B10": {"2025-11-27 20:00:00"},
    "SS_P45_B9": {"2025-11-27 20:00:00"},
}
ENERGY_DIR = Path("StudyA_A1_106039_Utilization_v1")
STRESS_DIR = Path("StudyA_A1_106039_NewHardware_AC_Stress_v1")
FRONTIER_MODULE = Path("case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17/validate_frontier_ac.py")
B9_MODULE = Path("case1/studies/SEEDExchange_StudyA_B9_SOC_Trial_v1/b9_soc_trial.py")
ETA_INV = 0.95
ETA_BAT = math.sqrt(0.95)
PF = 0.95
LENGTH_FACTOR = 1.6
PF_GRID_PROXY = 5.0
AC_COMPARE_TOL = 2e-4

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for data in iter(lambda: f.read(1 << 20), b""):
            h.update(data)
    return h.hexdigest()

def verify_signed_text(path, expected):
    """Allow only exact bytes or original CRLF SHA recreated from Git LF text."""
    path=Path(path)
    raw=path.read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    if actual==expected:
        return "EXACT_SIGNED_BYTES"
    if b"\r" not in raw and b"\n" in raw:
        if hashlib.sha256(raw.replace(b"\n",b"\r\n")).hexdigest()==expected:
            return "GIT_LF_RECONSTRUCTS_SIGNED_CRLF"
    raise ValueError("Signed source bytes differ: "+str(path)+
                     " expected="+str(expected)+" actual="+actual)

def load_module(label, file):
    spec = importlib.util.spec_from_file_location(label, file)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def move_one(frame, donor, target, amount, bank_kw, inverter_kva):
    """Pure energy redistribution. Full annual SOC/AC gates run separately."""
    a = frame.copy(deep=True)
    donor, target = pd.Timestamp(donor), pd.Timestamp(target)
    amount = float(amount)
    if donor not in a.index or target not in a.index or donor >= target:
        raise ValueError("Donor and target must be present, ordered timestamps")
    if donor.date() != target.date() or amount <= 0:
        raise ValueError("Transfers must be positive and within one local day")
    if float(a.at[donor, "battery_discharge_dc_kw"]) < amount - 1e-6:
        raise ValueError("Insufficient donor battery discharge")
    if (float(a.at[target, "battery_charge_dc_kw"]) > 1e-7 or
        float(a.at[target, "pv_dc_available_kw"]) > 1e-7):
        raise ValueError("Target must have no PV availability or battery charging")
    if float(a.at[target, "grid_import_kw"]) < ETA_INV * amount - 1e-6:
        raise ValueError("Target would export")
    if float(a.at[target, "battery_discharge_dc_kw"]) + amount > bank_kw + 1e-6:
        raise ValueError("Bank discharge power exceeded")
    if float(a.at[target, "inverter_ac_kw"]) + ETA_INV * amount > inverter_kva + 1e-6:
        raise ValueError("Inverter power exceeded")
    if float(a.at[donor, "inverter_ac_kw"]) < ETA_INV * amount - 1e-6:
        raise ValueError("Donor inverter injection unavailable")
    a.at[donor, "battery_discharge_dc_kw"] -= amount
    a.at[target, "battery_discharge_dc_kw"] += amount
    a.at[donor, "inverter_ac_kw"] -= ETA_INV * amount
    a.at[target, "inverter_ac_kw"] += ETA_INV * amount
    a.at[donor, "grid_import_kw"] += ETA_INV * amount
    a.at[target, "grid_import_kw"] -= ETA_INV * amount
    a.loc[(a.index >= donor) & (a.index < target), "battery_soc_usable_kwh"] += amount / ETA_BAT
    if {"pcc_p_kw", "pcc_q_kvar_proxy", "pcc_kva_proxy"}.issubset(a.columns):
        for t in (donor, target):
            a.at[t, "pcc_p_kw"] = a.at[t, "grid_import_kw"] - a.at[t, "grid_export_kw"]
            a.at[t, "pcc_kva_proxy"] = math.hypot(
                float(a.at[t, "pcc_p_kw"]), float(a.at[t, "pcc_q_kvar_proxy"]))
    return a

def verify_candidate(base, trial, hardware, b9):
    """Recheck manufacturer-SOC, annual cycles, power and protected series."""
    old = b9.check_dispatch(base, hardware)
    new = b9.check_dispatch(trial, hardware)
    for key in ("annual_grid_import_kwh", "annual_discharge_dc_kwh", "year_end_usable_soc_kwh"):
        if abs(old[key] - new[key]) > 5e-5:
            raise ValueError("Changed annual throughput, purchase or terminal SOC: "+key)
    for key in ("demand_kw", "pv_dc_available_kw", "pv_dc_generated_kw",
                "battery_charge_dc_kw", "curtailed_pv_dc_kw", "grid_export_kw", "unserved_kw"):
        if not np.allclose(base[key].to_numpy(), trial[key].to_numpy(), atol=1e-9, rtol=0):
            raise ValueError("Protected power series changed: "+key)
    ch, dis = trial.battery_charge_dc_kw, trial.battery_discharge_dc_kw
    if ((ch > 1e-6) & (dis > 1e-6)).any():
        raise ValueError("Simultaneous battery charge and discharge")
    if "pcc_kva_proxy" not in trial.columns or trial.pcc_kva_proxy.max() > PF_GRID_PROXY + 1e-5:
        raise ValueError("5 kVA source dispatch proxy exceeded")
    if not np.allclose(trial.pcc_kva_proxy.to_numpy(),
                       np.hypot(trial.pcc_p_kw, trial.pcc_q_kvar_proxy),
                       atol=1e-5, rtol=0):
        raise ValueError("PCC apparent-power proxy no longer matches P and Q")
    return {"original": old, "candidate": new,
            "max_pcc_kva_proxy": float(trial.pcc_kva_proxy.max())}

def check_source_ac(repo, frontier, b9, st, ctx, case, df, manifest_sha):
    """Check the exact original full-year AC source for the same hardware."""
    folder = repo / STRESS_DIR / f"{case}_pf095_l16"
    provenance = {
        "case_id":case, "scenario":"A1", "transformer":"106039",
        "pf":PF, "length_factor":LENGTH_FACTOR, "2025_hours":8760,
        "new_energy_manifest_sha256":manifest_sha,
        "source_v6_2_sha256":frontier.sha(repo / st.RUNNER_REL),
        "input_manifest_sha256":frontier.sha(ctx["mp"]),
        "q_ratio_daylight":0.25, "night_q_disabled":True,
        "method":"independent_hourly_balanced_pandapower_replay"}
    record = frontier.check_saved(folder, provenance)
    if record is None:
        raise FileNotFoundError("Missing signed 8760h original AC stress source: "+str(folder))
    ac = pd.read_csv(frontier.xp(folder/"ac_hourly.csv"),
                     parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    if not ac.index.equals(df.index) or len(ac) != 8760:
        raise ValueError("AC and dispatch timebase differ: "+case)
    if not np.allclose(ac.inverter_ac_kw, df.inverter_ac_kw, atol=5e-6, rtol=0):
        raise ValueError("Original AC inverter mismatch: "+case)
    if not np.allclose(ac.gross_demand_kw, ctx["trace"].sum(axis=1), atol=5e-6, rtol=0):
        raise ValueError("Original AC household demand mismatch: "+case)
    valid = b9.validated_ac_mask(frontier, ac)
    observed = set(ac.index[~valid].strftime("%Y-%m-%d %H:%M:%S"))
    if observed != KNOWN_BASELINE_FAILURES[case]:
        raise ValueError(f"Unexpected AC failure hours for {case}: {observed}")
    return ac, record

def preflight(repo):
    """All source gates must pass before any output folder is created."""
    repo = Path(repo).resolve()
    frontier = load_module("nh_frontier", repo / FRONTIER_MODULE)
    b9 = load_module("nh_b9", repo / B9_MODULE)
    st, ctx = frontier.make_context(repo)
    all_cases = {}
    for case in CASES:
        df, man, raw_energy_manifest_sha = frontier.signed_energy(
            repo, repo / ENERGY_DIR, case, st, ctx)
        archived_ac_metadata = json.loads((
            repo / STRESS_DIR / f"{case}_pf095_l16" / "ac_summary.json"
        ).read_text(encoding="utf-8"))
        energy_manifest_sha = archived_ac_metadata["new_energy_manifest_sha256"]
        source_hash_mode = verify_signed_text(
            repo / ENERGY_DIR / ("energy_"+case) / "energy_manifest.json",
            energy_manifest_sha)
        baseline, ac_record = check_source_ac(
            repo, frontier, b9, st, ctx, case, df, energy_manifest_sha)
        trial = df.copy(deep=True)
        for donor, target, amount in PLAN[case]:
            trial = move_one(trial, donor, target, amount,
                             float(man["hardware"]["battery_power_dc_kw"]),
                             float(man["hardware"]["inverter_kva"]))
        gates = verify_candidate(df, trial, man["hardware"], b9)
        changed = np.flatnonzero(np.abs(df.inverter_ac_kw.to_numpy() -
                                       trial.inverter_ac_kw.to_numpy()) > 1e-7).tolist()
        expected = {df.index.get_loc(pd.Timestamp(t)) for donor, target, _ in PLAN[case]
                    for t in (donor, target)}
        if set(changed) != expected or len(changed) != 2 * len(PLAN[case]):
            raise ValueError("Candidate changed unexpected inverter hour(s): "+case)
        all_cases[case] = {
            "original":df, "candidate":trial, "original_ac":baseline,
            "energy_manifest":man, "energy_manifest_sha256":energy_manifest_sha,
            "energy_manifest_checkout_sha256":raw_energy_manifest_sha,
            "energy_manifest_hash_mode":source_hash_mode,
            "ac_manifest":ac_record, "gates":gates, "changed":changed}
    receipt = {
        "status":"SIGNED_SOURCES_AND_ANNUAL_ENERGY_PREFLIGHT_PASS_NO_NEW_AC",
        "case_count":len(all_cases), "cases":{},
        "network":"A1 106039 provisional balanced EPM, assumed 5 kVA",
        "year":2025, "hours_per_case":8760,
        "stress_factor":{"pf":PF, "length_factor":LENGTH_FACTOR},
        "all_nine_factors_tested":False,
        "provenance":"Original signed PyPSA + independent historical 8760h AC, no new solver yet"}
    for case, d in all_cases.items():
        receipt["cases"][case] = {
            "hardware":d["energy_manifest"]["hardware"],
            "source_energy_manifest_sha256":d["energy_manifest_sha256"],
            "source_energy_checkout_sha256":d["energy_manifest_checkout_sha256"],
            "source_energy_manifest_hash_mode":d["energy_manifest_hash_mode"],
            "source_ac_hourly_sha256":d["ac_manifest"]["ac_hourly_sha256"],
            "original_infeasible_hours":len(KNOWN_BASELINE_FAILURES[case]),
            "exact_plan":[list(x) for x in PLAN[case]],
            "changed_hour_count":len(d["changed"]),
            "energy_gates":d["gates"]}
    return frontier, b9, st, ctx, all_cases, receipt

def check_replayed_old(prior, observed, case, timestamp):
    if observed.get("status") != "CONVERGED" or not bool(observed.get("ac_feasible")) == bool(prior["ac_feasible"]):
        raise ValueError(f"Original AC status mismatch: {case} {timestamp}")
    for metric in ("min_v_pu", "max_v_pu", "max_trafo_pct",
                   "max_line_pct", "pcc_kva", "loss_kw"):
        if not np.isfinite(float(observed[metric])) or abs(
                float(observed[metric]) - float(prior[metric])) > AC_COMPARE_TOL:
            raise ValueError(f"Original AC reproduction differs at {case}/{timestamp}/{metric}")

def solve_stress(repo, frontier, b9, ctx, cases, report, out):
    ctx["v6"].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    good = True
    out.mkdir(parents=True, exist_ok=False)
    (out/"figures"/"audit").mkdir(parents=True)
    for case, d in cases.items():
        try:
            territory = ctx["v6"].new_territory(repo, "A1", "106039", ctx["houses"], LENGTH_FACTOR)
            net, nodes = build_net(territory, "head")
            if set(nodes["loads"]) != set(ctx["houses"]):
                raise ValueError("A1 GIS household nodes differ")
            original_ac = d["original_ac"]
            corrected_ac = original_ac.copy(deep=True)
            changed_rows = []
            for index in d["changed"]:
                timestamp = d["original"].index[index]
                records = {}
                for label, frame in (("original",d["original"]),("candidate",d["candidate"])):
                    record = ctx["v6"].solve_ac_hour(
                        net, nodes, territory, timestamp, ctx["trace"].loc[timestamp],
                        PF, float(frame.at[timestamp,"inverter_ac_kw"]),
                        float(d["energy_manifest"]["hardware"]["inverter_kva"]),
                        float(frame.at[timestamp,"pv_dc_available_kw"]), .25, 9, "pvbess", pp)
                    if record["status"] != "CONVERGED":
                        raise RuntimeError(f"AC did not converge: {case} {timestamp} {label}")
                    records[label] = record
                    if label == "original":
                        check_replayed_old(original_ac.loc[timestamp], record, case, timestamp)
                    else:
                        b9.overlay_ac_hour(corrected_ac, timestamp, record)
                changed_rows.append({
                    "case_id":case, "timestamp_lst":str(timestamp),
                    "old_inverter_kw":float(d["original"].at[timestamp,"inverter_ac_kw"]),
                    "new_inverter_kw":float(d["candidate"].at[timestamp,"inverter_ac_kw"]),
                    "old_trafo_pct":float(records["original"]["max_trafo_pct"]),
                    "new_trafo_pct":float(records["candidate"]["max_trafo_pct"]),
                    "old_min_v_pu":float(records["original"]["min_v_pu"]),
                    "new_min_v_pu":float(records["candidate"]["min_v_pu"]),
                    "old_ac_feasible":bool(records["original"]["ac_feasible"]),
                    "new_ac_feasible":bool(records["candidate"]["ac_feasible"]),
                    "old_loss_kw":float(records["original"]["loss_kw"]),
                    "new_loss_kw":float(records["candidate"]["loss_kw"])})
            valid = b9.validated_ac_mask(frontier, corrected_ac)
            bad = list(corrected_ac.index[~valid].strftime("%Y-%m-%d %H:%M:%S"))
            if len(changed_rows) != len(d["changed"]) or len(corrected_ac)!=8760:
                raise ValueError("Missing changed-hour or annual AC row")
            if not np.isfinite(corrected_ac[["min_v_pu","max_v_pu","max_trafo_pct","loss_kw"]].to_numpy(float)).all():
                raise ValueError("Nonfinite corrected AC metrics")
            cdir = out/case
            cdir.mkdir()
            ac_path = cdir/"CHANGED_HOUR_AC.csv"
            energy_path = cdir/"CANDIDATE_ENERGY_8760.csv"
            pd.DataFrame(changed_rows).to_csv(ac_path,index=False,float_format="%.10f")
            d["candidate"].to_csv(energy_path,index_label="timestamp_lst",float_format="%.10f")
            result = {
                "status":"STRESS_PASS_ONLY_ALL_NINE_PENDING" if not bad else "STRESS_FAILED_RETAIN_EVIDENCE",
                "baseline_bad_hours":len(KNOWN_BASELINE_FAILURES[case]),
                "corrected_bad_hours":len(bad),
                "failed_timestamps":bad,
                "corrected_min_v_pu":float(corrected_ac.min_v_pu.min()),
                "corrected_max_trafo_pct":float(corrected_ac.max_trafo_pct.max()),
                "corrected_max_line_pct":float(corrected_ac.max_line_pct.max()),
                "stage1_ac_losses_kwh":float(original_ac.loss_kw.sum()),
                "corrected_ac_losses_kwh":float(corrected_ac.loss_kw.sum()),
                "changed_hour_ac_calls":2 * len(changed_rows),
                "changed_hour_csv":str(ac_path.relative_to(out)),
                "changed_hour_sha256":sha(ac_path),
                "candidate_energy_csv":str(energy_path.relative_to(out)),
                "candidate_energy_sha256":sha(energy_path),
                "source_original_ac_sha256":d["ac_manifest"]["ac_hourly_sha256"]}
            report["cases"][case]["stress_result"] = result
            if bad:
                good=False
            # Visualization is supporting evidence; never turn a successful AC case
            # into a false failure due to a matplotlib/backend error.
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                fig,ax=plt.subplots(figsize=(10,4))
                labels=[r["timestamp_lst"][5:16] for r in changed_rows]
                x=np.arange(len(labels));width=.36
                ax.bar(x-width/2,[r["old_trafo_pct"] for r in changed_rows],width,label="Original")
                ax.bar(x+width/2,[r["new_trafo_pct"] for r in changed_rows],width,label="Corrected")
                ax.axhline(100,linewidth=1,color="black",linestyle="--",label="100% transformer")
                ax.set_xticks(x,labels,rotation=30,ha="right")
                ax.set_ylabel("Transformer loading (%)")
                ax.set_title(case+" | A1 106039 | PF 0.95, length x1.6")
                ax.legend();fig.tight_layout()
                fig.savefig(out/"figures"/"audit"/(case+"_changed_hour_trafo.png"),dpi=160)
                plt.close(fig)
            except Exception as exc:
                report.setdefault("plot_errors",{})[case]=str(exc)
        except Exception as exc:
            good=False
            report.setdefault("errors",{})[case] = {
                "type":type(exc).__name__, "message":str(exc), "traceback":traceback.format_exc()}
        (out/"RUN_MANIFEST.json").write_text(
            json.dumps(report,indent=2,allow_nan=False,default=str)+"\n",encoding="utf-8")
    report["status"] = ("STRESS_PASS_ONLY_ALL_NINE_PENDING"
                        if good and not report.get("errors")
                        else "STRESS_FAILED_RETAIN_EVIDENCE")
    (out/"RUN_MANIFEST.json").write_text(
        json.dumps(report,indent=2,allow_nan=False,default=str)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path.cwd())
    parser.add_argument("--preflight-only",action="store_true")
    parser.add_argument("--out",type=Path,help="Optional. A new unused result folder is chosen.")
    args=parser.parse_args(argv)
    repo=args.repo_root.resolve()
    frontier,b9,st,ctx,cases,report=preflight(repo)
    if args.preflight_only:
        print(json.dumps(report,indent=2,allow_nan=False,default=str))
        return
    if args.out is None:
        stem="StudyA_A1_106039_NewHardware_Reserve_Stress_v"
        out=next((repo/(stem+str(i)) for i in range(1,1000)
                  if not (repo/(stem+str(i))).exists()),None)
        if out is None:raise FileExistsError("No unused output folder")
    else:
        out=args.out.resolve()
    if out.exists():
        raise FileExistsError("Refusing to overwrite: "+str(out))
    report["output_folder"]=str(out)
    report["status"]="STRESS_IN_PROGRESS"
    report=solve_stress(repo,frontier,b9,ctx,cases,report,out)
    print(json.dumps({"status":report["status"],"output_folder":str(out),
                      "cases":{k:v.get("stress_result",{}) for k,v in report["cases"].items()},
                      "errors":report.get("errors",{})},indent=2,allow_nan=False))
    if report["status"]!="STRESS_PASS_ONLY_ALL_NINE_PENDING":
        raise SystemExit(2)

if __name__=="__main__":
    main()
