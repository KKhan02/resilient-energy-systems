#!/usr/bin/env python3
"""A1 eight-house head reserve: reproduce exact schedules then final annual AC.
No new design or operating policy. No repeated completed annual or sample campaigns.
"""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import remote_94022_A1_reserve as reserve
import remote_94022_A1_annual as prev
import remote_94022_A1_sizing as src
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import reserve_full_night as rn
from audit_battery_coverage import read_frame

EXPECTED=json.loads("{\"A0_94022_min_cost_to_A1\":{\"source_sha\":\"ef6172e9e1a9ebb2b45d819208765dd4a9de440dd48412b79eae59eecae370e1\",\"sha\":\"3574feca8259aa714285d4e936166a7a534b2a51d97521746dccb042597bd658\",\"changed\":3,\"imports\":1519.801062224,\"spill\":3173.4184958907,\"cost\":3267.2510182024553,\"cycles\":319.5620455984141},\"A1_94022_min_cost_ref\":{\"source_sha\":\"120edc90e5e9b18a88b5361266ca3f7f7e9000b8fa8b0d0b0abb5a3924c672ae\",\"sha\":\"db06f1f0dcb4ba6bc0f0f0a80c2b73d436585f6d61c9b29f5b5324bcd7abeb6b\",\"changed\":12,\"imports\":3275.1461519598997,\"spill\":1409.0428586225999,\"cost\":3233.967123476741,\"cycles\":302.1203905464275},\"A1_94022_ss90_ref\":{\"source_sha\":\"90367bab85b649462d3b7178f5e65d1d954d7650b59241b8052bab66e6183f4e\",\"sha\":\"357a8fcb0ee4179b71769af54813b5cbcc4da9cbaa6ae1988a3c400c619c10ca\",\"changed\":6,\"imports\":1519.8010622242,\"spill\":3173.4184958908,\"cost\":3267.251018202455,\"cycles\":319.56204559840586},\"A1_94022_P34_B8\":{\"source_sha\":\"6380b3bbe6536f0d45df1164cda2495a4ec97c999653d7e4f7116ce2a9d1b08b\",\"sha\":\"23adadfc4817bca774437bda93ca74d88311fdca3e09c40d892b88796dfe638c\",\"changed\":3,\"imports\":966.3731149971,\"spill\":2560.2019338683003,\"cost\":3574.2509973829415,\"cycles\":257.91157240341846},\"A1_94022_P30_B8\":{\"source_sha\":\"6b5a9e494ca80c84a6306b116f9b75a2e4a8bf2d26bdd906747a8eccc80736d4\",\"sha\":\"db3b8ad139e39ebb9289675457a8ee1851152cfde93fe48460ee91ac6687416d\",\"changed\":2,\"imports\":1766.6750846109999,\"spill\":1328.066569678,\"cost\":3679.8860730479673,\"cycles\":235.10128547206193},\"A1_94022_P34_B7\":{\"source_sha\":\"9ff8435e6b09bc44866c5d24c5f319709f67ed019f123e70677ac1acbcfccb7d\",\"sha\":\"a5badd109c0c4eec6fc99b62dbdbaa5478363854342d1e536104e1b8c1c5c279\",\"changed\":4,\"imports\":1115.4939575355002,\"spill\":2725.4327843253996,\"cost\":3471.0440614271556,\"cycles\":289.13920523968045}}")
PRIOR=json.loads("[{\"case\":\"A0_94022_min_cost_to_A1\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.950039666560338,\"maximum_voltage_pu\":0.996426283104658,\"peak_transformer_pct\":69.8087161105412,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":61,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"3574feca8259aa714285d4e936166a7a534b2a51d97521746dccb042597bd658\"},{\"case\":\"A1_94022_min_cost_ref\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9500391617675761,\"maximum_voltage_pu\":0.9953739742824625,\"peak_transformer_pct\":79.69892725530171,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":63,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"db06f1f0dcb4ba6bc0f0f0a80c2b73d436585f6d61c9b29f5b5324bcd7abeb6b\"},{\"case\":\"A1_94022_ss90_ref\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.950039666560338,\"maximum_voltage_pu\":0.996426283104658,\"peak_transformer_pct\":69.8087161105412,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":59,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"357a8fcb0ee4179b71769af54813b5cbcc4da9cbaa6ae1988a3c400c619c10ca\"},{\"case\":\"A1_94022_P34_B8\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.950039666560338,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":69.8087161105412,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":60,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"23adadfc4817bca774437bda93ca74d88311fdca3e09c40d892b88796dfe638c\"},{\"case\":\"A1_94022_P30_B8\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.950039666560338,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":78.60231617244781,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":60,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"db3b8ad139e39ebb9289675457a8ee1851152cfde93fe48460ee91ac6687416d\"},{\"case\":\"A1_94022_P34_B7\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9500392541637857,\"maximum_voltage_pu\":0.9964518911661135,\"peak_transformer_pct\":69.8087161105412,\"peak_line_pct\":9.677200372543334,\"optional_under_097_hours\":60,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"a5badd109c0c4eec6fc99b62dbdbaa5478363854342d1e536104e1b8c1c5c279\"},{\"case\":\"A0_94022_min_cost_to_A1\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9585982960411369,\"maximum_voltage_pu\":0.9976520626621798,\"peak_transformer_pct\":67.1601753193317,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":37,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"3574feca8259aa714285d4e936166a7a534b2a51d97521746dccb042597bd658\"},{\"case\":\"A1_94022_min_cost_ref\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9582660694828022,\"maximum_voltage_pu\":0.9969985978476452,\"peak_transformer_pct\":76.62475339292686,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":46,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"db06f1f0dcb4ba6bc0f0f0a80c2b73d436585f6d61c9b29f5b5324bcd7abeb6b\"},{\"case\":\"A1_94022_ss90_ref\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9585982960411369,\"maximum_voltage_pu\":0.9976520626621798,\"peak_transformer_pct\":67.1601753193317,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":38,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"357a8fcb0ee4179b71769af54813b5cbcc4da9cbaa6ae1988a3c400c619c10ca\"},{\"case\":\"A1_94022_P34_B8\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9585982960411369,\"maximum_voltage_pu\":0.9976690617354131,\"peak_transformer_pct\":67.1601753193317,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":35,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"23adadfc4817bca774437bda93ca74d88311fdca3e09c40d892b88796dfe638c\"},{\"case\":\"A1_94022_P30_B8\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9585982960411369,\"maximum_voltage_pu\":0.9976690617354131,\"peak_transformer_pct\":75.56414659347024,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":41,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"db3b8ad139e39ebb9289675457a8ee1851152cfde93fe48460ee91ac6687416d\"},{\"case\":\"A1_94022_P34_B7\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":91,\"converged\":91,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9585982960411369,\"maximum_voltage_pu\":0.9976690617354131,\"peak_transformer_pct\":67.1601753193317,\"peak_line_pct\":9.320527413732837,\"optional_under_097_hours\":37,\"optional_above_103_hours\":0,\"first_failed_timestamps\":[],\"corrected_energy_sha256\":\"a5badd109c0c4eec6fc99b62dbdbaa5478363854342d1e536104e1b8c1c5c279\"}]")
HASHES=json.loads("{\"A1_HEAD_NIGHT_PROBES.csv\":\"3072991d61c67808cc91d0690cc1f6c5704782d9899403174c95cb74458e9bba\",\"A1_HEAD_NIGHT_SCREEN.csv\":\"aa713b759d2f0e336969a382f260d71f9612b4f4ae6891a306be4961e8e83b4e\",\"RESERVE_COMMON_SAMPLE_HOURS.csv\":\"7a97f22411bf0afcc383e27d62f8562cb073074c19abe5c75d35b4619bcc790a\"}")
FACTORS=prev.FACTORS
CASES=reserve.CASES

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def plan_gate():
    reserve.plan_gate()
    if set(EXPECTED)!=set(CASES) or len(CASES)!=6:
        raise ValueError("Corrected case population")
    if len(PRIOR)!=12 or {(r["case"],r["pf"],r["length_factor"]) for r in PRIOR}!={(c,p,l) for c in CASES for p,l in FACTORS}:
        raise ValueError("Sample evidence population")
    for r in PRIOR:
        e=EXPECTED[r["case"]]
        if r["sampled_hours"]!=91 or r["converged"]!=91 or r["strict_failures"] or r["corrected_energy_sha256"]!=e["sha"] or e["source_sha"]!=prev.EXPECTED[r["case"]]:
            raise ValueError("Corrected evidence identity")
    if set(HASHES)!={"A1_HEAD_NIGHT_SCREEN.csv","A1_HEAD_NIGHT_PROBES.csv","RESERVE_COMMON_SAMPLE_HOURS.csv"}:
        raise ValueError("Source file hash gate")

