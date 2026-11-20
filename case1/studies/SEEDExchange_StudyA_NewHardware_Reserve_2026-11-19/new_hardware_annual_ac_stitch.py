#!/usr/bin/env python3
"""Source-stitch original annual AC and independently replay reserve corrections.

A1 106039, three new hardware configurations. Same-factor signed B9 reference
hours are reused ONLY on exact matching electrical inputs. For mismatches,
the unchanged original 2025 pandapower solver is executed. Original candidate
PF .95 / line x1.6 AC years are independently signed and reused as-is.

The saved nine-factor changed-hour AC rows are source evidence and cross-checks.
We independently re-solve each corrected hour to record the complete AC row.
No old evidence is modified; output is a compact, reproducible AC delta ledger,
one receipt per case-factor and a complete 8760-hour annual numerical summary.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path("case1/studies/SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19")
FRONTIER=Path("case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17/validate_frontier_ac.py")
BASE_AC=Path("StudyA_A1_106039_Frontier_AC_v1")
OWN_STRESS=Path("StudyA_A1_106039_NewHardware_AC_Stress_v1")
ENERGY=Path("StudyA_A1_106039_Utilization_v1")
SOURCE_STRESS=Path("StudyA_A1_106039_NewHardware_Reserve_Stress_v1")
SOURCE_SCREEN=Path("StudyA_A1_106039_NewHardware_Reserve_NineFactor_v1")
BASE_REF={"MC_B10":"MC_B9","SS_B10":"SS_B9","SS_P45_B9":"SS_B9"}
SCOPE_PILOT={("MC_B10",.95,1.0)}
FACTORS=tuple((pf,lf) for pf in (.95,.98,1.) for lf in (1.,1.3,1.6))
METRICS=("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw","pcc_kva")
TOL=2e-4

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def import_file(label,path):
    spec=importlib.util.spec_from_file_location(label,path)
    if not spec or not spec.loader:
        raise FileNotFoundError(path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def factor_tag(case,pf,lf):
    return f"{case}_pf{round(pf*100):03d}_l{round(lf*10):02d}"

def verify_reference(repo,nh,frontier,st,ctx,ref,pf,lf):
    """Verify original matching-B9 annual AC and underlying original B9 energy."""
    df,energy_meta,_=frontier.signed_energy(repo,repo/ENERGY,ref,st,ctx)
    path=repo/BASE_AC/factor_tag(ref,pf,lf)
    summary=json.loads((path/"ac_summary.json").read_text(encoding="utf-8"))
    signed_energy=summary["new_energy_manifest_sha256"]
    energy_mode=nh.verify_signed_text(repo/ENERGY/("energy_"+ref)/"energy_manifest.json",
                                      signed_energy)
    proven={"case_id":ref,"scenario":"A1","transformer":"106039",
            "pf":pf,"length_factor":lf,"2025_hours":8760,
            "new_energy_manifest_sha256":signed_energy,
            "source_v6_2_sha256":frontier.sha(repo/st.RUNNER_REL),
            "input_manifest_sha256":frontier.sha(ctx["mp"]),
            "q_ratio_daylight":.25,"night_q_disabled":True,
            "method":"independent_hourly_balanced_pandapower_replay"}
    record=frontier.check_saved(path,proven)
    if record is None:
        raise FileNotFoundError("Missing original 8760h signed B9 AC "+str(path))
    ac=pd.read_csv(frontier.xp(path/"ac_hourly.csv"),
                   parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    if (len(ac)!=8760 or not ac.index.equals(df.index)
        or not ac.index.equals(ctx["trace"].index)):
        raise ValueError("Signed B9 AC chronology mismatch: "+ref)
    if (not np.allclose(ac.inverter_ac_kw,df.inverter_ac_kw,atol=1e-7,rtol=0)
        or not np.allclose(ac.gross_demand_kw,ctx["trace"].sum(axis=1),atol=5e-6,rtol=0)):
        raise ValueError("Signed B9 AC and energy/household source differ: "+ref)
    if (ac.night_reactive_disabled.astype(bool).to_numpy()!=
        (df.pv_dc_available_kw.to_numpy(float)<=1e-9)).any():
        raise ValueError("B9 source PV Q enable state mismatches AC: "+ref)
    return df,ac,{"ref_case":ref,"ref_ac_sha256":record["ac_hourly_sha256"],
                  "ref_energy_signed_sha256":signed_energy,
                  "ref_energy_hash_mode":energy_mode,
                  "ref_original_ac_folder":str(path.relative_to(repo))}

def exact_source_mask(new,reference,new_hardware,ref_hardware):
    """Exact recorded inverter input + Q-enable status; no numeric tolerance."""
    if not new.index.equals(reference.index) or len(new)!=8760:
        raise ValueError("Different source annual timebases")
    if float(new_hardware["inverter_kva"])!=float(ref_hardware["inverter_kva"]):
        raise ValueError("Cannot reuse AC from a different inverter kVA")
    pnew=new.inverter_ac_kw.to_numpy(float)
    pref=reference.inverter_ac_kw.to_numpy(float)
    pvnew=new.pv_dc_available_kw.to_numpy(float)>1e-9
    pvref=reference.pv_dc_available_kw.to_numpy(float)>1e-9
    if not np.isfinite(pnew).all() or not np.isfinite(pref).all():
        raise ValueError("Nonfinite inverter power")
    return (pnew==pref)&(pvnew==pvref)

def check_screen(repo,screen_manifest,source_stress,nh,cases):
    manpath=repo/SOURCE_SCREEN/"SCREEN_MANIFEST.json"
    man=json.loads(manpath.read_text(encoding="utf-8"))
    if (man.get("status")!="NINE_FACTOR_CHANGED_HOURS_PASS_ONLY" or
        man.get("AC_calls")!=144 or man.get("factor_case_count")!=27 or
        man.get("annual_ac_cases_completed_by_this_screen")!=0 or
        man.get("may_claim_annual_ac_feasibility") is not False or
        man.get("stress_manifest_sha256")!=source_stress["stress_manifest_sha256"]):
        raise ValueError("Signed changed-hour screen status or source mismatch")
    csvpath=repo/SOURCE_SCREEN/"ALL_NINE_CHANGED_HOUR_AC.csv"
    frame=pd.read_csv(csvpath,parse_dates=["timestamp_lst"])
    expected={(case,pf,lf,t,phase)
        for case in nh.CASES for pf,lf in FACTORS
        for t in (cases[case]["candidate"].index[i] for i in cases[case]["changed"])
        for phase in ("original","candidate")}
    observed={(r.case_id,float(r.pf),float(r.length_factor),r.timestamp_lst,r.phase)
        for r in frame.itertuples()}
    if len(frame)!=144 or len(expected)!=144 or observed!=expected or frame.duplicated(
        ["case_id","pf","length_factor","timestamp_lst","phase"]).any():
        raise ValueError("Changed-hour source does not cover all 144 signed calls")
    for case in nh.CASES:
        item=man.get("cases",{}).get(case,{})
        src=source_stress["cases"][case]
        for key,left,right in (
            ("source_energy",item.get("signed_source_energy_manifest_sha256"),src["signed_source_energy_manifest_sha256"]),
            ("source_ac",item.get("source_annual_stress_ac_sha256"),src["source_annual_stress_ac_sha256"]),
            ("candidate",item.get("stress_corrected_csv_sha256"),src["stress_corrected_csv_sha256"])):
            if left!=right:
                raise ValueError("Nine-factor source drift: "+case+"/"+key)
    if not (frame.status=="CONVERGED").all():
        raise ValueError("Signed changed-hour screen contains nonconvergence")
    if not frame.loc[frame.phase=="candidate","ac_feasible"].astype(bool).all():
        raise ValueError("Signed corrected changed hours not all feasible")
    for row in frame.itertuples():
        source=cases[row.case_id]["candidate" if row.phase=="candidate" else "original"]
        if abs(float(row.inverter_ac_kw)-float(source.loc[row.timestamp_lst,"inverter_ac_kw"]))>2e-7:
            raise ValueError("Changed hour signed source inverter mismatch")
    return frame,{"screen_manifest_sha256":sha(manpath),
                  "screen_csv_checkout_sha256":sha(csvpath),
                  "screen_row_count":len(frame)}

def lookup_screen(screen,case,pf,lf,t,phase):
    hits=screen[(screen.case_id==case)&(abs(screen.pf-pf)<1e-9)&
                (abs(screen.length_factor-lf)<1e-9)&
                (screen.timestamp_lst==t)&(screen.phase==phase)]
    if len(hits)!=1:
        raise ValueError("Missing unique signed changed hour "+case+str((pf,lf,t,phase)))
    return hits.iloc[0]

def compare_saved(record,saved):
    if str(record.get("status"))!=str(saved["status"]):
        raise ValueError("Solver status differs from independently saved changed-hour AC")
    for k in METRICS:
        if record.get(k) is None or not math.isfinite(float(record[k])):
            raise ValueError("Nonfinite changed-hour solver metric "+k)
        if abs(float(record[k])-float(saved[k]))>TOL:
            raise ValueError("Independent AC replay mismatches source "+k)
    if bool(record.get("ac_feasible"))!=bool(saved["ac_feasible"]):
        raise ValueError("Independent AC feasibility flag mismatch")

def fill_ac(base,t,record):
    for k in base.columns:
        if k in record:
            if k=="error" and pd.api.types.is_numeric_dtype(base[k]):
                base[k]=base[k].astype(object)
            base.at[t,k]=record[k]
    return base

def validate_year(frontier,b9,frame):
    if len(frame)!=8760 or frame.index.has_duplicates:
        raise ValueError("Incomplete 8760-row AC reconstruction")
    # b9's contract recomputes the SAME original .95/1.05, trafo, line limits.
    mask=b9.validated_ac_mask(frontier,frame)
    status=(frame.status=="CONVERGED").to_numpy()
    if not np.isfinite(frame.loc[status,list(METRICS)].to_numpy(float)).all():
        raise ValueError("Nonfinite AC metrics in a converged annual row")
    return {
        "year_hours":8760,"converged_hours":int(status.sum()),
        "ac_failed_hours":int((~mask).sum()),
        "strict_097_103_failed_hours":int(((frame.min_v_pu<.97)|
                                        (frame.max_v_pu>1.03)).sum()),
        "min_v_pu":float(frame.min_v_pu.min()) if status.any() else None,
        "max_v_pu":float(frame.max_v_pu.max()) if status.any() else None,
        "max_trafo_pct":float(frame.max_trafo_pct.max()) if status.any() else None,
        "max_line_pct":float(frame.max_line_pct.max()) if status.any() else None,
        "losses_kwh":float(frame.loss_kw.sum()) if status.all() else None}

def prepare(repo):
    nine=import_file("nh_nine_stage",repo/ROOT/"new_hardware_nine_factor.py")
    nh,frontier,b9,ctx,cases,stress,pre=nine.verify_source(repo,repo/SOURCE_STRESS)
    st_path=repo/"case1/studies/SEEDExchange_StudyA_PVBESS_v1"
    if str(st_path) not in sys.path:sys.path.insert(0,str(st_path))
    import study_a_pvbess as st
    screen,screen_meta=check_screen(repo,None,pre,nh,cases)
    references={}
    all_factors={}
    for case in nh.CASES:
        ref=BASE_REF[case]
        ref_energy=None
        for pf,lf in FACTORS:
            r_energy,r_ac,prov=verify_reference(repo,nh,frontier,st,ctx,ref,pf,lf)
            if ref_energy is None:
                ref_energy=r_energy
            equal=exact_source_mask(cases[case]["original"],r_energy,
                                    cases[case]["energy_manifest"]["hardware"],
                                    # Signed reference manifest kVA from independently checked PyPSA source
                                    json.loads((repo/ENERGY/("energy_"+ref)/"energy_manifest.json").read_text(encoding="utf-8"))["hardware"])
            expected={ "MC_B10":159, "SS_B10":267, "SS_P45_B9":731}[case]
            if int((~equal).sum())!=expected:
                raise ValueError("Source-matching numerical cohort count changed: "+case)
            for index in cases[case]["changed"]:
                t=cases[case]["candidate"].index[index]
                for phase in ("original","candidate"):
                    lookup_screen(screen,case,pf,lf,t,phase)
            all_factors[(case,pf,lf)]={"ref_ac":r_ac,"ref_energy":r_energy,
                "reusable":equal,"source":prov}
    return nine,nh,frontier,b9,ctx,cases,screen,screen_meta,pre,all_factors

def sim_one(repo,nh,frontier,b9,ctx,cases,screen,factors,case,pf,lf):
    c=cases[case]
    source=factors[(case,pf,lf)]
    stress=(pf,lf)==(.95,1.6)
    if stress:
        base=c["original_ac"].copy(deep=True)
        baseline_mode="OWN_ORIGINAL_SIGNED_8760H_STRESS_AC"
        new_hours=np.array([],dtype=int)
        reused=8760
    else:
        base=source["ref_ac"].copy(deep=True)
        baseline_mode="EXACT_B9_SIGNED_8760H_PLUS_NEW_UNMATCHED_HOURS"
        new_hours=np.flatnonzero(~source["reusable"])
        reused=int(source["reusable"].sum())
    new_base=base.copy(deep=True)
    ctx["v6"].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    territory=ctx["v6"].new_territory(repo,"A1","106039",ctx["houses"],lf)
    net,nodes=build_net(territory,"head")
    if set(nodes["loads"])!=set(ctx["houses"]):
        raise ValueError("Household mapping changed during AC reconstruction")
    inv=float(c["energy_manifest"]["hardware"]["inverter_kva"])
    original=c["original"];candidate=c["candidate"]
    signed_rows=[]
    def solve(t,frame):
        return ctx["v6"].solve_ac_hour(net,nodes,territory,t,ctx["trace"].loc[t],pf,
            float(frame.loc[t,"inverter_ac_kw"]),inv,
            float(frame.loc[t,"pv_dc_available_kw"]),.25,9,"pvbess",pp)
    # Recompute deterministic reused source samples at night, in daylight and at
    # high inverter power. A numerical mismatch invalidates the entire reuse case.
    samples=[]
    if not stress:
        allowed=np.flatnonzero(source["reusable"])
        if not len(allowed):
            raise ValueError("No matching reference hours, refuse reuse")
        samples.append(int(allowed[0]))
        daylight=np.flatnonzero(source["reusable"]&
            (original.pv_dc_available_kw.to_numpy(float)>1e-9))
        if len(daylight):samples.append(int(daylight[0]))
        samples.append(int(allowed[np.argmax(original.inverter_ac_kw.to_numpy(float)[allowed])]))
        samples=sorted(set(samples))
        for idx in samples:
            t=original.index[idx]
            rec=solve(t,original)
            compare_saved(rec,source["ref_ac"].loc[t])
    for i,idx in enumerate(new_hours):
        t=original.index[idx]
        raw=solve(t,original)
        if t in {original.index[j] for j in c["changed"]}:
            compare_saved(raw,lookup_screen(screen,case,pf,lf,t,"original"))
        fill_ac(base,t,raw)
        signed_rows.append({"case_id":case,"pf":pf,"length_factor":lf,
                            "phase":"original_different_from_B9","timestamp_lst":str(t),**raw})
        if (i+1)%200==0:
            print(f"Original source-stitch {case} PF{pf:.2f} x{lf:.1f}: {i+1}/{len(new_hours)}",flush=True)
    # Full source-stitched annual ORIGINAL AC, verify independently saved
    # changed-hour original AC for every corrected or donor time.
    changed_t={original.index[j] for j in c["changed"]}
    for t in changed_t:
        s=lookup_screen(screen,case,pf,lf,t,"original")
        compare_saved(base.loc[t],s)
    base_stats=validate_year(frontier,b9,base)
    new_base=base.copy(deep=True)
    for idx in c["changed"]:
        t=original.index[idx]
        raw=solve(t,candidate)
        compare_saved(raw,lookup_screen(screen,case,pf,lf,t,"candidate"))
        fill_ac(new_base,t,raw)
        signed_rows.append({"case_id":case,"pf":pf,"length_factor":lf,
                            "phase":"candidate_reserve_correction","timestamp_lst":str(t),**raw})
    if not np.allclose(new_base.inverter_ac_kw.to_numpy(float),
                       candidate.inverter_ac_kw.to_numpy(float),atol=1e-7,rtol=0):
        raise ValueError("Corrected annual AC injection not equal to 8760h candidate")
    corrected_stats=validate_year(frontier,b9,new_base)
    if base_stats["year_hours"]!=8760 or corrected_stats["year_hours"]!=8760:
        raise ValueError("Incomplete annual chronology")
    row={"case_id":case,"pf":pf,"length_factor":lf,
         "source_mode":baseline_mode,
         "reference":BASE_REF[case],"source_ref_ac_sha256":source["source"]["ref_ac_sha256"],
         "source_own_stress_ac_sha256":c["ac_manifest"]["ac_hourly_sha256"],
         "reference_energy_signed_sha256":source["source"]["ref_energy_signed_sha256"],
         "reference_energy_hash_mode":source["source"]["ref_energy_hash_mode"],
         "source_energy_manifest_sha256":c["energy_manifest_sha256"],
         "exact_source_reused_hours":reused,
         "new_original_ac_hours":len(new_hours),
         "independent_reuse_samples":len(samples),
         "reserve_corrected_hours":len(c["changed"]),
         "replayed_changed_hour_ac_calls":len(c["changed"]),
         "baseline":base_stats,"corrected":corrected_stats,
         "no_new_full_8760h_AC_solve":True,
         "coverage":"SIGNED_EXACT_REFERENCE_HOURS_PLUS_NEW_MISMATCH_AC_PLUS_SAME_FACTOR_RESERVE_REPLAY"}
    return row,pd.DataFrame(signed_rows)

def commit_case_result(out,row,delta):
    tag=factor_tag(row["case_id"],row["pf"],row["length_factor"])
    d=out/tag
    if d.exists():
        raise FileExistsError("No overwrite of case output: "+str(d))
    d.mkdir()
    target=d/"AC_NEW_SOLVED_HOURS.csv"
    delta.to_csv(target,index=False,float_format="%.10f")
    row["new_ac_delta_file"]=str(target.relative_to(out)).replace("\\","/")
    row["new_ac_delta_sha256"]=sha(target)
    (d/"CASE_RECEIPT.json").write_text(json.dumps(row,indent=2,allow_nan=False)+"\n",
                                       encoding="utf-8")
    return tag

def cli(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path.cwd())
    ap.add_argument("--scope",choices=("pilot","full"),default="pilot")
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--resume",action="store_true",help="Resume a previously started unchanged, source-matched result directory")
    ap.add_argument("--out",type=Path)
    args=ap.parse_args(argv)
    repo=args.repo_root.resolve()
    nine,nh,frontier,b9,ctx,cases,screen,screen_meta,stress,source=prepare(repo)
    selected=[(c,pf,lf) for c in nh.CASES for pf,lf in FACTORS
              if args.scope=="full" or (c,pf,lf) in SCOPE_PILOT]
    receipt={
        "status":"SIGNED_2025_ANNUAL_SOURCE_EQUIVALENCE_PREFLIGHT_PASS_NO_AC",
        "scope":args.scope,
        "modelled_case_factors":len(selected),
        "source_all_nine_factor_case_factors_checked":len(source),
        "screen_sha256":screen_meta["screen_manifest_sha256"],
        "screen_csv_sha256":screen_meta["screen_csv_checkout_sha256"],
        "stress_source_sha256":stress["stress_manifest_sha256"],
        "runner_sha256":sha(Path(__file__)),
        "expected_new_original_hour_solves":sum(0 if (pf,lf)==(.95,1.6)
                    else int((~source[(c,pf,lf)]["reusable"]).sum())
                    for c,pf,lf in selected),
        "expected_candidate_overlay_hours":sum(len(cases[c]["changed"]) for c,pf,lf in selected),
        "original_annual_factor_coverage_from_signed_B9":18,
        "annual_ac_claim_before_simulation":False,
        "no_new_full_year_AC_solves":True,
        "factors":list(FACTORS),
        "source":"Signed original B9 and own-stress annual AC, verified per-hour electrical equivalence",
        "cases":{}}
    if args.preflight_only:
        print(json.dumps(receipt,indent=2,allow_nan=False))
        return receipt
    if args.out is None:
        stem="StudyA_A1_106039_NewHardware_Reserve_AnnualAC_"+args.scope.capitalize()+"_v"
        out=next((repo/(stem+str(i)) for i in range(1,1000) if not
                  (repo/(stem+str(i))).exists()),None)
        if out is None:raise FileExistsError("No unused annual-AC output path")
    else:
        out=args.out.resolve()
    output_manifest=out/"RUN_MANIFEST.json"
    if args.resume:
        if args.out is None or not out.is_dir() or not output_manifest.is_file():
            raise ValueError("--resume requires --out pointing to an existing case receipt")
        previous=json.loads(output_manifest.read_text(encoding="utf-8"))
        for key in ("scope","screen_sha256","screen_csv_sha256",
                    "stress_source_sha256","runner_sha256","modelled_case_factors"):
            if previous.get(key)!=receipt.get(key):
                raise ValueError("Cannot resume changed source or scope: "+key)
        if previous.get("status")!="INCOMPLETE_SOURCE_STITCHED_AC":
            raise ValueError("Only resume an explicitly incomplete annual receipt")
        receipt=previous
        print("SOURCE-VERIFIED RESUME: "+str(out),flush=True)
    else:
        if out.exists():raise FileExistsError("No overwrite: "+str(out))
        out.mkdir()
        receipt["status"]="INCOMPLETE_SOURCE_STITCHED_AC"
        receipt["output_folder"]=str(out)
        output_manifest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",
                                   encoding="utf-8")
    expected_tags={factor_tag(c,pf,lf) for c,pf,lf in selected}
    if not set(receipt["cases"]).issubset(expected_tags):
        raise ValueError("Resume includes unexpected case-factor results")
    for c,pf,lf in selected:
        tag=factor_tag(c,pf,lf)
        expected_new=0 if (pf,lf)==(.95,1.6) else int(
            (~source[(c,pf,lf)]["reusable"]).sum())
        if tag in receipt["cases"]:
            row=receipt["cases"][tag]
            if (row.get("new_original_ac_hours")!=expected_new or
                row.get("source_ref_ac_sha256")!=source[(c,pf,lf)]["source"]["ref_ac_sha256"] or
                row.get("source_energy_manifest_sha256")!=cases[c]["energy_manifest_sha256"] or
                row.get("reserve_corrected_hours")!=len(cases[c]["changed"])):
                raise ValueError("Existing partial case does not match signed inputs: "+tag)
            case_file=out/row["new_ac_delta_file"]
            if (not case_file.is_file() or sha(case_file)!=row.get("new_ac_delta_sha256") or
                not (out/tag/"CASE_RECEIPT.json").is_file()):
                raise ValueError("Missing or modified saved partial case: "+tag)
            archived=json.loads((out/tag/"CASE_RECEIPT.json").read_text(encoding="utf-8"))
            if archived!=row:
                raise ValueError("Partial case receipt differs from running manifest: "+tag)
            print("REUSED VERIFIED COMPLETED CASE "+tag,flush=True)
            continue
        if (out/tag).exists():
            raise FileExistsError("Partial uncommitted case folder: "+str(out/tag))
        row,delta=sim_one(repo,nh,frontier,b9,ctx,cases,screen,source,c,pf,lf)
        commit_case_result(out,row,delta)
        receipt["cases"][tag]=row
        output_manifest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",
                                   encoding="utf-8")
        print(f"Completed {tag}: original {row['new_original_ac_hours']} new,"
              f" reuses {row['exact_source_reused_hours']}, corrected fail hours"
              f" {row['corrected']['ac_failed_hours']}",flush=True)
    rows=list(receipt["cases"].values())
    flat=[{"case_id":r["case_id"],"pf":r["pf"],"length_factor":r["length_factor"],
          "reused_hours":r["exact_source_reused_hours"],
          "new_original_ac_hours":r["new_original_ac_hours"],
          "baseline_bad_hours":r["baseline"]["ac_failed_hours"],
          "corrected_bad_hours":r["corrected"]["ac_failed_hours"],
          "min_voltage_pu":r["corrected"]["min_v_pu"],
          "max_transformer_pct":r["corrected"]["max_trafo_pct"],
          "losses_kwh":r["corrected"]["losses_kwh"],
          "strict_097_103_failed_hours":r["corrected"]["strict_097_103_failed_hours"]}
          for r in rows]
    summary=out/"ANNUAL_AC_PAIRED_SUMMARY.csv"
    pd.DataFrame(flat).to_csv(summary,index=False,float_format="%.10f")
    receipt["summary_sha256"]=sha(summary)
    receipt["status"]=("SOURCE_STITCHED_ANNUAL_AC_ALL_CASES_PASS"
         if len(rows)==len(selected) and
         all(r["corrected"]["ac_failed_hours"]==0 and
             r["corrected"]["converged_hours"]==8760 for r in rows)
         else "SOURCE_STITCHED_ANNUAL_AC_EXPLICIT_FAILURES")
    receipt["completed_annual_case_factors"]=len(rows)
    receipt["new_original_ac_calls"]=sum(r["new_original_ac_hours"] for r in rows)
    receipt["new_corrected_hour_ac_calls"]=sum(r["replayed_changed_hour_ac_calls"] for r in rows)
    output_manifest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",
                               encoding="utf-8")
    print(json.dumps({"status":receipt["status"],"folder":str(out),
                      "annual_cases":len(rows),
                      "new_original_ac_calls":receipt["new_original_ac_calls"],
                      "new_corrected_hour_ac_calls":receipt["new_corrected_hour_ac_calls"]},indent=2))
    if receipt["status"]!="SOURCE_STITCHED_ANNUAL_AC_ALL_CASES_PASS":
        raise SystemExit(2)
    return receipt

if __name__=="__main__":
    cli()
