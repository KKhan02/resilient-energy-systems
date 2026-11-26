#!/usr/bin/env python3
"""Approved eight-house 94022 A1 fixed-hardware sizing and common risk sample."""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import sizing_ac_followup as follow
import reserve_full_night as rn
from audit_battery_coverage import BASE,signed,read_frame,read_json
import sizing_nine_factor as nf

REF="A0_94022_ss90_to_A1"
RECIP="A0_94022_min_cost_to_A1"
NATIVE=("A1_94022_min_cost_ref","A1_94022_ss90_ref")
REF_SHA="352b693570129ec6a2d4aa5bfa1cceb1a3c66a7b6f96a6527c5a0e365c37e1c0"
REF_HW=(41,8,11.366868519705127,12.,5.)
PLAN=(("A1_94022_P37_B8",37,8),("A1_94022_P34_B8",34,8),("A1_94022_P30_B8",30,8),
      ("A1_94022_P41_B7",41,7),("A1_94022_P34_B7",34,7))
FACTORS=nf.FACTORS
ARCHIVE="StudyA_Reciprocal12_P2P3_AC_Screen_v1"
ARCHIVE_SHA="e141e1a39c42279235a06e5f5c49a7057cec1642bc7639e8a66d67e4ce618d8f"
NATIVE_SHA=dict(zip(NATIVE,("120edc90e5e9b18a88b5361266ca3f7f7e9000b8fa8b0d0b0abb5a3924c672ae",
"90367bab85b649462d3b7178f5e65d1d954d7650b59241b8052bab66e6183f4e")))
HOUSE_IDS=["H01","H02","H26","H27","H28","H29","H34","H35"]

def new_designs(h):
    if sizing.hardware_tuple(h)!=REF_HW:raise ValueError("Reference hardware differs")
    return {name:dict(h,pv_panels=p,battery_modules=m) for name,p,m in PLAN}

def duplicate_guard(hardware,inventory):
    for name,h in hardware.items():
        for other,old in inventory.items():
            if np.allclose(sizing.hardware_tuple(h),sizing.hardware_tuple(old),rtol=0,atol=1e-8):
                raise ValueError("Duplicate same-cohort hardware: "+name+" / "+other)
    if len({sizing.hardware_tuple(h) for h in hardware.values()})!=len(hardware):
        raise ValueError("Duplicate new candidate")

