#!/usr/bin/env python3
"""A1 eight-house head network, annual night support and conditional reserve LPs.
No new physical assumptions, no causal control or full-year AC certification.
"""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import remote_94022_A1_annual as prev
import remote_94022_A1_sizing as src
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import sizing_ac_followup as follow
import reserve_full_night as rn
from audit_battery_coverage import read_frame

EVENTS=json.loads("[{\"case\":\"A0_94022_min_cost_to_A1\",\"timestamp_lst\":\"2025-11-27 20:00:00\",\"source_energy_sha256\":\"ef6172e9e1a9ebb2b45d819208765dd4a9de440dd48412b79eae59eecae370e1\",\"original_p_kw\":0,\"original_min_v_pu\":0.9495815904523528,\"zero_min_v_pu\":0.9495815904523528,\"ceiling_kw\":3.2067823769,\"ceiling_min_v_pu\":0.9618826623297987,\"ceiling_pass\":true,\"tested_lower_kw\":0.11678835844950196,\"tested_upper_kw\":3.2067823769,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_min_cost_ref\",\"timestamp_lst\":\"2025-03-28 20:00:00\",\"source_energy_sha256\":\"120edc90e5e9b18a88b5361266ca3f7f7e9000b8fa8b0d0b0abb5a3924c672ae\",\"original_p_kw\":0,\"original_min_v_pu\":0.9494387373935768,\"zero_min_v_pu\":0.9494387373935768,\"ceiling_kw\":3.06492717,\"ceiling_min_v_pu\":0.9611908191437835,\"ceiling_pass\":true,\"tested_lower_kw\":0.15336915179980468,\"tested_upper_kw\":3.06492717,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_min_cost_ref\",\"timestamp_lst\":\"2025-11-16 20:00:00\",\"source_energy_sha256\":\"120edc90e5e9b18a88b5361266ca3f7f7e9000b8fa8b0d0b0abb5a3924c672ae\",\"original_p_kw\":0,\"original_min_v_pu\":0.9484245161144307,\"zero_min_v_pu\":0.9484245161144307,\"ceiling_kw\":3.1764378588,\"ceiling_min_v_pu\":0.9606229403711066,\"ceiling_pass\":true,\"tested_lower_kw\":0.41217301600919926,\"tested_upper_kw\":3.1764378588,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_min_cost_ref\",\"timestamp_lst\":\"2025-11-27 20:00:00\",\"source_energy_sha256\":\"120edc90e5e9b18a88b5361266ca3f7f7e9000b8fa8b0d0b0abb5a3924c672ae\",\"original_p_kw\":0,\"original_min_v_pu\":0.9495815904523528,\"zero_min_v_pu\":0.9495815904523528,\"ceiling_kw\":3.2067823769,\"ceiling_min_v_pu\":0.9618826623297987,\"ceiling_pass\":true,\"tested_lower_kw\":0.11678835844950196,\"tested_upper_kw\":3.2067823769,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_ss90_ref\",\"timestamp_lst\":\"2025-11-27 20:00:00\",\"source_energy_sha256\":\"90367bab85b649462d3b7178f5e65d1d954d7650b59241b8052bab66e6183f4e\",\"original_p_kw\":0,\"original_min_v_pu\":0.9495815904523528,\"zero_min_v_pu\":0.9495815904523528,\"ceiling_kw\":3.2067823769,\"ceiling_min_v_pu\":0.9618826623297987,\"ceiling_pass\":true,\"tested_lower_kw\":0.11678835844950196,\"tested_upper_kw\":3.2067823769,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_P34_B8\",\"timestamp_lst\":\"2025-11-27 20:00:00\",\"source_energy_sha256\":\"6380b3bbe6536f0d45df1164cda2495a4ec97c999653d7e4f7116ce2a9d1b08b\",\"original_p_kw\":0,\"original_min_v_pu\":0.9495815904523528,\"zero_min_v_pu\":0.9495815904523528,\"ceiling_kw\":3.2067823769,\"ceiling_min_v_pu\":0.9618826623297987,\"ceiling_pass\":true,\"tested_lower_kw\":0.11678835844950196,\"tested_upper_kw\":3.2067823769,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_P30_B8\",\"timestamp_lst\":\"2025-11-27 20:00:00\",\"source_energy_sha256\":\"6b5a9e494ca80c84a6306b116f9b75a2e4a8bf2d26bdd906747a8eccc80736d4\",\"original_p_kw\":0,\"original_min_v_pu\":0.9495815904523528,\"zero_min_v_pu\":0.9495815904523528,\"ceiling_kw\":3.2067823769,\"ceiling_min_v_pu\":0.9618826623297987,\"ceiling_pass\":true,\"tested_lower_kw\":0.11678835844950196,\"tested_upper_kw\":3.2067823769,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_P34_B7\",\"timestamp_lst\":\"2025-03-28 20:00:00\",\"source_energy_sha256\":\"9ff8435e6b09bc44866c5d24c5f319709f67ed019f123e70677ac1acbcfccb7d\",\"original_p_kw\":0,\"original_min_v_pu\":0.9494387373935768,\"zero_min_v_pu\":0.9494387373935768,\"ceiling_kw\":3.06492717,\"ceiling_min_v_pu\":0.9611908191437835,\"ceiling_pass\":true,\"tested_lower_kw\":0.15336915179980468,\"tested_upper_kw\":3.06492717,\"status\":\"TESTED_TERMINAL_CORRIDOR\"},{\"case\":\"A1_94022_P34_B7\",\"timestamp_lst\":\"2025-11-27 20:00:00\",\"source_energy_sha256\":\"9ff8435e6b09bc44866c5d24c5f319709f67ed019f123e70677ac1acbcfccb7d\",\"original_p_kw\":0.0620962245,\"original_min_v_pu\":0.9498252467237503,\"zero_min_v_pu\":0.9495815904523528,\"ceiling_kw\":3.2067823769,\"ceiling_min_v_pu\":0.9618826623297987,\"ceiling_pass\":true,\"tested_lower_kw\":0.11678835844950196,\"tested_upper_kw\":3.2067823769,\"status\":\"TESTED_TERMINAL_CORRIDOR\"}]")
CASES=tuple(r["case"] for r in prev.FAILED)
PF=.95
LENGTH=1.6
FACTORS=src.FACTORS

