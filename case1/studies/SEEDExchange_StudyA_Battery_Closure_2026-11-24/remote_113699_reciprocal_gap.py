#!/usr/bin/env python3
"""Close two remaining 113699 reciprocal gaps, fixed equipment, no new LP."""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import remote_94022_A1_annual as runner
import reserve_full_night as rn
from audit_battery_coverage import signed,read_frame,read_json

SIX="A0_113699_ss90_to_A1"
FOUR="A1_113699_min_cost_to_A0"
CASES=(SIX,FOUR)
FACTORS=((.98,1.),(.95,1.6))
EXPECTED={SIX:"720442fb593a06b97057c283c402a9e926ca15f594c266bd32909f98e811fa68",
 FOUR:"05b9c362c6dc5387f363994fba09ea9f6c2403d430ac9119e3e7fd51bbcd5ef6"}
IDS={SIX:["H03","H04","H05","H06","H07","H10"],FOUR:["H04","H05","H07","H10"]}
HW={SIX:(17,4,5.759999999999999,5.,3.),FOUR:(20,4,6.439699033049508,6.,3.)}
SHIFTS=(("2025-03-14 17:00:00","2025-03-14 19:00:00",.396591898775),
        ("2025-11-30 17:00:00","2025-11-30 20:00:00",.507748279825))
THERMAL_SHA="a143a2fe8c2a2877614f526f2e59030fd24002873721b69c9387476813cbfb37"
PAIR_SHA="23d0ddb9fdbf418c3c138232b5f16e3538dfe1b236aa5b5ef61b3daaca745f0d"
P2_SHA="e141e1a39c42279235a06e5f5c49a7057cec1642bc7639e8a66d67e4ce618d8f"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def changes(a,b):
    if not a.index.equals(b.index):raise ValueError("Schedule chronology")
    return [str(t) for t in a.index[(a.inverter_ac_kw-b.inverter_ac_kw).abs()>1e-7]]

def plan_gate():
    if len(set(EXPECTED.values()))!=2 or len(CASES)*len(FACTORS)*8760!=35040:
        raise ValueError("Plan population")
    if len({s for d,t,x in SHIFTS for s in (d,t)})!=4 or any(d>=t or x<=0 for d,t,x in SHIFTS):
        raise ValueError("Transfer plan")

