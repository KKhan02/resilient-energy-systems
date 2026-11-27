#!/usr/bin/env python3
"""Approved 85398 A0 four-house sizing; exact archived comparator reuse."""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import sizing_nine_factor as nf
import remote_94022_A1_sizing as prior
import remote_94022_A1_annual as runner
import reserve_full_night as rn
from audit_battery_coverage import BASE,signed,read_frame,read_json

REF="A1_85398_ss90_to_A0"
RECIP="A1_85398_min_cost_to_A0"
NATIVE=("A0_85398_min_cost_four","A0_85398_ss90_four")
REF_HW=(20,5,6.096291873336107,6.,5.)
PLAN=(("A0_85398_P18_B5",18,5),("A0_85398_P17_B5",17,5),("A0_85398_P16_B5",16,5),
      ("A0_85398_P20_B4",20,4),("A0_85398_P17_B4",17,4))
EXPECTED={REF:"5571c6432f565a99eecf77f81db7004faea27ac63a3dd2763860e562012314aa",
 RECIP:"70ca9a6ae9025ea4d7e0d5ebbbab13c94b32e7ea6cb0ab0763047b78a94f4440",
 NATIVE[0]:"a5eeb2ef95159efd0279c17587a6e8ebb11130d7496e89108a8bf97cbf48e14a",
 NATIVE[1]:"88dfbad1ae71c0039a743520820dc70ea3431d28cdd7caf7e2f1eacd9e07567d"}
ARCHIVE_FAMILY={REF:"A0_85398_ss90_ref",RECIP:"A0_85398_min_cost_ref",NATIVE[0]:NATIVE[0],NATIVE[1]:NATIVE[1]}
HOUSE_IDS=["H09","H12","H14","H15"]
FACTORS=nf.FACTORS

def new_designs(h):
    if sizing.hardware_tuple(h)!=REF_HW:raise ValueError("Reference hardware differs")
    return {name:dict(h,pv_panels=p,battery_modules=m) for name,p,m in PLAN}

def archive_key(family,pf,length):
    return family+"_mapped_optimized_pf"+str(round(pf*100)).zfill(3)+"_length"+str(round(length*10))+"_annual8760"

