#!/usr/bin/env python3
"""Fixed hardware, SOC constrained middle-placement reserve benchmark. No new assets."""
import hashlib, json, os, platform, sys, time, traceback
from urllib.request import Request, build_opener, HTTPRedirectHandler, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT, OUT, STUDY, run, save, restore
import remote_94022_middle_night as screen
import sizing_matched_physical_options as mo
import sizing_priority_pilot as sizing
import sizing_ac_followup as follow
import reserve_full_night as rn
from audit_battery_coverage import read_frame

SCREEN_SHA="e3ad2ccebf9654bafa0a1a47e70d81eaf38b460986d04107e094843824777f60"
SCREEN_JOB=18393653618
FACTORS=((.98,1.),(.95,1.6))
CASE_HASHES={
    "A1_94022_min_cost_to_A0":"e7a4178ac1f9df771a19ab631222b1396279c2669b5b5334e9c4f792a83eac00",
    "94022_B6":"8bc331e1f7100caf7e6ec51521f745b77218beb0a2aa0fe6487b7cff53b00fb7",
    "94022_B7":"fb87f90e55aa523790353e4d172c577aea91e0e1a816ccebef9498ca1b93b37e"}
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def fetch_screen():
    """Read only the exact same-project prior artifact with the ephemeral job token.
    Never forward that token to redirected storage, log it, or modify the project.
    """
    token=os.environ.get("CI_JOB_TOKEN")
    if not token:return None
    endpoint="https://gitlab.com/api/v4/projects/88036556/jobs/18393653618/artifacts/remote-research/MIDDLE_NIGHT_SCREEN.csv"
    req=Request(endpoint,headers={"JOB-TOKEN":token})
    try:
        try:
            response=build_opener(NoRedirect()).open(req,timeout=45)
        except HTTPError as exc:
            if exc.code in (301,302,303,307,308):
                dest=urljoin(endpoint,exc.headers.get("Location",""))
                parts=urlsplit(dest)
                if parts.scheme!="https" or not parts.hostname or parts.username or parts.password or dest==endpoint:
                    raise ValueError("Unexpected artifact redirect")
                response=urlopen(Request(dest),timeout=45)
            elif exc.code in (401,403,404,405):
                print("Prior artifact endpoint unavailable; verified deterministic screen replay permitted",flush=True)
                return None
            else:raise
        with response:
            data=response.read(10_000_001)
        if len(data)>10_000_000 or hashlib.sha256(data).hexdigest()!=SCREEN_SHA:
            raise ValueError("Prior artifact digest mismatch")
        return data
    except (HTTPError, URLError, TimeoutError) as exc:
        # Do not log exceptions containing signed redirect URLs.
        print("Prior artifact retrieval unavailable: "+type(exc).__name__,flush=True)
        return None

def validate_corridors(path,night):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=SCREEN_SHA:
        raise ValueError("Screen SHA differs from prior completed job")
    a=pd.read_csv(path,parse_dates=["timestamp_lst"],keep_default_na=False)
    if len(a)!=4353 or not pd.DatetimeIndex(a.timestamp_lst).equals(night) or not a.timestamp_lst.is_unique:
        raise ValueError("Night chronology/coverage")
    if not a.zero_pass.isin([True,False]).all() or not a.ceiling_pass.eq(True).all():
        raise ValueError("Endpoint status mismatch")
    sel=a.status.eq("TESTED_TERMINAL_CORRIDOR")
    if int(sel.sum())!=241 or not np.array_equal(sel.to_numpy(),(~a.zero_pass).to_numpy()) or not a.loc[~sel,"status"].eq("BOTH_ENDPOINTS_PASS_NOT_CONTINUOUS_PROOF").all():
        raise ValueError("Corridor identities changed")
    q=a[sel].copy()
    lo=pd.to_numeric(q.lower_kw);hi=pd.to_numeric(q.upper_kw);cap=pd.to_numeric(q.ceiling_kw)
    if not np.isfinite(np.column_stack([lo,hi,cap])).all() or (lo<=0).any() or (hi<lo).any() or (hi>cap+1e-9).any():
        raise ValueError("Invalid tested bounds")
    if abs(float(lo.sum())-63.81174350369871)>1e-8 or abs(float(lo.max())-1.1808925642623145)>1e-9:
        raise ValueError("Corridor summary changed")
    return {pd.Timestamp(t):(float(l),float(h)) for t,l,h in zip(q.timestamp_lst,lo,hi)}

def source_controls(prepared):
    import pandapower as pp
    v6,annual,x,reg,bench,night,endpoint=prepared
    checks=0
    for pf,l in FACTORS:
        terr=x["territories"][l]
        net,meta=mo.build(terr,"middle",reg,l)
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
        for c in mo.CASES:
            for t in x["hours"]:
                q=follow.evaluate(v6,pp,net,meta,terr,x,c,t,pf)
                q["strict_feasible"]=rn.strict_point(q)
                mo.exact_sample_row(annual,q,bench.loc[("middle",c,pf,l,t)].to_dict(),c+" "+str(t))
                checks+=1
    if checks!=402:raise ValueError("Regression coverage")
    return checks