def prepare():
    st,fh,m,mapping,profiles,solar,top,table,validate_device=sizing.context(ROOT)
    sys.path.insert(0,str(ROOT/sample.SYN))
    import matched16_94022_ss90_mar_nov_annual_ac as annual
    _,v6,_,_=st.secure_context(ROOT,ROOT/st.MANIFEST_REL)
    annual.check_source_stateless(v6)
    ids,trace=st.source_trace(m,mapping,profiles,"A1","94022")
    if ids!=HOUSE_IDS or abs(float(trace.sum().sum())-15184)>1e-5:
        raise ValueError("Eight-house population changed")
    demand=trace.sum(axis=1)
    frames={};hardware={};signatures={};models={}
    for c in (REF,RECIP):
        r=read_json(ROOT/sizing.MATCH/c/"CASE_RECEIPT.json")
        if r!=top["completed_cases"][c] or r["assignment_for_load"]!="A1" or r["transformer"]!="94022" or r["target_house_ids"]!=ids:
            raise ValueError("Reciprocal source identity "+c)
        path=ROOT/r["target_energy_csv"];h=r["hardware"];sha=r["target_energy_sha256"]
        if c==REF and (sha!=REF_SHA or sizing.hardware_tuple(h)!=REF_HW):raise ValueError("Reference changed")
        signed(path,sha);f=read_frame(path)
        frames[c]=f;hardware[c]=h;signatures[c]=sha;models[c]=r["target_model_summary"]
    for c in NATIVE:
        folder=ROOT/BASE/("energy_"+c);r=read_json(folder/"energy_manifest.json")
        if r["scenario"]!="A1" or r["transformer"]!="94022" or r["selected_house_ids"]!=ids or r["energy_csv_sha256"]!=NATIVE_SHA[c] or r["input_manifest_sha256"]!=top["input_manifest_sha256"]:
            raise ValueError("Native identity "+c)
        path=folder/"energy_hourly_2025.csv"
        signed(path,NATIVE_SHA[c]);f=read_frame(path)
        frames[c]=f;hardware[c]=r["hardware"];signatures[c]=NATIVE_SHA[c];models[c]=r["source_model_summary"]
    for c,f in frames.items():
        h=hardware[c];sizing.validate_comparison(f,h,demand,solar)
        q=table[table.case.eq(c)]
        if len(q)!=1 or q.iloc[0].source_sha!=signatures[c]:
            raise ValueError("Coverage identity "+c)
        for k,col in (("source_import_ac_kwh","grid_import_kw"),("source_curtail_dc_kwh","curtailed_pv_dc_kw")):
            if abs(float(q.iloc[0][k])-float(f[col].sum()))>1e-5:
                raise ValueError("Coverage energy mismatch "+c)
        if abs(float(models[c]["annual_grid_import_usd"])-.29*float(f.grid_import_kw.sum()))>1e-5:
            raise ValueError("Archived cost/import mismatch")
    candidates=new_designs(hardware[REF])
    # Existing A1 94022 native/reciprocal roster plus exact hardware tuple.
    inv={}
    for z in table.itertuples():
        c=z.case
        if "_94022_" in c and ((c.startswith("A1_") and "_to_" not in c) or c.endswith("_to_A1")):
            inv[c]=dict(pv_panels=int(z.pv_panels),battery_modules=int(z.battery_modules),
                battery_power_dc_kw=float(z.battery_power_dc_kw),inverter_kva=float(z.inverter_kva),
                transformer_kva_assumed_or_evidenced=float(z.transformer_kva))
    if set(inv)!=set(frames):raise ValueError("Unexpected same-cohort roster")
    duplicate_guard(candidates,inv)
    for h in candidates.values():validate_device(sizing.device_input(h))
    ar=read_json(ROOT/ARCHIVE/"RUN_MANIFEST.json")
    path=ROOT/ARCHIVE/"TARGETED_300_AC_CASEHOURS.csv"
    if ar["status"]!="P2P3_TARGETED_300_AC_CASEHOURS_RECORDED_NOT_ANNUAL" or ar["targeted_ac_csv_sha256"]!=ARCHIVE_SHA or ar["daytime_Q_ratio"]!=sample.Q:
        raise ValueError("Archived AC receipt changed")
    signed(path,ARCHIVE_SHA)
    a=pd.read_csv(path,parse_dates=["timestamp_lst"])
    if len(a)!=300 or a.duplicated(["case","pf","timestamp_lst"]).any():raise ValueError("Archive population")
    bench=a[a.case.isin([REF,RECIP])].copy()
    if len(bench)!=100 or not bench.status.eq("CONVERGED").all() or not bench.length_factor.eq(1.).all():raise ValueError("Archive control coverage")
    for (c,pf),g in bench.groupby(["case","pf"]):
        if len(g)!=25 or pf not in (.95,.98) or not g.source_sha256.eq(signatures[c]).all():raise ValueError("Archive identity")
        f=frames[c].loc[g.timestamp_lst]
        for ac,e in (("inverter_ac_kw","inverter_ac_kw"),("gross_demand_kw","demand_kw"),("grid_import_kw","grid_import_kw"),("pv_dc_available_kw","pv_dc_available_kw")):
            if not np.allclose(g[ac].to_numpy(),f[e].to_numpy(),rtol=0,atol=1e-6):raise ValueError("Archive source P mismatch")
    territories={l:v6.new_territory(ROOT,"A1","94022",ids,l) for l in (1.,1.3,1.6)}
    if any(float(t.trafo["kva"])!=5. or sorted(z["house"] for z in t.attachments)!=sorted(ids) for t in territories.values()):
        raise ValueError("GIS territory/rating mismatch")
    return fh,v6,annual,dict(ids=ids,trace=trace,frames=frames,hardware=hardware,signatures=signatures,
        models=models,candidates=candidates,territories=territories,bench=bench,demand=demand,solar=solar)

