#!/usr/bin/env python3
"""94022 full-night reference reserve screening, LP and source-stitched annual AC."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
import reserve_reference_annual as prev
import sizing_ac_followup as follow
import sizing_priority_pilot as sizing
from audit_battery_coverage import signed, read_frame, read_json

SOURCE=Path("StudyA_94022_Sizing_Reserve_AnnualAC_v1")
CASES=prev.CASES
AC_HASH={
    CASES[0]:"eaf128da95e34eeea8886ae8089839e678bb4b5227bcc08a50f77475b45fef7b",
    CASES[1]:"81c24d0a0a13bf03a5add637a4ce98e3f6537f3a9806d1be0aa408b6515bc102",
    CASES[2]:"cd92812c4b6e0be32647de6b391705ab4632354ab8a271e818affa9c2fb2d291",
}
COUNTS=dict(zip(CASES,(9,8,8)))
SUMMARY_HASH="63e0da34a0b2e0e3ad9911505b9095d0e20403d44f75c4f5e748bb76903b9318"

def strict_point(r):
    return (r["status"]=="CONVERGED" and bool(r["ac_feasible"]) and
        float(r["min_v_pu"])>=.95 and float(r["max_v_pu"])<=1.05 and
        float(r["max_trafo_pct"])<=100 and float(r["max_line_pct"])<=100)

def zero_archive(t,records):
    for c in CASES:
        r=records[c].loc[t]
        if float(r.inverter_ac_kw)==0. and r.status=="CONVERGED":
            return c,r.to_dict()
    return None,None

def interval(measure,cap):
    if cap<=0:raise ValueError("Nonpositive event ceiling")
    points=[(float(p),measure(float(p))) for p in np.linspace(0,cap,21)]
    seg=follow.choose_grid_interval(points)
    if seg is None:return None
    hi,upper,lo=seg
    if lo is not None:
        for _ in range(10):
            mid=(hi+lo)/2
            if measure(mid):hi=mid
            else:lo=mid
    lower=min(upper,hi+.01)
    if not measure(lower):
        return None
    return lower,upper

def intersect(a,b):
    lo,hi=max(a[0],b[0]),min(a[1],b[1])
    if lo>hi:raise ValueError("Empty intersection with prior corridor")
    return lo,hi

def changed_mask(old,new):
    if not old.index.equals(new.index):raise ValueError("Chronology changed")
    for k in ("demand_kw","pv_dc_available_kw"):
        if not np.array_equal(old[k].to_numpy(),new[k].to_numpy()):
            raise ValueError("Exogenous source changed: "+k)
    # Exact equality, not a tolerance: do not reuse a changed AC input.
    return old.inverter_ac_kw.ne(new.inverter_ac_kw)

def prepare(repo):
    v6,annual,x,frames,benches,sm=prev.prepare(repo)
    annual.check_source_stateless(v6)
    m=read_json(repo/SOURCE/"RUN_MANIFEST.json")
    if (m["status"]!="COMPLETE_94022_RESERVE_REFERENCE_ANNUAL_AC" or
        m["new_AC_case_hours"]!=26280 or m["regressions_passed"]!=51 or
        m["pf"]!=.98 or m["length_factor"]!=1. or
        m["source_reserve_hashes"]!=prev.ENERGY_HASHES or
        any(m["annual_AC_verified_by_case"].values())):
        raise ValueError("Annual source receipt changed")
    if m["output_sha256"]["ANNUAL_AC_SUMMARY.csv"]!=SUMMARY_HASH:
        raise ValueError("Annual summary identity")
    signed(repo/SOURCE/"ANNUAL_AC_SUMMARY.csv",SUMMARY_HASH)
    records={};old_limits={};fail=set()
    ref=frames[CASES[0]]
    hw0=x["hardware"][CASES[0]]
    for c in CASES:
        for k in ("demand_kw","pv_dc_available_kw"):
            if not np.array_equal(ref[k].to_numpy(),frames[c][k].to_numpy()):
                raise ValueError("Unmatched common AC inputs")
        for k in ("inverter_kva","battery_power_dc_kw","transformer_kva_assumed_or_evidenced"):
            if x["hardware"][c][k]!=hw0[k]:raise ValueError("Different common AC power limits")
        name=c+"_ANNUAL_AC.csv";path=repo/SOURCE/name
        if m["output_sha256"][name]!=AC_HASH[c]:raise ValueError("Annual hash identity")
        signed(path,AC_HASH[c])
        a=pd.read_csv(path,parse_dates=["timestamp_lst"],keep_default_na=False).set_index("timestamp_lst")
        if (not a.index.equals(ref.index) or not a.case.eq(c).all() or
            not a.reserve_energy_sha256.eq(prev.ENERGY_HASHES[c]).all() or
            not a.source_energy_sha256.eq(x["signatures"][c]).all() or
            not a.pf.eq(.98).all() or not a.length_factor.eq(1.).all() or
            not a.status.eq("CONVERGED").all() or
            not a.ac_feasible.isin([True,False]).all() or
            not np.isfinite(a[["min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw"]].to_numpy(float)).all()):
            raise ValueError("Annual AC input/status mismatch")
        for ac,energy in (("gross_demand_kw","demand_kw"),("inverter_ac_kw","inverter_ac_kw"),
                          ("source_grid_import_kw","grid_import_kw")):
            if not np.allclose(a[ac],frames[c][energy],rtol=0,atol=1e-9):
                raise ValueError("Annual P/load/import mismatch")
        bad=a[~a.ac_feasible]
        if len(bad)!=COUNTS[c] or not bad.night_reactive_disabled.all():
            raise ValueError("Annual failure identity changed")
        if not np.array_equal(a.night_reactive_disabled.to_numpy(),(ref.pv_dc_available_kw<=1e-9).to_numpy()):
            raise ValueError("Night policy changed")
        fail.update(bad.index)
        for t,r in benches[c].items():annual.exact_ac_regression(a.loc[t].to_dict(),r,c+" archive "+str(t))
        records[c]=a
        rc=read_json(repo/prev.SOURCE/(c+"_RESERVE_RECEIPT.json"))
        old_limits[c]={pd.Timestamp(t):tuple(b) for t,b in rc["corridors"].items()}
    if len(fail)!=9 or any(old_limits[c]!=old_limits[CASES[0]] for c in CASES):
        raise ValueError("Unexpected source failure/corridor population")
    night=ref.index[ref.pv_dc_available_kw<=1e-9]
    reuse=sum(zero_archive(t,records)[0] is not None for t in night)
    if len(night)!=4353 or reuse!=2660:raise ValueError("Night source coverage changed")
    return v6,annual,x,frames,benches,sm,records,old_limits[CASES[0]],night,fail

def run(repo,out,prepared,cases,doc):
    import pandapower as pp
    from run_epm_validation import build_net
    import fixed_hardware as fh
    import study_a_pvbess as st
    v6,annual,x,frames,benches,sm,records,old_limits,night,fail=prepared
    common=CASES[0];ref=frames[common];demand=x["trace"].sum(axis=1)
    solar,_=st.solar_per_unit(repo,demand.index)
    terr=x["territories"][1.];net,meta=build_net(terr,"head")
    if set(meta["loads"])!=set(x["ids"]):raise ValueError("GIS load keys changed")
    old=dict(x,frames=frames)
    probes=[];risk=[];screen=[];regressions=0
    for c in CASES:
        for t in sorted(set(benches[c])|set(records[c].index[~records[c].ac_feasible])):
            actual=follow.evaluate(v6,pp,net,meta,terr,old,c,t,.98)
            annual.exact_ac_regression(actual,records[c].loc[t].to_dict(),c+" annual "+str(t));regressions+=1
    for i,t in enumerate(night):
        source,r=zero_archive(t,records)
        if source is None:
            r=follow.evaluate(v6,pp,net,meta,terr,old,common,t,.98,p=0.)
            probes.append(dict(probe="zero_screen",**r))
        ok=strict_point(r)
        screen.append(dict(timestamp_lst=str(t),source=source or "NEW_AC",gross_demand_kw=float(demand.loc[t]),
            zero_p_feasible=ok,status=r["status"],min_v_pu=r["min_v_pu"],max_trafo_pct=r["max_trafo_pct"]))
        if not ok:risk.append(t)
        if (i+1)%1000==0:print("Night screen",i+1,"/",len(night),flush=True)
    pd.DataFrame(screen).to_csv(out/"NIGHT_ZERO_P_SCREEN.csv",index=False)
    required=sorted(set(risk)|fail|set(old_limits))
    corridors={};limits=[];unresolved=[]
    for t in required:
        cap=follow.power_ceiling(demand.loc[t],x["hardware"][common])
        def measure(p):
            r=follow.evaluate(v6,pp,net,meta,terr,old,common,t,.98,p=p)
            probes.append(dict(probe="corridor",**r))
            return strict_point(r)
        bound=interval(measure,cap)
        if bound is not None and t in old_limits:
            bound=intersect(bound,old_limits[t])
        if bound is not None and (not measure(bound[0]) or not measure(bound[1])):
            bound=None
        if bound is None:
            unresolved.append(str(t))
            limits.append(dict(timestamp_lst=str(t),status="NO_TESTED_CORRIDOR",ceiling_kw=cap))
        else:
            corridors[t]=bound
            limits.append(dict(timestamp_lst=str(t),status="TESTED_ENDPOINTS",ceiling_kw=cap,
                lower_kw=bound[0],upper_kw=bound[1]))
    pd.DataFrame(limits).to_csv(out/"NIGHT_P_CORRIDORS.csv",index=False)
    pd.DataFrame(probes).to_csv(out/"NEW_POWER_PROBES.csv",index=False)
    doc.update(source_regressions=regressions,zero_P_reused=2660,zero_P_new=1693,
        new_power_probes=len(probes),zero_P_risk_hours=len(risk),corridor_count=len(corridors),
        unresolved_corridor_hours=unresolved)
    follow.jsonsave(out/"RUN_MANIFEST.json",doc)
    if unresolved:
        doc.update(status="NIGHT_CORRIDOR_SCREEN_UNRESOLVED_NO_LP",completed_cases=[]);return
    results=[];errors=[]
    for c in cases:
        hw=x["hardware"][c]
        equipment=fh.Hardware(panels=hw["pv_panels"],battery_modules=hw["battery_modules"],
            battery_power_dc_kw=hw["battery_power_dc_kw"],inverter_kva=hw["inverter_kva"],
            transformer_kva=hw["transformer_kva_assumed_or_evidenced"],loading_pu=1.,
            load_pf=.98,export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        try:
            f,model=fh.solve_fixed(repo,equipment,demand,solar,corridors=corridors,min_physical_soc=.20)
        except RuntimeError as e:
            errors.append(dict(case=c,stage="LP",error=str(e)));continue
        f.index.name="timestamp_lst"
        sizing.validate_comparison(f,hw,demand,solar)
        energy_path=out/(c+"_CORRECTED_8760.csv")
        f.to_csv(energy_path,float_format="%.10f")
        f=read_frame(energy_path)
        sizing.validate_comparison(f,hw,demand,solar)
        for t,(lo,hi) in corridors.items():
            if not lo-1e-6<=float(f.at[t,"inverter_ac_kw"])<=hi+1e-6:
                raise ValueError("Corrected schedule outside corridor")
        changed=changed_mask(frames[c],f);new=dict(x,frames={c:f});newhash=follow.sample.sha(energy_path)
        rows=[];evaluated=0
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(x["ids"]):raise ValueError("GIS load keys changed")
        for t in f.index:
            if bool(changed.loc[t]):
                r=follow.evaluate(v6,pp,net,meta,terr,new,c,t,.98);evaluated+=1
                origin="NEW_CHANGED_P_AC"
            else:
                r=records[c].loc[t].to_dict()
                r["timestamp_lst"]=str(t)
                origin="REUSED_SIGNED_SAME_INPUT_AC"
            r.update(case=c,pf=.98,length_factor=1.,source_energy_sha256=x["signatures"][c],
                reserve_energy_sha256=prev.ENERGY_HASHES[c],corrected_energy_sha256=newhash,
                source_grid_import_kw=float(f.at[t,"grid_import_kw"]),AC_origin=origin)
            rows.append(r)
        result=annual.annual_summary(rows)
        cost=float(model["annual_total_usd"]);loss=result["annual_ac_network_losses_kwh"]
        metric=sizing.summary(c,"constraint","OFFLINE_FULL_NIGHT_REFERENCE_RESERVE",hw,f,model)
        result.update(case=c,pf=.98,length_factor=1.,changed_P_AC_hours=evaluated,
            reused_AC_hours=8760-evaluated,prior_failure_hours=COUNTS[c],
            annual_energy_model_cost_usd=cost,annual_import_kwh=float(f.grid_import_kw.sum()),
            annual_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),
            annual_discharge_dc_kwh=metric["discharge_dc_kwh"],
            store_equivalent_discharge_cycles=metric["store_equivalent_discharge_cycles"],
            delta_annual_model_usd=cost-float(sm.loc[c,"annual_total_usd"]),
            all_losses_purchased_cost_sensitivity_usd=cost+.29*loss if loss is not None else None,
            corrected_energy_sha256=newhash)
        annual.save_csv(out/(c+"_ANNUAL_AC.csv"),rows)
        results.append(result);doc["completed_cases"]=results
        follow.jsonsave(out/"RUN_MANIFEST.json",doc)
        print(c,"new AC",evaluated,"retained",8760-evaluated,"remaining",result["main_band_infeasible_hours"],flush=True)
    pd.DataFrame(results).to_csv(out/"ANNUAL_AC_SUMMARY.csv",index=False)
    doc.update(status="COMPLETE_NIGHT_REFERENCE_REPLAY" if not errors else "PARTIAL_NIGHT_REFERENCE_REPLAY",
        completed_cases=results,errors=errors,new_LPs_completed=len(results),
        all_selected_cases_pass=(len(results)==len(cases) and all(r["all_2025_model_main_band_pass"] for r in results)),
        new_changed_P_AC_hours=sum(r["changed_P_AC_hours"] for r in results),
        reused_AC_hours=sum(r["reused_AC_hours"] for r in results))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--cases",nargs="+",choices=CASES)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--out",type=Path)
    a=ap.parse_args();cases=a.cases or list(CASES);repo=a.repo_root.resolve()
    if len(set(cases))!=len(cases):ap.error("Duplicate case")
    if not a.preflight_only and (a.out is None or a.out.exists()):ap.error("Choose fresh output")
    prepared=prepare(repo)
    doc=dict(status="SIGNED_FULL_NIGHT_REFERENCE_PREFLIGHT_NO_SOLVES",cases=cases,pf=.98,length_factor=1.,
        night_hours=4353,zero_P_reused=2660,zero_P_new_planned=1693,known_failed_timestamps=9,
        planned_source_regressions=76,planned_LPs_max=len(cases),annual_case_hours=8760*len(cases),
        field_verified=False,offline_perfect_foresight=True,source_annual_hashes=AC_HASH,
        reuse_rule="Exact same P/load/PV and fixed network/controller, flat independent solve")
    print(json.dumps(doc,indent=2),flush=True)
    if a.preflight_only:return
    out=a.out;out.mkdir(parents=False,exist_ok=False);doc["status"]="INCOMPLETE_NIGHT_REFERENCE_REPLAY"
    follow.jsonsave(out/"RUN_MANIFEST.json",doc)
    try:
        run(repo,out,prepared,cases,doc)
        doc["output_sha256"]={p.name:follow.sample.sha(p) for p in out.iterdir() if p.is_file() and p.name!="RUN_MANIFEST.json"}
    except Exception as e:
        doc["error"]=repr(e);follow.jsonsave(out/"RUN_MANIFEST.json",doc);raise
    follow.jsonsave(out/"RUN_MANIFEST.json",doc)
    print(json.dumps({k:v for k,v in doc.items() if k!="completed_cases"},indent=2))

if __name__=="__main__":
    main()
