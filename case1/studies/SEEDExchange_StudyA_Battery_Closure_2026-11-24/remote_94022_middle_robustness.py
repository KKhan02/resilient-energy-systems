#!/usr/bin/env python3
"""Nine-factor risk sample of the EXACT previously validated middle reserve schedules.
No new design, margin, dispatch policy, or full-year AC replay.
"""
import hashlib, json, os, platform, sys, time, traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT, OUT, STUDY, run, save, restore
import remote_94022_middle_night as screen
import remote_94022_middle_reserve as reserve
import sizing_matched_physical_options as mo
import sizing_nine_factor as nf
import sizing_priority_pilot as sizing
import sizing_ac_followup as follow
import reserve_full_night as rn
from audit_battery_coverage import read_frame

EXPECTED={
    "A1_94022_min_cost_to_A0":"f603cbb075c99d964a43966b388315cb20ca30c2381c33e921fb8831dbac5e62",
    "94022_B6":"07afc4f017de4ad7480459a79ec1f959c2c4e552614af282bf66b827ba8e84a6",
    "94022_B7":"3fd91441f4eaf48ede433089d10e7948804ea99013216b0c8836223cd330bb7d"}
COUNTS=dict(zip(mo.CASES,(142,143,142)))
FACTORS=nf.FACTORS
PRIOR_ANNUAL_VMIN={.98:.9553534543100245,.95:.9500001035212022}
PRIOR_ANNUAL_VMAX={.98:1.0144577664432284,.95:1.0310504175994948}
PRIOR_ANNUAL_TRAFO={.98:86.48552664279352,.95:90.4721231092274}
PRIOR_ANNUAL_LINE={.98:18.50528991137248,.95:18.172761913459638}

def select_hours(base,corridors,old,new):
    hours=set(base)|set(corridors)
    if set(old)!=set(new):raise ValueError("Case identity mismatch")
    for c,f in new.items():
        a=old[c]
        if not a.index.equals(f.index) or not f.index.is_unique:
            raise ValueError("Chronology mismatch")
        hours.update(f.index[a.inverter_ac_kw.ne(f.inverter_ac_kw)])
        for k in ("demand_kw","grid_import_kw","inverter_ac_kw","pv_dc_available_kw"):
            hours.update(f[k].nlargest(3,keep="first").index)
        hours.update(f.battery_soc_usable_kwh.nsmallest(3,keep="first").index)
    if not hours.issubset(set(next(iter(new.values())).index)):
        raise ValueError("Unknown sample timestamp")
    return sorted(hours)

def reconstruct(prepared,report):
    """Previous artifact endpoint was unavailable. Recover only the inputs,
    never repeat the already completed 52,560 annual AC case-hours.
    """
    import fixed_hardware as fh
    import study_a_pvbess as st
    v6,annual,x,reg,bench,night,endpoint=prepared
    rec={}
    screen.solve(prepared,rec)
    if rec.get("status")!="COMPLETE_STATIC_NIGHT_SUPPORT_SCREEN":
        raise ValueError("Screen replay incomplete")
    corridors=reserve.validate_corridors(OUT/"MIDDLE_NIGHT_SCREEN.csv",night)
    demand=x["trace"].sum(axis=1)
    solar,_=st.solar_per_unit(ROOT,demand.index)
    frames={}
    for c in mo.CASES:
        h=x["hardware"][c]
        hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
            battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
            transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,
            load_pf=.98,export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        f,model=fh.solve_fixed(ROOT,hw,demand,solar,corridors=corridors,min_physical_soc=.20)
        f.index.name="timestamp_lst"
        sizing.validate_comparison(f,h,demand,solar)
        path=OUT/(c+"_MIDDLE_RESERVE_8760.csv")
        f.to_csv(path,float_format="%.10f")
        got=hashlib.sha256(path.read_bytes()).hexdigest()
        if got!=EXPECTED[c]:raise ValueError("Prior optimized schedule digest mismatch: "+c)
        f=read_frame(path)
        sizing.validate_comparison(f,h,demand,solar)
        if int(x["frames"][c].inverter_ac_kw.ne(f.inverter_ac_kw).sum())!=COUNTS[c]:
            raise ValueError("Changed hour population mismatch")
        for t,(lo,hi) in corridors.items():
            if not lo-1e-6<=float(f.at[t,"inverter_ac_kw"])<=hi+1e-6:raise ValueError("Reserve constraint")
        frames[c]=f
    report.update(verified_prior_schedules=3,verified_corridors=len(corridors),
        original_annual_AC_repeated=False,recovery="EXACT_DETERMINISTIC_RECONSTRUCTION")
    return frames,corridors

