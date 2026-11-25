#!/usr/bin/env python3
"""Nighttime fixed-power feasibility probes for the 94022 failed sampled factors.
No new LP, network changes, causal policy, or annual feasibility claim.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import sizing_nine_factor as nf
import reserve_full_night as rn
import sizing_ac_followup as follow
from audit_battery_coverage import signed, read_json

SOURCE=Path("StudyA_Sizing_NineFactor_Sample_v1")
HOUR_HASH="222f498193ebc54c12406b00d956db6325261f9ded8925bcbcae845fd02559ff"
SUMMARY_HASH="a641606147653e1626eff0a632654215e99731c46ac69ef9374744a029fbf95b"

def prepare(repo):
    m=read_json(repo/SOURCE/"RUN_MANIFEST.json")
    if m["status"]!="COMPLETE_NINE_FACTOR_SAMPLE_NOT_ANNUAL" or m["completed_case_factors"]!=72 or m["planned_case_hours"]!=5409:
        raise ValueError("Wrong completed sizing sample")
    for name,h in (("FACTOR_AC_HOURLY.csv",HOUR_HASH),("FACTOR_AC_SUMMARY.csv",SUMMARY_HASH)):
        nf.check_receipt_hash(repo/SOURCE/name,h,m["output_sha256"][name]);signed(repo/SOURCE/name,h)
    a=pd.read_csv(repo/SOURCE/"FACTOR_AC_HOURLY.csv",parse_dates=["timestamp_lst"],keep_default_na=False)
    keys=["case","pf","length_factor","timestamp_lst"]
    if len(a)!=5409 or a.duplicated(keys).any() or not a.status.eq("CONVERGED").all():
        raise ValueError("Unexpected sample coverage")
    fail=a.loc[~a.ac_feasible].copy()
    if len(fail)!=342 or not fail.night_reactive_disabled.all() or not fail.family.eq("constraint").all():
        raise ValueError("Unexpected failed population")
    if not fail.min_v_pu.lt(.95).all() or fail.max_trafo_pct.gt(100).any() or fail.max_line_pct.gt(100).any():
        raise ValueError("Failure mechanism changed")
    events=fail.groupby(["pf","length_factor","timestamp_lst"],sort=True)
    if events.ngroups!=115 or fail.timestamp_lst.nunique()!=24:
        raise ValueError("Failure events changed")
    v6,annual,groups=nf.prepare(repo)
    x=groups["constraint"];c0=x["cases"][0];f0=x["frames"][c0]
    for c in x["cases"]:
        f=x["frames"][c]
        for col in ("demand_kw","pv_dc_available_kw"):
            if not np.array_equal(f[col],f0[col]):
                raise ValueError("Unmatched event inputs")
        for col in ("inverter_kva","battery_power_dc_kw","transformer_kva_assumed_or_evidenced"):
            if x["hardware"][c][col]!=x["hardware"][c0][col]:
                raise ValueError("Unmatched common power limits")
        z=fail[fail.case.eq(c)]
        if not z.energy_sha256.eq(x["signatures"][c]).all():
            raise ValueError("Energy source mismatch")
        for row in z.itertuples():
            t=row.timestamp_lst
            if f.at[t,"pv_dc_available_kw"]>1e-9 or abs(f.at[t,"inverter_ac_kw"]-row.inverter_ac_kw)>1e-9 or abs(f.at[t,"demand_kw"]-row.gross_demand_kw)>1e-9:
                raise ValueError("Failed sample input mismatch")
    return v6,annual,x,fail

def scan(measure,cap):
    """Test a grid including both endpoints; distinguish any pass from a terminal segment."""
    points=[(float(p),measure(float(p))) for p in np.linspace(0,cap,21)]
    passing=[p for p,ok in points if ok]
    seg=follow.choose_grid_interval(points)
    if seg is None:
        return passing,None
    lo,hi,previous=seg
    if previous is not None:
        for _ in range(10):
            mid=(lo+previous)/2
            if measure(mid):lo=mid
            else:previous=mid
    lower=min(hi,lo+.01)
    if not measure(lower) or not measure(hi):
        return passing,None
    return passing,(lower,hi)

def run(out,prepared,doc):
    import pandapower as pp
    from run_epm_validation import build_net
    v6,annual,x,fail=prepared
    common=x["cases"][0];f=x["frames"][common]
    probes=[];limits=[];regressions=0
    for (pf,l),g in fail.groupby(["pf","length_factor"],sort=True):
        terr=x["territories"][l];net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):
            raise ValueError("GIS load identity changed")
        for t,z in g.groupby("timestamp_lst",sort=True):
            for row in z.to_dict("records"):
                c=row["case"]
                actual=follow.evaluate(v6,pp,net,meta,terr,x,c,t,pf)
                annual.exact_ac_regression(actual,row,c+" sampled failure "+str(t));regressions+=1
            cap=follow.power_ceiling(float(f.at[t,"demand_kw"]),x["hardware"][common])
            if cap<=0:raise ValueError("Unexpected nonpositive power ceiling")
            event=[]
            def measure(p):
                q=follow.evaluate(v6,pp,net,meta,terr,x,common,t,pf,p=p)
                if not q["night_reactive_disabled"]:
                    raise ValueError("Night policy changed")
                ok=rn.strict_point(q)
                event.append(dict(q,pf=pf,length_factor=l,probe_p_kw=p,strict_feasible=ok))
                return ok
            passing,bounds=scan(measure,cap)
            probes.extend(event)
            finite=[float(q["min_v_pu"]) for q in event if q["status"]=="CONVERGED" and np.isfinite(q["min_v_pu"])]
            limits.append(dict(pf=pf,length_factor=l,timestamp_lst=str(t),failed_source_cases=len(z),
                ceiling_kw=cap,zero_P_pass=event[0]["strict_feasible"],ceiling_P_pass=event[20]["strict_feasible"],
                grid_pass_count=len(passing),best_tested_voltage_pu=max(finite) if finite else np.nan,
                status="TESTED_TERMINAL_SEGMENT" if bounds else ("OTHER_GRID_PASS_NO_TERMINAL_SEGMENT" if passing else "NO_TESTED_FEASIBLE_POINT"),
                lower_kw=bounds[0] if bounds else np.nan,upper_kw=bounds[1] if bounds else np.nan))
        print("Factor",pf,l,"events",g.timestamp_lst.nunique(),"complete",flush=True)
    event_frame=pd.DataFrame(limits)
    fail.to_csv(out/"SOURCE_FAILED_CASE_HOURS.csv",index=False)
    pd.DataFrame(probes).to_csv(out/"STRESS_P_PROBES.csv",index=False)
    event_frame.to_csv(out/"STRESS_P_CORRIDORS.csv",index=False)
    doc.update(status="COMPLETE_TARGETED_STRESS_P_DIAGNOSTIC",regressions=regressions,probes=len(probes),
               event_status_counts={str(k):int(v) for k,v in event_frame.status.value_counts().items()},
               output_sha256={p.name:follow.sample.sha(p) for p in out.iterdir() if p.is_file() and p.name!="RUN_MANIFEST.json"})

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--out",type=Path)
    ap.add_argument("--preflight-only",action="store_true")
    a=ap.parse_args()
    if not a.preflight_only and (a.out is None or a.out.exists()):ap.error("Choose fresh output")
    prepared=prepare(a.repo_root.resolve())
    doc=dict(status="SIGNED_STRESS_P_PREFLIGHT_NO_SOLVES",source_hourly_sha256=HOUR_HASH,source_summary_sha256=SUMMARY_HASH,
             failed_case_hours=342,factor_timestamp_events=115,unique_timestamps=24,planned_regressions=342,
             grid_probes_minimum=115*21,no_new_LP=True,annual_verified=False,field_verified=False,
             interpretation="Finite-grid instantaneous AC feasibility only; no SOC or global infeasibility guarantee")
    print(doc,flush=True)
    if a.preflight_only:return
    a.out.mkdir(parents=False,exist_ok=False);doc["status"]="INCOMPLETE_STRESS_P_DIAGNOSTIC"
    follow.jsonsave(a.out/"RUN_MANIFEST.json",doc)
    try:run(a.out,prepared,doc)
    except Exception as e:
        doc["error"]=repr(e);follow.jsonsave(a.out/"RUN_MANIFEST.json",doc);raise
    follow.jsonsave(a.out/"RUN_MANIFEST.json",doc);print(doc,flush=True)

if __name__=="__main__":main()
