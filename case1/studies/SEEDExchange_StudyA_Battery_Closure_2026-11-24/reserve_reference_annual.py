#!/usr/bin/env python3
"""Replay signed 94022 reference reserve schedules for every hour; no new LP."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
import sizing_ac_followup as follow
import sizing_priority_pilot as sizing
from audit_battery_coverage import signed, read_frame, read_json

SOURCE=Path("StudyA_94022_Sizing_Reserve_v1")
CASES=("A1_94022_min_cost_to_A0","94022_B6","94022_B7")
ENERGY_HASHES={
    CASES[0]:"fc7ce6ca7dbe4152668a2214cc6770a217e2667e19ec0c4c6f919493836a387b",
    CASES[1]:"33ece75305e965273e3390b059b5e3d5c2f3bcf23638dec33fbacfcc88e5953a",
    CASES[2]:"cdc4471c2e69d9bdcd2144f588bc0551f9317bfb3ca8491968c510e44a2a4163",
}
SAMPLE_HASH="56be1c9f37f9de1d384982ffe83f157fb9b416b66688fa9a01bc893dfc718097"
SUMMARY_HASH="2b0b301b2ace0916fd90632837a6c27b9d429136ce6e778015f60d8c2cfaaa2d"
RECEIPT_HASHES={
    CASES[0]:"e8d84757b125dc6e7e7ed2427147c238d8c0f28276d5b4c3c13407cc6c5497a0",
    CASES[1]:"17d81ed895e0974c9c96bbb613e598945a13ac64cc34263b9d2c043cafd01ca2",
    CASES[2]:"6abc96f2c63820b664d1d4705980edd75bb112c2cab62ce4b0f38312f2f5bb66",
}

def reference_benchmarks(a,case,source_sha,energy_sha,frame,hours):
    q=a[(a.case==case)&np.isclose(a.pf,.98)&np.isclose(a.length_factor,1.)]
    ts=pd.to_datetime(q.timestamp_lst)
    if (len(q)!=17 or not ts.is_unique or set(ts)!=set(hours) or
        not q.status.eq("CONVERGED").all() or not q.ac_feasible.eq(True).all() or
        not q.source_sha256.eq(source_sha).all() or not q.new_energy_sha256.eq(energy_sha).all()):
        raise ValueError("Reference sample identity/coverage changed: "+case)
    for t,r in zip(ts,q.to_dict("records")):
        if (abs(float(r["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-6 or
            abs(float(r["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5):
            raise ValueError("Reference P/load mismatch: "+case)
    return dict(zip(ts,q.to_dict("records")))

def prepare(repo):
    v6,annual,items,_,events=follow.prepare(repo)
    x=items["constraint"];demand=x["trace"].sum(axis=1)
    import study_a_pvbess as st
    solar,_=st.solar_per_unit(repo,demand.index)
    root=repo/SOURCE;m=read_json(root/"RUN_MANIFEST.json")
    if (m["status"]!="COMPLETE_94022_REFERENCE_RESERVE_PILOT_NOT_ANNUAL_AC" or
        m["new_LPs_completed"]!=3 or m["new_reserve_AC_case_hours"]!=102 or
        m["errors"] or m["annual_AC_verified"] or not m["offline_perfect_foresight"]):
        raise ValueError("Reserve manifest changed")
    expected={"RESERVE_SAMPLED_AC.csv":SAMPLE_HASH,"RESERVE_ENERGY_SUMMARY.csv":SUMMARY_HASH}
    for case in CASES:
        expected[case+"_RESERVE_8760.csv"]=ENERGY_HASHES[case]
        expected[case+"_RESERVE_RECEIPT.json"]=RECEIPT_HASHES[case]
    for name,h in expected.items():
        if m["output_sha256"][name]!=h:
            raise ValueError("Reserve output identity changed: "+name)
        signed(root/name,h)
    a=pd.read_csv(root/"RESERVE_SAMPLED_AC.csv")
    if len(a)!=102 or a.duplicated(["case","pf","length_factor","timestamp_lst"]).any():
        raise ValueError("Reserve sample coverage changed")
    sm=pd.read_csv(root/"RESERVE_ENERGY_SUMMARY.csv").set_index("case")
    if set(sm.index)!=set(CASES) or not sm.index.is_unique:
        raise ValueError("Reserve summary cases changed")
    frames={};benches={}
    for case in CASES:
        f=read_frame(root/(case+"_RESERVE_8760.csv"))
        receipt=read_json(root/(case+"_RESERVE_RECEIPT.json"))
        if (receipt["hardware"]!=x["hardware"][case] or receipt["annual_AC_verified"] or
            not receipt["offline_perfect_foresight"] or
            receipt["metrics"]["source_energy_sha256"]!=x["signatures"][case] or
            receipt["metrics"]["new_energy_sha256"]!=ENERGY_HASHES[case]):
            raise ValueError("Reserve case identity changed: "+case)
        sizing.validate_comparison(f,x["hardware"][case],demand,solar)
        old=x["frames"][case]
        for col in ("demand_kw","pv_dc_available_kw"):
            if not np.allclose(f[col],old[col],atol=1e-6,rtol=0):
                raise ValueError("Reserve/source inputs differ: "+case)
        for col,metric in (("grid_import_kw","import_ac_kwh"),("curtailed_pv_dc_kw","curtail_dc_kwh")):
            if abs(float(f[col].sum())-float(sm.loc[case,metric]))>1e-5:
                raise ValueError("Reserve energy totals changed: "+case)
        if set(pd.to_datetime(list(receipt["corridors"])))!=set(events[(.98,1.)]):
            raise ValueError("Reserve event identity changed")
        for stamp,(lo,hi) in receipt["corridors"].items():
            if not lo-1e-6<=float(f.at[pd.Timestamp(stamp),"inverter_ac_kw"])<=hi+1e-6:
                raise ValueError("Reserve corridor violated")
        benches[case]=reference_benchmarks(a,case,x["signatures"][case],ENERGY_HASHES[case],f,x["hours"])
        frames[case]=f
    return v6,annual,x,frames,benches,sm

def run(out,prepared,cases,doc):
    import pandapower as pp
    from run_epm_validation import build_net
    v6,annual,x,frames,benches,sm=prepared
    results=[]
    for case in cases:
        f=frames[case];terr=x["territories"][1.]
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):
            raise ValueError("GIS load keys changed")
        new=dict(x,frames={case:f})
        rows=[];checks=0
        for i,t in enumerate(f.index):
            r=follow.evaluate(v6,pp,net,meta,terr,new,case,t,.98)
            if t in benches[case]:
                annual.exact_ac_regression(r,benches[case][t],case+" "+str(t));checks+=1
            rows.append(dict(case=case,source_energy_sha256=x["signatures"][case],
                reserve_energy_sha256=ENERGY_HASHES[case],pf=.98,length_factor=1.,
                source_grid_import_kw=float(f.at[t,"grid_import_kw"]),**r))
            if (i+1)%1000==0:
                print(case,i+1,"/8760",flush=True)
        if checks!=17:
            raise ValueError("Reserve sample regressions incomplete")
        result=annual.annual_summary(rows)
        path=out/(case+"_ANNUAL_AC.csv")
        annual.save_csv(path,rows)
        cost=float(sm.loc[case,"annual_total_usd"])
        loss=result["annual_ac_network_losses_kwh"]
        result.update(case=case,pf=.98,length_factor=1.,archive_regressions=checks,
            reserve_energy_sha256=ENERGY_HASHES[case],annual_energy_model_cost_usd=cost,
            annual_import_kwh=float(f.grid_import_kw.sum()),annual_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),
            all_losses_purchased_cost_sensitivity_usd=cost+.29*loss if loss is not None else None,
            hourly_csv_sha256=follow.sample.sha(path))
        results.append(result);doc["completed_cases"]=results
        follow.jsonsave(out/"RUN_MANIFEST.json",doc)
    pd.DataFrame(results).to_csv(out/"ANNUAL_AC_SUMMARY.csv",index=False)
    doc.update(status="COMPLETE_94022_RESERVE_REFERENCE_ANNUAL_AC",
        new_AC_case_hours=8760*len(results),regressions_passed=17*len(results),
        annual_AC_verified_by_case={r["case"]:r["all_2025_model_main_band_pass"] for r in results},
        output_sha256={p.name:follow.sample.sha(p) for p in out.iterdir() if p.is_file() and p.name!="RUN_MANIFEST.json"})

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--cases",nargs="+",choices=CASES)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--out",type=Path)
    a=ap.parse_args();repo=a.repo_root.resolve();cases=a.cases or list(CASES)
    if len(set(cases))!=len(cases):ap.error("Duplicate case")
    if not a.preflight_only and (a.out is None or a.out.exists()):ap.error("Choose fresh output")
    prepared=prepare(repo)
    doc=dict(status="SIGNED_RESERVE_ANNUAL_PREFLIGHT_NO_SOLVES",cases=cases,pf=.98,length_factor=1.,
        planned_AC_case_hours=8760*len(cases),planned_regressions=17*len(cases),
        source_reserve_hashes={c:ENERGY_HASHES[c] for c in cases},
        offline_perfect_foresight=True,field_verified=False,no_new_LP=True)
    print(json.dumps(doc,indent=2),flush=True)
    if a.preflight_only:return
    out=a.out;out.mkdir(parents=False,exist_ok=False)
    doc["status"]="INCOMPLETE_94022_RESERVE_REFERENCE_ANNUAL_AC"
    follow.jsonsave(out/"RUN_MANIFEST.json",doc)
    try:run(out,prepared,cases,doc)
    except Exception as e:
        doc["error"]=repr(e);follow.jsonsave(out/"RUN_MANIFEST.json",doc);raise
    follow.jsonsave(out/"RUN_MANIFEST.json",doc)
    print(json.dumps({k:v for k,v in doc.items() if k!="completed_cases"},indent=2))

if __name__=="__main__":
    main()