def plan_gate():
    prev.check_plan()
    if len(set(CASES))!=6 or set(CASES)&set(prev.SELECTED) or set(CASES)|set(prev.SELECTED)!=set(prev.EXPECTED):
        raise ValueError("Reserve case population")
    expected={(r["case"],t) for r in prev.FAILED for t in r["first_failed_timestamps"]}
    if len(EVENTS)!=9 or {(e["case"],e["timestamp_lst"]) for e in EVENTS}!=expected or any(e["status"]!="TESTED_TERMINAL_CORRIDOR" or not e["ceiling_pass"] or e["source_energy_sha256"]!=prev.EXPECTED[e["case"]] for e in EVENTS):
        raise ValueError("Prior event identity")

def common_night(x):
    f=x["frames"][src.REF]
    night=f.index[f.pv_dc_available_kw<=1e-9]
    if len(night)!=4353 or not f.index.equals(pd.date_range("2025-01-01",periods=8760,freq="h")):
        raise ValueError("Annual night chronology")
    for c,other in x["frames"].items():
        if not other.index.equals(f.index) or not np.allclose(other.demand_kw,f.demand_kw,rtol=0,atol=1e-7) or not other.index[other.pv_dc_available_kw<=1e-9].equals(night):
            raise ValueError("Common night/load identity")
        h=x["hardware"][c]
        if h["transformer_kva_assumed_or_evidenced"]!=5. or (other.loc[night,"demand_kw"]>min(h["inverter_kva"],.95*h["battery_power_dc_kw"])+1e-9).any():
            raise ValueError("Shared zero-export ceiling cannot be assumed")
    return night

