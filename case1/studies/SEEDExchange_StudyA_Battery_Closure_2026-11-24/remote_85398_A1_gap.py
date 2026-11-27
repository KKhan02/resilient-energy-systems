#!/usr/bin/env python3
"""85398 A1 five-house reciprocal annual gap closure; no new LPs."""
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

RECIP=["A0_85398_min_cost_to_A1","A0_85398_ss90_to_A1"]
NATIVE=["A1_85398_min_cost_ref","A1_85398_ss90_ref"]
EXPECTED={"A0_85398_min_cost_to_A1":"d611c19058bc92480d6cabf480b71d8f697ad5ae1aa5a8ce517a36e8a3f9ae2d","A0_85398_ss90_to_A1":"03d2810cd867a8d5cc316af52905a8f545b38503a38136668f591fee04876410","A1_85398_min_cost_ref":"b55320cde3affee28114b477de286e429854334325cc537cda726cd5d57654ea","A1_85398_ss90_ref":"d2aa2d7fb51f26b7ea65afdb68aef5a3cdd316fcea7f3337224fc24d581e7087"}
HOUSE_IDS=["H09","H12","H13","H14","H15"]
FACTORS=nf.FACTORS
ANNUAL_FACTORS=((.98,1.),(.95,1.6))

def archive_key(family,pf,length):
    return family+"_mapped_optimized_pf"+str(round(pf*100)).zfill(3)+"_length"+str(round(length*10))+"_annual8760"

