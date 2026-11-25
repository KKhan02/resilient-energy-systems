#!/usr/bin/env python3
"""Matched placement/retrofit replay using frozen three-design dispatch; no new LP."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import sizing_physical_option_probe as phys
import sizing_nine_factor as nf
import sizing_ac_followup as follow
import reserve_full_night as rn
from audit_battery_coverage import signed,read_json

SOURCE=Path("StudyA_94022_Physical_Options_v1")
HASHES={"PHYSICAL_OPTION_PROBES.csv":"1986a8f373430fdf87ab75d125e6974a8bc1204e01f72ab383372c77410bcb4e",
"PHYSICAL_OPTION_SUMMARY.csv":"ee4e0fd7e88aa9728480f327d85477b856e6eb6866822e685849af51ab60c705"}
OPTIONS=("middle","end","head_hypothetical_R050")
CASES=nf.CASES[-3:]

def prepare(repo):
    m=read_json(repo/SOURCE/"RUN_MANIFEST.json")
    if m["status"]!="COMPLETE_PHYSICAL_OPTION_SCREEN" or m["probe_rows"]!=756 or m["head_regressions"]!=189:
        raise ValueError("Physical receipt changed")
    for name,h in HASHES.items():
        nf.check_receipt_hash(repo/SOURCE/name,h,m["output_sha256"][name]);signed(repo/SOURCE/name,h)
    a=pd.read_csv(repo/SOURCE/"PHYSICAL_OPTION_PROBES.csv",parse_dates=["timestamp_lst"],keep_default_na=False)
    if len(a)!=756 or a.duplicated(["option","pf","length_factor","timestamp_lst","probe_index"]).any() or not a.status.eq("CONVERGED").all():
        raise ValueError("Physical source population changed")
    v6,annual,x,events,archive,reg=phys.prepare(repo)
    if tuple(x["cases"])!=tuple(CASES) or len(x["hours"])!=67:
        raise ValueError("Matched schedule/sample changed")
    head=pd.read_csv(repo/phys.prior.SOURCE/"FACTOR_AC_HOURLY.csv",parse_dates=["timestamp_lst"],keep_default_na=False)
    head=head[head.family.eq("constraint")].copy()
    if len(head)!=1809 or head.duplicated(["case","pf","length_factor","timestamp_lst"]).any():
        raise ValueError("Head sample changed")
    for c in CASES:
        z=head[head.case.eq(c)]
        if not z.energy_sha256.eq(x["signatures"][c]).all():
            raise ValueError("Head schedule identity changed")
    return v6,annual,x,a,reg,head

def plan(options,cases,factors,hours):
    return [(o,c,pf,l,hours) for o in options for c in cases for pf,l in factors]

def build(terr,opt,reg,l):
    from run_epm_validation import build_net
    n,m=build_net(terr,"head" if opt.startswith("head") else opt)
    if opt=="head_hypothetical_R050":phys.apply_bundle(n,reg,l)
    return n,m

def run(out,prepared,options,cases,factors,scope,doc):
    import pandapower as pp
    v6,annual,x,a,reg,head=prepared
    common=CASES[0];checks=0;rows=[];summ=[]
    for (opt,pf,l),g in a[a.option.isin(options)&a.probe_index.isin([0,20])].groupby(["option","pf","length_factor"]):
        terr=x["territories"][l];net,meta=build(terr,opt,reg,l)
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("GIS load keys changed")
        for r in g.to_dict("records"):
            q=follow.evaluate(v6,pp,net,meta,terr,x,common,r["timestamp_lst"],pf,p=r["probe_p_kw"])
            annual.exact_ac_regression(q,r,opt+" endpoint "+str(r["timestamp_lst"]));checks+=1
    for opt,c,pf,l,n in plan(options,cases,factors,67 if scope=="sample" else 8760):
        terr=x["territories"][l];net,meta=build(terr,opt,reg,l)
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("GIS load keys changed")
        f=x["frames"][c];local=[]
        for t in (x["hours"] if scope=="sample" else f.index):
            q=follow.evaluate(v6,pp,net,meta,terr,x,c,t,pf)
            q.update(option=opt,case=c,pf=pf,length_factor=l,inverter_node=meta["node"],
                     source_energy_sha256=x["signatures"][c],source_grid_import_kw=float(f.at[t,"grid_import_kw"]),
                     strict_feasible=rn.strict_point(q))
            local.append(q)
        if len(local)!=n:raise ValueError("Incomplete factor replay")
        if scope=="annual":
            result=annual.annual_summary(local);result.update(option=opt,case=c,pf=pf,length_factor=l,
                strict_exact_failed_hours=sum(not r["strict_feasible"] for r in local))
            annual.save_csv(out/(opt+"_"+c+"_ANNUAL_AC.csv"),local)
        else:
            z=pd.DataFrame(local);conv=z[z.status.eq("CONVERGED")]
            result=dict(option=opt,case=c,pf=pf,length_factor=l,sampled_hours=n,converged=len(conv),
                infeasible=int((~z.strict_feasible).sum()),night_failed=int((~z.strict_feasible&z.night_reactive_disabled).sum()),
                daylight_failed=int((~z.strict_feasible&~z.night_reactive_disabled).sum()),
                min_v_pu=conv.min_v_pu.min(),max_v_pu=conv.max_v_pu.max(),max_trafo_pct=conv.max_trafo_pct.max(),max_line_pct=conv.max_line_pct.max())
            rows.extend(local)
        summ.append(result);print(opt,c,pf,l,n,"complete",flush=True)
    if scope=="sample":
        pd.DataFrame(rows).to_csv(out/"OPTION_AC_HOURLY.csv",index=False)
        head.to_csv(out/"SIGNED_HEAD_COMPARISON.csv",index=False)
    pd.DataFrame(summ).to_csv(out/"OPTION_AC_SUMMARY.csv",index=False)
    doc.update(status="COMPLETE_MATCHED_OPTION_SAMPLE_NOT_ANNUAL" if scope=="sample" else "COMPLETE_SELECTED_OPTION_ANNUAL",
        endpoint_regressions=checks,new_AC_case_hours=sum(z[-1] for z in plan(options,cases,factors,67 if scope=="sample" else 8760)),
        completed_case_factors=len(summ),output_sha256={p.name:follow.sample.sha(p) for p in out.iterdir() if p.is_file() and p.name!="RUN_MANIFEST.json"})

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--scope",choices=["sample","annual"],default="sample")
    ap.add_argument("--options",nargs="+",choices=OPTIONS);ap.add_argument("--cases",nargs="+",choices=CASES)
    ap.add_argument("--pf",type=float,choices=[.95,.98,1.]);ap.add_argument("--length",type=float,choices=[1.,1.3,1.6])
    ap.add_argument("--preflight-only",action="store_true");ap.add_argument("--out",type=Path);a=ap.parse_args()
    options=a.options or list(OPTIONS);cases=a.cases or list(CASES)
    if len(set(options))!=len(options) or len(set(cases))!=len(cases):ap.error("Duplicate selection")
    if a.scope=="annual" and (a.pf is None or a.length is None):ap.error("Annual requires explicit factor")
    if a.scope=="sample" and (a.pf is not None or a.length is not None):ap.error("Sample uses all nine factors")
    if not a.preflight_only and (a.out is None or a.out.exists()):ap.error("Choose fresh output")
    factors=nf.FACTORS if a.scope=="sample" else [(a.pf,a.length)]
    prepared=prepare(a.repo_root.resolve())
    n=67 if a.scope=="sample" else 8760
    grid=plan(options,cases,factors,n)
    doc=dict(status="SIGNED_MATCHED_PHYSICAL_OPTION_PREFLIGHT_NO_SOLVES",scope=a.scope,options=options,cases=cases,factors=[list(z) for z in factors],
             planned_case_factors=len(grid),planned_new_AC_case_hours=sum(z[-1] for z in grid),
             planned_endpoint_regressions=int(prepared[3].option.isin(options).mul(prepared[3].probe_index.isin([0,20])).sum()),
             field_verified=False,no_new_LP=True,annual_verified=False,interpretation="Frozen reference schedules; no optimization or physical installation approval")
    print(doc,flush=True)
    if a.preflight_only:return
    a.out.mkdir(parents=False);doc["status"]="INCOMPLETE_MATCHED_OPTION_REPLAY";follow.jsonsave(a.out/"RUN_MANIFEST.json",doc)
    try:run(a.out,prepared,options,cases,factors,a.scope,doc)
    except Exception as e:
        doc["error"]=repr(e);follow.jsonsave(a.out/"RUN_MANIFEST.json",doc);raise
    follow.jsonsave(a.out/"RUN_MANIFEST.json",doc);print(doc,flush=True)
if __name__=="__main__":main()
