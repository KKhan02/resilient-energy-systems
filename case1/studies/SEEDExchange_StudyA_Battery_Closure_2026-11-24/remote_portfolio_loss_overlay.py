#!/usr/bin/env python3
"""Source-locked annual AC overlay, four existing native schedules, zero annual re-solves."""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import remote_94022_A1_annual as runner
import reserve_full_night as rn
from audit_battery_coverage import signed,read_frame,read_json
from pathlib import Path

BASE=Path("case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01")
MC0="A0_106039_min_cost_ref"
SS0="A0_106039_ss90_ref"
SS1="A1_106039_ss90_ref"
MC1="A1_113699_min_cost_ref"
FACTORS=((.98,1.),(.95,1.6))
PLAN={
 MC0:("StudyA_A0_106039_Sequenced_Trial_v1","53012c200ee5b34cf0a2a4962dc52e92b492853ae95d702e78897b02796c6b54","e7012b9b4b1de728dd4ff756e6a55f42524d53f993003621476076e65c00f768",39),
 SS0:("StudyA_A0_106039_Sequenced_Trial_v1","a3453b283d2846bc8ddd7f809977ba75a9267b7f09088159ee52f2bea2c075ae","241887b0cde5d47c6dcf89aca299cd191d40811df356c2f26eb790906429928c",2),
 SS1:("StudyA_A1_106039_Redispatch_Trial_v1","449b8bbc098aba355b37abce10ece2ff6160b77eafc226c89139d430f948c947","942d7ff67ddde09b8bef0452896f92cf0944dd2cdb012cbfc4d766bc44c2dc74",2),
 MC1:("StudyA_A1_Mapped_Redispatch_Trial_v1","ce9493033a7c58775e5528a6e2809143746e3469019a1085891aa4348668c28a","417a1221c460d2749cef33f2bcea9c04287946fe0f41dd48f28416c5f193dc0c",4)}