def screen(prepared,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    night=common_night(x);terr=x["territories"][LENGTH]
    net,meta=build_net(terr,"head")
    if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
    common=src.REF;f=x["frames"][common]
    def measure(t,p,c=common):
        q=prev.checked(v6,pp,net,meta,terr,x,c,t,PF,p)
        if not q["night_reactive_disabled"]:raise ValueError("Not a night probe")
        return q
    endpoint_checks=0
    for e in EVENTS:
        t=pd.Timestamp(e["timestamp_lst"]);c=e["case"]
        if t not in night:raise ValueError("Prior event chronology")
        for p,k in ((e["original_p_kw"],"original_min_v_pu"),(0.,"zero_min_v_pu"),(e["ceiling_kw"],"ceiling_min_v_pu")):
            q=measure(t,p,c)
            if abs(q["min_v_pu"]-e[k])>1e-8:raise ValueError("Prior event regression")
            if k=="original_min_v_pu" and rn.strict_point(q):raise ValueError("Original fail changed")
            if k=="ceiling_min_v_pu" and not rn.strict_point(q):raise ValueError("Ceiling pass changed")
            endpoint_checks+=1
        for p in (e["tested_lower_kw"],e["tested_upper_kw"]):
            if not rn.strict_point(measure(t,p,c)):raise ValueError("Prior corridor endpoint")
            endpoint_checks+=1
    if endpoint_checks!=45:raise ValueError("Event regression coverage")
    rows=[];probes=[]
    for i,t in enumerate(night):
        cap=follow.power_ceiling(float(f.at[t,"demand_kw"]),x["hardware"][common])
        if cap<=0:raise ValueError("Nonpositive ceiling")
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
            grid_count=sum(ok(p) for p in np.linspace(0,cap,21))
            if h_ok:
                bounds=rn.interval(ok,cap)
                if bounds is not None:
                    lower,upper=map(float,bounds);status="TESTED_TERMINAL_CORRIDOR"
                else:status="NO_TESTED_TERMINAL_CORRIDOR"
            else:status="INTERIOR_OR_ZERO_ONLY_PASS" if grid_count else "NO_TESTED_FEASIBLE_POINT"
            for p,q in sorted(cache.items()):
                probes.append(dict(timestamp_lst=str(t),probe_p_kw=p,strict_feasible=rn.strict_point(q),
                    min_v_pu=q["min_v_pu"],max_v_pu=q["max_v_pu"],max_trafo_pct=q["max_trafo_pct"],
                    max_line_pct=q["max_line_pct"],loss_kw=q["loss_kw"]))
        rows.append(dict(timestamp_lst=str(t),gross_demand_kw=float(f.at[t,"demand_kw"]),ceiling_kw=cap,
            zero_pass=z_ok,ceiling_pass=h_ok,zero_min_v_pu=z["min_v_pu"],ceiling_min_v_pu=h["min_v_pu"],
            zero_max_v_pu=z["max_v_pu"],ceiling_max_v_pu=h["max_v_pu"],zero_trafo_pct=z["max_trafo_pct"],
            ceiling_trafo_pct=h["max_trafo_pct"],zero_line_pct=z["max_line_pct"],ceiling_line_pct=h["max_line_pct"],
            grid_pass_count=grid_count,lower_kw=lower,upper_kw=upper,status=status))
        if (i+1)%500==0:print("A1 night screen",i+1,"/",len(night),flush=True)
    a=pd.DataFrame(rows)
    if len(a)!=4353 or not a.timestamp_lst.is_unique:raise ValueError("Night coverage")
    a.to_csv(OUT/"A1_HEAD_NIGHT_SCREEN.csv",index=False)
    pd.DataFrame(probes,columns=["timestamp_lst","probe_p_kw","strict_feasible","min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw"]).to_csv(OUT/"A1_HEAD_NIGHT_PROBES.csv",index=False)
    limits=a[a.status.eq("TESTED_TERMINAL_CORRIDOR")]
    corridors={pd.Timestamp(r.timestamp_lst):(float(r.lower_kw),float(r.upper_kw)) for r in limits.itertuples()}
    unresolved=a[~a.status.isin(["TESTED_TERMINAL_CORRIDOR","BOTH_ENDPOINTS_PASS_NOT_CONTINUOUS_PROOF"])]
    report.update(night_hours=len(a),endpoint_evaluations=2*len(a),prior_event_regressions=endpoint_checks,
        zero_failures=int((~a.zero_pass).sum()),ceiling_failures=int((~a.ceiling_pass).sum()),
        status_counts={str(k):int(v) for k,v in a.status.value_counts().items()},
        diagnostic_probe_records=len(probes),min_zero_voltage=float(a.zero_min_v_pu.min()),
        min_ceiling_voltage=float(a.ceiling_min_v_pu.min()),corridor_count=len(corridors),
        tested_lower_sum_kwh=float(limits.lower_kw.sum()),tested_lower_peak_kw=float(limits.lower_kw.max()) if len(limits) else None,
        unresolved_hours=len(unresolved),unresolved_first_30=unresolved.timestamp_lst.head(30).tolist())
    print("NIGHT_SCREEN="+json.dumps({k:report[k] for k in ("night_hours","zero_failures","ceiling_failures","corridor_count","unresolved_hours","tested_lower_sum_kwh","tested_lower_peak_kw")},allow_nan=False),flush=True)
    save(OUT/"PARTIAL_RESULTS.json",report)
    if len(unresolved) or report["ceiling_failures"] or len(corridors)!=report["zero_failures"]:
        return None
    if not {pd.Timestamp(e["timestamp_lst"]) for e in EVENTS}.issubset(corridors):
        raise ValueError("Known adverse events missing from full-night screen")
    return corridors

def reserve(prepared,old_hours,corridors,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    corrected={};metrics=[];errors=[];hashes={}
    report.update(energy_results=metrics,solver_infeasible=errors)
    hours=set(old_hours)|set(corridors)
    for c in CASES:
        h=x["hardware"][c];old=x["frames"][c]
        hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
            battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
            transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,load_pf=.98,
            export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        print("Reserve LP",c,flush=True)
        try:f,sm=fh.solve_fixed(ROOT,hw,x["demand"],x["solar"],corridors=corridors,min_physical_soc=.20)
        except RuntimeError as exc:
            if "infeasible" not in str(exc).lower():raise
            errors.append(dict(case=c,error=str(exc)));continue
        f.index.name="timestamp_lst";sizing.validate_comparison(f,h,x["demand"],x["solar"])
        path=OUT/(c+"_HEAD_RESERVE_8760.csv");f.to_csv(path,float_format="%.10f")
        f=read_frame(path);sizing.validate_comparison(f,h,x["demand"],x["solar"])
        for t,(lo,hi) in corridors.items():
            if not lo-1e-6<=float(f.at[t,"inverter_ac_kw"])<=hi+1e-6:raise ValueError("Reserve constraint")
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        changed=old.inverter_ac_kw.ne(f.inverter_ac_kw)
        hours.update(f.index[changed])
        r=sizing.summary(c,"A1_94022_eight_house","OFFLINE_HEAD_RESERVE",h,f,sm)
        r.update(source_energy_sha256=prev.EXPECTED[c],corrected_energy_sha256=sha,
            changed_inverter_hours=int(changed.sum()),
            delta_import_kwh=float(f.grid_import_kw.sum()-old.grid_import_kw.sum()),
            delta_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()-old.curtailed_pv_dc_kw.sum()),
            delta_annual_cost_usd=float(sm["annual_total_usd"])-float(x["models"][c]["annual_total_usd"]))
        metrics.append(r);corrected[c]=f;hashes[c]=sha
        print("RESERVE_ENERGY="+json.dumps(r,allow_nan=False),flush=True)
    if len(metrics)+len(errors)!=6:raise ValueError("LP population")
    pd.DataFrame(metrics).to_csv(OUT/"A1_HEAD_RESERVE_ENERGY_SUMMARY.csv",index=False)
    report.update(new_LPs_optimal=len(metrics),planned_LPs=6)
    if not corrected:
        report["status"]="COMPLETE_NIGHT_SCREEN_NO_OPTIMAL_RESERVE";return
    hours=sample.pick_hours(corrected,hours)
    pd.DataFrame({"timestamp_lst":hours}).to_csv(OUT/"RESERVE_COMMON_SAMPLE_HOURS.csv",index=False)
    report.update(common_sample_hours=len(hours),planned_new_sample_case_hours=len(corrected)*len(hours)*9)
    rows=[];summary=[]
    for pf,l in FACTORS:
        terr=x["territories"][l]
        for c,f in corrected.items():
            net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
            new=dict(x,frames={c:f})
            local=[]
            for t in hours:
                q=prev.checked(v6,pp,net,meta,terr,new,c,t,pf)
                q.update(case=c,pf=pf,length_factor=l,source_energy_sha256=prev.EXPECTED[c],
                    corrected_energy_sha256=hashes[c],support_corridor=t in corridors,
                    changed_P=bool(x["frames"][c].at[t,"inverter_ac_kw"]!=f.at[t,"inverter_ac_kw"]),
                    strict_feasible=rn.strict_point(q))
                local.append(q)
            a=pd.DataFrame(local)
            r=dict(case=c,pf=pf,length_factor=l,sampled_hours=len(a),**prev.stats(a),
                first_failed_timestamps=a.loc[~a.strict_feasible,"timestamp_lst"].astype(str).head(30).tolist(),
                corrected_energy_sha256=hashes[c])
            rows.extend(local);summary.append(r)
            print("RESERVE_SAMPLE="+json.dumps(r,allow_nan=False),flush=True)
    a=pd.DataFrame(rows)
    if len(a)!=len(corrected)*len(hours)*9 or a.duplicated(["case","pf","length_factor","timestamp_lst"]).any():raise ValueError("Sample coverage")
    a.to_csv(OUT/"A1_HEAD_RESERVE_SAMPLE_HOURLY.csv",index=False)
    pd.DataFrame(summary).to_csv(OUT/"A1_HEAD_RESERVE_SAMPLE_SUMMARY.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    screen_rows=pd.read_csv(OUT/"A1_HEAD_NIGHT_SCREEN.csv")
    ax[0].scatter(screen_rows.gross_demand_kw,screen_rows.zero_min_v_pu,s=8,alpha=.4,label="Zero injection")
    ax[0].scatter(screen_rows.gross_demand_kw,screen_rows.ceiling_min_v_pu,s=8,alpha=.4,label="Zero-export ceiling")
    ax[0].axhline(.95,ls="--",color="firebrick");ax[0].set(xlabel="Gross demand (kW)",ylabel="Minimum voltage (pu)")
    ax[0].legend(fontsize=8)
    for r in metrics:
        c=r["case"];passed=all(g["strict_failures"]==0 for g in summary if g["case"]==c)
        ax[1].scatter(r["curtail_dc_kwh"],r["annual_total_usd"],marker="o" if passed else "x",label=c.replace("A1_94022_","").replace("A0_94022_",""))
    ax[1].set(xlabel="Annual DC curtailment (kWh)",ylabel="Energy model cost (USD/year)")
    ax[1].legend(fontsize=7)
    fig.suptitle("94022 A1 | annual night support, reserve energy and sampled AC")
    for ext in ("png","svg"):fig.savefig(OUT/("A1_head_reserve."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_A1_HEAD_NIGHT_RESERVE_SAMPLE",new_sample_case_hours=len(rows),
        completed_groups=len(summary),passing_groups=sum(r["strict_failures"]==0 for r in summary),summary=summary)

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),
        runner_id=os.environ.get("CI_RUNNER_ID"),prior_annual_job=18401857334,prior_sizing_job=18401211927,
        planned_cases=list(CASES),planned_LPs=6,planned_night_hours=4353,factors=[list(z) for z in FACTORS],
        field_verified=False,offline_perfect_foresight=True,annual_AC_verified=False,night_Q_disabled=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_A1_94022_annual.py","test_remote_A1_94022_reserve.py","test_reserve_full_night.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        plan_gate()
        prepared=src.prepare()
        _,_,_,x=prepared
        if x["signatures"]!={c:prev.EXPECTED[c] for c in x["frames"]} or set(x["candidates"])!=set(prev.EXPECTED)-set(x["frames"]):raise ValueError("Preflight source set")
        common_night(x)
        if preflight:report["status"]="COMPLETE_SIGNED_A1_HEAD_RESERVE_PREFLIGHT"
        else:
            hours=prev.restore_schedules(prepared,report)
            corridors=screen(prepared,report)
            if corridors is None:report["status"]="COMPLETE_NIGHT_SCREEN_UNRESOLVED_NO_RESERVE"
            else:reserve(prepared,hours,corridors,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"A1_HEAD_RESERVE_REPORT.json",report)
        print("A1_HEAD_RESERVE_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_A1_HEAD_RESERVE_PREFLIGHT","COMPLETE_NIGHT_SCREEN_UNRESOLVED_NO_RESERVE","COMPLETE_NIGHT_SCREEN_NO_OPTIMAL_RESERVE","COMPLETE_A1_HEAD_NIGHT_RESERVE_SAMPLE") else 1

if __name__=="__main__":raise SystemExit(main())
