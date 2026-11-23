#!/usr/bin/env python3
"""A0 106039 optimized 2025 SOC shift: targeted independently re-solved AC P/Q.

Only changed 39 hourly setpoints, or the two PV-daylight hours as a pilot.
Verifies frozen model, GIS, per-house demands, signed original annual AC source,
saved SOC-neutral candidate schedule and old compact changed-hour AC results.
No PyPSA solve, no 8,760-hour power-flow rerun, and no original file overwrites.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import matched16_original_ac_input_preflight as base
import matched16_four_family_input_gate as family

CASE = "A0_106039_min_cost_ref"
RECIPROCAL = "A1_106039_min_cost_to_A0"
TRIAL = Path("StudyA_A0_106039_Sequenced_Trial_v1")
PVBESS = Path("case1/studies/SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py")
OUTPUT = "StudyA_A0_106039_ChangedHour_PQ_Audit_v"
TOL = 2e-4
INPUT_TOL = 1e-6
RESULT_COLS = ("timestamp_lst", "pf", "length_factor", "point",
    "gross_demand_kw", "inverter_ac_kw", "pv_dc_available_kw",
    "load_pf", "night_reactive_disabled", "status", "ac_feasible",
    "q_selected_kvar", "q_requested_kvar", "q_controller_status",
    "ac_evaluations", "min_v_pu", "max_v_pu", "max_trafo_pct",
    "max_line_pct", "loss_kw", "pcc_kva",
    "archived_compact_max_trafo_pct",
    "archived_compact_min_v_pu", "comparison_pass")


def check_near(a, b, tolerance=TOL, label="value"):
    x, y = float(a), float(b)
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("Nonfinite comparison " + label)
    return abs(x-y) <= tolerance


def compare_result(new, old, columns, tol=TOL):
    """Numerical regression against original annual or saved changed-hour AC."""
    if new["status"] != "CONVERGED" or str(old.get("ac_feasible")) not in ("True", "true", "1"):
        return False
    for col in columns:
        if not check_near(new[col], old[col], tol, col):
            return False
    return True


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError("Required original module absent: " + str(path))
    import sys
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


def load_evidence(repo):
    """Strict original source, candidate and source-source coverage checks."""
    frozen = base.read_json(repo / base.SOURCE_MANIFEST)
    case = frozen["completed_cases"][RECIPROCAL]
    v1 = base.read_json(repo / "StudyA_Matched16_OriginalAC_InputPreflight_v1/RUN_MANIFEST.json")
    base.signed_bytes(repo/"StudyA_Matched16_OriginalAC_InputPreflight_v1/CASE_INPUT_GATE.csv",
                      v1["case_gate_csv_sha256"])
    if v1["original_AC_candidate_cases"] != 2 or case["assignment_for_load"] != "A0":
        raise ValueError("Original v1 source selection changed")
    raw = repo / base.ARCHIVED / ("energy_"+CASE)
    energy_meta = base.read_json(raw/"energy_manifest.json")
    source_sha = energy_meta["energy_csv_sha256"]
    if (source_sha != case["target_energy_sha256"]
        or energy_meta["selected_house_ids"] != case["target_house_ids"]
        or not base.same_hardware(energy_meta["hardware"],case["hardware"])):
        raise ValueError("Signed target source equipment/cohort changed")
    base.signed_bytes(raw/"energy_hourly_2025.csv",source_sha)
    source = base.read_csv(raw/"energy_hourly_2025.csv")
    base.validate_year(source, base.ENERGY_KEYS)
    trial = base.read_json(repo / TRIAL / "TRIAL_MANIFEST.json")
    entry = [x for x in trial["candidate_files"]
             if x["case"] == CASE and x["dispatch"] == "optimized"]
    if (len(entry)!=1 or entry[0]["input_energy_sha256"]!=source_sha
        or trial["status"]!="ALL_SELECTED_A0_PILOT_GROUPS_PASSED"):
        raise ValueError("A0 shift trial identity/source signature mismatch")
    candidate_path = repo/TRIAL/entry[0]["candidate_file"]
    base.signed_bytes(candidate_path,entry[0]["sha256"])
    candidate = base.read_csv(candidate_path)
    changes, delta_sum = family.annual_deltas(source,candidate)
    if len(changes)!=39 or abs(delta_sum)>1e-4:
        raise ValueError("Unexpected original 39-hour changed P schedule")
    detail_path=repo/TRIAL/"CHANGED_HOURS_FINAL_AC.csv"
    compact = base.read_csv(detail_path)
    original_compact=[r for r in compact if r["case"]==CASE
                      and r["dispatch"]=="optimized"]
    if family.factor_coverage(original_compact,changes)!=351:
        raise ValueError("Original saved AC compact coverage incomplete")
    lookup = {(float(r["pf"]),float(r["length_factor"]),r["timestamp_lst"]):r
              for r in original_compact}
    info={"source_energy_sha256":source_sha,
          "candidate_annual_energy_sha256":entry[0]["sha256"],
          "archived_compact_ac_sha256":hashlib.sha256(base.required_file(detail_path).read_bytes()).hexdigest(),
          "source_energy_manifest_sha256":hashlib.sha256(base.required_file(raw/"energy_manifest.json").read_bytes()).hexdigest(),
          "original_source_input_manifest_sha256":base.INPUT_SHA,
          "source_v1_expected_candidates":2,
          "changed_P_hours":39,
          "annual_inverter_P_delta_kwh":delta_sum}
    return source, candidate, changes, lookup, energy_meta, info


def choose_hours(source, changed, scope):
    by_time={x["timestamp_lst"]:x for x in source}
    if scope=="all":
        return changed
    hours=[ts for ts in changed if float(by_time[ts]["pv_dc_available_kw"])>1e-9]
    if len(hours)!=2:
        raise ValueError("Expected two daylight-eligible corrected hours, found "
                         +str(len(hours)))
    return hours


def verify_original_ac_source(repo, pf, length, trace, source, signed_ids,
                              energy_manifest_sha):
    name=(f"{CASE}_mapped_optimized_pf{round(pf*100):03d}_"
          f"length{round(length*10):02d}_annual8760")
    directory=repo/base.ARCHIVED/"annual_ac_replays_v1"/name
    summary=base.read_json(directory/"ac_summary.json")
    if (summary["status"]!="ANNUAL_PVBESS_AC"
        or summary["scenario"]!="A0" or str(summary["transformer"])!="106039"
        or summary["topology"]!="mapped" or summary["dispatch"]!="optimized"
        or summary["selected_house_ids"]!=signed_ids
        or summary["input_manifest_sha256"]!=base.INPUT_SHA
        or summary["energy_manifest_sha256"]!=energy_manifest_sha
        or summary["hours"]!=8760 or summary["converged_hours"]!=8760
        or not check_near(summary["pf"],pf,1e-9)
        or not check_near(summary["length_factor"],length,1e-9)
        or not check_near(summary["q_ratio_daylight"],.25,1e-9)
        or summary["night_q_disabled"] is not True):
        raise ValueError("Original AC source identity/factor/provenance changed: "+name)
    path=directory/"ac_hourly.csv"
    base.signed_bytes(path,summary["ac_hourly_sha256"])
    annual=base.read_csv(path)
    base.validate_year(annual,base.AC_KEYS)
    if any(x["status"]!="CONVERGED" for x in annual):
        raise ValueError("Original AC source contains nonconverged hours")
    return {r["timestamp_lst"]:r for r in annual},summary["ac_hourly_sha256"]


def run(repo, scope, dry_run=False):
    source,candidate,changed,compact,energy_meta,info=load_evidence(repo)
    selected=choose_hours(source,changed,scope)
    if dry_run:
        return {"status":"SIGNED_PRECHECK_ONLY_NO_AC_SOLVES",**info,
                "scope":scope,"selected_hours":selected,
                "pf_length_factor_count":9,
                "expected_new_AC_replays":len(selected)*9*2,
                "field_verified":False},[]
    # The original source verifies Python, geographic model, 2025 mapping
    # and reference load profiles against the signed frozen v6.2 manifest.
    mod=load_module(repo/PVBESS,"a0_changed_pq_original_pvbess")
    mp=repo/mod.MANIFEST_REL
    ctx=mod.secure_context(repo,mp)
    m,v6,mapping,profiles=ctx
    ids,trace=mod.source_trace(m,mapping,profiles,"A0","106039")
    if ids!=energy_meta["selected_house_ids"]:
        raise ValueError("Frozen spatial household membership differs")
    source_by_time={x["timestamp_lst"]:x for x in source}
    candidate_by_time={x["timestamp_lst"]:x for x in candidate}
    import pandas as pd
    for ts in selected:
        stamp=pd.Timestamp(ts)
        if abs(float(trace.loc[stamp].sum())-float(source_by_time[ts]["demand_kw"]))>1e-6:
            raise ValueError("Spatial household loads differ from signed annual input")
    v6.repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    rows=[]
    bad=[]
    reports={}
    for length in (1.,1.3,1.6):
        terr=v6.new_territory(repo,"A0","106039",ids,length)
        net,node=build_net(terr,"head")
        if set(node["loads"])!=set(ids):
            raise ValueError("Grid model missing a signed household")
        for pf in (.95,.98,1.):
            original_ac,archive_sha=verify_original_ac_source(
                repo,pf,length,trace,source,ids,info["source_energy_manifest_sha256"])
            reports[f"pf{pf:.2f}_length{length:.1f}"]=archive_sha
            for ts in selected:
                stamp=pd.Timestamp(ts)
                s=source_by_time[ts]
                c=candidate_by_time[ts]
                old=original_ac[ts]
                compact_row=compact[(pf,length,ts)]
                for point,energy in (("original",s),("corrected",c)):
                    rec=v6.solve_ac_hour(net,node,terr,stamp,trace.loc[stamp],pf,
                        float(energy["inverter_ac_kw"]),float(energy_meta["hardware"]["inverter_kva"]),
                        float(energy["pv_dc_available_kw"]),.25,9,"pvbess",pp)
                    row={"timestamp_lst":ts,"pf":pf,"length_factor":length,"point":point,
                         "pv_dc_available_kw":float(energy["pv_dc_available_kw"]),
                         **rec,
                         "archived_compact_max_trafo_pct":None,
                         "archived_compact_min_v_pu":None}
                    if point=="original":
                        passed=compare_result(rec,old,
                            ("inverter_ac_kw","gross_demand_kw","q_selected_kvar",
                             "min_v_pu","max_v_pu","max_trafo_pct",
                             "max_line_pct","loss_kw","pcc_kva"))
                        if str(rec["ac_feasible"]).lower()!=old["ac_feasible"].lower():
                            passed=False
                    else:
                        row["archived_compact_max_trafo_pct"]=float(compact_row["max_trafo_pct"])
                        row["archived_compact_min_v_pu"]=float(compact_row["min_v_pu"])
                        passed=compare_result(rec,compact_row,("max_trafo_pct","min_v_pu"))
                        if rec["ac_feasible"] is not True:
                            passed=False
                    row["comparison_pass"]=bool(passed)
                    if not passed:
                        bad.append({"pf":pf,"length":length,"timestamp":ts,
                                    "point":point,"reported_status":rec["status"]})
                    rows.append(row)
            print(f"A0 106039 P/Q replays: PF={pf} length={length} {len(selected)*2} solved",flush=True)
    info.update({"scope":scope,"selected_2025_hours":selected,"selected_hours":len(selected),
        "factor_count":9,"AC_replays_executed":len(rows),
        "AC_baseline_replays":len(rows)//2,"AC_corrected_replays":len(rows)//2,
        "source_AC_sha_by_factor":reports,"failed_comparisons":bad,
        "baseline_reproduction_pass":not any(x["point"]=="original" for x in bad),
        "corrected_compact_reproduction_pass":not any(x["point"]=="corrected" for x in bad),
        "corrected_Q_selected_nonzero_rows":sum(
           abs(float(x["q_selected_kvar"]))>1e-8
           for x in rows if x["point"]=="corrected" and x["q_selected_kvar"] is not None),
        "status":"A0_CHANGED_HOUR_PQ_REPLAY_PASS" if not bad else
                 "A0_CHANGED_HOUR_PQ_REPLAY_CONFLICT",
        "field_verified":False,"source_model":"FROZEN_V6_2_STATELESS_AC",
        "claimed_certified_annual_AC_reuse_hours":0,
        "source_hourly_inputs_only":False})
    return info, rows


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--scope",choices=("daylight","all"),default="daylight")
    ap.add_argument("--preflight",action="store_true")
    args=ap.parse_args(argv)
    repo=args.repo_root.resolve()
    result,rows=run(repo,args.scope,args.preflight)
    if args.preflight:
        print(json.dumps(result,indent=2))
        return 0
    dest=next((repo/(OUTPUT+str(i)) for i in range(1,1000)
               if not (repo/(OUTPUT+str(i))).exists()),None)
    if dest is None:
        raise ValueError("No new output version available")
    dest.mkdir(parents=False)
    csvfile=dest/"REPLAY_PQ_AUDIT.csv"
    with csvfile.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=RESULT_COLS,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    result["replay_csv_sha256"]=hashlib.sha256(csvfile.read_bytes()).hexdigest()
    (dest/"RUN_MANIFEST.json").write_text(
         json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"output":str(dest),
        "selected_changed_hours":result["selected_hours"],
        "ac_replays":result["AC_replays_executed"],
        "comparison_failures":len(result["failed_comparisons"]),
        "corrected_Q_nonzero_factor_hours":result["corrected_Q_selected_nonzero_rows"],
        "field_verified":False},indent=2))
    # Save all explicit disagreement evidence before returning a failed exit code.
    return 0 if result["status"]=="A0_CHANGED_HOUR_PQ_REPLAY_PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
