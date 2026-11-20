#!/usr/bin/env python3
"""A1 106039 | three new-hardware reserve schedules, NINE-FACTOR changed-hours AC.

This is a strictly source-signed CHANGED-HOUR screen, NOT an annual AC
certification. It must pass before any missing full-year AC baseline runs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

FACTORS = tuple((p, l) for p in (.95, .98, 1.0) for l in (1.0, 1.3, 1.6))
TRIAL_ROOT = Path("StudyA_A1_106039_NewHardware_Reserve_Stress_v1")
NH_MODULE = Path("case1/studies/SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19/new_hardware_reserve.py")
METRICS = ("min_v_pu", "max_v_pu", "max_trafo_pct", "max_line_pct", "loss_kw", "pcc_kva")
LIMITS = {"min_v_pu": .95, "max_v_pu": 1.05, "max_trafo_pct": 100., "max_line_pct": 100.}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def import_nh(repo):
    file = repo / NH_MODULE
    spec = importlib.util.spec_from_file_location("new_hardware_reserve_signed", file)
    if not spec or not spec.loader:
        raise FileNotFoundError(file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def checked_case_path(root, case, name):
    if not isinstance(name,str):
        raise ValueError("Missing relative signed result filename")
    normalized = name.replace("\\", "/")
    rel = Path(normalized)
    if (rel.is_absolute() or ".." in rel.parts or
        rel.parts[0:1] != (case,) or len(rel.parts) != 2):
        raise ValueError("Unexpected signed case filename: "+name)
    return root / rel

def exact_source_stress(nh, trial_root, original, source_meta, mcase, case):
    """Preserve source hashes and verify signed stress candidate against source."""
    for key in ("source_energy_manifest_sha256", "source_ac_hourly_sha256"):
        source = (source_meta["energy_manifest_sha256"] if key=="source_energy_manifest_sha256"
                  else source_meta["ac_manifest"]["ac_hourly_sha256"])
        if mcase.get(key) != source:
            raise ValueError("Source lineage mismatch: "+case+" "+key)
    saved_result=mcase.get("stress_result",{})
    if (saved_result.get("status")!="STRESS_PASS_ONLY_ALL_NINE_PENDING" or
        saved_result.get("corrected_bad_hours")!=0 or
        saved_result.get("baseline_bad_hours")!=len(nh.KNOWN_BASELINE_FAILURES[case]) or
        saved_result.get("source_original_ac_sha256")!=source_meta["ac_manifest"]["ac_hourly_sha256"] or
        mcase.get("changed_hour_count")!=len(source_meta["changed"])):
        raise ValueError("Original stress did not pass for "+case)
    candidate_file=checked_case_path(trial_root,case,saved_result["candidate_energy_csv"])
    changed_file=checked_case_path(trial_root,case,saved_result["changed_hour_csv"])
    cand_mode=nh.verify_signed_text(candidate_file,saved_result["candidate_energy_sha256"])
    check_mode=nh.verify_signed_text(changed_file,saved_result["changed_hour_sha256"])
    df=pd.read_csv(candidate_file,parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    if len(df)!=8760 or not df.index.equals(original["candidate"].index) or set(df)!=set(original["candidate"]):
        raise ValueError("Changed annual candidate schedule identity: "+case)
    for col in original["candidate"]:
        lhs=pd.to_numeric(df[col],errors="raise").to_numpy(float)
        rhs=original["candidate"][col].to_numpy(float)
        if not np.isfinite(lhs).all() or not np.allclose(lhs,rhs,atol=2e-7,rtol=0):
            raise ValueError("Signed stress candidate differs from generated schedule: "+case+" "+col)
    saved=pd.read_csv(changed_file)
    expected=set(original["candidate"].index[i].strftime("%Y-%m-%d %H:%M:%S")
                 for i in original["changed"])
    observed=set(saved.timestamp_lst)
    if (len(saved)!=len(expected) or len(observed)!=len(expected) or observed!=expected or
        set(saved.case_id)!={case} or not saved.new_ac_feasible.astype(bool).all()):
        raise ValueError("Signed stress changed-hour rows inconsistent: "+case)
    return {"original_stress":saved,"candidate_mode":cand_mode,"changed_mode":check_mode,
            "candidate_sha256":saved_result["candidate_energy_sha256"],
            "changed_sha256":saved_result["changed_hour_sha256"]}

def verify_source(repo, root):
    """Runs all original annual energy and AC source gates without writing output."""
    nh=import_nh(repo)
    frontier,b9,st,ctx,cases,pref=nh.preflight(repo)
    manifest_file=root/"RUN_MANIFEST.json"
    saved=json.loads(manifest_file.read_text(encoding="utf-8"))
    if (saved.get("status")!="STRESS_PASS_ONLY_ALL_NINE_PENDING" or
        saved.get("case_count")!=len(nh.CASES) or
        set(saved.get("cases",{}))!=set(nh.CASES) or
        saved.get("all_nine_factors_tested") is not False or
        saved.get("stress_factor")!={"pf":.95,"length_factor":1.6}):
        raise ValueError("Missing/incorrect signed 3-case stress source")
    checks={}
    for case in nh.CASES:
        checks[case]=exact_source_stress(
            nh,root,cases[case],cases[case],saved["cases"][case],case)
    source_receipt={"status":"SIGNED_3CASE_STRESS_PREFLIGHT_PASS_NO_NEW_AC",
        "stress_manifest_sha256":sha(manifest_file),
        "stress_root":str(root),
        "three_case_year":2025,
        "factor_count":len(FACTORS),
        "planned_changed_hour_AC_solves":sum(
            len(cases[x]["changed"])*2*len(FACTORS) for x in nh.CASES),
        "annual_ac_cases_completed_by_this_screen":0,
        "cases":{case:{
            "signed_source_energy_manifest_sha256":cases[case]["energy_manifest_sha256"],
            "source_annual_stress_ac_sha256":cases[case]["ac_manifest"]["ac_hourly_sha256"],
            "stress_corrected_csv_sha256":checks[case]["candidate_sha256"],
            "stress_correction_checks_sha256":checks[case]["changed_sha256"],
            "candidate_source_mode":checks[case]["candidate_mode"],
            "stress_changed_source_mode":checks[case]["changed_mode"],
            "changed_hours":len(cases[case]["changed"])
            } for case in nh.CASES}}
    return nh,frontier,b9,ctx,cases,checks,source_receipt

def finite_extreme(values, what):
    """Preserve non-converged cases as null, never emit a NaN JSON result."""
    arr=pd.to_numeric(values,errors="coerce").to_numpy(float)
    finite=arr[np.isfinite(arr)]
    if not len(finite):
        return None
    return float(finite.min() if what=="min" else finite.max())

def ac_screen(record):
    status=str(record.get("status"))=="CONVERGED"
    try:
        vals={k:float(record[k]) for k in METRICS}
        finite=all(math.isfinite(x) for x in vals.values())
    except (KeyError,ValueError,TypeError):
        vals={k:None for k in METRICS};finite=False
    good=(status and finite and
          vals["min_v_pu"]>=LIMITS["min_v_pu"]-1e-10 and
          vals["max_v_pu"]<=LIMITS["max_v_pu"]+1e-10 and
          vals["max_trafo_pct"]<=LIMITS["max_trafo_pct"]+1e-9 and
          vals["max_line_pct"]<=LIMITS["max_line_pct"]+1e-9)
    if status and finite and bool(record.get("ac_feasible"))!=bool(good):
        raise ValueError("Original pandapower feasibility flag disagrees with limits")
    return {"status":str(record.get("status")),"ac_feasible":bool(good),**vals}

def compare_stress_stored(rows,case,phase,t,rec):
    matches=rows[rows.timestamp_lst==str(t)]
    if len(matches)!=1:
        raise ValueError("Missing saved stress hour: "+case+" "+str(t))
    prior=matches.iloc[0]
    prefix="old" if phase=="original" else "new"
    for metric,key in (("max_trafo_pct",prefix+"_trafo_pct"),("min_v_pu",prefix+"_min_v_pu"),
                       ("loss_kw",prefix+"_loss_kw")):
        if rec[metric] is None or abs(rec[metric]-float(prior[key]))>2e-4:
            raise ValueError("Changed-hour stress solver mismatch: "+case+" "+phase+" "+metric)
    if rec["ac_feasible"]!=bool(prior[prefix+"_ac_feasible"]):
        raise ValueError("Changed-hour stress feasibility mismatch: "+case+" "+phase)

def run_screen(repo, root, out, run_preflight_only=False):
    nh,frontier,b9,ctx,cases,stresses,receipt=verify_source(repo,root)
    if run_preflight_only:
        return receipt
    if out.exists():
        raise FileExistsError("Never overwrite result directory: "+str(out))
    ctx["v6"].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    rows=[]
    for case in nh.CASES:
        c=cases[case]
        timestamps=[c["candidate"].index[i] for i in c["changed"]]
        hw=c["energy_manifest"]["hardware"]
        for pf,lf in FACTORS:
            territory=ctx["v6"].new_territory(repo,"A1","106039",ctx["houses"],lf)
            net,nodes=build_net(territory,"head")
            if set(nodes["loads"])!=set(ctx["houses"]):
                raise ValueError("EPM household membership drifted: "+case)
            for t in timestamps:
                for phase,frame in (("original",c["original"]),("candidate",c["candidate"])):
                    raw=ctx["v6"].solve_ac_hour(
                        net,nodes,territory,t,ctx["trace"].loc[t],pf,
                        float(frame.at[t,"inverter_ac_kw"]),
                        float(hw["inverter_kva"]),
                        float(frame.at[t,"pv_dc_available_kw"]),
                        .25,9,"pvbess",pp)
                    rec=ac_screen(raw)
                    if abs(pf-.95)<1e-10 and abs(lf-1.6)<1e-10:
                        compare_stress_stored(stresses[case]["original_stress"],case,phase,t,rec)
                        if phase=="original":
                            nh.check_replayed_old(c["original_ac"].loc[t],raw,case,t)
                    rows.append({
                        "case_id":case,"pf":pf,"length_factor":lf,
                        "timestamp_lst":str(t),"phase":phase,
                        "inverter_ac_kw":float(frame.at[t,"inverter_ac_kw"]),**rec})
            print(f"CHANGED-HOUR AC {case} PF {pf:.2f} length x{lf:.1f}",flush=True)
    frame=pd.DataFrame(rows)
    expected={(case,float(pf),float(lf),phase,str(cases[case]["candidate"].index[i]))
              for case in nh.CASES for pf,lf in FACTORS
              for i in cases[case]["changed"] for phase in ("original","candidate")}
    actual={(r.case_id,float(r.pf),float(r.length_factor),r.phase,r.timestamp_lst)
            for r in frame.itertuples()}
    if len(frame)!=len(expected) or actual!=expected or frame.duplicated(
        ["case_id","pf","length_factor","timestamp_lst","phase"]).any():
        raise ValueError("Nine-factor changed-hour AC identity/coverage incomplete")
    group=frame[frame.phase=="candidate"]
    summary=[]
    for (case,pf,lf),part in group.groupby(["case_id","pf","length_factor"]):
        feas=part.ac_feasible.astype(bool)
        summary.append({
            "case_id":case,"pf":float(pf),"length_factor":float(lf),
            "changed_case_hours":len(part),
            "corrected_changed_hour_failures":int((~feas).sum()),
            "nonconverged_changed_hours":int((part.status!="CONVERGED").sum()),
            "worst_changed_hour_trafo_pct":finite_extreme(part.max_trafo_pct,"max"),
            "lowest_changed_hour_voltage_pu":finite_extreme(part.min_v_pu,"min"),
            "coverage":"CHANGED_HOURS_ONLY_2025_NO_ANNUAL_CLAIM"})
    summary=sorted(summary,key=lambda s:(s["case_id"],s["pf"],s["length_factor"]))
    if len(summary)!=len(nh.CASES)*len(FACTORS):
        raise ValueError("Missing factor-case changed-hour summary")
    good=all(x["corrected_changed_hour_failures"]==0 and
             x["nonconverged_changed_hours"]==0 for x in summary)
    doc={**receipt,
         "status":"NINE_FACTOR_CHANGED_HOURS_PASS_ONLY" if good else "NINE_FACTOR_CHANGED_HOURS_EXPLICIT_FAILURES",
         "AC_calls":len(frame),
         "factor_case_count":len(summary),
         "changed_hour_factor_summaries":summary,
         "all_nine_changed_hour_conditions_tested":True,
         "annual_ac_cases_completed_by_this_screen":0,
         "may_claim_annual_ac_feasibility":False,
         "next_gate":"Run signed original annual AC missing PF/length factors, then source-stitch reserve changes"}
    out.mkdir(parents=True,exist_ok=False)
    frame.to_csv(out/"ALL_NINE_CHANGED_HOUR_AC.csv",index=False,float_format="%.10f")
    pd.DataFrame(summary).to_csv(out/"NINE_FACTOR_CHANGED_HOUR_SUMMARY.csv",
                                 index=False,float_format="%.10f")
    (out/"SCREEN_MANIFEST.json").write_text(
        json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        figures=out/"figures"/"audit"
        figures.mkdir(parents=True,exist_ok=True)
        for case in nh.CASES:
            selected=[v for v in summary if v["case_id"]==case]
            fig,ax=plt.subplots(figsize=(9,4))
            keys=[f'PF{v["pf"]:.2f} x{v["length_factor"]:.1f}' for v in selected]
            values=[float(v["worst_changed_hour_trafo_pct"])
                    if v["worst_changed_hour_trafo_pct"] is not None else np.nan
                    for v in selected]
            ax.bar(np.arange(len(keys)),values)
            ax.axhline(100,color="black",linestyle="--",label="Transformer rating")
            ax.set_xticks(np.arange(len(keys)),keys,rotation=40,ha="right")
            ax.set_ylabel("Maximum of altered hours, transformer loading (%)")
            ax.set_title(case+": nine-factor changed-hour screen only")
            fig.tight_layout()
            fig.savefig(figures/(case+"_changed_hour_nine_factor.png"),dpi=170)
            plt.close(fig)
    except Exception as exc:
        print("Optional audit figure export issue:",exc,flush=True)
    return {"status":doc["status"],"out":str(out),"AC_calls":len(frame),
            "factor_cases":len(summary),"annual_cases":0}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path.cwd())
    ap.add_argument("--stress-root",type=Path,default=TRIAL_ROOT)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--preflight-only",action="store_true")
    args=ap.parse_args(argv)
    repo=args.repo_root.resolve()
    root=args.stress_root if args.stress_root.is_absolute() else repo/args.stress_root
    if args.out is None:
        stem="StudyA_A1_106039_NewHardware_Reserve_NineFactor_v"
        out=next((repo/(stem+str(i)) for i in range(1,1000)
                  if not (repo/(stem+str(i))).exists()),None)
        if out is None:raise FileExistsError("No unused version folder 1..999")
    else:
        out=args.out.resolve()
    result=run_screen(repo,root,out,run_preflight_only=args.preflight_only)
    print(json.dumps(result,indent=2,allow_nan=False))
    if not args.preflight_only and result["status"]!="NINE_FACTOR_CHANGED_HOURS_PASS_ONLY":
        raise SystemExit(2)

if __name__=="__main__":
    main()