def prepare():
    st,fh,m,mapping,profiles,solar,top,table,validate_device=sizing.context(ROOT)
    sys.path.insert(0,str(ROOT/sample.SYN))
    import matched16_94022_ss90_mar_nov_annual_ac as annual
    import matched16_original_ac_input_preflight as base
    _,v6,_,_=st.secure_context(ROOT,ROOT/st.MANIFEST_REL)
    annual.check_source_stateless(v6)
    ids,trace=st.source_trace(m,mapping,profiles,"A0","85398")
    if ids!=HOUSE_IDS or abs(float(trace.sum().sum())-7592)>1e-5:
        raise ValueError("Four-house population changed")
    demand=trace.sum(axis=1)
    frames={};hardware={};signatures={};models={}
    for c in (REF,RECIP):
        r=read_json(ROOT/sizing.MATCH/c/"CASE_RECEIPT.json")
        if r!=top["completed_cases"][c] or r["assignment_for_load"]!="A0" or r["transformer"]!="85398" or r["target_house_ids"]!=ids or r["target_energy_sha256"]!=EXPECTED[c]:
            raise ValueError("Reciprocal source identity "+c)
        path=ROOT/r["target_energy_csv"];h=r["hardware"]
        signed(path,EXPECTED[c]);f=read_frame(path)
        frames[c]=f;hardware[c]=h;signatures[c]=EXPECTED[c];models[c]=r["target_model_summary"]
    for c in NATIVE:
        folder=ROOT/BASE/("energy_"+c);r=read_json(folder/"energy_manifest.json")
        if r["scenario"]!="A0" or r["transformer"]!="85398" or r["selected_house_ids"]!=ids or r["energy_csv_sha256"]!=EXPECTED[c] or r["input_manifest_sha256"]!=top["input_manifest_sha256"]:
            raise ValueError("Native identity "+c)
        path=folder/"energy_hourly_2025.csv"
        signed(path,EXPECTED[c]);f=read_frame(path)
        frames[c]=f;hardware[c]=r["hardware"];signatures[c]=EXPECTED[c];models[c]=r["source_model_summary"]
    for c,f in frames.items():
        h=hardware[c];sizing.validate_comparison(f,h,demand,solar)
        q=table[table.case.eq(c)]
        if len(q)!=1 or q.iloc[0].source_sha!=signatures[c]:raise ValueError("Coverage identity "+c)
        for k,col in (("source_import_ac_kwh","grid_import_kw"),("source_curtail_dc_kwh","curtailed_pv_dc_kw")):
            if abs(float(q.iloc[0][k])-float(f[col].sum()))>1e-5:raise ValueError("Coverage totals "+c)
        if abs(float(models[c]["annual_grid_import_usd"])-.29*float(f.grid_import_kw.sum()))>1e-5:raise ValueError("Archived cost/import mismatch")
    candidates=new_designs(hardware[REF])
    inv={}
    for z in table.itertuples():
        c=z.case
        if "_85398_" in c and ((c.startswith("A0_") and "_to_" not in c) or c.endswith("_to_A0")):
            inv[c]=dict(pv_panels=int(z.pv_panels),battery_modules=int(z.battery_modules),
                battery_power_dc_kw=float(z.battery_power_dc_kw),inverter_kva=float(z.inverter_kva),
                transformer_kva_assumed_or_evidenced=float(z.transformer_kva))
    if set(inv)!=set(frames):raise ValueError("Unexpected same-cohort roster")
    prior.duplicate_guard(candidates,inv)
    for h in candidates.values():validate_device(sizing.device_input(h))
    territories={l:v6.new_territory(ROOT,"A0","85398",ids,l) for l in (1.,1.3,1.6)}
    if any(float(t.trafo["kva"])!=5. or sorted(z["house"] for z in t.attachments)!=sorted(ids) for t in territories.values()):
        raise ValueError("GIS territory/rating mismatch")
    # Source-lock all archived annual comparator groups before reusing them.
    archive={};archive_receipts=[];hours=set()
    for c,f in frames.items():
        family=ARCHIVE_FAMILY[c];folder=ROOT/BASE/("energy_"+family)
        ep=folder/"energy_manifest.json";em=base.read_json(ep)
        if em["scenario"]!="A0" or em["transformer"]!="85398" or em["selected_house_ids"]!=ids or em["energy_csv_sha256"]!=EXPECTED[c] or em["input_manifest_sha256"]!=top["input_manifest_sha256"] or not base.same_hardware(em["hardware"],hardware[c]):
            raise ValueError("Archive energy identity "+c)
        base.signed_bytes(folder/"energy_hourly_2025.csv",EXPECTED[c])
        for pf,l in FACTORS:
            folder2=ROOT/BASE/"annual_ac_replays_v1"/archive_key(family,pf,l)
            ar=base.read_json(folder2/"ac_summary.json")
            if ar["status"]!="ANNUAL_PVBESS_AC" or ar["scenario"]!="A0" or ar["transformer"]!="85398" or ar["topology"]!="mapped" or ar["dispatch"]!="optimized" or ar["selected_house_ids"]!=ids or ar["hours"]!=8760 or ar["converged_hours"]!=8760 or ar["pf"]!=pf or ar["length_factor"]!=l or ar["q_ratio_daylight"]!=sample.Q or ar["night_q_disabled"] is not True or ar["input_manifest_sha256"]!=top["input_manifest_sha256"] or ar["tier"]!=em["hardware_selection_tier"]:
                raise ValueError("Archive AC receipt "+c+" "+str((pf,l)))
            base.signed_bytes(ep,ar["energy_manifest_sha256"])
            path=folder2/"ac_hourly.csv";mode=base.signed_bytes(path,ar["ac_hourly_sha256"])
            ac=pd.read_csv(base.required_file(path),parse_dates=["timestamp_lst"]).set_index("timestamp_lst",drop=False)
            if not ac.index.equals(f.index) or not ac.status.eq("CONVERGED").all() or not np.allclose(ac.load_pf,pf,rtol=0,atol=1e-8):
                raise ValueError("Archive chronology/status/PF")
            for ak,ek in (("gross_demand_kw","demand_kw"),("inverter_ac_kw","inverter_ac_kw")):
                if not np.allclose(ac[ak],f[ek],rtol=0,atol=1e-8):raise ValueError("Archive AC input "+ak)
            night=f.pv_dc_available_kw<=1e-9
            if not np.array_equal(ac.night_reactive_disabled.to_numpy(),night.to_numpy()) or (ac.loc[night,"q_selected_kvar"].abs()>1e-8).any():
                raise ValueError("Archive night Q")
            if not np.isfinite(ac[["min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw","q_selected_kvar","pcc_kva"]].to_numpy(float)).all():raise ValueError("Archive finite quantities")
            ac["strict_feasible"]=ac.ac_feasible & ac.min_v_pu.ge(.95)&ac.max_v_pu.le(1.05)&ac.max_trafo_pct.le(100)&ac.max_line_pct.le(100)
            if int((~ac.ac_feasible).sum())!=ar["AC_infeasible_hours"] or abs(float(ac.loss_kw.sum())-ar["annual_or_sample_losses_kwh"])>1e-6 or abs(float(ac.min_v_pu.min())-ar["min_voltage_pu"])>1e-8 or abs(float(ac.max_trafo_pct.max())-ar["max_transformer_loading_pct"])>1e-8:
                raise ValueError("Archive summary mismatch")
            stress=runner.stats(ac)
            receipt=dict(case=c,archive_family=family,pf=pf,length_factor=l,source_energy_sha256=EXPECTED[c],
                source_ac_sha256=ar["ac_hourly_sha256"],signature_mode=mode,annual_hours=8760,**stress,
                annual_losses_kwh=float(ac.loss_kw.sum()),all_loss_purchase_cost_usd=float(models[c]["annual_total_usd"])+.29*float(ac.loss_kw.sum()))
            archive_receipts.append(receipt);archive[c,pf,l]=ac
            hours.update(ac.min_v_pu.nsmallest(3,keep="first").index)
            hours.update(ac.max_v_pu.nlargest(3,keep="first").index)
            hours.update(ac.max_trafo_pct.nlargest(3,keep="first").index)
            hours.update(ac.max_line_pct.nlargest(3,keep="first").index)
            hours.update(ac.index[~ac.strict_feasible])
    if len(archive)!=36 or len(archive_receipts)!=36:raise ValueError("Archive coverage")
    return fh,v6,annual,dict(ids=ids,trace=trace,frames=frames,hardware=hardware,signatures=signatures,
        models=models,candidates=candidates,territories=territories,demand=demand,solar=solar,
        archive=archive,archive_receipts=archive_receipts,archived_risk_hours=hours)

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
        f.index.name="timestamp_lst";sizing.validate_comparison(f,h,x["demand"],x["solar"])
        path=OUT/(c+"_8760.csv");f.to_csv(path,float_format="%.10f")
        f=read_frame(path);sizing.validate_comparison(f,h,x["demand"],x["solar"])
        frames[c]=f;hardware[c]=h;signatures[c]=hashlib.sha256(path.read_bytes()).hexdigest();models[c]=sm
    if len(frames)+len(errors)!=9:raise ValueError("LP population")
    for c,f in frames.items():
        r=sizing.summary(c,"A0_85398_four_house","NEW_FIXED_HARDWARE" if c in x["candidates"] else "SIGNED_EXISTING_ENERGY",
            hardware[c],f,models[c])
        r.update(energy_sha256=signatures[c],source_ref_sha256=EXPECTED[REF])
        metrics.append(r);print("SIZING_ENERGY="+json.dumps(r,allow_nan=False),flush=True)
    pd.DataFrame(metrics).to_csv(OUT/"A0_85398_SIZING_ENERGY_SUMMARY.csv",index=False)
    hours=sample.pick_hours(frames,x["archived_risk_hours"])
    pd.DataFrame({"timestamp_lst":hours}).to_csv(OUT/"COMMON_SAMPLE_HOURS.csv",index=False)
    report.update(common_hours=len(hours),new_LPs_optimal=len(frames)-4,
        planned_new_AC_case_hours=(len(frames)-4)*len(hours)*9,planned_reused_sample_case_hours=4*len(hours)*9)
    rows=[];summ=[];checks=0;reused=0;new=0
    for pf,l in FACTORS:
        terr=x["territories"][l]
        for c,f in frames.items():
            net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
            local=[]
            archived=x["archive"].get((c,pf,l))
            # Two independent operating-point regressions per archived group:
            # lowest household voltage and highest transformer loading.
            if archived is not None:
                for t in (archived.min_v_pu.idxmin(),archived.max_trafo_pct.idxmax()):
                    q=runner.checked(v6,pp,net,meta,terr,x,c,t,pf)
                    annual.exact_ac_regression(q,archived.loc[t].to_dict(),c+" "+str(t))
                    checks+=1
            for t in hours:
                if archived is None:
                    q=runner.checked(v6,pp,net,meta,terr,x,c,t,pf)
                    q["strict_feasible"]=rn.strict_point(q);new+=1
                else:
                    q=archived.loc[t].to_dict()
                    q["timestamp_lst"]=str(t);reused+=1
                q.update(case=c,pf=pf,length_factor=l,source_energy_sha256=signatures[c],
                    evidence="NEW_AC_SAMPLE" if archived is None else "SIGNED_ARCHIVED_ANNUAL_ROW")
                local.append(q)
            a=pd.DataFrame(local)
            r=dict(case=c,pf=pf,length_factor=l,sampled_hours=len(a),**runner.stats(a),
                evidence="NEW_AC_SAMPLE" if archived is None else "SIGNED_ARCHIVED_ANNUAL_ROWS",
                first_failed_timestamps=a.loc[~a.strict_feasible,"timestamp_lst"].astype(str).head(30).tolist(),energy_sha256=signatures[c])
            rows.extend(local);summ.append(r)
            print("AC_SAMPLE="+json.dumps(r,allow_nan=False),flush=True)
    if checks!=72 or len(summ)!=len(frames)*9 or new!=(len(frames)-4)*len(hours)*9 or reused!=4*len(hours)*9:raise ValueError("Sample accounting")
    a=pd.DataFrame(rows)
    if a.duplicated(["case","pf","length_factor","timestamp_lst"]).any():raise ValueError("Duplicate sample")
    a.to_csv(OUT/"A0_85398_AC_SAMPLE_HOURLY.csv",index=False)
    pd.DataFrame(summ).to_csv(OUT/"A0_85398_AC_SAMPLE_SUMMARY.csv",index=False)
    pd.DataFrame(x["archive_receipts"]).to_csv(OUT/"A0_85398_ARCHIVED_ANNUAL_COMPARATORS.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    for r in metrics:
        c=r["case"];passed=all(g["strict_failures"]==0 for g in summ if g["case"]==c)
        label=c.replace("A0_85398_","").replace("A1_85398_","")
        marker="o" if passed else "x"
        ax[0].scatter(r["import_ac_kwh"],r["annual_total_usd"],marker=marker,label=label)
        ax[1].scatter(r["curtail_dc_kwh"],r["annual_total_usd"],marker=marker,label=label)
    ax[0].set(xlabel="Annual AC grid imports (kWh)",ylabel="Energy model cost (USD/year)")
    ax[1].set(xlabel="Annual DC curtailment (kWh)",ylabel="Energy model cost (USD/year)")
    ax[1].legend(fontsize=7)
    fig.suptitle("85398 A0 four-house sizing | archived annual comparators and new AC sample")
    for ext in ("png","svg"):fig.savefig(OUT/("A0_85398_sizing."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_A0_85398_SIZING_AND_ARCHIVE_REUSE_SAMPLE",archived_point_regressions=checks,
        new_AC_sample_case_hours=new,reused_AC_sample_case_hours=reused,completed_groups=len(summ),
        passing_groups=sum(r["strict_failures"]==0 for r in summ),summary=summ)

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),runner_id=os.environ.get("CI_RUNNER_ID"),
        assignment="A0",transformer="85398",house_ids=HOUSE_IDS,reference=REF,reference_sha=EXPECTED[REF],
        planned_LPs=5,plan=[list(z) for z in PLAN],factors=[list(z) for z in FACTORS],field_verified=False,
        minimum_physical_soc=.20,energy_model_pf=.98,zero_export=True,night_Q_disabled=True,
        offline_perfect_foresight=True,new_design_annual_AC_verified=False)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_A0_85398_sizing.py","test_remote_A1_94022_annual.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        prepared=prepare()
        _,_,_,x=prepared
        report.update(existing_energy_hashes=dict(x["signatures"]),new_hardware={c:dict(h) for c,h in x["candidates"].items()},
            archived_annual_groups=len(x["archive_receipts"]),archived_annual_case_hours=8760*len(x["archive_receipts"]),
            archive_receipts=x["archive_receipts"],archived_risk_hours=len(x["archived_risk_hours"]))
        if preflight:report["status"]="COMPLETE_SIGNED_A0_85398_SIZING_PREFLIGHT"
        else:solve(prepared,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"A0_85398_SIZING_REPORT.json",report)
        print("A0_85398_SIZING_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_A0_85398_SIZING_PREFLIGHT","COMPLETE_A0_85398_SIZING_AND_ARCHIVE_REUSE_SAMPLE") else 1

if __name__=="__main__":raise SystemExit(main())
