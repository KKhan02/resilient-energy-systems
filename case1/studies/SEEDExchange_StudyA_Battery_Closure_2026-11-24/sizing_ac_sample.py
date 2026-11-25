#!/usr/bin/env python3
"""Bounded paired AC screening for seven new sizing candidates. No new LP."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from audit_battery_coverage import signed, read_frame, read_json
import sizing_priority_pilot as sizing

PILOT=Path("StudyA_Battery_Sizing_Pilot_v1")
SYN=Path("case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22")
FACTORS=((.98,1.),(.95,1.6))
Q=.25
ARCHIVES={
 "oversize":("StudyA_Reciprocal12_P2P3_AC_Screen_v1","TARGETED_300_AC_CASEHOURS.csv",25),
 "constraint":("StudyA_Reciprocal12_P1_AC_Pilot_v1","TARGETED_36_AC_CASEHOURS.csv",3),
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def pick_hours(frames,bench):
    """Common union: archived stress hours plus 3 largest per metric per design.
    Include lowest Store and maximum active inverter, demand, grid P and PV.
    Stable first timestamp tie-break. No random sampling or annual claim.
    """
    selected=set(pd.Timestamp(t) for t in bench)
    for f in frames.values():
        for key in ("demand_kw","grid_import_kw","inverter_ac_kw","pv_dc_available_kw"):
            selected.update(f[key].nlargest(3,keep="first").index)
        selected.update(f.battery_soc_usable_kwh.nsmallest(3,keep="first").index)
    return sorted(selected)

def prepare(repo):
    sys.path.insert(0,str(repo/SYN))
    import matched16_94022_ss90_mar_nov_annual_ac as annual
    _,contexts=sizing.preflight(repo,"both")
    import study_a_pvbess as st
    m,v6,mapping,profiles=st.secure_context(repo,repo/st.MANIFEST_REL)
    annual.check_source_stateless(v6)
    receipt=read_json(repo/PILOT/"RUN_MANIFEST.json")
    if receipt["status"]!="COMPLETE_ENERGY_ONLY_SIZING_PILOT" or receipt["completed_new"]!=7 or receipt["errors"]:
        raise ValueError("Incomplete source sizing pilot")
    summary=pd.read_csv(repo/PILOT/"SIZING_SUMMARY.csv").set_index("case")
    if len(summary)!=9 or not summary.index.is_unique:
        raise ValueError("Unexpected sizing summary")
    out={}
    for family,(source,t,ref,ids,demand,solar,original,mode) in contexts.items():
        _,trace=st.source_trace(m,mapping,profiles,"A0",t)
        frames={source:original}
        hardware={source:ref["hardware"]}
        signatures={source:ref["target_energy_sha256"]}
        for label,h in sizing.designs(family):
            name=t+"_"+label
            path=repo/PILOT/name
            info=read_json(path/"energy_manifest.json")
            if (info["status"]!="FULL_8760H_FIXED_HARDWARE_FRONTIER_ENERGY_ONLY" or
                info["case_id"]!=name or info["scenario"]!="A0" or info["transformer"]!=t or
                info["selected_house_ids"]!=ids or info["source_case"]!=source or
                info["source_energy_sha256"]!=signatures[source] or info["hardware"]!=h or
                info["input_manifest_sha256"]!="2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69"):
                raise ValueError("Source sizing identity mismatch "+name)
            signed(path/"energy_hourly_2025.csv",info["energy_csv_sha256"])
            f=read_frame(path/"energy_hourly_2025.csv")
            sizing.validate_comparison(f,h,demand,solar)
            for k,col in (("import_ac_kwh","grid_import_kw"),("curtail_dc_kwh","curtailed_pv_dc_kw"),
                          ("discharge_dc_kwh","battery_discharge_dc_kw")):
                if abs(float(f[col].sum())-float(summary.loc[name,k]))>1e-5:
                    raise ValueError("Source totals mismatch "+name)
            frames[name]=f
            hardware[name]=h
            signatures[name]=info["energy_csv_sha256"]
        folder,filename,count=ARCHIVES[family]
        ap=repo/folder/filename
        ar=read_json(repo/folder/"RUN_MANIFEST.json")
        signed(ap,ar["targeted_ac_csv_sha256"])
        ac=pd.read_csv(ap)
        bench=ac[(ac.case==source)&np.isclose(ac.pf,.98)].copy()
        if len(bench)!=count or not bench.timestamp_lst.is_unique or not bench.status.eq("CONVERGED").all():
            raise ValueError("Archived benchmark count/status")
        if not bench.source_sha256.eq(signatures[source]).all():
            raise ValueError("Archived source signature changed")
        benchmarks={pd.Timestamp(r["timestamp_lst"]):r for r in bench.to_dict("records")}
        for stamp,r in benchmarks.items():
            if abs(float(r["inverter_ac_kw"])-original.at[stamp,"inverter_ac_kw"])>1e-6:
                raise ValueError("Archived source P differs")
        if family=="constraint":
            for stamp in ("2025-03-28 20:00:00","2025-11-27 20:00:00"):
                if str(benchmarks[pd.Timestamp(stamp)]["ac_feasible"]).lower()!="false":
                    raise ValueError("Original voltage failure not reproduced in archive")
        hours=pick_hours(frames,benchmarks)
        territories={}
        for _,length in FACTORS:
            terr=v6.new_territory(repo,"A0",t,ids,length)
            if abs(float(terr.trafo["kva"])-float(ref["hardware"]["transformer_kva_assumed_or_evidenced"]))>1e-9:
                raise ValueError("Transformer assumption changed")
            territories[length]=terr
        out[family]=dict(source=source,transformer=t,ids=ids,trace=trace,
            frames=frames,hardware=hardware,signatures=signatures,benchmarks=benchmarks,
            hours=hours,territories=territories)
    return v6,annual,out

def plan(items):
    groups={}
    for k,x in items.items():
        groups[k]=dict(cases=list(x["frames"]),common_hours=len(x["hours"]),
            timestamps=[str(t) for t in x["hours"]],archived_reference_benchmarks=len(x["benchmarks"]),
            planned_AC_case_hours=len(x["frames"])*len(x["hours"])*len(FACTORS))
    return dict(status="SIGNED_SIZING_AC_SAMPLE_PREFLIGHT_NO_SOLVES",groups=groups,
        planned_AC_case_hours=sum(x["planned_AC_case_hours"] for x in groups.values()),
        factors=[list(x) for x in FACTORS],daylight_Q_ratio=Q,night_Q_off=True,
        annual_AC_verified=False,field_verified=False)

def summarize(rows):
    out=[]
    for (case,pf,length),g in pd.DataFrame(rows).groupby(["case","pf","length_factor"],sort=False):
        good=g[g.status=="CONVERGED"]
        out.append(dict(case=case,pf=pf,length_factor=length,sampled_hours=len(g),
            converged=len(good),nonconverged=len(g)-len(good),
            infeasible=int((~good.ac_feasible.astype(bool)).sum()),
            min_v_pu=float(good.min_v_pu.min()) if len(good) else None,
            max_v_pu=float(good.max_v_pu.max()) if len(good) else None,
            max_trafo_pct=float(good.max_trafo_pct.max()) if len(good) else None,
            max_line_pct=float(good.max_line_pct.max()) if len(good) else None,
            annual_AC_verified=False))
    return out

def run(repo,out,v6,annual,items,doc):
    import pandapower as pp
    from run_epm_validation import build_net
    out.mkdir(parents=False,exist_ok=False)
    manifest=out/"RUN_MANIFEST.json"
    def save():
        manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    doc.update(status="INCOMPLETE_SIZING_AC_SAMPLE",new_AC_case_hours=0)
    save()
    rows=[];checks=0
    try:
        for family,x in items.items():
            for pf,length in FACTORS:
                terr=x["territories"][length]
                for case,f in x["frames"].items():
                    net,meta=build_net(terr,"head")
                    if set(meta["loads"])!=set(x["ids"]):
                        raise ValueError("GIS load keys changed")
                    for t in x["hours"]:
                        e=f.loc[t];h=x["hardware"][case]
                        r=v6.solve_ac_hour(net,meta,terr,t,x["trace"].loc[t],pf,
                              float(e.inverter_ac_kw),float(h["inverter_kva"]),
                              float(e.pv_dc_available_kw),Q,9,"pvbess",pp)
                        if (abs(float(r["gross_demand_kw"])-float(e.demand_kw))>1e-5 or
                            abs(float(r["inverter_ac_kw"])-float(e.inverter_ac_kw))>1e-5):
                            raise ValueError("P/load replay mismatch")
                        if case==x["source"] and (pf,length)==FACTORS[0] and t in x["benchmarks"]:
                            annual.exact_ac_regression(r,x["benchmarks"][t],case+" "+str(t));checks+=1
                        rows.append(dict(case=case,family=family,pf=pf,length_factor=length,
                            source_energy_sha256=x["signatures"][case],source_grid_import_kw=float(e.grid_import_kw),**r))
                    print("AC",case,pf,length,len(rows),"/",doc["planned_AC_case_hours"],flush=True)
        if len(rows)!=doc["planned_AC_case_hours"] or checks!=28:
            raise ValueError("Incomplete sample or archived benchmark regression")
        csv=out/"SAMPLED_AC_CASE_HOURS.csv"
        pd.DataFrame(rows).to_csv(csv,index=False)
        sm=out/"SAMPLED_AC_SUMMARY.csv"
        pd.DataFrame(summarize(rows)).to_csv(sm,index=False)
        doc.update(status="COMPLETE_SIZING_AC_SAMPLE_NOT_ANNUAL",
            new_AC_case_hours=len(rows),archived_regressions_passed=checks,
            outputs_sha256={csv.name:sha(csv),sm.name:sha(sm)})
        save();return doc
    except Exception as exc:
        doc.update(new_AC_case_hours=len(rows),error=repr(exc))
        save();raise

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    repo=a.repo_root.resolve()
    v6,annual,items=prepare(repo);doc=plan(items)
    if not a.preflight_only:
        if a.out is None or a.out.exists():
            ap.error("Choose fresh output")
        doc=run(repo,a.out,v6,annual,items,doc)
    print(json.dumps(doc,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