def evaluate_sample(prepared,frames,corridors,report):
    import pandapower as pp
    v6,annual,x,reg,bench,night,endpoint=prepared
    hours=select_hours(x["hours"],corridors,x["frames"],frames)
    if len(corridors)!=241 or not set(corridors).issubset(hours) or not set(x["hours"]).issubset(hours):
        raise ValueError("Sample selection coverage")
    pd.DataFrame({"timestamp_lst":hours}).to_csv(OUT/"COMMON_SAMPLE_HOURS.csv",index=False)
    report.update(common_hours=len(hours),planned_new_sample_case_hours=27*len(hours))
    controls=0
    rows=[];summ=[]
    for pf,l in FACTORS:
        terr=x["territories"][l]
        net,meta=mo.build(terr,"middle",reg,l)
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
        for c in mo.CASES:
            for t in x["hours"]:
                q=follow.evaluate(v6,pp,net,meta,terr,x,c,t,pf)
                q["strict_feasible"]=rn.strict_point(q)
                mo.exact_sample_row(annual,q,bench.loc[("middle",c,pf,l,t)].to_dict(),c+" "+str(t))
                controls+=1
            new=dict(x,frames={c:frames[c]})
            local=[]
            for t in hours:
                q=follow.evaluate(v6,pp,net,meta,terr,new,c,t,pf)
                metrics=[q[k] for k in ("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw")]
                if q["status"]!="CONVERGED" or not np.isfinite(metrics).all():
                    raise ValueError("Nonconverged or nonfinite sample")
                if bool(q["night_reactive_disabled"])!=bool(frames[c].at[t,"pv_dc_available_kw"]<=1e-9):
                    raise ValueError("Night policy")
                if q["night_reactive_disabled"] and abs(float(q["q_selected_kvar"]))>1e-9:
                    raise ValueError("Night Q")
                q.update(case=c,pf=pf,length_factor=l,strict_feasible=rn.strict_point(q),
                    reserve_energy_sha256=EXPECTED[c],source_energy_sha256=reserve.CASE_HASHES[c],
                    support_corridor=t in corridors,changed_P=bool(x["frames"][c].at[t,"inverter_ac_kw"]!=frames[c].at[t,"inverter_ac_kw"]))
                local.append(q)
            z=pd.DataFrame(local);failed=~z.strict_feasible
            r=dict(case=c,pf=pf,length_factor=l,sampled_hours=len(z),converged=len(z),
                strict_failures=int(failed.sum()),night_failures=int((failed&z.night_reactive_disabled).sum()),
                daylight_failures=int((failed&~z.night_reactive_disabled).sum()),
                low_voltage_hours=int(z.min_v_pu.lt(.95).sum()),high_voltage_hours=int(z.max_v_pu.gt(1.05).sum()),
                optional_under_097_hours=int(z.min_v_pu.lt(.97).sum()),optional_above_103_hours=int(z.max_v_pu.gt(1.03).sum()),
                transformer_overload_hours=int(z.max_trafo_pct.gt(100).sum()),line_overload_hours=int(z.max_line_pct.gt(100).sum()),
                minimum_voltage_pu=float(z.min_v_pu.min()),maximum_voltage_pu=float(z.max_v_pu.max()),
                peak_transformer_pct=float(z.max_trafo_pct.max()),peak_line_pct=float(z.max_line_pct.max()),
                first_failed_timestamps=z.loc[failed,"timestamp_lst"].astype(str).head(20).tolist(),
                reserve_energy_sha256=EXPECTED[c],previous_annual_pass=(pf,l) in reserve.FACTORS)
            if (pf,l) in reserve.FACTORS:
                if r["strict_failures"] or r["minimum_voltage_pu"]<PRIOR_ANNUAL_VMIN[pf]-1e-8 or r["maximum_voltage_pu"]>PRIOR_ANNUAL_VMAX[pf]+1e-8 or r["peak_transformer_pct"]>PRIOR_ANNUAL_TRAFO[pf]+1e-6 or r["peak_line_pct"]>PRIOR_ANNUAL_LINE[pf]+1e-6:
                    raise ValueError("Previously completed annual bound contradicted")
            rows.extend(local);summ.append(r)
            print("SAMPLE_RESULT="+json.dumps(r,allow_nan=False),flush=True)
    if controls!=1809 or len(summ)!=27 or len(rows)!=27*len(hours):
        raise ValueError("Nine-factor coverage mismatch")
    a=pd.DataFrame(rows)
    if a.duplicated(["case","pf","length_factor","timestamp_lst"]).any():raise ValueError("Duplicate sample keys")
    a.to_csv(OUT/"MIDDLE_RESERVE_NINE_FACTOR_HOURLY.csv",index=False)
    pd.DataFrame(summ).to_csv(OUT/"MIDDLE_RESERVE_NINE_FACTOR_SUMMARY.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    labels=[f"{pf:.2f} / {l:.1f}" for pf,l in FACTORS]
    for i,c in enumerate(mo.CASES):
        g=[next(r for r in summ if r["case"]==c and r["pf"]==pf and r["length_factor"]==l) for pf,l in FACTORS]
        xx=np.arange(9)+(i-1)*.25
        ax[0].bar(xx,[r["minimum_voltage_pu"] for r in g],.25,label=f"{i+5} modules")
        ax[1].bar(xx,[r["strict_failures"] for r in g],.25,label=f"{i+5} modules")
    ax[0].axhline(.95,ls="--",color="firebrick")
    ax[0].set_ylim(min(.93,float(a.min_v_pu.min())-.002),1.05)
    ax[0].set_ylabel("Sample minimum voltage (pu)");ax[1].set_ylabel("Sample failed case-hours")
    for z in ax:z.set_xticks(range(9),labels,rotation=35,ha="right");z.set_xlabel("Load PF / service length multiplier");z.legend(fontsize=8)
    fig.suptitle("94022 | exact reserve schedules, nine-factor common risk sample (not annual)")
    for ext in ("png","svg"):fig.savefig(OUT/("middle_reserve_nine_factor."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_NINE_FACTOR_RESERVE_SAMPLE",source_sample_regressions=controls,
        new_sample_case_hours=len(rows),completed_groups=len(summ),passing_groups=sum(r["strict_failures"]==0 for r in summ),
        summary=summ)

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "sample",
        job_id=os.environ.get("CI_JOB_ID"),pipeline_id=os.environ.get("CI_PIPELINE_ID"),
        execution_commit=os.environ.get("CI_COMMIT_SHA"),runner_id=os.environ.get("CI_RUNNER_ID"),
        prior_reserve_job=18394344888,prior_screen_job=18393653618,expected_energy_sha256=EXPECTED,
        factors=[list(z) for z in FACTORS],field_verified=False,annual_replay=False,
        offline_perfect_foresight=True,night_Q_disabled=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":
            raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_sizing_option_annual_gate.py","test_reserve_full_night.py","test_remote_middle_robustness.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        prepared=screen.prepare()
        if prepared[2]["signatures"]!=reserve.CASE_HASHES or len(FACTORS)!=9:
            raise ValueError("Source identity mismatch")
        if preflight:report["status"]="COMPLETE_SIGNED_NINE_FACTOR_RESERVE_PREFLIGHT"
        else:
            frames,corridors=reconstruct(prepared,report)
            evaluate_sample(prepared,frames,corridors,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
        save(OUT/"MIDDLE_ROBUSTNESS_REPORT.json",report)
        print("MIDDLE_ROBUSTNESS_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_NINE_FACTOR_RESERVE_PREFLIGHT","COMPLETE_NINE_FACTOR_RESERVE_SAMPLE") else 1

if __name__=="__main__":raise SystemExit(main())