def solve(prepared,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    frames=x["frames"];hardware=x["hardware"];signatures=x["signatures"];models=x["models"]
    metrics=[];errors=[]
    report.update(energy_results=metrics,solver_infeasible=errors)
    for c,h in x["candidates"].items():
        hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
            battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
            transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,load_pf=.98,
            export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        print("Sizing LP",c,flush=True)
        try:f,sm=fh.solve_fixed(ROOT,hw,x["demand"],x["solar"],min_physical_soc=.20)
        except RuntimeError as exc:
            if "infeasible" not in str(exc).lower():raise
            errors.append(dict(case=c,error=str(exc)));continue
        f.index.name="timestamp_lst"
        sizing.validate_comparison(f,h,x["demand"],x["solar"])
        path=OUT/(c+"_8760.csv");f.to_csv(path,float_format="%.10f")
        f=read_frame(path);sizing.validate_comparison(f,h,x["demand"],x["solar"])
        frames[c]=f;hardware[c]=h;signatures[c]=hashlib.sha256(path.read_bytes()).hexdigest();models[c]=sm
    if len(frames)+len(errors)!=9:raise ValueError("LP population")
    for c,f in frames.items():
        r=sizing.summary(c,"A1_94022_eight_house","NEW_FIXED_HARDWARE" if c in x["candidates"] else "SIGNED_EXISTING_ENERGY",
            hardware[c],f,models[c])
        r.update(energy_sha256=signatures[c],source_ref_sha256=REF_SHA)
        metrics.append(r)
    pd.DataFrame(metrics).to_csv(OUT/"A1_94022_SIZING_ENERGY_SUMMARY.csv",index=False)
    hours=sample.pick_hours(frames,x["bench"].timestamp_lst)
    if not set(x["bench"].timestamp_lst).issubset(hours):raise ValueError("Missing controls")
    pd.DataFrame({"timestamp_lst":hours}).to_csv(OUT/"COMMON_SAMPLE_HOURS.csv",index=False)
    report.update(common_hours=len(hours),new_LPs_optimal=len(frames)-4,planned_sample_case_hours=len(frames)*len(hours)*9)
    rows=[];summ=[];checks=0
    bench=x["bench"].set_index(["case","pf","timestamp_lst"])
    for pf,l in FACTORS:
        terr=x["territories"][l]
        for c,f in frames.items():
            net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
            local=[]
            for t in hours:
                q=follow.evaluate(v6,pp,net,meta,terr,x,c,t,pf)
                if q["status"]!="CONVERGED" or not np.isfinite([q[k] for k in ("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw")]).all():
                    raise ValueError("Nonconverged/nonfinite "+c+" "+str(t))
                if bool(q["night_reactive_disabled"])!=bool(f.at[t,"pv_dc_available_kw"]<=1e-9) or (q["night_reactive_disabled"] and abs(float(q["q_selected_kvar"]))>1e-9):
                    raise ValueError("Night Q policy")
                if l==1. and (c,pf,t) in bench.index:
                    annual.exact_ac_regression(q,bench.loc[(c,pf,t)].to_dict(),c+" "+str(t));checks+=1
                q.update(case=c,pf=pf,length_factor=l,source_energy_sha256=signatures[c],strict_feasible=rn.strict_point(q))
                local.append(q)
            a=pd.DataFrame(local);bad=~a.strict_feasible
            r=dict(case=c,pf=pf,length_factor=l,sampled_hours=len(a),converged=len(a),strict_failures=int(bad.sum()),
                night_failures=int((bad&a.night_reactive_disabled).sum()),daylight_failures=int((bad&~a.night_reactive_disabled).sum()),
                low_voltage_hours=int(a.min_v_pu.lt(.95).sum()),high_voltage_hours=int(a.max_v_pu.gt(1.05).sum()),
                transformer_overload_hours=int(a.max_trafo_pct.gt(100).sum()),line_overload_hours=int(a.max_line_pct.gt(100).sum()),
                minimum_voltage_pu=float(a.min_v_pu.min()),maximum_voltage_pu=float(a.max_v_pu.max()),
                peak_transformer_pct=float(a.max_trafo_pct.max()),peak_line_pct=float(a.max_line_pct.max()),
                optional_under_097_hours=int(a.min_v_pu.lt(.97).sum()),optional_above_103_hours=int(a.max_v_pu.gt(1.03).sum()),
                first_failed_timestamps=a.loc[bad,"timestamp_lst"].astype(str).head(20).tolist(),energy_sha256=signatures[c])
            rows.extend(local);summ.append(r)
            print("AC_SAMPLE="+json.dumps(r,allow_nan=False),flush=True)
    a=pd.DataFrame(rows)
    if checks!=100 or len(a)!=len(frames)*len(hours)*9 or a.duplicated(["case","pf","length_factor","timestamp_lst"]).any():
        raise ValueError("Sample or regression coverage")
    a.to_csv(OUT/"A1_94022_SIZING_AC_HOURLY.csv",index=False)
    pd.DataFrame(summ).to_csv(OUT/"A1_94022_SIZING_AC_SUMMARY.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    for r in metrics:
        c=r["case"];passed=all(g["strict_failures"]==0 for g in summ if g["case"]==c)
        label=c.replace("A1_94022_","").replace("A0_94022_","").replace("_to_A1","")
        marker="o" if passed else "x"
        ax[0].scatter(r["import_ac_kwh"],r["annual_total_usd"],marker=marker,label=label)
        ax[1].scatter(r["curtail_dc_kwh"],r["annual_total_usd"],marker=marker,label=label)
    ax[0].set(xlabel="Annual AC grid imports (kWh)",ylabel="Energy model cost (USD/year)")
    ax[1].set(xlabel="Annual DC PV curtailment (kWh)",ylabel="Energy model cost (USD/year)")
    ax[1].legend(fontsize=7)
    fig.suptitle("94022 A1 | 8-house fixed hardware sizing | circles: nine-factor sample pass")
    for ext in ("png","svg"):fig.savefig(OUT/("A1_94022_sizing."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_A1_94022_SIZING_AND_NINE_FACTOR_SAMPLE",archived_regressions=checks,
        new_sample_case_hours=len(a),completed_groups=len(summ),passing_groups=sum(r["strict_failures"]==0 for r in summ),
        summary=summ)

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),runner_id=os.environ.get("CI_RUNNER_ID"),
        case=REF,source_ref_sha256=REF_SHA,assignment="A1",transformer="94022",households=8,
        planned_LPs=5,planned_existing_energy_comparators=4,plan=[list(z) for z in PLAN],
        factors=[list(z) for z in FACTORS],inverter_site="head",energy_model_pf=.98,minimum_physical_soc=.20,
        zero_export=True,night_Q_disabled=True,annual_AC_verified=False,field_verified=False,offline_perfect_foresight=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_sizing_option_annual_gate.py","test_remote_A1_94022_sizing.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        prepared=prepare()
        report.update(existing_energy_hashes=prepared[2]["signatures"],new_hardware=prepared[2]["candidates"],planned_archived_regressions=100)
        # Snapshot mutable dictionaries before computation.
        report["existing_energy_hashes"]=dict(report["existing_energy_hashes"])
        if preflight:report["status"]="COMPLETE_SIGNED_A1_94022_SIZING_PREFLIGHT"
        else:solve(prepared,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"A1_94022_SIZING_REPORT.json",report)
        print("A1_94022_SIZING_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_A1_94022_SIZING_PREFLIGHT","COMPLETE_A1_94022_SIZING_AND_NINE_FACTOR_SAMPLE") else 1

if __name__=="__main__":raise SystemExit(main())