AUDIT=Path("StudyA_A0_106039_ChangedHour_PQ_Audit_v2")
COLS=["min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw","q_selected_kvar","pcc_kva"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(a,b,tol=1e-6):
    if not np.allclose(a,b,rtol=0,atol=tol):raise ValueError("Numeric identity mismatch")
def changed(a,b):
    if not a.index.equals(b.index):raise ValueError("Clock mismatch")
    for col in ("demand_kw","pv_dc_available_kw"):
        check(a[col],b[col],1e-8)
    delta=b.inverter_ac_kw-a.inverter_ac_kw
    if abs(float(delta.sum()))>1e-4:raise ValueError("Nonneutral P change")
    return a.index[delta.abs()>1e-8]
def strict(a):
    return a.ac_feasible & a.min_v_pu.ge(.95)&a.max_v_pu.le(1.05)&a.max_trafo_pct.le(100)&a.max_line_pct.le(100)
def overlay(a,rows):
    z=a.copy()
    for t,q in rows.items():
        if t not in z.index:raise ValueError("Unknown timestamp")
        for k in z.columns:
            if k in q and k!="timestamp_lst":z.at[t,k]=q[k]
    z["strict_feasible"]=strict(z)
    return z
def prepare():
    st,fh,m,mapping,profiles,solar,top,table,validate_device=sizing.context(ROOT)
    sys.path.insert(0,str(ROOT/sample.SYN))
    import matched16_original_ac_input_preflight as base
    import matched16_94022_ss90_mar_nov_annual_ac as annual
    _,v6,_,_=st.secure_context(ROOT,ROOT/st.MANIFEST_REL)
    annual.check_source_stateless(v6)
    am=read_json(ROOT/AUDIT/"RUN_MANIFEST.json")
    if am["status"]!="A0_CHANGED_HOUR_PQ_REPLAY_PASS" or am["changed_P_hours"]!=39 or am["candidate_annual_energy_sha256"]!=PLAN[MC0][2] or am["source_energy_sha256"]!=PLAN[MC0][1] or am["replay_csv_sha256"]!="bc1fec7944e0b9b412b4209d99622f06c2250ab67ed33e065300c0427961c120" or am["failed_comparisons"]:
        raise ValueError("Existing MC0 replay receipt")
    signed(ROOT/AUDIT/"REPLAY_PQ_AUDIT.csv",am["replay_csv_sha256"])
    replay=pd.read_csv(ROOT/AUDIT/"REPLAY_PQ_AUDIT.csv",parse_dates=["timestamp_lst"])
    if len(replay)!=702:raise ValueError("Replay population")
    data={};receipts=[]
    for c,(folder,source_sha,candidate_sha,n) in PLAN.items():
        assign,territory=c.split("_")[:2]
        ep=ROOT/BASE/("energy_"+c);em=read_json(ep/"energy_manifest.json")
        h=em["hardware"];ids,trace=st.source_trace(m,mapping,profiles,assign,territory)
        if em["energy_csv_sha256"]!=source_sha or em["selected_house_ids"]!=ids or em["scenario"]!=assign or str(em["transformer"])!=territory or em["input_manifest_sha256"]!=top["input_manifest_sha256"]:
            raise ValueError("Native energy identity "+c)
        path=ep/"energy_hourly_2025.csv";signed(path,source_sha);f=read_frame(path)
        root=ROOT/folder
        if c==SS1:
            tm=read_json(root/"trial_manifest.json");q=tm["candidate_annual_files"]["ss90_ref"]
            if tm["status"]!="ALL_NINE_PF_LENGTH_CASES_FEASIBLE" or q["sha256"]!=candidate_sha:raise ValueError("SS1 manifest")
            cp=root/q["path"];compact=None
        else:
            tm=read_json(root/"TRIAL_MANIFEST.json");q=[z for z in tm["candidate_files"] if z["case"]==c and z["dispatch"]=="optimized"]
            if len(q)!=1 or q[0]["input_energy_sha256"]!=source_sha or q[0]["sha256"]!=candidate_sha:raise ValueError("Trial candidate")
            if tm["status"]!=("ALL_SELECTED_A1_PASSED" if c==MC1 else "ALL_SELECTED_A0_PILOT_GROUPS_PASSED"):raise ValueError("Trial status")
            cp=root/q[0]["candidate_file"];compact=pd.read_csv(root/"CHANGED_HOURS_FINAL_AC.csv",parse_dates=["timestamp_lst"])
            reuse=pd.read_csv(root/"NINE_FACTOR_ANNUAL_REUSE.csv")
        signed(cp,candidate_sha);z=read_frame(cp)
        for fr in (f,z):sizing.validate_comparison(fr,h,trace.sum(axis=1),solar)
        for k in ("grid_import_kw","curtailed_pv_dc_kw","battery_discharge_dc_kw","battery_charge_dc_kw"):check(f[k].sum(),z[k].sum(),1e-5)
        check(f.battery_soc_usable_kwh.iloc[-1],z.battery_soc_usable_kwh.iloc[-1],1e-7)
        times=changed(f,z)
        if len(times)!=n:raise ValueError("Changed hour count "+c+" "+str(len(times)))
        xs=dict(ids=ids,trace=trace,frames={c:f},hardware={c:h});zs=dict(xs,frames={c:z})
        for pf,l in FACTORS:
            name=f"{c}_mapped_optimized_pf{round(pf*100):03d}_length{round(l*10):02d}_annual8760"
            ardir=ROOT/BASE/"annual_ac_replays_v1"/name;ar=read_json(ardir/"ac_summary.json")
            if ar["status"]!="ANNUAL_PVBESS_AC" or ar["scenario"]!=assign or str(ar["transformer"])!=territory or ar["selected_house_ids"]!=ids or ar["input_manifest_sha256"]!=top["input_manifest_sha256"] or ar["topology"]!="mapped" or ar["dispatch"]!="optimized" or ar["hours"]!=8760 or ar["converged_hours"]!=8760 or ar["pf"]!=pf or ar["length_factor"]!=l or ar["q_ratio_daylight"]!=.25 or ar["night_q_disabled"] is not True:
                raise ValueError("Archive metadata "+name)
            signed(ep/"energy_manifest.json",ar["energy_manifest_sha256"])
            if c==SS1:
                if tm["source_annual_signatures"]["ss90_ref"]!=ar["energy_manifest_sha256"]:raise ValueError("SS1 energy manifest")
                q=[v for v in tm["screens"] if v["tier"]=="ss90_ref" and v["pf"]==pf and v["length_factor"]==l]
                if len(q)!=1 or q[0]["original_ac_sha256"]!=ar["ac_hourly_sha256"] or not q[0]["all_8760_hours_accounted_for"] or q[0]["candidate_bad_hours"]!=0 or q[0]["changed_hours"]!=n:raise ValueError("SS1 annual receipt")
                control=q[0];comp=None
            else:
                q=reuse[(reuse.case==c)&(reuse.dispatch=="optimized")&(reuse.pf==pf)&(reuse.length_factor==l)]
                if len(q)!=1 or q.iloc[0].source_ac_sha256!=ar["ac_hourly_sha256"] or q.iloc[0].trial_bad_hours!=0 or q.iloc[0].annual_hours_accounted_for!=8760:raise ValueError("Annual reuse receipt")
                comp=compact[(compact.case==c)&(compact.dispatch=="optimized")&(compact.pf==pf)&(compact.length_factor==l)].set_index("timestamp_lst")
                if len(comp)!=n or set(comp.index)!=set(times) or not comp.ac_feasible.all():raise ValueError("Compact controls "+c)
                control=None
            ap=ardir/"ac_hourly.csv";mode=signed(ap,ar["ac_hourly_sha256"])
            ac=pd.read_csv(ap,parse_dates=["timestamp_lst"]).set_index("timestamp_lst",drop=False)
            if not ac.index.equals(f.index) or not ac.status.eq("CONVERGED").all():raise ValueError("Archive chronology")
            check(ac.load_pf,pf,1e-8);check(ac.inverter_ac_kw,f.inverter_ac_kw,1e-8);check(ac.gross_demand_kw,f.demand_kw,1e-8)
            night=f.pv_dc_available_kw<=1e-9
            if not np.array_equal(night.to_numpy(),ac.night_reactive_disabled.to_numpy()) or (ac.loc[night,"q_selected_kvar"].abs()>1e-8).any() or not np.isfinite(ac[COLS].to_numpy(float)).all():raise ValueError("Archive night/finite")
            check(ac.loss_kw.sum(),ar["annual_or_sample_losses_kwh"],1e-6)
            check(ac.min_v_pu.min(),ar["min_voltage_pu"],1e-8);check(ac.max_trafo_pct.max(),ar["max_transformer_loading_pct"],1e-8)
            if int((~ac.ac_feasible).sum())!=ar["AC_infeasible_hours"]:raise ValueError("Archive failure count")
            ac["strict_feasible"]=strict(ac)
            if c==MC0 and am["source_AC_sha_by_factor"][f"pf{pf:.2f}_length{l:.1f}"]!=ar["ac_hourly_sha256"]:raise ValueError("MC0 audit AC source")
            terr=v6.new_territory(ROOT,assign,territory,ids,l)
            if sorted(a["house"] for a in terr.attachments)!=sorted(ids) or float(terr.trafo["kva"])!=float(h["transformer_kva_assumed_or_evidenced"]):raise ValueError("Territory identity")
            data[c,pf,l]=(xs,zs,times,ac,comp,control,terr)
            receipts.append(dict(case=c,pf=pf,length_factor=l,source_energy_sha256=source_sha,validated_schedule_sha256=candidate_sha,source_ac_sha256=ar["ac_hourly_sha256"],archive_signature_mode=mode,changed_hours=n,source_annual_hours=8760))
    return v6,annual,data,receipts,replay

def execute(prepared,report):
    import pandapower as pp
    from run_epm_validation import build_net
    v6,annual,data,receipts,replay=prepared;results=[];detail=[];solves=0;reused_points=0
    report["annual_results"]=results
    for (c,pf,l),(xs,zs,times,ac,comp,control,terr) in data.items():
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(xs["ids"]):raise ValueError("Net load identity")
        corrected={}
        for t in times:
            if c==MC0:
                a=replay[(replay.pf==pf)&(replay.length_factor==l)&(replay.timestamp_lst==t)]
                if len(a)!=2 or not a.comparison_pass.all():raise ValueError("MC0 replay coverage")
                old=a[a.point=="original"].iloc[0].to_dict();new=a[a.point=="corrected"].iloc[0].to_dict();reused_points+=2
            else:
                old=runner.checked(v6,pp,net,meta,terr,xs,c,t,pf)
                new=runner.checked(v6,pp,net,meta,terr,zs,c,t,pf);solves+=2
            annual.exact_ac_regression(old,ac.loc[t].to_dict(),c+" original "+str(t))
            check(new["inverter_ac_kw"],zs["frames"][c].at[t,"inverter_ac_kw"],1e-5)
            if new["status"]!="CONVERGED" or not rn.strict_point(new):raise ValueError("Corrected point failed")
            if comp is not None:
                for k in ("min_v_pu","max_trafo_pct"):check(new[k],comp.loc[t,k],2e-4)
            corrected[t]=new
            detail.append(dict(case=c,pf=pf,length_factor=l,timestamp_lst=str(t),old_loss_kw=float(old["loss_kw"]),new_loss_kw=float(new["loss_kw"]),old_min_v=float(old["min_v_pu"]),new_min_v=float(new["min_v_pu"]),old_peak_trafo=float(old["max_trafo_pct"]),new_peak_trafo=float(new["max_trafo_pct"]),evidence="SIGNED_EXISTING_REPLAY" if c==MC0 else "NEW_CHANGED_HOUR_REPLAY"))
        stitched=overlay(ac,corrected)
        check(stitched.inverter_ac_kw,zs["frames"][c].inverter_ac_kw,1e-8)
        check(stitched.loss_kw.sum(),ac.loss_kw.sum()+sum(float(q["loss_kw"])-float(ac.at[t,"loss_kw"]) for t,q in corrected.items()),1e-7)
        stats=runner.stats(stitched)
        if control is not None:
            check(stats["minimum_voltage_pu"],control["min_v_pu"],2e-4);check(stats["peak_transformer_pct"],control["candidate_max_trafo_pct"],2e-4)
            if pf==.98:check(stitched.loss_kw.sum(),398.29336041168557,1e-5)
        source=next(r for r in receipts if r["case"]==c and r["pf"]==pf and r["length_factor"]==l)
        path=OUT/(c+f"_PF{round(pf*100)}_L{round(l*10)}_OVERLAY.csv")
        stitched.to_csv(path,index=False)
        r=dict(**source,**stats,unchanged_hours=8760-len(times),baseline_losses_kwh=float(ac.loss_kw.sum()),annual_losses_kwh=float(stitched.loss_kw.sum()),delta_loss_kwh=float(stitched.loss_kw.sum()-ac.loss_kw.sum()),output_sha256=sha(path),failed_timestamps=[str(t) for t in stitched.index[~stitched.strict_feasible]])
        results.append(r);print("PORTFOLIO_OVERLAY_RESULT="+json.dumps(r,allow_nan=False),flush=True)
    if len(results)!=8 or solves!=32 or reused_points!=156 or len(detail)!=94:raise ValueError("Overlay accounting")
    pd.DataFrame(detail).to_csv(OUT/"CHANGED_HOUR_LOSS_DELTA.csv",index=False);pd.DataFrame(results).to_csv(OUT/"ANNUAL_OVERLAY_SUMMARY.csv",index=False)
    report.update(status="COMPLETE_NATIVE_PORTFOLIO_LOSS_OVERLAY",new_AC_point_solves=solves,reused_signed_point_records=reused_points,annual_case_hours_accounted=8*8760,passing_groups=sum(r["strict_failures"]==0 for r in results))
def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter();preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),runner_id=os.environ.get("CI_RUNNER_ID"),planned_new_AC_point_solves=32,planned_annual_hours_accounted=70080,planned_new_LPs=0,field_verified=False)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_portfolio_loss_overlay.py","test_remote_A1_94022_annual.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        prepared=prepare();report["archive_receipts"]=prepared[3]
        if preflight:report["status"]="COMPLETE_SIGNED_NATIVE_LOSS_OVERLAY_PREFLIGHT"
        else:execute(prepared,report)
    except Exception as exc:report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}
        save(OUT/"PORTFOLIO_OVERLAY_REPORT.json",report)
        print("PORTFOLIO_OVERLAY_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_NATIVE_LOSS_OVERLAY_PREFLIGHT","COMPLETE_NATIVE_PORTFOLIO_LOSS_OVERLAY") else 1
if __name__=="__main__":raise SystemExit(main())