def reconstruct(prepared,report):
    old_hours=prev.restore_schedules(prepared,report)
    corridors=reserve.screen(prepared,report)
    if corridors is None or len(corridors)!=34 or report["prior_event_regressions"]!=45:
        raise ValueError("Night corridor gate")
    for name in ("A1_HEAD_NIGHT_SCREEN.csv","A1_HEAD_NIGHT_PROBES.csv"):
        if sha(OUT/name)!=HASHES[name]:raise ValueError("Prior screen identity "+name)
    fh,v6,annual,x=prepared
    corrected={};models={};hours=set(old_hours)|set(corridors);metrics=[]
    for c in CASES:
        h=x["hardware"][c];old=x["frames"][c];e=EXPECTED[c]
        hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
            battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
            transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,load_pf=.98,
            export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        f,sm=fh.solve_fixed(ROOT,hw,x["demand"],x["solar"],corridors=corridors,min_physical_soc=.20)
        f.index.name="timestamp_lst";sizing.validate_comparison(f,h,x["demand"],x["solar"])
        path=OUT/(c+"_HEAD_RESERVE_8760.csv");f.to_csv(path,float_format="%.10f")
        if sha(path)!=e["sha"]:raise ValueError("Corrected schedule hash "+c)
        f=read_frame(path);sizing.validate_comparison(f,h,x["demand"],x["solar"])
        for t,(lo,hi) in corridors.items():
            if not lo-1e-6<=float(f.at[t,"inverter_ac_kw"])<=hi+1e-6:raise ValueError("Reserve corridor")
        changed=old.inverter_ac_kw.ne(f.inverter_ac_kw)
        if int(changed.sum())!=e["changed"]:raise ValueError("Dispatch change count")
        hours.update(f.index[changed])
        r=sizing.summary(c,"A1_94022_eight_house","OFFLINE_HEAD_RESERVE",h,f,sm)
        for actual,expected in ((r["import_ac_kwh"],e["imports"]),(r["curtail_dc_kwh"],e["spill"]),(r["annual_total_usd"],e["cost"]),(r["store_equivalent_discharge_cycles"],e["cycles"])):
            if abs(actual-expected)>1e-6:raise ValueError("Prior energy metric "+c)
        metrics.append(dict(r,source_energy_sha256=e["source_sha"],corrected_energy_sha256=e["sha"],changed_inverter_hours=e["changed"]))
        corrected[c]=f;models[c]=sm
    hours=sample.pick_hours(corrected,hours)
    path=OUT/"RESERVE_COMMON_SAMPLE_HOURS.csv"
    pd.DataFrame({"timestamp_lst":hours}).to_csv(path,index=False)
    if len(hours)!=91 or sha(path)!=HASHES[path.name]:raise ValueError("Prior risk sample identity")
    report.update(verified_corrected_schedules=6,reconstructed_reserve_LPs=6,verified_risk_hours=91,
        prior_reserve_AC_sample_repeated=False,energy_results=metrics)
    save(OUT/"PARTIAL_RESULTS.json",report)
    return corrected,models,set(hours)

