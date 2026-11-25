#!/usr/bin/env python3
"""Source-matched sizing follow-up: 113699 annual AC or 94022 reserve pilot."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
import sizing_ac_sample as sample
import sizing_priority_pilot as sizing
from audit_battery_coverage import signed, read_json

ARCHIVE=Path("StudyA_Battery_Sizing_AC_Sample_v1")
NEW_113=("113699_P20_B4","113699_B4","113699_P18","113699_P20","113699_P22")
FACTORS=sample.FACTORS
EXPECTED_HASHES={
"SAMPLED_AC_CASE_HOURS.csv":"f924fc5ce5adf40c154838cab0ad2a5908b3504b2cd8247af8a1230ce16140bf",
"SAMPLED_AC_SUMMARY.csv":"2bd159cfb402d60f37c6116dca2a192036f14169fa9abcedee8c6724d7a22142"}
TOL=1e-6

def prepare(repo):
    v6,annual,items=sample.prepare(repo)
    m=read_json(repo/ARCHIVE/"RUN_MANIFEST.json")
    if (m["status"]!="COMPLETE_SIZING_AC_SAMPLE_NOT_ANNUAL" or
        m["new_AC_case_hours"]!=642 or m["archived_regressions_passed"]!=28 or
        m["outputs_sha256"]!=EXPECTED_HASHES):
        raise ValueError("Sample receipt changed")
    for name,h in EXPECTED_HASHES.items():
        signed(repo/ARCHIVE/name,h)
    a=pd.read_csv(repo/ARCHIVE/"SAMPLED_AC_CASE_HOURS.csv")
    if len(a)!=642 or a.duplicated(["case","pf","length_factor","timestamp_lst"]).any() or not a.status.eq("CONVERGED").all():
        raise ValueError("Sample coverage changed")
    for family,x in items.items():
        for case,f in x["frames"].items():
            for pf,length in FACTORS:
                q=a[(a.case==case)&np.isclose(a.pf,pf)&np.isclose(a.length_factor,length)]
                if len(q)!=len(x["hours"]) or set(pd.to_datetime(q.timestamp_lst))!=set(x["hours"]) or not q.source_energy_sha256.eq(x["signatures"][case]).all():
                    raise ValueError("Archived source sample changed")
                for r in q.to_dict("records"):
                    t=pd.Timestamp(r["timestamp_lst"]);e=f.loc[t]
                    if abs(r["inverter_ac_kw"]-e.inverter_ac_kw)>TOL or abs(r["gross_demand_kw"]-e.demand_kw)>1e-5 or abs(r["source_grid_import_kw"]-e.grid_import_kw)>TOL:
                        raise ValueError("Archived P/load differs from source")
    bad=a[~a.ac_feasible]
    if len(bad)!=37 or set(bad.family)!={"constraint"} or not bad.night_reactive_disabled.all():
        raise ValueError("Original nighttime voltage failure population changed")
    events={}
    for pf,length in FACTORS:
        q=bad[np.isclose(bad.pf,pf)&np.isclose(bad.length_factor,length)]
        events[(pf,length)]=sorted(set(pd.to_datetime(q.timestamp_lst)))
    if [len(events[k]) for k in FACTORS]!=[5,8]:
        raise ValueError("Expected five reference and eight stress events")
    return v6,annual,items,a,events

def evaluate(v6,pp,net,meta,terr,x,case,t,pf,p=None):
    f=x["frames"][case];h=x["hardware"][case];e=f.loc[t]
    p=float(e.inverter_ac_kw if p is None else p)
    r=v6.solve_ac_hour(net,meta,terr,t,x["trace"].loc[t],pf,p,float(h["inverter_kva"]),
             float(e.pv_dc_available_kw),sample.Q,9,"pvbess",pp)
    if abs(float(r["inverter_ac_kw"])-p)>1e-5 or abs(float(r["gross_demand_kw"])-float(e.demand_kw))>1e-5:
        raise ValueError("AC input mismatch")
    return r

def power_ceiling(demand,h):
    return min(float(demand),float(h["inverter_kva"]),.95*float(h["battery_power_dc_kw"]))

def choose_grid_interval(points):
    """Conservative tested feasible contiguous segment ending at highest P.
    No inference of global feasibility from a finite grid.
    """
    if not points or not points[-1][1]:
        return None
    i=len(points)-1
    while i>0 and points[i-1][1]:
        i-=1
    return points[i][0],points[-1][0],(None if i==0 else points[i-1][0])

def jsonsave(path,obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def annual_run(repo,out,v6,annual,items,a,cases,doc):
    import pandapower as pp
    from run_epm_validation import build_net
    x=items["oversize"];terr=x["territories"][1.]
    summary=pd.read_csv(repo/sample.PILOT/"SIZING_SUMMARY.csv").set_index("case")
    results=[]
    for case in cases:
        f=x["frames"][case]
        bench=a[(a.case==case)&np.isclose(a.pf,.98)&np.isclose(a.length_factor,1.)]
        benchmarks={pd.Timestamp(r["timestamp_lst"]):r for r in bench.to_dict("records")}
        if len(benchmarks)!=45 or not bench.ac_feasible.all():
            raise ValueError("Case lacks complete passing sample")
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):
            raise ValueError("GIS load keys changed")
        rows=[];checks=0
        for i,t in enumerate(f.index):
            r=evaluate(v6,pp,net,meta,terr,x,case,t,.98)
            if t in benchmarks:
                annual.exact_ac_regression(r,benchmarks[t],case+" "+str(t));checks+=1
            rows.append(dict(case=case,source_energy_sha256=x["signatures"][case],
                source_grid_import_kw=float(f.at[t,"grid_import_kw"]),**r))
            if (i+1)%1000==0:
                print(case,i+1,"/8760",flush=True)
        if checks!=45:
            raise ValueError("Annual sample regressions incomplete")
        result=annual.annual_summary(rows)
        path=out/(case+"_ANNUAL_AC.csv")
        annual.save_csv(path,rows)
        cost=float(summary.loc[case,"annual_total_usd"])
        losses=result["annual_ac_network_losses_kwh"]
        result.update(case=case,source_energy_sha256=x["signatures"][case],archive_regressions=checks,
            annual_energy_model_cost_usd=cost,annual_import_kwh=float(f.grid_import_kw.sum()),
            annual_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),
            all_losses_purchased_cost_sensitivity_usd=cost+.29*losses if losses is not None else None,
            hourly_csv_sha256=sample.sha(path))
        results.append(result)
        doc["completed_cases"]=results
        jsonsave(out/"RUN_MANIFEST.json",doc)
    pd.DataFrame(results).to_csv(out/"ANNUAL_AC_SUMMARY.csv",index=False)
    doc.update(status="COMPLETE_113699_SIZING_ANNUAL_AC_RESULTS",new_AC_case_hours=8760*len(results),
        regressions_passed=45*len(results),field_verified=False,
        annual_AC_verified_by_case={r["case"]:r["all_2025_model_main_band_pass"] for r in results})

def reserve_run(repo,out,v6,annual,items,a,events,doc):
    import pandapower as pp
    from run_epm_validation import build_net
    import fixed_hardware as fh
    import study_a_pvbess as st
    x=items["constraint"];source=x["source"];h=x["hardware"][source]
    demand=x["trace"].sum(axis=1)
    solar,_=st.solar_per_unit(repo,demand.index)
    probes=[];limits=[];corridors={}
    for pf,length in FACTORS:
        terr=x["territories"][length];net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):
            raise ValueError("GIS load keys changed")
        for t in events[(pf,length)]:
            cap=power_ceiling(demand.loc[t],h)
            if cap<=0 or any(float(f.at[t,"pv_dc_available_kw"])>1e-9 for f in x["frames"].values()):
                raise ValueError("Expected positive load and nighttime-only event")
            def measure(p):
                r=evaluate(v6,pp,net,meta,terr,x,source,t,pf,p)
                probes.append(dict(pf=pf,length_factor=length,requested_p_kw=float(p),**r))
                return r["status"]=="CONVERGED" and bool(r["ac_feasible"])
            grid=[(float(p),measure(float(p))) for p in np.linspace(0,cap,21)]
            seg=choose_grid_interval(grid)
            if seg is None:
                limits.append(dict(timestamp_lst=str(t),pf=pf,length_factor=length,ceiling_kw=cap,
                     status="NO_TESTED_FEASIBLE_SEGMENT_TO_ZERO_EXPORT_CEILING",minimum_tested_feasible_kw=None))
                continue
            hi,upper,lo=seg
            if lo is not None:
                for _ in range(10):
                    mid=(hi+lo)/2
                    if measure(mid):
                        hi=mid
                    else:
                        lo=mid
            # use tested feasible lower endpoint plus small numerical search margin;
            # independently evaluate actual LP output, not interpolate a guarantee.
            chosen=min(upper,hi+.01)
            if not measure(chosen):
                chosen=hi
                if not measure(chosen):
                    raise ValueError("Feasible endpoint not repeatable")
            limits.append(dict(timestamp_lst=str(t),pf=pf,length_factor=length,ceiling_kw=cap,
                status="TESTED_FEASIBLE_ENDPOINT",minimum_tested_feasible_kw=hi,chosen_lower_kw=chosen,
                tested_upper_kw=upper))
            if (pf,length)==FACTORS[0]:
                corridors[t]=(chosen,upper)
    pd.DataFrame(probes).to_csv(out/"AC_POWER_PROBES.csv",index=False)
    pd.DataFrame(limits).to_csv(out/"EVENT_POWER_LIMITS.csv",index=False)
    doc.update(power_probe_count=len(probes),reference_corridor_count=len(corridors),
        stress_events_without_tested_segment=sum(r["status"]!="TESTED_FEASIBLE_ENDPOINT" and r["pf"]==.95 for r in limits))
    jsonsave(out/"RUN_MANIFEST.json",doc)
    if len(corridors)!=len(events[FACTORS[0]]):
        doc.update(status="REFERENCE_POWER_ENVELOPE_INCOMPLETE_NO_LP",new_LPs=0)
        return
    rows=[];metrics=[];errors=[]
    sm0=pd.read_csv(repo/sample.PILOT/"SIZING_SUMMARY.csv").set_index("case")
    for case,old in list(x["frames"].items()):
        hw=x["hardware"][case]
        try:
            equipment=fh.Hardware(panels=hw["pv_panels"],battery_modules=hw["battery_modules"],
                 battery_power_dc_kw=hw["battery_power_dc_kw"],inverter_kva=hw["inverter_kva"],
                 transformer_kva=hw["transformer_kva_assumed_or_evidenced"],loading_pu=1.,
                 load_pf=.98,export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
            f,sm=fh.solve_fixed(repo,equipment,demand,solar,corridors=corridors,min_physical_soc=.20)
            f.index.name="timestamp_lst"
            sizing.validate_comparison(f,hw,demand,solar)
            for t,(lo,hi) in corridors.items():
                if not lo-1e-5<=float(f.at[t,"inverter_ac_kw"])<=hi+1e-5:
                    raise ValueError("LP P corridor violated")
            path=out/(case+"_RESERVE_8760.csv")
            f.to_csv(path,float_format="%.10f")
            # use actual schedule, unchanged hardware, not source schedule
            new=dict(x,frames={case:f})
            newhash=sample.sha(path)
            for pf,length in FACTORS:
                terr=x["territories"][length];net,meta=build_net(terr,"head")
                for t in x["hours"]:
                    r=evaluate(v6,pp,net,meta,terr,new,case,t,pf)
                    rows.append(dict(case=case,pf=pf,length_factor=length,source_sha256=x["signatures"][case],
                        new_energy_sha256=newhash,**r))
            metric=sizing.summary(case,"constraint","OFFLINE_REFERENCE_P_RESERVE_LP",hw,f,sm)
            metric.update(source_energy_sha256=x["signatures"][case],new_energy_sha256=newhash,
                delta_import_ac_kwh=float(f.grid_import_kw.sum()-old.grid_import_kw.sum()),
                delta_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()-old.curtailed_pv_dc_kw.sum()),
                delta_annual_model_usd=float(sm["annual_total_usd"])-float(sm0.loc[case,"annual_total_usd"]),
                changed_inverter_hours=int(((f.inverter_ac_kw-old.inverter_ac_kw).abs()>1e-6).sum()))
            metrics.append(metric)
            jsonsave(out/(case+"_RESERVE_RECEIPT.json"),dict(metrics=metric,hardware=hw,model_summary=sm,
                corridors={str(t):list(b) for t,b in corridors.items()},field_verified=False,
                offline_perfect_foresight=True,annual_AC_verified=False))
            print(case,"reference-reserve LP and paired AC completed",flush=True)
        except Exception as e:
            errors.append(dict(case=case,error=repr(e)))
            print("UNRESOLVED",case,repr(e),flush=True)
    pd.DataFrame(rows).to_csv(out/"RESERVE_SAMPLED_AC.csv",index=False)
    pd.DataFrame(metrics).to_csv(out/"RESERVE_ENERGY_SUMMARY.csv",index=False)
    if rows:
        pd.DataFrame(sample.summarize(rows)).to_csv(out/"RESERVE_SAMPLED_AC_SUMMARY.csv",index=False)
    doc.update(status="COMPLETE_94022_REFERENCE_RESERVE_PILOT_NOT_ANNUAL_AC" if not errors else "PARTIAL_94022_RESERVE_PILOT",
        new_LPs_completed=len(metrics),new_reserve_AC_case_hours=len(rows),errors=errors,
        annual_AC_verified=False,offline_perfect_foresight=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--scope",choices=["annual113699","reserve94022"],required=True)
    ap.add_argument("--cases",nargs="+",choices=NEW_113)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--out",type=Path)
    args=ap.parse_args();repo=args.repo_root.resolve()
    cases=args.cases or list(NEW_113)
    if len(set(cases))!=len(cases) or (args.scope=="reserve94022" and args.cases):
        ap.error("Invalid case selection")
    v6,annual,items,a,events=prepare(repo)
    doc=dict(status="SIGNED_SIZING_FOLLOWUP_PREFLIGHT_NO_SOLVES",scope=args.scope,
        source_sample_hashes=EXPECTED_HASHES,field_verified=False)
    if args.scope=="annual113699":
        doc.update(cases=cases,planned_AC_case_hours=8760*len(cases),planned_regressions=45*len(cases))
    else:
        doc.update(reference_events=[str(t) for t in events[FACTORS[0]]],
            stress_events=[str(t) for t in events[FACTORS[1]]],planned_LPs_max=3,
            note="Reference-only corridors; stress diagnostic separate, not full nine-factor")
    print(json.dumps(doc,indent=2),flush=True)
    if args.preflight_only:return
    if args.out is None or args.out.exists():
        ap.error("Choose fresh output folder")
    out=args.out;out.mkdir(parents=False,exist_ok=False)
    doc["status"]="INCOMPLETE_SIZING_FOLLOWUP";jsonsave(out/"RUN_MANIFEST.json",doc)
    try:
        if args.scope=="annual113699":
            annual_run(repo,out,v6,annual,items,a,cases,doc)
        else:
            reserve_run(repo,out,v6,annual,items,a,events,doc)
        doc["output_sha256"]={p.name:sample.sha(p) for p in out.iterdir() if p.is_file() and p.name!="RUN_MANIFEST.json"}
        jsonsave(out/"RUN_MANIFEST.json",doc)
    except Exception as e:
        doc["error"]=repr(e);jsonsave(out/"RUN_MANIFEST.json",doc);raise
    print(json.dumps({k:v for k,v in doc.items() if k!="completed_cases"},indent=2,allow_nan=False))
    if doc["status"].startswith("PARTIAL"):raise SystemExit(2)

if __name__=="__main__":
    main()