def solve(prepared,report,corridors):
    import pandapower as pp
    import fixed_hardware as fh
    import study_a_pvbess as st
    v6,annual,x,reg,bench,night,endpoint=prepared
    common=mo.CASES[0];demand=x["trace"].sum(axis=1)
    solar,_=st.solar_per_unit(ROOT,demand.index)
    completed=[];energy=[];errors=[]
    report.update(completed_cases=completed,energy_results=energy,solver_infeasible=errors)
    for c in mo.CASES:
        h=x["hardware"][c];old=x["frames"][c]
        hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
            battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
            transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,
            load_pf=.98,export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        print("Reserve LP",c,flush=True)
        try:
            f,model=fh.solve_fixed(ROOT,hw,demand,solar,corridors=corridors,min_physical_soc=.20)
        except RuntimeError as exc:
            if "infeasible" not in str(exc).lower():raise
            errors.append(dict(case=c,solver_result=str(exc)));continue
        f.index.name="timestamp_lst";sizing.validate_comparison(f,h,demand,solar)
        path=OUT/(c+"_MIDDLE_RESERVE_8760.csv")
        f.to_csv(path,float_format="%.10f")
        f=read_frame(path);sizing.validate_comparison(f,h,demand,solar)
        for t,(lo,hi) in corridors.items():
            if not lo-1e-6<=float(f.at[t,"inverter_ac_kw"])<=hi+1e-6:
                raise ValueError("Reserve corridor violated")
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        metric=sizing.summary(c,"constraint","OFFLINE_MIDDLE_STRESS_RESERVE",h,f,model)
        er=dict(case=c,source_energy_sha256=CASE_HASHES[c],new_energy_sha256=sha,
            battery_modules=int(h["battery_modules"]),annual_model_usd=metric["annual_total_usd"],
            imports_kwh=float(f.grid_import_kw.sum()),curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),
            cycles=float(metric["store_equivalent_discharge_cycles"]),
            annual_self_sufficiency_pct=float(metric["self_sufficiency_pct"]),
            min_store_kwh=float(f.battery_soc_usable_kwh.min()),max_store_kwh=float(f.battery_soc_usable_kwh.max()),
            changed_inverter_hours=int(old.inverter_ac_kw.ne(f.inverter_ac_kw).sum()))
        energy.append(er)
        new=dict(x,frames={c:f})
        for pf,l in FACTORS:
            terr=x["territories"][l];net,meta=mo.build(terr,"middle",reg,l)
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity changed")
            rows=[]
            for i,t in enumerate(f.index):
                q=follow.evaluate(v6,pp,net,meta,terr,new,c,t,pf)
                if q["status"]!="CONVERGED" or not np.isfinite([q[k] for k in ("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw")]).all():
                    raise ValueError("Annual AC nonconvergence/nonfinite "+c+" "+str(t))
                if bool(q["night_reactive_disabled"])!=bool(f.at[t,"pv_dc_available_kw"]<=1e-9):
                    raise ValueError("Night policy")
                if q["night_reactive_disabled"] and abs(float(q["q_selected_kvar"]))>1e-9:raise ValueError("Night Q")
                q.update(case=c,option="middle",pf=pf,length_factor=l,source_energy_sha256=CASE_HASHES[c],
                    corrected_energy_sha256=sha,source_grid_import_kw=float(f.at[t,"grid_import_kw"]),strict_feasible=rn.strict_point(q))
                rows.append(q)
                if (i+1)%2000==0:print("Annual AC",c,pf,l,i+1,flush=True)
            if len(rows)!=8760:raise ValueError("AC coverage")
            z=pd.DataFrame(rows)
            if not pd.DatetimeIndex(pd.to_datetime(z.timestamp_lst)).equals(f.index):raise ValueError("AC chronology")
            failed=~z.strict_feasible
            name=c+"_PF"+str(round(pf*100))+"_L"+str(round(l*10))+"_ANNUAL_AC.csv"
            annual.save_csv(OUT/name,rows)
            result=dict(case=c,pf=pf,length_factor=l,hours=8760,converged=8760,
                strict_failures=int(failed.sum()),night_failures=int((failed&z.night_reactive_disabled).sum()),
                daylight_failures=int((failed&~z.night_reactive_disabled).sum()),
                low_voltage_hours=int(z.min_v_pu.lt(.95).sum()),high_voltage_hours=int(z.max_v_pu.gt(1.05).sum()),
                transformer_overload_hours=int(z.max_trafo_pct.gt(100).sum()),line_overload_hours=int(z.max_line_pct.gt(100).sum()),
                minimum_voltage_pu=float(z.min_v_pu.min()),maximum_voltage_pu=float(z.max_v_pu.max()),
                peak_transformer_pct=float(z.max_trafo_pct.max()),peak_line_pct=float(z.max_line_pct.max()),
                losses_kwh=float(z.loss_kw.sum()),all_loss_purchase_cost_usd=float(metric["annual_total_usd"]+.29*z.loss_kw.sum()),
                failed_timestamps_first_30=z.loc[failed,"timestamp_lst"].astype(str).head(30).tolist(),
                corrected_energy_sha256=sha,output_sha256=hashlib.sha256((OUT/name).read_bytes()).hexdigest())
            completed.append(result);print("AC_RESULT="+json.dumps(result,allow_nan=False),flush=True)
        save(OUT/"PARTIAL_RESULTS.json",dict(energy_results=energy,completed_cases=completed,solver_infeasible=errors))
    if len(energy)+len(errors)!=3 or len(completed)!=2*len(energy):raise ValueError("Case coverage")
    pd.DataFrame(energy).to_csv(OUT/"MIDDLE_RESERVE_ENERGY_SUMMARY.csv",index=False)
    pd.DataFrame(completed).to_csv(OUT/"MIDDLE_RESERVE_AC_SUMMARY.csv",index=False)
    if completed:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        a=pd.DataFrame(completed)
        fig,ax=plt.subplots(1,2,figsize=(11,4.5),layout="constrained")
        labels=[c.replace("A1_94022_min_cost_to_A0","5B").replace("94022_B","") for c in mo.CASES]
        for i,(pf,l) in enumerate(FACTORS):
            g=a[a.pf.eq(pf)].set_index("case").reindex(mo.CASES)
            xx=np.arange(3)+(i-.5)*.36
            ax[0].bar(xx,g.minimum_voltage_pu,.36,label=f"PF {pf}, length {l}")
            ax[1].bar(xx,g.strict_failures,.36,label=f"PF {pf}, length {l}")
        ax[0].axhline(.95,ls="--",color="firebrick");ax[0].set_ylim(min(.93,float(a.minimum_voltage_pu.min())-.002),1.05)
        ax[0].set_ylabel("Minimum voltage (pu)");ax[1].set_ylabel("Failed annual hours")
        for z in ax:z.set_xticks(range(3),["5 modules","6 modules","7 modules"]);z.legend(fontsize=8)
        fig.suptitle("94022 | middle placement, offline SOC-constrained reserve")
        for ext in ("png","svg"):fig.savefig(OUT/("middle_reserve_annual."+ext),dpi=180)
        plt.close(fig)
    report.update(status="COMPLETE_MIDDLE_RESERVE_ANNUAL_COMPARISON",new_LPs_optimal=len(energy),
        new_AC_case_hours=sum(z["hours"] for z in completed),
        all_selected_cases_pass=len(completed)==6 and all(z["strict_failures"]==0 for z in completed))

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "annual",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),runner_id=os.environ.get("CI_RUNNER_ID"),
        option="middle",source_screen_job=SCREEN_JOB,source_screen_sha256=SCREEN_SHA,
        factors=[list(x) for x in FACTORS],energy_model_pf=.98,minimum_physical_soc=.20,offline_perfect_foresight=True,
        field_verified=False,night_Q_disabled=True,zero_export=True,planned_LPs=3,planned_max_AC_case_hours=52560)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":
            raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_sizing_option_annual_gate.py","test_reserve_full_night.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        prepared=screen.prepare()
        if prepared[2]["signatures"]!=CASE_HASHES:raise ValueError("Frozen energy identity mismatch")
        if preflight:
            report["status"]="COMPLETE_SIGNED_MIDDLE_RESERVE_PREFLIGHT"
        else:
            data=fetch_screen();path=OUT/"MIDDLE_NIGHT_SCREEN.csv"
            if data is None:
                rec={};screen.solve(prepared,rec)
                if rec.get("status")!="COMPLETE_STATIC_NIGHT_SUPPORT_SCREEN":raise ValueError("Screen replay incomplete")
                report["corridor_source"]="DETERMINISTIC_REPLAY_ARTIFACT_UNAVAILABLE"
            else:
                path.write_bytes(data);report["corridor_source"]="VERIFIED_PRIOR_JOB_ARTIFACT"
            corridors=validate_corridors(path,prepared[5])
            report["corridor_count"]=len(corridors)
            report["source_sample_regressions"]=source_controls(prepared)
            solve(prepared,report,corridors)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"MIDDLE_RESERVE_REPORT.json",report)
        print("MIDDLE_RESERVE_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_MIDDLE_RESERVE_PREFLIGHT","COMPLETE_MIDDLE_RESERVE_ANNUAL_COMPARISON") else 1

if __name__=="__main__":raise SystemExit(main())
