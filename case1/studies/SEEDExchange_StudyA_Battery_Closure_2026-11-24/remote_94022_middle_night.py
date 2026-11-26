#!/usr/bin/env python3
"""Source-locked static middle-placement night support screen; no LP or design change."""
import json, os, sys, time, traceback, platform, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT, OUT, STUDY, run, save, restore
import sizing_matched_physical_options as mo
import sizing_ac_followup as follow
import reserve_full_night as rn

PF=.95
LENGTH=1.6
OPTION="middle"

def prepare():
    v6,annual,x,a,reg,head=mo.prepare(ROOT)
    bench=mo.annual_sample_gate(ROOT,(v6,annual,x,a,reg,head))
    common=mo.CASES[0]
    f=x["frames"][common]
    night=f.index[f.pv_dc_available_kw<=1e-9]
    if len(night)!=4353 or len(x["hours"])!=67 or not f.index.equals(pd.date_range("2025-01-01",periods=8760,freq="h")):
        raise ValueError("Night/time/sample population changed")
    for c in mo.CASES:
        other=x["frames"][c]
        for k in ("demand_kw","pv_dc_available_kw"):
            if not np.array_equal(f[k].to_numpy(),other[k].to_numpy()):
                raise ValueError("Common input mismatch")
        for k in ("inverter_kva","battery_power_dc_kw","transformer_kva_assumed_or_evidenced"):
            if x["hardware"][common][k]!=x["hardware"][c][k]:
                raise ValueError("Common power limit mismatch")
    endpoint=a[a.option.eq(OPTION)&a.pf.eq(PF)&a.length_factor.eq(LENGTH)&a.probe_index.isin([0,20])]
    if len(endpoint)==0 or endpoint.duplicated(["timestamp_lst","probe_index"]).any():
        raise ValueError("Missing or duplicate endpoint controls")
    return v6,annual,x,reg,bench,night,endpoint