def annual_validation(prepared,corrected,models,hours,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    results=[];checks=0
    report["annual_results"]=results
    for c in CASES:
        f=corrected[c];e=EXPECTED[c];new=dict(x,frames={c:f})
        for pf,l in FACTORS:
            terr=x["territories"][l];net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
            rows=[]
            for i,t in enumerate(f.index):
                q=prev.checked(v6,pp,net,meta,terr,new,c,t,pf)
                q.update(case=c,pf=pf,length_factor=l,source_energy_sha256=e["source_sha"],
                    corrected_energy_sha256=e["sha"],source_grid_import_kw=float(f.at[t,"grid_import_kw"]),
                    strict_feasible=rn.strict_point(q))
                rows.append(q)
                if (i+1)%2000==0:print("Annual reserve",c,pf,l,i+1,flush=True)
            a=pd.DataFrame(rows)
            if len(a)!=8760 or not pd.DatetimeIndex(pd.to_datetime(a.timestamp_lst)).equals(f.index):
                raise ValueError("Annual chronology")
            select=a[pd.to_datetime(a.timestamp_lst).isin(hours)]
            expected=next(r for r in PRIOR if r["case"]==c and r["pf"]==pf and r["length_factor"]==l)
            if len(select)!=91:raise ValueError("Annual sample coverage")
            prev.sample_regression(prev.stats(select),expected);checks+=91
            name=c+"_RESERVE_PF"+str(round(pf*100))+"_L"+str(round(l*10))+"_ANNUAL_AC.csv"
            annual.save_csv(OUT/name,rows)
            cost=float(models[c]["annual_total_usd"]);loss=float(a.loss_kw.sum())
            result=dict(case=c,pf=pf,length_factor=l,hours=8760,source_energy_sha256=e["source_sha"],
                corrected_energy_sha256=e["sha"],**prev.stats(a),losses_kwh=loss,annual_energy_cost_usd=cost,
                all_loss_purchase_cost_usd=cost+.29*loss,annual_import_kwh=float(f.grid_import_kw.sum()),
                annual_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),failed_timestamps_first_30=a.loc[~a.strict_feasible,"timestamp_lst"].astype(str).head(30).tolist(),
                output_sha256=sha(OUT/name))
            results.append(result);print("RESERVE_ANNUAL_RESULT="+json.dumps(result,allow_nan=False),flush=True)
            save(OUT/"PARTIAL_RESULTS.json",report)
    if checks!=1092 or len(results)!=12:raise ValueError("Annual regression coverage")
    pd.DataFrame(results).to_csv(OUT/"RESERVE_ANNUAL_AC_SUMMARY.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a=pd.DataFrame(results)
    fig,ax=plt.subplots(1,2,figsize=(14,5),layout="constrained")
    labels=["Reciprocal MC","Native MC","Native SS90","P34 B8","P30 B8","P34 B7"]
    for i,(pf,l) in enumerate(FACTORS):
        s=a[a.pf.eq(pf)&a.length_factor.eq(l)].set_index("case").loc[list(CASES)]
        xx=np.arange(len(CASES))+(i-.5)*.36
        ax[0].bar(xx,s.minimum_voltage_pu,.36,label=f"PF {pf}, length {l}")
        ax[1].bar(xx,s.all_loss_purchase_cost_usd,.36,label=f"PF {pf}, length {l}")
    ax[0].axhline(.95,ls="--",color="firebrick")
    ax[0].set_ylim(min(.93,float(a.minimum_voltage_pu.min())-.002),1.05)
    ax[0].set_ylabel("Annual minimum voltage (pu)")
    ax[1].set_ylabel("Annual modeled cost incl. loss sensitivity (USD)")
    for z in ax:z.set_xticks(range(len(CASES)),labels,rotation=35,ha="right");z.legend(fontsize=8)
    fig.suptitle("94022 A1 | annual AC and cost, corrected head reserve schedules")
    for ext in ("png","svg"):fig.savefig(OUT/("A1_head_reserve_annual."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_A1_HEAD_RESERVE_ANNUAL",sampled_case_hours_reconciled=checks,
        annual_sample_summary_groups=12,new_AC_case_hours=105120,
        annual_passing_groups=sum(r["strict_failures"]==0 for r in results))

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),
        runner_id=os.environ.get("CI_RUNNER_ID"),prior_reserve_job=18412258573,selected_cases=list(CASES),
        factors=[list(z) for z in FACTORS],planned_annual_AC_case_hours=105120,
        field_verified=False,offline_perfect_foresight=True,no_new_equipment_design=True,no_new_dispatch_policy=True,
        night_Q_disabled=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_A1_94022_reserve.py","test_remote_A1_94022_reserve_annual.py","test_remote_A1_94022_annual.py","test_reserve_full_night.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        plan_gate()
        prepared=src.prepare()
        _,_,_,x=prepared
        if x["signatures"]!={c:prev.EXPECTED[c] for c in x["frames"]} or set(x["candidates"])!=set(prev.EXPECTED)-set(x["frames"]):raise ValueError("Preflight source set")
        reserve.common_night(x)
        if preflight:report["status"]="COMPLETE_SIGNED_A1_HEAD_RESERVE_ANNUAL_PREFLIGHT"
        else:
            corrected,models,hours=reconstruct(prepared,report)
            annual_validation(prepared,corrected,models,hours,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}
        save(OUT/"A1_HEAD_RESERVE_ANNUAL_REPORT.json",report)
        print("A1_HEAD_RESERVE_ANNUAL_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_A1_HEAD_RESERVE_ANNUAL_PREFLIGHT","COMPLETE_A1_HEAD_RESERVE_ANNUAL") else 1

if __name__=="__main__":raise SystemExit(main())
