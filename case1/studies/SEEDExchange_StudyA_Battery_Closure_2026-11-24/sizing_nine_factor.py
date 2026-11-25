#!/usr/bin/env python3
"""Matched nine-factor AC screen of eight sizing cases, optional annual factor replay."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
import reserve_reference_annual as prev
import sizing_ac_followup as follow
import sizing_priority_pilot as sizing
from audit_battery_coverage import signed,read_frame,read_json

FULL=Path("StudyA_94022_FullNight_Reserve_v1")
SMALL=Path("StudyA_113699_Sizing_AnnualAC_v1")
SMALL_CASES=follow.NEW_113
CASES=SMALL_CASES+prev.CASES
FACTORS=tuple((pf,l) for pf in (.95,.98,1.) for l in (1.,1.3,1.6))
REF=(.98,1.)
SMALL_HASHES=dict(zip(SMALL_CASES,(
"53f19d206b4a4448b1c2a7ddb3ce4e738e37ff58debd87f4f6719d06257e998b",
"c7bb44746870ca545d4b2aa323138ca894186c338e8d88a5091c992e036a48ef",
"35f12d3def005f6df65177bd8d109c127f367143e39d68cad2b073037a354285",
"b00d90ae9eee3b91aa333fe7048b4226f208c3472f4c6ee97d08a3475935be26",
"275669d906117a12c40e9d4c80f9ee78450b0bd6199561b4f0b7ff2ee5f42992")))
FULL_AC_HASH=dict(zip(prev.CASES,(
"659f0627fa9fa7e9b9b4e8e77f7c6efccc538119eb6f93c61f9d8fb28c680f22",
"26807d7bae832558647249c498900834ae90bab7a70a472a0c1fc1c3cf8e01f0",
"92195aa8c5414a7881d71c0518a2562c7356a7f1848c5f7d944b6632b6193073")))
FULL_ENERGY_HASH=dict(zip(prev.CASES,(
"e7a4178ac1f9df771a19ab631222b1396279c2669b5b5334e9c4f792a83eac00",
"8bc331e1f7100caf7e6ec51521f745b77218beb0a2aa0fe6487b7cff53b00fb7",
"fb87f90e55aa523790353e4d172c577aea91e0e1a816ccebef9498ca1b93b37e")))
CORRIDOR_HASH="f73514b790646741e44b28b31fa119e08428a4ef9f198854dc08208ecf5e603a"

def common_hours(base,records,frames):
    hours=set(base)
    for c,a in records.items():
        f=frames[c]
        hours.update(a.min_v_pu.nsmallest(10,keep="first").index)
        for key in ("max_trafo_pct","max_line_pct","max_v_pu"):
            hours.update(a[key].nlargest(10,keep="first").index)
        for key in ("demand_kw","grid_import_kw","inverter_ac_kw","pv_dc_available_kw"):
            hours.update(f[key].nlargest(3,keep="first").index)
        hours.update(f.battery_soc_usable_kwh.nsmallest(3,keep="first").index)
    return sorted(hours)

def check_receipt_hash(path, expected, recorded):
    """Fail closed on malformed pins or disagreement with a source receipt."""
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError(f"Malformed pinned SHA256: {path}: {expected}")
    if recorded != expected:
        raise ValueError(f"Source receipt SHA256 mismatch: {path}: pinned={expected}, receipt={recorded}")


def source_ac(path,signature,case,frame,energy_sha,field):
    signed(path,signature)
    a=pd.read_csv(path,parse_dates=["timestamp_lst"],keep_default_na=False).set_index("timestamp_lst")
    if (not a.index.equals(frame.index) or not a.case.eq(case).all() or
        not a[field].eq(energy_sha).all() or not a.load_pf.eq(.98).all() or
        not a.status.eq("CONVERGED").all() or not a.ac_feasible.eq(True).all() or
        not np.isfinite(a[["min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw"]].to_numpy(float)).all()):
        raise ValueError("Annual reference source identity/coverage changed "+case)
    if "length_factor" in a and not a.length_factor.eq(1.).all():
        raise ValueError("Reference length changed")
    for k,z in (("gross_demand_kw","demand_kw"),("inverter_ac_kw","inverter_ac_kw"),
                ("source_grid_import_kw","grid_import_kw")):
        if not np.allclose(a[k],frame[z],atol=1e-9,rtol=0):
            raise ValueError("Reference AC input mismatch "+case)
    if not np.array_equal(a.night_reactive_disabled.to_numpy(),(frame.pv_dc_available_kw<=1e-9).to_numpy()):
        raise ValueError("Reference night policy changed")
    return a

def prepare(repo):
    v6,annual,items,old_sample,_=follow.prepare(repo)
    annual.check_source_stateless(v6)
    sm=read_json(repo/SMALL/"RUN_MANIFEST.json")
    fm=read_json(repo/FULL/"RUN_MANIFEST.json")
    if (sm["status"]!="COMPLETE_113699_SIZING_ANNUAL_AC_RESULTS" or sm["new_AC_case_hours"]!=43800 or
        fm["status"]!="COMPLETE_NIGHT_REFERENCE_REPLAY" or not fm["all_selected_cases_pass"] or
        fm["new_changed_P_AC_hours"]!=81 or fm["reused_AC_hours"]!=26199):
        raise ValueError("Annual sizing receipts changed")
    signed(repo/FULL/"NIGHT_P_CORRIDORS.csv",CORRIDOR_HASH)
    corridors=pd.read_csv(repo/FULL/"NIGHT_P_CORRIDORS.csv",parse_dates=["timestamp_lst"])
    if len(corridors)!=38 or not corridors.timestamp_lst.is_unique:raise ValueError("Reserve corridors changed")
    import study_a_pvbess as st
    groups={}
    for family,cases,root,hashes in (("oversize",SMALL_CASES,SMALL,SMALL_HASHES),
                                    ("constraint",prev.CASES,FULL,FULL_AC_HASH)):
        x=items[family];frames={};records={};signatures={};base=set(x["hours"])
        for c in cases:
            f=x["frames"][c];h=x["signatures"][c];field="source_energy_sha256"
            if family=="constraint":
                h=FULL_ENERGY_HASH[c];path=repo/FULL/(c+"_CORRECTED_8760.csv")
                check_receipt_hash(path,h,fm["output_sha256"][path.name])
                signed(path,h);f=read_frame(path);field="corrected_energy_sha256"
                demand=x["trace"].sum(axis=1);solar,_=st.solar_per_unit(repo,demand.index)
                sizing.validate_comparison(f,x["hardware"][c],demand,solar)
                for row in corridors.itertuples():
                    if not row.lower_kw-1e-6<=float(f.at[row.timestamp_lst,"inverter_ac_kw"])<=row.upper_kw+1e-6:
                        raise ValueError("Reserve corridor violated")
                base.update(corridors.timestamp_lst)
                base.update(pd.to_datetime(["2025-09-24 19:00","2025-09-24 20:00"]))
            path=repo/root/(c+"_ANNUAL_AC.csv")
            check_receipt_hash(path,hashes[c],(sm if family=="oversize" else fm)["output_sha256"][path.name])
            records[c]=source_ac(path,hashes[c],c,f,h,field)
            frames[c]=f;signatures[c]=h
        hours=common_hours(base,records,frames)
        territories={l:v6.new_territory(repo,"A0",x["transformer"],x["ids"],l) for l in (1.,1.3,1.6)}
        for terr in territories.values():
            if abs(float(terr.trafo["kva"])-float(x["hardware"][cases[0]]["transformer_kva_assumed_or_evidenced"]))>1e-9:
                raise ValueError("Transformer assumption changed")
        groups[family]=dict(x,frames=frames,signatures=signatures,records=records,
                           territories=territories,hours=hours,cases=cases)
    return v6,annual,groups

def selection(groups,cases,scope,factors):
    return [(family,c,pf,l,len(x["hours"]) if scope=="sample" else 8760)
            for family,x in groups.items() for c in x["cases"] if c in cases for pf,l in factors]

def run(out,prepared,plan,scope,doc):
    import pandapower as pp
    from run_epm_validation import build_net
    v6,annual,groups=prepared
    allrows=[];summaries=[];checks=0;new=0
    # Reference regression of 3 electrical extrema per case even in nonreference runs.
    for family,x in groups.items():
        for c in sorted({z[1] for z in plan if z[0]==family}):
            a=x["records"][c];terr=x["territories"][1.]
            net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("GIS loads changed")
            stamps={a.min_v_pu.idxmin(),a.max_trafo_pct.idxmax(),a.max_line_pct.idxmax()}
            for t in stamps:
                r=follow.evaluate(v6,pp,net,meta,terr,x,c,t,.98)
                annual.exact_ac_regression(r,a.loc[t].to_dict(),c+" reference "+str(t));checks+=1
    for family,c,pf,l,n in plan:
        x=groups[family];f=x["frames"][c];a=x["records"][c];terr=x["territories"][l]
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("GIS loads changed")
        rows=[];hours=x["hours"] if scope=="sample" else f.index
        for t in hours:
            if (pf,l)==REF:
                r=a.loc[t].to_dict();r["timestamp_lst"]=str(t);origin="SIGNED_REFERENCE_AC"
            else:
                r=follow.evaluate(v6,pp,net,meta,terr,x,c,t,pf);origin="NEW_FACTOR_AC";new+=1
            r.update(case=c,family=family,pf=pf,length_factor=l,energy_sha256=x["signatures"][c],
                     source_grid_import_kw=float(f.at[t,"grid_import_kw"]),AC_origin=origin)
            rows.append(r)
        if len(rows)!=n:raise ValueError("Incomplete factor result")
        if scope=="annual":
            s=annual.annual_summary(rows);s.update(case=c,pf=pf,length_factor=l)
            annual.save_csv(out/(c+"_PF"+str(round(pf*100))+"_L"+str(l).replace(".","p")+"_ANNUAL_AC.csv"),rows)
            summaries.append(s)
        else:
            allrows.extend(rows);summaries.extend(follow.sample.summarize(rows))
        print(c,pf,l,n,"complete",flush=True)
    if scope=="sample":pd.DataFrame(allrows).to_csv(out/"FACTOR_AC_HOURLY.csv",index=False)
    pd.DataFrame(summaries).to_csv(out/"FACTOR_AC_SUMMARY.csv",index=False)
    doc.update(status="COMPLETE_NINE_FACTOR_SAMPLE_NOT_ANNUAL" if scope=="sample" else "COMPLETE_SELECTED_ANNUAL_FACTOR_REPLAY",
               new_AC_case_hours=new,reference_regressions=checks,completed_case_factors=len(summaries),
               output_sha256={p.name:follow.sample.sha(p) for p in out.iterdir() if p.is_file() and p.name!="RUN_MANIFEST.json"})

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--scope",choices=["sample","annual"],default="sample")
    ap.add_argument("--cases",nargs="+",choices=CASES)
    ap.add_argument("--pf",type=float,choices=[.95,.98,1.])
    ap.add_argument("--length",type=float,choices=[1.,1.3,1.6])
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--out",type=Path)
    a=ap.parse_args();cases=a.cases or list(CASES)
    if len(cases)!=len(set(cases)):ap.error("Duplicate case")
    if a.scope=="annual" and (a.pf is None or a.length is None):ap.error("Annual requires explicit PF/length")
    if a.scope=="sample" and (a.pf is not None or a.length is not None):ap.error("Sample uses all nine factors")
    if not a.preflight_only and (a.out is None or a.out.exists()):ap.error("Choose fresh output")
    factors=FACTORS if a.scope=="sample" else [(a.pf,a.length)]
    prepared=prepare(a.repo_root.resolve());plan=selection(prepared[2],cases,a.scope,factors)
    doc=dict(status="SIGNED_SIZING_NINE_FACTOR_PREFLIGHT_NO_SOLVES",scope=a.scope,cases=cases,
             factors=[list(k) for k in factors],planned_case_factors=len(plan),
             common_hours_by_family={k:len(x["hours"]) for k,x in prepared[2].items()},
             planned_case_hours=sum(z[4] for z in plan),
             planned_new_AC_case_hours=sum(z[4] for z in plan if (z[2],z[3])!=REF),
             no_new_LP=True,field_verified=False,annual_AC_verified=False,
             note="Fixed schedules; stress failure is not proof no alternative controller is feasible")
    print(json.dumps(doc,indent=2),flush=True)
    if a.preflight_only:return
    a.out.mkdir(parents=False,exist_ok=False);doc["status"]="INCOMPLETE_FACTOR_REPLAY"
    follow.jsonsave(a.out/"RUN_MANIFEST.json",doc)
    try:run(a.out,prepared,plan,a.scope,doc)
    except Exception as e:
        doc["error"]=repr(e);follow.jsonsave(a.out/"RUN_MANIFEST.json",doc);raise
    follow.jsonsave(a.out/"RUN_MANIFEST.json",doc)
    print(json.dumps(doc,indent=2))

if __name__=="__main__":main()