def solve(prepared,report):
    import pandapower as pp
    v6,annual,x,reg,bench,night,endpoint=prepared
    common=mo.CASES[0];f=x["frames"][common];terr=x["territories"][LENGTH]
    net,meta=mo.build(terr,OPTION,reg,LENGTH)
    if set(meta["loads"])!=set(x["ids"]):
        raise ValueError("Household identity changed")
    regressions=0
    for c in mo.CASES:
        for t in x["hours"]:
            q=follow.evaluate(v6,pp,net,meta,terr,x,c,t,PF)
            q["strict_feasible"]=rn.strict_point(q)
            mo.exact_sample_row(annual,q,bench.loc[(OPTION,c,PF,LENGTH,t)].to_dict(),c+" "+str(t))
            regressions+=1
    if regressions!=201:
        raise ValueError("Sample regression coverage")
    endpoint_checks=0
    for r in endpoint.to_dict("records"):
        q=follow.evaluate(v6,pp,net,meta,terr,x,common,r["timestamp_lst"],PF,p=r["probe_p_kw"])
        annual.exact_ac_regression(q,r,OPTION+" endpoint "+str(r["timestamp_lst"]))
        endpoint_checks+=1
    rows=[];probes=[]
    def measure(t,p):
        q=follow.evaluate(v6,pp,net,meta,terr,x,common,t,PF,p=float(p))
        if q["status"]!="CONVERGED" or not q["night_reactive_disabled"] or not np.isfinite([q[k] for k in ("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw")]).all():
            raise ValueError("Nonconverged/nonfinite/night Q failure "+str(t))
        return q
    for i,t in enumerate(night):
        cap=follow.power_ceiling(float(f.at[t,"demand_kw"]),x["hardware"][common])
        if cap<0:raise ValueError("Negative power ceiling")
        z=measure(t,0.);h=measure(t,cap)
        z_ok=rn.strict_point(z);h_ok=rn.strict_point(h)
        lower=None;upper=None;grid_count=None
        status="BOTH_ENDPOINTS_PASS_NOT_CONTINUOUS_PROOF"
        if not z_ok or not h_ok:
            cache={0.:z,float(cap):h}
            def get(p):
                p=float(p)
                if p not in cache:cache[p]=measure(t,p)
                return cache[p]
            def ok(p):return rn.strict_point(get(p))
            grid=np.linspace(0,cap,21)
            grid_count=int(sum(ok(p) for p in grid))
            # Reuse the established terminal-segment method only where its
            # required upper endpoint passes; report interior-only points separately.
            if h_ok and cap>0:
                bound=rn.interval(ok,cap)
                if bound is not None:
                    lower,upper=map(float,bound)
                    status="TESTED_TERMINAL_CORRIDOR"
                else:status="NO_TESTED_TERMINAL_CORRIDOR"
            else:
                status="INTERIOR_OR_ZERO_ONLY_PASS" if grid_count else "NO_TESTED_FEASIBLE_POINT"
            for p,q in sorted(cache.items()):
                probes.append(dict(timestamp_lst=str(t),probe_p_kw=p,strict_feasible=rn.strict_point(q),
                    min_v_pu=float(q["min_v_pu"]),max_v_pu=float(q["max_v_pu"]),
                    max_trafo_pct=float(q["max_trafo_pct"]),max_line_pct=float(q["max_line_pct"]),
                    loss_kw=float(q["loss_kw"])))
        rows.append(dict(timestamp_lst=str(t),gross_demand_kw=float(f.at[t,"demand_kw"]),
            ceiling_kw=cap,zero_pass=z_ok,ceiling_pass=h_ok,
            zero_min_v_pu=float(z["min_v_pu"]),ceiling_min_v_pu=float(h["min_v_pu"]),
            zero_max_v_pu=float(z["max_v_pu"]),ceiling_max_v_pu=float(h["max_v_pu"]),
            zero_trafo_pct=float(z["max_trafo_pct"]),ceiling_trafo_pct=float(h["max_trafo_pct"]),
            zero_line_pct=float(z["max_line_pct"]),ceiling_line_pct=float(h["max_line_pct"]),
            grid_pass_count=grid_count,lower_kw=lower,upper_kw=upper,status=status))
        if (i+1)%500==0:print("Middle night screen",i+1,"/",len(night),flush=True)
    a=pd.DataFrame(rows);p=pd.DataFrame(probes,columns=["timestamp_lst","probe_p_kw","strict_feasible","min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw"])
    if len(a)!=4353 or not a.timestamp_lst.is_unique:raise ValueError("Coverage")
    a.to_csv(OUT/"MIDDLE_NIGHT_SCREEN.csv",index=False)
    p.to_csv(OUT/"MIDDLE_NIGHT_PROBES.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,5),layout="constrained")
    ax.scatter(a.gross_demand_kw,a.zero_min_v_pu,s=8,alpha=.4,label="Zero injection")
    ax.scatter(a.gross_demand_kw,a.ceiling_min_v_pu,s=8,alpha=.4,label="Zero-export ceiling")
    ax.axhline(.95,ls="--",color="firebrick",label="Planning limit")
    ax.set(xlabel="Gross demand (kW)",ylabel="Minimum voltage (pu)",title="94022 middle placement | PF 0.95, length ×1.6 | 4353 night hours")
    ax.legend()
    for ext in ("png","svg"):fig.savefig(OUT/("middle_night_support."+ext),dpi=180)
    plt.close(fig)
    limits=a[a.status.eq("TESTED_TERMINAL_CORRIDOR")]
    report.update(status="COMPLETE_STATIC_NIGHT_SUPPORT_SCREEN",night_hours=len(a),
        baseline_endpoint_solves=2*len(a),sample_regressions=regressions,endpoint_regressions=endpoint_checks,
        zero_failures=int((~a.zero_pass).sum()),ceiling_failures=int((~a.ceiling_pass).sum()),
        status_counts={str(k):int(v) for k,v in a.status.value_counts().items()},
        diagnostic_probe_records=len(p),min_zero_voltage=float(a.zero_min_v_pu.min()),min_ceiling_voltage=float(a.ceiling_min_v_pu.min()),
        tested_lower_p_sum_kwh=float(limits.lower_kw.sum()),tested_lower_p_peak_kw=float(limits.lower_kw.max()) if len(limits) else None,
        unresolved_first_30=a.loc[a.status.isin(["NO_TESTED_FEASIBLE_POINT","NO_TESTED_TERMINAL_CORRIDOR","INTERIOR_OR_ZERO_ONLY_PASS"]),"timestamp_lst"].head(30).tolist())

def main():
    OUT.mkdir(exist_ok=False)
    start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "screen",job_id=os.environ.get("CI_JOB_ID"),pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),runner_id=os.environ.get("CI_RUNNER_ID"),pf=PF,length_factor=LENGTH,option=OPTION,no_new_LP=True,field_verified=False,limitations=["Static endpoints and finite probes, not continuous feasibility proof","No SOC reserve or causal dispatch result","No retrofit or connection approval"])
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":
            raise ValueError("Unexpected execution environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_sizing_option_annual_gate.py","test_reserve_full_night.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        prepared=prepare()
        report.update(planned_night_hours=len(prepared[5]),planned_endpoint_solves=2*len(prepared[5]),planned_sample_regressions=201,planned_endpoint_regressions=len(prepared[6]))
        if preflight:report["status"]="COMPLETE_SIGNED_MIDDLE_NIGHT_PREFLIGHT"
        else:solve(prepared,report)
    except Exception as e:
        report["error"]=repr(e);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"MIDDLE_NIGHT_REPORT.json",report)
        print("MIDDLE_NIGHT_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_MIDDLE_NIGHT_PREFLIGHT","COMPLETE_STATIC_NIGHT_SUPPORT_SCREEN") else 1

if __name__=="__main__":raise SystemExit(main())
