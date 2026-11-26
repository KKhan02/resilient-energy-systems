#!/usr/bin/env python3
"""A1 eight-house 94022: exact sizing schedules, annual reference/stress and failed-event probes."""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import remote_94022_A1_sizing as src
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import sizing_ac_followup as follow
import reserve_full_night as rn
from audit_battery_coverage import read_frame

EXPECTED=json.loads("{\"A0_94022_ss90_to_A1\":\"352b693570129ec6a2d4aa5bfa1cceb1a3c66a7b6f96a6527c5a0e365c37e1c0\",\"A0_94022_min_cost_to_A1\":\"ef6172e9e1a9ebb2b45d819208765dd4a9de440dd48412b79eae59eecae370e1\",\"A1_94022_min_cost_ref\":\"120edc90e5e9b18a88b5361266ca3f7f7e9000b8fa8b0d0b0abb5a3924c672ae\",\"A1_94022_ss90_ref\":\"90367bab85b649462d3b7178f5e65d1d954d7650b59241b8052bab66e6183f4e\",\"A1_94022_P37_B8\":\"b5c70e7bd4e97e64143bbfa32cb2146d64a5c0367117b5028f0c7195edaddcaa\",\"A1_94022_P34_B8\":\"6380b3bbe6536f0d45df1164cda2495a4ec97c999653d7e4f7116ce2a9d1b08b\",\"A1_94022_P30_B8\":\"6b5a9e494ca80c84a6306b116f9b75a2e4a8bf2d26bdd906747a8eccc80736d4\",\"A1_94022_P41_B7\":\"06dbead80c69755b41c2275fe329791d6c72a310702b6176a950f5c132da0d2e\",\"A1_94022_P34_B7\":\"9ff8435e6b09bc44866c5d24c5f319709f67ed019f123e70677ac1acbcfccb7d\"}")
PRIOR=json.loads("[{\"case\":\"A0_94022_ss90_to_A1\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9509528945195984,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":57.355551581536346,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":24,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"energy_sha256\":\"352b693570129ec6a2d4aa5bfa1cceb1a3c66a7b6f96a6527c5a0e365c37e1c0\"},{\"case\":\"A1_94022_P37_B8\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9509528945195984,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":67.67052536002161,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":27,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"energy_sha256\":\"b5c70e7bd4e97e64143bbfa32cb2146d64a5c0367117b5028f0c7195edaddcaa\"},{\"case\":\"A1_94022_P41_B7\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9509528945195984,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":58.0897325914529,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":24,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"energy_sha256\":\"06dbead80c69755b41c2275fe329791d6c72a310702b6176a950f5c132da0d2e\"},{\"case\":\"A0_94022_ss90_to_A1\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9624791616071331,\"maximum_voltage_pu\":0.9976690617354131,\"peak_transformer_pct\":55.16072612165869,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":6,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"energy_sha256\":\"352b693570129ec6a2d4aa5bfa1cceb1a3c66a7b6f96a6527c5a0e365c37e1c0\"},{\"case\":\"A1_94022_P37_B8\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.960328911136701,\"maximum_voltage_pu\":0.9976690617354131,\"peak_transformer_pct\":65.14129164709959,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":10,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"energy_sha256\":\"b5c70e7bd4e97e64143bbfa32cb2146d64a5c0367117b5028f0c7195edaddcaa\"},{\"case\":\"A1_94022_P41_B7\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9620775874877406,\"maximum_voltage_pu\":0.9976690617354131,\"peak_transformer_pct\":55.918751256446264,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":8,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"energy_sha256\":\"06dbead80c69755b41c2275fe329791d6c72a310702b6176a950f5c132da0d2e\"}]")
FAILED=json.loads("[{\"case\":\"A0_94022_min_cost_to_A1\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":1,\"night_failures\":1,\"daylight_failures\":0,\"low_voltage_hours\":1,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9495815904523528,\"maximum_voltage_pu\":0.996426283104658,\"peak_transformer_pct\":71.28290512040194,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":30,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[\"2025-11-27 20:00:00\"],\"energy_sha256\":\"ef6172e9e1a9ebb2b45d819208765dd4a9de440dd48412b79eae59eecae370e1\"},{\"case\":\"A1_94022_min_cost_ref\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":3,\"night_failures\":3,\"daylight_failures\":0,\"low_voltage_hours\":3,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9484245161144307,\"maximum_voltage_pu\":0.9953739742824625,\"peak_transformer_pct\":79.69892725530171,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":30,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[\"2025-03-28 20:00:00\",\"2025-11-16 20:00:00\",\"2025-11-27 20:00:00\"],\"energy_sha256\":\"120edc90e5e9b18a88b5361266ca3f7f7e9000b8fa8b0d0b0abb5a3924c672ae\"},{\"case\":\"A1_94022_ss90_ref\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":1,\"night_failures\":1,\"daylight_failures\":0,\"low_voltage_hours\":1,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9495815904523528,\"maximum_voltage_pu\":0.996426283104658,\"peak_transformer_pct\":71.28290512040194,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":29,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[\"2025-11-27 20:00:00\"],\"energy_sha256\":\"90367bab85b649462d3b7178f5e65d1d954d7650b59241b8052bab66e6183f4e\"},{\"case\":\"A1_94022_P34_B8\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":1,\"night_failures\":1,\"daylight_failures\":0,\"low_voltage_hours\":1,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9495815904523528,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":71.28290512040194,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":29,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[\"2025-11-27 20:00:00\"],\"energy_sha256\":\"6380b3bbe6536f0d45df1164cda2495a4ec97c999653d7e4f7116ce2a9d1b08b\"},{\"case\":\"A1_94022_P30_B8\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":1,\"night_failures\":1,\"daylight_failures\":0,\"low_voltage_hours\":1,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9495815904523528,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":78.60231617244781,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":29,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[\"2025-11-27 20:00:00\"],\"energy_sha256\":\"6b5a9e494ca80c84a6306b116f9b75a2e4a8bf2d26bdd906747a8eccc80736d4\"},{\"case\":\"A1_94022_P34_B7\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":55,\"converged\":55,\"strict_failures\":2,\"night_failures\":2,\"daylight_failures\":0,\"low_voltage_hours\":2,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9494387373935768,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":70.0763830394785,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":29,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[\"2025-03-28 20:00:00\",\"2025-11-27 20:00:00\"],\"energy_sha256\":\"9ff8435e6b09bc44866c5d24c5f319709f67ed019f123e70677ac1acbcfccb7d\"}]")
SELECTED=(src.REF,"A1_94022_P37_B8","A1_94022_P41_B7")
FACTORS=((.98,1.),(.95,1.6))
HOURS_SHA="4229a3391c7939bd6430c74c65899b625d0cc07a2a522102639f2d5db689c9f3"

def check_plan():
    expected={(c,pf,l) for c in SELECTED for pf,l in FACTORS}
    actual={(r["case"],r["pf"],r["length_factor"]) for r in PRIOR}
    if expected!=actual or len(PRIOR)!=6 or any(r["strict_failures"] or r["sampled_hours"]!=55 or r["energy_sha256"]!=EXPECTED[r["case"]] for r in PRIOR):
        raise ValueError("Selected annual evidence plan")
    if len(FAILED)!=6 or sum(r["strict_failures"] for r in FAILED)!=9 or any(r["pf"]!=.95 or r["length_factor"]!=1.6 or r["daylight_failures"] or r["night_failures"]!=r["strict_failures"] or len(r["first_failed_timestamps"])!=r["strict_failures"] or r["energy_sha256"]!=EXPECTED[r["case"]] for r in FAILED):
        raise ValueError("Failed event plan")
    if len({t for r in FAILED for t in r["first_failed_timestamps"]})!=3:
        raise ValueError("Failed event timestamps")

def restore_schedules(prepared,report):
    fh,v6,annual,x=prepared
    for c,h in x["candidates"].items():
        hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
            battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
            transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,load_pf=.98,
            export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        f,sm=fh.solve_fixed(ROOT,hw,x["demand"],x["solar"],min_physical_soc=.20)
        f.index.name="timestamp_lst"
        sizing.validate_comparison(f,h,x["demand"],x["solar"])
        path=OUT/(c+"_8760.csv");f.to_csv(path,float_format="%.10f")
        got=hashlib.sha256(path.read_bytes()).hexdigest()
        if got!=EXPECTED[c]:raise ValueError("Prior schedule hash mismatch "+c)
        f=read_frame(path);sizing.validate_comparison(f,h,x["demand"],x["solar"])
        x["frames"][c]=f;x["hardware"][c]=h;x["signatures"][c]=got;x["models"][c]=sm
    if x["signatures"]!=EXPECTED:raise ValueError("Schedule identity set")
    hours=sample.pick_hours(x["frames"],x["bench"].timestamp_lst)
    path=OUT/"COMMON_SAMPLE_HOURS.csv"
    pd.DataFrame({"timestamp_lst":hours}).to_csv(path,index=False)
    if len(hours)!=55 or hashlib.sha256(path.read_bytes()).hexdigest()!=HOURS_SHA:
        raise ValueError("Prior common hour hash mismatch")
    report.update(verified_energy_schedules=9,reconstructed_LPs=5,common_hours=55,prior_sample_repeated=False)
    return set(hours)

def checked(v6,pp,net,meta,terr,x,c,t,pf,p=None):
    q=follow.evaluate(v6,pp,net,meta,terr,x,c,t,pf,p=p)
    if q["status"]!="CONVERGED" or not np.isfinite([q[k] for k in ("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw")]).all():
        raise ValueError("Nonconverged/nonfinite "+c+" "+str(t))
    if bool(q["night_reactive_disabled"])!=bool(x["frames"][c].at[t,"pv_dc_available_kw"]<=1e-9) or (q["night_reactive_disabled"] and abs(float(q["q_selected_kvar"]))>1e-9):
        raise ValueError("Night Q policy")
    return q

def stats(a):
    bad=~a.strict_feasible
    return dict(converged=len(a),strict_failures=int(bad.sum()),
        night_failures=int((bad&a.night_reactive_disabled).sum()),daylight_failures=int((bad&~a.night_reactive_disabled).sum()),
        low_voltage_hours=int(a.min_v_pu.lt(.95).sum()),high_voltage_hours=int(a.max_v_pu.gt(1.05).sum()),
        transformer_overload_hours=int(a.max_trafo_pct.gt(100).sum()),line_overload_hours=int(a.max_line_pct.gt(100).sum()),
        minimum_voltage_pu=float(a.min_v_pu.min()),maximum_voltage_pu=float(a.max_v_pu.max()),
        peak_transformer_pct=float(a.max_trafo_pct.max()),peak_line_pct=float(a.max_line_pct.max()),
        optional_under_097_hours=int(a.min_v_pu.lt(.97).sum()),optional_above_103_hours=int(a.max_v_pu.gt(1.03).sum()))

def sample_regression(actual,expected):
    for k,v in actual.items():
        tol=1e-7 if k in ("minimum_voltage_pu","maximum_voltage_pu","peak_transformer_pct","peak_line_pct") else 0
        if abs(v-expected[k])>tol:raise ValueError("Sample summary regression "+k)

def event_probes(prepared,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    rows=[];events=[]
    terr=x["territories"][1.6]
    for r in FAILED:
        c=r["case"];f=x["frames"][c];h=x["hardware"][c]
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
        for ts in r["first_failed_timestamps"]:
            t=pd.Timestamp(ts)
            if f.at[t,"pv_dc_available_kw"]>1e-9:raise ValueError("Not a night event")
            old=checked(v6,pp,net,meta,terr,x,c,t,.95)
            if rn.strict_point(old):raise ValueError("Failed sample no longer fails")
            cap=follow.power_ceiling(f.at[t,"demand_kw"],h)
            def measure(p):
                q=checked(v6,pp,net,meta,terr,x,c,t,.95,p)
                ok=rn.strict_point(q)
                rows.append(dict(case=c,requested_p_kw=float(p),strict_feasible=ok,**q))
                return ok
            bounds=rn.interval(measure,cap)
            qmax=checked(v6,pp,net,meta,terr,x,c,t,.95,cap)
            qzero=checked(v6,pp,net,meta,terr,x,c,t,.95,0.)
            event=dict(case=c,timestamp_lst=str(t),source_energy_sha256=EXPECTED[c],original_p_kw=float(f.at[t,"inverter_ac_kw"]),
                original_min_v_pu=float(old["min_v_pu"]),zero_min_v_pu=float(qzero["min_v_pu"]),
                ceiling_kw=float(cap),ceiling_min_v_pu=float(qmax["min_v_pu"]),ceiling_pass=rn.strict_point(qmax),
                tested_lower_kw=None if bounds is None else float(bounds[0]),tested_upper_kw=None if bounds is None else float(bounds[1]),
                status="NO_TESTED_TERMINAL_CORRIDOR" if bounds is None else "TESTED_TERMINAL_CORRIDOR")
            events.append(event);print("EVENT_RESULT="+json.dumps(event,allow_nan=False),flush=True)
    if len(events)!=9 or len({(e["case"],e["timestamp_lst"]) for e in events})!=9:
        raise ValueError("Probe event coverage")
    pd.DataFrame(rows).to_csv(OUT/"FAILED_NIGHT_PROBES.csv",index=False)
    pd.DataFrame(events).to_csv(OUT/"FAILED_NIGHT_EVENT_SUMMARY.csv",index=False)
    report.update(event_results=events,event_probe_records=len(rows),static_corridors_found=sum(e["tested_lower_kw"] is not None for e in events))
    save(OUT/"PARTIAL_RESULTS.json",report)

def annual_validation(prepared,hours,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    results=[];checks=0;summary_checks=0
    report["annual_results"]=results
    bench=x["bench"].set_index(["case","pf","timestamp_lst"])
    for c in SELECTED:
        f=x["frames"][c]
        for pf,l in FACTORS:
            terr=x["territories"][l];net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
            rows=[]
            for i,t in enumerate(f.index):
                q=checked(v6,pp,net,meta,terr,x,c,t,pf)
                if l==1. and (c,pf,t) in bench.index:
                    annual.exact_ac_regression(q,bench.loc[(c,pf,t)].to_dict(),c+" "+str(t));checks+=1
                q.update(case=c,pf=pf,length_factor=l,source_energy_sha256=EXPECTED[c],
                    source_grid_import_kw=float(f.at[t,"grid_import_kw"]),strict_feasible=rn.strict_point(q))
                rows.append(q)
                if (i+1)%2000==0:print("Annual",c,pf,l,i+1,flush=True)
            a=pd.DataFrame(rows)
            if len(a)!=8760 or not pd.DatetimeIndex(pd.to_datetime(a.timestamp_lst)).equals(f.index):
                raise ValueError("Annual chronology")
            select=a[pd.to_datetime(a.timestamp_lst).isin(hours)]
            expected=next(r for r in PRIOR if r["case"]==c and r["pf"]==pf and r["length_factor"]==l)
            if len(select)!=55:raise ValueError("Annual sample coverage")
            sample_regression(stats(select),expected);summary_checks+=55
            name=c+"_PF"+str(round(pf*100))+"_L"+str(round(l*10))+"_ANNUAL_AC.csv"
            annual.save_csv(OUT/name,rows)
            cost=float(x["models"][c]["annual_total_usd"]);loss=float(a.loss_kw.sum())
            result=dict(case=c,pf=pf,length_factor=l,hours=8760,source_energy_sha256=EXPECTED[c],
                **stats(a),losses_kwh=loss,annual_energy_cost_usd=cost,all_loss_purchase_cost_usd=cost+.29*loss,
                annual_import_kwh=float(f.grid_import_kw.sum()),annual_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),
                failed_timestamps_first_30=a.loc[~a.strict_feasible,"timestamp_lst"].astype(str).head(30).tolist(),
                output_sha256=hashlib.sha256((OUT/name).read_bytes()).hexdigest())
            results.append(result);print("ANNUAL_RESULT="+json.dumps(result,allow_nan=False),flush=True)
            save(OUT/"PARTIAL_RESULTS.json",report)
    if checks!=25 or summary_checks!=330 or len(results)!=6:
        raise ValueError("Annual regression coverage")
    pd.DataFrame(results).to_csv(OUT/"ANNUAL_AC_SUMMARY.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a=pd.DataFrame(results)
    fig,ax=plt.subplots(1,2,figsize=(11,4.7),layout="constrained")
    for i,(pf,l) in enumerate(FACTORS):
        s=a[a.pf.eq(pf)&a.length_factor.eq(l)].set_index("case").loc[list(SELECTED)]
        xx=np.arange(3)+(i-.5)*.36
        ax[0].bar(xx,s.minimum_voltage_pu,.36,label=f"PF {pf}, length {l}")
        ax[1].bar(xx,s.all_loss_purchase_cost_usd,.36,label=f"PF {pf}, length {l}")
    ax[0].axhline(.95,ls="--",color="firebrick")
    ax[0].set_ylim(min(.93,float(a.minimum_voltage_pu.min())-.002),1.05)
    ax[0].set_ylabel("Annual minimum voltage (pu)")
    ax[1].set_ylabel("Annual modeled cost incl. loss sensitivity (USD)")
    for z in ax:z.set_xticks(range(3),["Reference","P37 B8","P41 B7"]);z.legend(fontsize=8)
    fig.suptitle("94022 A1 | annual AC and cost, original head placement")
    for ext in ("png","svg"):fig.savefig(OUT/("A1_94022_annual."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_A1_94022_ANNUAL_AND_EVENT_DIAGNOSTIC",historical_hour_regressions=checks,
        sampled_case_hours_reconciled=summary_checks,annual_sample_summary_groups=6,new_AC_case_hours=52560,
        annual_passing_groups=sum(r["strict_failures"]==0 for r in results))

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),
        runner_id=os.environ.get("CI_RUNNER_ID"),prior_job=18401211927,expected_schedule_hashes=EXPECTED,
        selected_cases=list(SELECTED),factors=[list(z) for z in FACTORS],planned_annual_AC_case_hours=52560,
        planned_failed_events=9,field_verified=False,offline_perfect_foresight=True,
        no_new_equipment_design=True,no_new_dispatch_policy=True,night_Q_disabled=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_A1_94022_sizing.py","test_remote_A1_94022_annual.py","test_reserve_full_night.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        check_plan()
        prepared=src.prepare()
        _,_,_,x=prepared
        if x["signatures"]!={c:EXPECTED[c] for c in x["frames"]} or set(x["candidates"])!=set(EXPECTED)-set(x["frames"]):raise ValueError("Preflight source set")
        if preflight:report["status"]="COMPLETE_SIGNED_A1_94022_ANNUAL_PREFLIGHT"
        else:
            hours=restore_schedules(prepared,report)
            event_probes(prepared,report)
            annual_validation(prepared,hours,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"A1_94022_ANNUAL_REPORT.json",report)
        print("A1_94022_ANNUAL_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_A1_94022_ANNUAL_PREFLIGHT","COMPLETE_A1_94022_ANNUAL_AND_EVENT_DIAGNOSTIC") else 1

if __name__=="__main__":raise SystemExit(main())