def prepare():
    st,fh,m,mapping,profiles,solar,top,table,validate_device=sizing.context(ROOT)
    sys.path.insert(0,str(ROOT/sample.SYN))
    import matched16_reciprocal_p1_thermal_ac as thermal
    import matched16_106039_ss90_reciprocal_annual as cache
    import matched16_reciprocal12_p2p3_ac_screen as p2
    import matched16_94022_ss90_mar_nov_annual_ac as annual
    gate=thermal.gate
    _,prepared,v6=thermal.preflight(ROOT)
    _,planned,groups,_=p2.preflight(ROOT)
    annual.check_source_stateless(v6)
    item=prepared[SIX]
    r=gate.read_json(ROOT/cache.ARCHIVE/"RUN_MANIFEST.json")
    if r["status"]!="P1_THERMAL_120_AC_COMPLETE_NOT_ANNUAL" or r["new_AC_case_hours"]!=120 or r["converged"]!=120 or r["infeasible"]!=12 or r["annual_AC_verified"] is not False:
        raise ValueError("Thermal receipt")
    a=ROOT/cache.ARCHIVE/"DONOR_TARGET_120_AC_CASEHOURS.csv"
    b=ROOT/cache.ARCHIVE/"PAIR_CANDIDATES_30.csv"
    for path,sig in ((a,THERMAL_SHA),(b,PAIR_SHA)):
        if r["outputs_sha256"][path.name]!=sig:raise ValueError("Thermal hash receipt")
        gate.signed_bytes(path,sig)
    rows=gate.read_csv(a);pairs=gate.read_csv(b)
    if len(rows)!=120 or len(pairs)!=30 or len({(z["case"],z["target_time"],z["fraction"],z["pf"],z["point"]) for z in rows})!=120:
        raise ValueError("Thermal population")
    chosen=[z for z in r["combined_candidates"] if z["case"]==SIX]
    if len(chosen)!=1 or not chosen[0]["combined_annual_SOC_valid"] or not chosen[0]["all_event_pairs_pass"]:
        raise ValueError("Combined SOC receipt")
    choices=chosen[0]["choices"]
    if [(z["donor_time"],z["target_time"],z["moved_dc_kw"]) for z in choices]!=list(SHIFTS):
        raise ValueError("Frozen transfer choices")
    original=item["source"]
    modified=thermal.combined_frame(original,choices)
    em=thermal.check_energy(modified,item)
    old={};new={}
    for d,t,x in SHIFTS:
        events=[z for z in item["events"] if z["donor"]==d and z["target"]==t]
        w=[z for z in pairs if z["case"]==SIX and z["target_time"]==t and float(z["fraction"])==.25]
        if len(events)!=1 or len(w)!=1 or w[0]["pair_4of4_AC_screen_pass"]!="True" or int(w[0]["passed_local_AC_points"])!=4 or abs(float(w[0]["moved_dc_kw"])-x)>1e-8 or abs(events[0]["cap"]*.25-x)>1e-8:
            raise ValueError("Selected transfer gate")
        old.update(cache.select_pair(rows,SIX,d,t,0.));new.update(cache.select_pair(rows,SIX,d,t,.25))
    changed=changes(original,modified)
    if changed!=sorted(old) or set(new)!=set(old) or len(changed)!=4:
        raise ValueError("Four changed P hours")
    for t in changed:
        cache.validate_row(old[t],original,t,EXPECTED[SIX])
        cache.validate_row(new[t],modified,t,EXPECTED[SIX])
        if not cache.bool_ac(new[t]["ac_feasible"]):raise ValueError("Corrected archive failed")
    p1m=gate.read_json(ROOT/thermal.nov.P1/"RUN_MANIFEST.json")
    p1path=ROOT/thermal.nov.P1/"TARGETED_36_AC_CASEHOURS.csv"
    gate.signed_bytes(p1path,p1m["targeted_ac_csv_sha256"])
    p1=[z for z in gate.read_csv(p1path) if z["case"]==SIX and float(z["pf"])==.98]
    if len(p1)!=4:raise ValueError("Six-house P1 reference population")
    for z in p1:cache.validate_row(z,original,z["timestamp_lst"],EXPECTED[SIX])
    terr,ids,trace,c=groups[FOUR]
    f=read_frame(ROOT/c["target_energy_csv"])
    p2m=gate.read_json(ROOT/"StudyA_Reciprocal12_P2P3_AC_Screen_v1/RUN_MANIFEST.json")
    p2path=ROOT/"StudyA_Reciprocal12_P2P3_AC_Screen_v1/TARGETED_300_AC_CASEHOURS.csv"
    if p2m["status"]!="P2P3_TARGETED_300_AC_CASEHOURS_RECORDED_NOT_ANNUAL" or p2m["targeted_ac_csv_sha256"]!=P2_SHA or p2m["converged"]!=300 or p2m["infeasible"]!=0:
        raise ValueError("P2/P3 receipt")
    gate.signed_bytes(p2path,P2_SHA)
    p3=[z for z in gate.read_csv(p2path) if z["case"]==FOUR and float(z["pf"])==.98]
    stamps={z["timestamp_lst"] for z in planned if z["case"]==FOUR}
    if len(p3)!=25 or len(stamps)!=25 or {z["timestamp_lst"] for z in p3}!=stamps:raise ValueError("Four-house benchmark population")
    for z in p3:cache.validate_row(z,f,z["timestamp_lst"],EXPECTED[FOUR])
    datasets={SIX:(item["case"],item["ids"],item["trace"],original,modified),FOUR:(c,ids,trace,f,f)}
    contexts={};energy=[]
    for name,(c,ids,trace,orig,frame) in datasets.items():
        h=c["hardware"]
        if c!=top["completed_cases"][name] or c["target_energy_sha256"]!=EXPECTED[name] or c["assignment_for_load"]!=name[-2:] or str(c["transformer"])!="113699" or ids!=IDS[name] or sizing.hardware_tuple(h)!=HW[name]:
            raise ValueError("Frozen source case identity "+name)
        signed(ROOT/c["target_energy_csv"],EXPECTED[name])
        q=table[table.case.eq(name)]
        if len(q)!=1 or q.iloc[0].source_sha!=EXPECTED[name]:raise ValueError("Coverage identity")
        demand=trace.sum(axis=1)
        if abs(float(demand.sum())-1898*len(ids))>1e-5:raise ValueError("Household annual demand")
        for a in (orig,frame):sizing.validate_comparison(a,h,demand,solar)
        for k,col in (("source_import_ac_kwh","grid_import_kw"),("source_curtail_dc_kwh","curtailed_pv_dc_kw")):
            if abs(float(q.iloc[0][k])-float(frame[col].sum()))>1e-5:raise ValueError("Energy source total")
        territories={l:v6.new_territory(ROOT,name[-2:],"113699",ids,l) for l in (1.,1.6)}
        if any(float(z.trafo["kva"])!=3. or sorted(a["house"] for a in z.attachments)!=sorted(ids) for z in territories.values()):
            raise ValueError("GIS/rating identity")
        contexts[name]=dict(ids=ids,trace=trace,frames={name:frame},hardware={name:h},original=orig,territories=territories)
        e=sizing.summary(name,"113699_reciprocal","SIGNED_SOURCE_25PCT_SHIFT" if name==SIX else "SIGNED_ORIGINAL",h,frame,c["target_model_summary"])
        e.update(source_energy_sha256=EXPECTED[name],changed_inverter_hours=len(changes(orig,frame)));energy.append(e)
    return v6,annual,contexts,energy,old,new,p1,p3