def prepare():
    st,fh,m,mapping,profiles,solar,top,table,validate_device=sizing.context(ROOT)
    sys.path.insert(0,str(ROOT/sample.SYN))
    import matched16_94022_ss90_mar_nov_annual_ac as annual
    import matched16_original_ac_input_preflight as base
    _,v6,_,_=st.secure_context(ROOT,ROOT/st.MANIFEST_REL)
    annual.check_source_stateless(v6)
    ids,trace=st.source_trace(m,mapping,profiles,"A1","85398")
    if ids!=HOUSE_IDS or abs(float(trace.sum().sum())-9490)>1e-5:
        raise ValueError("Five-house population changed")
    demand=trace.sum(axis=1)
    frames={};hardware={};signatures={};models={}
    for c in RECIP:
        r=read_json(ROOT/sizing.MATCH/c/"CASE_RECEIPT.json")
        if r!=top["completed_cases"][c] or r["assignment_for_load"]!="A1" or r["transformer"]!="85398" or r["target_house_ids"]!=ids or r["target_energy_sha256"]!=EXPECTED[c]:
            raise ValueError("Reciprocal source identity "+c)
        path=ROOT/r["target_energy_csv"];h=r["hardware"]
        signed(path,EXPECTED[c]);f=read_frame(path)
        frames[c]=f;hardware[c]=h;signatures[c]=EXPECTED[c];models[c]=r["target_model_summary"]
    for c in NATIVE:
        folder=ROOT/BASE/("energy_"+c);r=read_json(folder/"energy_manifest.json")
        if r["scenario"]!="A1" or r["transformer"]!="85398" or r["selected_house_ids"]!=ids or r["energy_csv_sha256"]!=EXPECTED[c] or r["input_manifest_sha256"]!=top["input_manifest_sha256"]:
            raise ValueError("Native identity "+c)
        path=folder/"energy_hourly_2025.csv"
        signed(path,EXPECTED[c]);f=read_frame(path)
        frames[c]=f;hardware[c]=r["hardware"];signatures[c]=EXPECTED[c];models[c]=r['source_model_summary']
    for c,f in frames.items():
        h=hardware[c];sizing.validate_comparison(f,h,demand,solar)
        q=table[table.case.eq(c)]
        if len(q)!=1 or q.iloc[0].source_sha!=signatures[c]:raise ValueError("Coverage identity "+c)
        for k,col in (("source_import_ac_kwh","grid_import_kw"),("source_curtail_dc_kwh","curtailed_pv_dc_kw")):
            if abs(float(q.iloc[0][k])-float(f[col].sum()))>1e-5:raise ValueError("Coverage totals "+c)
        if abs(float(models[c]["annual_grid_import_usd"])-.29*float(f.grid_import_kw.sum()))>1e-5:raise ValueError("Archived cost/import mismatch")
    territories={l:v6.new_territory(ROOT,"A1","85398",ids,l) for l in (1.,1.3,1.6)}
    if any(float(t.trafo["kva"])!=5. or sorted(z["house"] for z in t.attachments)!=sorted(ids) for t in territories.values()):
        raise ValueError("GIS territory/rating mismatch")
    # Source-lock all archived annual comparator groups before reusing them.
    archive={};archive_receipts=[];hours=set()
    for c in NATIVE:
        f=frames[c]
        family=c;folder=ROOT/BASE/("energy_"+family)
        ep=folder/"energy_manifest.json";em=base.read_json(ep)
        if em["scenario"]!="A1" or em["transformer"]!="85398" or em["selected_house_ids"]!=ids or em["energy_csv_sha256"]!=EXPECTED[c] or em["input_manifest_sha256"]!=top["input_manifest_sha256"] or not base.same_hardware(em["hardware"],hardware[c]):
            raise ValueError("Archive energy identity "+c)
        base.signed_bytes(folder/"energy_hourly_2025.csv",EXPECTED[c])
        for pf,l in FACTORS:
            folder2=ROOT/BASE/"annual_ac_replays_v1"/archive_key(family,pf,l)
            ar=base.read_json(folder2/"ac_summary.json")
            if ar["status"]!="ANNUAL_PVBESS_AC" or ar["scenario"]!="A1" or ar["transformer"]!="85398" or ar["topology"]!="mapped" or ar["dispatch"]!="optimized" or ar["selected_house_ids"]!=ids or ar["hours"]!=8760 or ar["converged_hours"]!=8760 or ar["pf"]!=pf or ar["length_factor"]!=l or ar["q_ratio_daylight"]!=sample.Q or ar["night_q_disabled"] is not True or ar["input_manifest_sha256"]!=top["input_manifest_sha256"] or ar["tier"]!=em["hardware_selection_tier"]:
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
    if len(archive)!=18 or len(archive_receipts)!=18:raise ValueError("Archive coverage")
    ar=read_json(ROOT/prior.ARCHIVE/"RUN_MANIFEST.json")
    path=ROOT/prior.ARCHIVE/"TARGETED_300_AC_CASEHOURS.csv"
    if ar["status"]!="P2P3_TARGETED_300_AC_CASEHOURS_RECORDED_NOT_ANNUAL" or ar["targeted_ac_csv_sha256"]!=prior.ARCHIVE_SHA or ar["daytime_Q_ratio"]!=sample.Q:
        raise ValueError("Archived reciprocal sample receipt changed")
    signed(path,prior.ARCHIVE_SHA)
    a=pd.read_csv(path,parse_dates=["timestamp_lst"])
    if len(a)!=300 or a.duplicated(["case","pf","timestamp_lst"]).any():raise ValueError("Archive sample population")
    bench=a[a.case.isin(RECIP)].copy()
    if len(bench)!=100 or not bench.status.eq("CONVERGED").all() or not bench.length_factor.eq(1.).all():raise ValueError("Archive reciprocal control coverage")
    for (c,pf),g in bench.groupby(["case","pf"]):
        if len(g)!=25 or pf not in (.95,.98) or not g.source_sha256.eq(signatures[c]).all():raise ValueError("Archive sample identity")
        f=frames[c].loc[g.timestamp_lst]
        for ac,e in (("inverter_ac_kw","inverter_ac_kw"),("gross_demand_kw","demand_kw"),("grid_import_kw","grid_import_kw"),("pv_dc_available_kw","pv_dc_available_kw")):
            if not np.allclose(g[ac].to_numpy(),f[e].to_numpy(),rtol=0,atol=1e-6):raise ValueError("Archive sample P/load mismatch")
    hours.update(bench.timestamp_lst)
    return fh,v6,annual,dict(ids=ids,trace=trace,frames=frames,hardware=hardware,signatures=signatures,
        models=models,territories=territories,demand=demand,solar=solar,
        archive=archive,archive_receipts=archive_receipts,archived_risk_hours=hours,bench=bench)