def execute(prepared,report):
    import pandapower as pp
    from run_epm_validation import build_net
    v6,annual,contexts,energy,old,new,p1,p3=prepared
    for e in energy:
        c=e["case"];f=contexts[c]["frames"][c];path=OUT/(c+"_VALIDATED_SCHEDULE.csv")
        f.to_csv(path,index_label="timestamp_lst",float_format="%.10f")
        e["validated_schedule_sha256"]=sha(path)
        print("GAP113699_ENERGY="+json.dumps(e,allow_nan=False),flush=True)
    pd.DataFrame(energy).to_csv(OUT/"ENERGY_SUMMARY.csv",index=False)
    report["energy_results"]=energy
    results=[];report["annual_results"]=results
    old_checks=0;new_checks=0;four_checks=0;extra_solves=0
    for c in CASES:
        x=contexts[c];f=x["frames"][c]
        e=next(z for z in energy if z["case"]==c)
        for pf,l in FACTORS:
            terr=x["territories"][l];net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Load keys")
            if c==SIX and (pf,l)==(.98,1.):
                orig=dict(x,frames={c:x["original"]})
                for t,r in old.items():
                    q=runner.checked(v6,pp,net,meta,terr,orig,c,pd.Timestamp(t),pf)
                    extra_solves+=1
                    annual.exact_ac_regression(q,r,c+" original "+t);old_checks+=1
                    for z in p1:
                        if z["timestamp_lst"]==t:
                            annual.exact_ac_regression(q,z,c+" old P1 "+t);old_checks+=1
            rows=[]
            for i,t in enumerate(f.index):
                q=runner.checked(v6,pp,net,meta,terr,x,c,t,pf)
                stamp=str(t)
                if (pf,l)==(.98,1.):
                    if c==SIX:
                        if stamp in new:
                            annual.exact_ac_regression(q,new[stamp],c+" corrected "+stamp);new_checks+=1
                        else:
                            for z in p1:
                                if z["timestamp_lst"]==stamp:
                                    annual.exact_ac_regression(q,z,c+" unchanged P1 "+stamp);old_checks+=1
                    else:
                        for z in p3:
                            if z["timestamp_lst"]==stamp:
                                annual.exact_ac_regression(q,z,c+" P3 "+stamp);four_checks+=1
                q.update(case=c,pf=pf,length_factor=l,source_energy_sha256=EXPECTED[c],
                         validated_schedule_sha256=e["validated_schedule_sha256"],source_grid_import_kw=float(f.at[t,"grid_import_kw"]),strict_feasible=rn.strict_point(q))
                rows.append(q)
                if (i+1)%2000==0:print("Annual",c,pf,l,i+1,flush=True)
            a=pd.DataFrame(rows)
            if len(a)!=8760 or not pd.DatetimeIndex(pd.to_datetime(a.timestamp_lst)).equals(f.index):raise ValueError("Annual chronology")
            file=OUT/(c+"_PF"+str(round(pf*100))+"_L"+str(round(l*10))+"_ANNUAL_AC.csv")
            annual.save_csv(file,rows)
            loss=float(a.loss_kw.sum())
            result=dict(case=c,pf=pf,length_factor=l,hours=8760,source_energy_sha256=EXPECTED[c],
                validated_schedule_sha256=e["validated_schedule_sha256"],**runner.stats(a),
                annual_losses_kwh=loss,annual_energy_cost_usd=e["annual_total_usd"],
                all_loss_purchase_cost_usd=e["annual_total_usd"]+.29*loss,
                annual_import_kwh=e["import_ac_kwh"],annual_curtail_dc_kwh=e["curtail_dc_kwh"],
                failed_timestamps_first_100=a.loc[~a.strict_feasible,"timestamp_lst"].astype(str).head(100).tolist(),output_sha256=sha(file))
            results.append(result);print("GAP113699_ANNUAL_RESULT="+json.dumps(result,allow_nan=False),flush=True)
            save(OUT/"PARTIAL_RESULTS.json",report)
    if len(results)!=4 or old_checks!=8 or new_checks!=4 or four_checks!=25 or extra_solves!=4:
        raise ValueError("Regression accounting")
    pd.DataFrame(results).to_csv(OUT/"ANNUAL_SUMMARY.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(11,4.5),layout="constrained")
    a=pd.DataFrame(results)
    for i,(pf,l) in enumerate(FACTORS):
        z=a[a.pf.eq(pf)&a.length_factor.eq(l)].set_index("case").loc[list(CASES)]
        pos=np.arange(2)+(i-.5)*.36
        ax[0].bar(pos,z.minimum_voltage_pu,.36,label=f"PF {pf}, length {l}")
        ax[1].bar(pos,z.peak_transformer_pct,.36,label=f"PF {pf}, length {l}")
    ax[0].axhline(.95,ls="--",color="firebrick");ax[0].set_ylim(min(.93,float(a.minimum_voltage_pu.min())-.002),1.05);ax[0].set_ylabel("Annual minimum voltage (pu)")
    ax[1].axhline(100,ls="--",color="firebrick");ax[1].set_ylabel("Peak transformer loading (%)")
    for z in ax:z.set_xticks(range(2),["A1 six-house SS90","A0 four-house min-cost"]);z.legend(fontsize=8)
    fig.suptitle("113699 reciprocal annual reference and stress replay")
    for ext in ("png","svg"):fig.savefig(OUT/("113699_gap."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_113699_RECIPROCAL_GAP_ANNUAL",new_annual_AC_case_hours=35040,
        old_source_regressions=old_checks,corrected_point_regressions=new_checks,
        four_house_regressions=four_checks,extra_original_point_solves=extra_solves,
        passing_groups=sum(r["strict_failures"]==0 for r in results))

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter();preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),
        runner_id=os.environ.get("CI_RUNNER_ID"),cases=list(CASES),factors=[list(z) for z in FACTORS],
        planned_annual_AC_case_hours=35040,planned_new_LPs=0,source_energy_hashes=EXPECTED,field_verified=False,
        offline_perfect_foresight=True,assumed_transformer_kva=3.,night_Q_disabled=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_113699_reciprocal_gap.py","test_remote_A1_94022_annual.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        plan_gate()
        prepared=prepare()
        report.update(preflight_source_energy_results=prepared[3],source_thermal_archive_sha256=THERMAL_SHA,
            source_p2_archive_sha256=P2_SHA,planned_changed_hours=4)
        if preflight:report["status"]="COMPLETE_SIGNED_113699_GAP_PREFLIGHT"
        else:execute(prepared,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}
        save(OUT/"GAP113699_REPORT.json",report)
        print("GAP113699_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_113699_GAP_PREFLIGHT","COMPLETE_113699_RECIPROCAL_GAP_ANNUAL") else 1

if __name__=="__main__":raise SystemExit(main())