def plan_gate():
    if len(HOUSE_IDS)!=5 or set(RECIP)&set(NATIVE) or set(EXPECTED)!=set(RECIP+NATIVE) or len(FACTORS)!=9:
        raise ValueError("Population gate")

def execute(prepared,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    energy=[]
    for c,f in x["frames"].items():
        r=sizing.summary(c,"A1_85398_five_house","SIGNED_EXISTING_ENERGY",x["hardware"][c],f,x["models"][c])
        r.update(energy_sha256=EXPECTED[c]);energy.append(r)
        print("A1_85398_ENERGY="+json.dumps(r,allow_nan=False),flush=True)
    pd.DataFrame(energy).to_csv(OUT/"A1_85398_ENERGY_SUMMARY.csv",index=False)
    report["energy_results"]=energy
    checks=0
    for (c,pf,l),a in x["archive"].items():
        terr=x["territories"][l];net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
        for t in (a.min_v_pu.idxmin(),a.max_trafo_pct.idxmax()):
            q=runner.checked(v6,pp,net,meta,terr,x,c,t,pf)
            annual.exact_ac_regression(q,a.loc[t].to_dict(),c+" "+str(t));checks+=1
    if checks!=36:raise ValueError("Native archive regression count")
    report.update(native_archive_point_regressions=checks)
    hours=sample.pick_hours(x["frames"],x["archived_risk_hours"])
    pd.DataFrame({"timestamp_lst":hours}).to_csv(OUT/"COMMON_SAMPLE_HOURS.csv",index=False)
    report["common_hours"]=len(hours)
    results=[];summ=[];sample_rows=[];old_checks=0;new_sample=0;annual_count=0;annual_sample_reused=0;native_reused=0
    report.update(annual_results=results,sample_summary=summ)
    for pf,l in FACTORS:
        terr=x["territories"][l]
        for c in RECIP+NATIVE:
            f=x["frames"][c];net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
            archived=x["archive"].get((c,pf,l));full=(c in RECIP and (pf,l) in ANNUAL_FACTORS)
            stamps=f.index if full else hours
            local=[]
            for i,t in enumerate(stamps):
                if archived is not None:
                    q=archived.loc[t].to_dict();q["timestamp_lst"]=str(t);native_reused+=1
                else:
                    q=runner.checked(v6,pp,net,meta,terr,x,c,t,pf)
                    q["strict_feasible"]=rn.strict_point(q)
                    if full:annual_count+=1
                    else:new_sample+=1
                q.update(case=c,pf=pf,length_factor=l,energy_sha256=EXPECTED[c],source_grid_import_kw=float(f.at[t,"grid_import_kw"]))
                local.append(q)
                if full and (i+1)%2000==0:print("Annual",c,pf,l,i+1,flush=True)
            a=pd.DataFrame(local)
            if a.duplicated("timestamp_lst").any() or len(a)!=len(stamps):raise ValueError("Time coverage")
            if c in RECIP and l==1. and pf in (.95,.98):
                prior_rows=x["bench"][(x["bench"].case==c)&(x["bench"].pf==pf)]
                indexed=a.set_index(pd.to_datetime(a.timestamp_lst))
                for r in prior_rows.to_dict("records"):
                    t=pd.Timestamp(r["timestamp_lst"])
                    annual.exact_ac_regression(indexed.loc[t].to_dict(),r,c+" "+str(t));old_checks+=1
            if full:
                if not pd.DatetimeIndex(pd.to_datetime(a.timestamp_lst)).equals(f.index):raise ValueError("Annual chronology")
                name=c+"_PF"+str(round(pf*100))+"_L"+str(round(l*10))+"_ANNUAL_AC.csv"
                annual.save_csv(OUT/name,local)
                loss=float(a.loss_kw.sum());cost=float(x["models"][c]["annual_total_usd"])
                r=dict(case=c,pf=pf,length_factor=l,hours=8760,energy_sha256=EXPECTED[c],**runner.stats(a),
                    losses_kwh=loss,annual_energy_cost_usd=cost,all_loss_purchase_cost_usd=cost+.29*loss,
                    annual_import_kwh=float(f.grid_import_kw.sum()),annual_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),
                    failed_timestamps_first_30=a.loc[~a.strict_feasible,"timestamp_lst"].astype(str).head(30).tolist(),
                    output_sha256=hashlib.sha256((OUT/name).read_bytes()).hexdigest())
                results.append(r);print("A1_85398_ANNUAL_RESULT="+json.dumps(r,allow_nan=False),flush=True)
                a=a[pd.to_datetime(a.timestamp_lst).isin(hours)].copy();annual_sample_reused+=len(a)
            if len(a)!=len(hours):raise ValueError("Common sample coverage")
            evidence="SIGNED_ARCHIVED_ANNUAL_ROWS" if archived is not None else ("NEW_ANNUAL_ROWS" if full else "NEW_AC_SAMPLE")
            a["evidence"]=evidence;sample_rows.extend(a.to_dict("records"))
            r=dict(case=c,pf=pf,length_factor=l,sampled_hours=len(a),**runner.stats(a),evidence=evidence,energy_sha256=EXPECTED[c])
            summ.append(r);print("A1_85398_SAMPLE="+json.dumps(r,allow_nan=False),flush=True)
            save(OUT/"PARTIAL_RESULTS.json",report)
    if old_checks!=100 or annual_count!=35040 or len(results)!=4 or len(summ)!=36 or new_sample!=14*len(hours) or native_reused!=18*len(hours) or annual_sample_reused!=4*len(hours):
        raise ValueError("Final coverage")
    pd.DataFrame(results).to_csv(OUT/"A1_85398_ANNUAL_SUMMARY.csv",index=False)
    pd.DataFrame(summ).to_csv(OUT/"A1_85398_SAMPLE_SUMMARY.csv",index=False)
    pd.DataFrame(sample_rows).to_csv(OUT/"A1_85398_SAMPLE_HOURLY.csv",index=False)
    pd.DataFrame(x["archive_receipts"]).to_csv(OUT/"A1_85398_ARCHIVED_NATIVE_ANNUAL.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(11,4.5),layout="constrained")
    for r in energy:
        label=r["case"].replace("_85398_"," ")
        ax[0].scatter(r["import_ac_kwh"],r["annual_total_usd"],label=label)
        ax[1].scatter(r["curtail_dc_kwh"],r["annual_total_usd"],label=label)
    ax[0].set(xlabel="Annual AC grid imports (kWh)",ylabel="Energy model cost (USD/year)")
    ax[1].set(xlabel="Annual DC curtailment (kWh)",ylabel="Energy model cost (USD/year)")
    ax[1].legend(fontsize=7)
    fig.suptitle("85398 A1 five-house matched hardware comparison")
    for ext in ("png","svg"):fig.savefig(OUT/("A1_85398_comparison."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_A1_85398_RECIPROCAL_ANNUAL_AND_SAMPLE",old_sample_regressions=old_checks,
        new_annual_AC_case_hours=annual_count,new_sample_AC_case_hours=new_sample,native_reused_sample_case_hours=native_reused,
        new_annual_reused_sample_case_hours=annual_sample_reused,annual_passing_groups=sum(r["strict_failures"]==0 for r in results),
        sample_passing_groups=sum(r["strict_failures"]==0 for r in summ))

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),
        runner_id=os.environ.get("CI_RUNNER_ID"),assignment="A1",transformer="85398",house_ids=HOUSE_IDS,
        planned_annual_AC_case_hours=35040,planned_new_LPs=0,field_verified=False,
        offline_perfect_foresight=True,night_Q_disabled=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_A1_85398_gap.py","test_remote_A0_85398_sizing.py","test_remote_A1_94022_annual.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        plan_gate()
        prepared=prepare()
        _,_,_,x=prepared
        report.update(existing_energy_hashes=x["signatures"],archive_receipts=x["archive_receipts"],
            archived_native_annual_groups=18,archived_native_annual_case_hours=157680,archived_reciprocal_sample_rows=100)
        if preflight:report["status"]="COMPLETE_SIGNED_A1_85398_GAP_PREFLIGHT"
        else:execute(prepared,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"A1_85398_GAP_REPORT.json",report)
        print("A1_85398_GAP_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_A1_85398_GAP_PREFLIGHT","COMPLETE_A1_85398_RECIPROCAL_ANNUAL_AND_SAMPLE") else 1

if __name__=="__main__":raise SystemExit(main())
