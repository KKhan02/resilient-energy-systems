#!/usr/bin/env python3
"""Matched 106039 SS90 reference annual AC: both transfer directions.
Original signed P evaluated at every hour; two cached corrected points per
case substituted after exact source and stateless solver checks. No new LP.
"""
from __future__ import annotations
import argparse
import json
import traceback
from pathlib import Path
import matched16_reciprocal_p1_thermal_ac as thermal
import matched16_94022_ss90_mar_nov_annual_ac as annual

nov=thermal.nov
gate=nov.gate
PF=.98
CASES=("A0_106039_ss90_to_A1","A1_106039_ss90_to_A0")
ARCHIVE=Path("StudyA_Reciprocal_P1_Thermal_DonorTarget_v1")
OUT_STEM="StudyA_106039_Reciprocal_SS90_AnnualAC_PF98_v"
FRACTION=.25

def select_pair(rows, case, donor,target,fraction):
    selected={}
    for row in rows:
        if row["case"]!=case or row["target_time"]!=target or float(row["fraction"])!=fraction or float(row["pf"])!=PF:
            continue
        point=row["point"]
        if point not in ("donor","target") or row["donor_time"]!=donor or row["timestamp_lst"]!=(donor if point=="donor" else target) or point in selected:
            raise ValueError("Cached thermal pair identity or duplicate")
        selected[point]=row
    if set(selected)!={"donor","target"}:
        raise ValueError("Missing exact cached pair")
    return {row["timestamp_lst"]:row for row in selected.values()}

def bool_ac(x):
    if str(x).lower() not in ("true","false"):
        raise ValueError("Invalid AC flag")
    return str(x).lower()=="true"

def clean_ac(row):
    # Retain only v6 AC output fields, not experiment-specific metadata.
    excluded={"case","donor_time","target_time","fraction","moved_dc_kw","point","pf","source_sha256"}
    return {k:(bool_ac(v) if k=="ac_feasible" else v) for k,v in row.items() if k not in excluded}

def validate_row(row,frame,stamp,source_sha):
    import pandas as pd
    t=pd.Timestamp(stamp)
    if (row["source_sha256"]!=source_sha or abs(float(row["load_pf"])-PF)>1e-9
        or row["status"]!="CONVERGED"
        or abs(float(row["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5
        or abs(float(row["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-6):
        raise ValueError("Cached AC source/P/PF mismatch: "+stamp)

def preflight(repo):
    import pandas as pd
    base,prepared,v6=thermal.preflight(repo)
    annual.check_source_stateless(v6)
    m=gate.read_json(repo/ARCHIVE/"RUN_MANIFEST.json")
    if (m["status"]!="P1_THERMAL_120_AC_COMPLETE_NOT_ANNUAL" or m["new_AC_case_hours"]!=120
        or m["converged"]!=120 or m["infeasible"]!=12 or m["annual_AC_verified"] is not False):
        raise ValueError("Thermal archive receipt changed")
    a=repo/ARCHIVE/"DONOR_TARGET_120_AC_CASEHOURS.csv"
    b=repo/ARCHIVE/"PAIR_CANDIDATES_30.csv"
    sig={q.name:gate.signed_bytes(q,m["outputs_sha256"][q.name]) for q in (a,b)}
    rows=gate.read_csv(a);pairs=gate.read_csv(b)
    if len(rows)!=120 or len(pairs)!=30 or len({(r["case"],r["target_time"],r["fraction"],r["pf"],r["point"]) for r in rows})!=120:
        raise ValueError("Thermal archive row population changed")
    p1m=gate.read_json(repo/nov.P1/"RUN_MANIFEST.json")
    p1path=repo/nov.P1/"TARGETED_36_AC_CASEHOURS.csv"
    gate.signed_bytes(p1path,p1m["targeted_ac_csv_sha256"])
    p1=gate.read_csv(p1path)
    results={};evidence=[]
    for case in CASES:
        item=prepared[case];e=item["events"][0];donor,target=e["donor"],e["target"];source=item["source"]
        c=item["case"];sha=c["target_energy_sha256"]
        winner=[r for r in pairs if r["case"]==case and r["target_time"]==target and float(r["fraction"])==FRACTION]
        if len(winner)!=1 or winner[0]["pair_4of4_AC_screen_pass"]!="True" or int(winner[0]["passed_local_AC_points"])!=4:
            raise ValueError("Selected 25% pair did not pass")
        x=float(winner[0]["moved_dc_kw"])
        if abs(x-e["cap"]*FRACTION)>1e-8:
            raise ValueError("Signed transfer cap changed")
        chosen=[r for r in m["combined_candidates"] if r["case"]==case]
        if len(chosen)!=1 or not chosen[0]["all_event_pairs_pass"] or not chosen[0]["combined_annual_SOC_valid"] or len(chosen[0]["choices"])!=1 or abs(float(chosen[0]["choices"][0]["moved_dc_kw"])-x)>1e-8:
            raise ValueError("Combined annual SOC receipt does not match 25%")
        modified=nov.transfer(source,donor,target,x);energy=thermal.check_energy(modified,item)
        altered=[str(t) for t in source.index[(source.inverter_ac_kw-modified.inverter_ac_kw).abs()>1e-7]]
        if altered!=[donor,target] or not item["trace"].index.equals(source.index):
            raise ValueError("Expected two changed source hours and equal trace chronology")
        if (item["trace"].sum(axis=1)-source.demand_kw).abs().max()>1e-5:
            raise ValueError("Full year individual demand trace mismatch")
        old=select_pair(rows,case,donor,target,0.)
        new=select_pair(rows,case,donor,target,FRACTION)
        for stamp in altered:
            validate_row(old[stamp],source,stamp,sha);validate_row(new[stamp],modified,stamp,sha)
            if not bool_ac(new[stamp]["ac_feasible"]):
                raise ValueError("Cached corrected point failed AC")
        # Verify the selected corrected pair at both PFs even though annual PF is .98.
        both=[r for r in rows if r["case"]==case and r["target_time"]==target and float(r["fraction"])==FRACTION]
        if len(both)!=4 or {float(r["pf"]) for r in both}!={.98,.95} or any(r["status"]!="CONVERGED" or not bool_ac(r["ac_feasible"]) for r in both):
            raise ValueError("Both-PF corrected pair regression changed")
        # Additional unchanged daylight reference for annual original replay.
        daylight=[r for r in p1 if r["case"]==case and float(r["pf"])==PF and r["reason"]=="DAYLIGHT_PV_Q_CHECK"]
        if len(daylight)!=1:
            raise ValueError("Missing original daytime AC regression")
        stamp=daylight[0]["timestamp_lst"]
        validate_row(daylight[0],source,stamp,sha)
        if stamp in old:raise ValueError("Daylight benchmark collides with pair")
        results[case]={"item":item,"source":source,"modified":modified,"changed":altered,"old":{**old,stamp:daylight[0]},"new":new,"energy":energy}
        evidence.append({"case":case,"source_energy_sha256":sha,"changed_hours":altered,"shift_dc_kwh":x,
                         "annual_import_kwh":energy["annual_import_kwh"],"annual_curtail_dc_kwh":energy["annual_curtail_dc_kwh"]})
    return {"status":"SIGNED_106039_RECIPROCAL_SS90_ANNUAL_PREFLIGHT_NO_AC",
            "pf":PF,"cases":2,"hours_per_case":8760,"planned_new_AC_case_hours":17520,
            "planned_cached_corrected_AC_hours":4,"new_AC_case_hours":0,"annual_AC_verified":False,
            "field_EPM_verified":False,"length_factor":1.0,"stateless_solver_confirmed":True,
            "archive_signatures":sig,"case_sources":evidence},results,v6

def replace_pair(original,cache,modified,case,sha):
    import pandas as pd
    if len(original)!=8760 or len(cache)!=2:
        raise ValueError("Expected complete annual source and two changed points")
    by={r["timestamp_lst"]:i for i,r in enumerate(original)}
    if len(by)!=8760 or not set(cache).issubset(by):
        raise ValueError("Annual source chronology mismatch")
    corrected=[dict(r) for r in original];ledger=[]
    for stamp,r in sorted(cache.items()):
        i=by[stamp];old=original[i];t=pd.Timestamp(stamp)
        validate_row(r,modified,stamp,sha)
        if not bool_ac(r["ac_feasible"]):raise ValueError("Cached point infeasible")
        v=clean_ac(r)
        if old["status"]!="CONVERGED":
            raise ValueError("Cannot replace nonconverged original pair")
        if abs(float(v["inverter_ac_kw"])-float(old["inverter_ac_kw"]))<=1e-7:
            raise ValueError("Expected actual P change at pair point")
        corrected[i]={**old,**v,"scenario":"corrected_25pct_source_locked","source_grid_import_kw":float(modified.at[t,"grid_import_kw"])}
        ledger.append({"case":case,"timestamp_lst":stamp,"original_P_kw":float(old["inverter_ac_kw"]),"corrected_P_kw":float(v["inverter_ac_kw"]),
                       "original_voltage_pu":float(old["min_v_pu"]),"corrected_voltage_pu":float(v["min_v_pu"]),
                       "original_trafo_pct":float(old["max_trafo_pct"]),"corrected_trafo_pct":float(v["max_trafo_pct"]),
                       "loss_delta_kw":float(v["loss_kw"])-float(old["loss_kw"])})
    if sum(x!=y for x,y in zip(original,corrected))!=2:
        raise ValueError("Exactly two annual rows must change")
    return corrected,ledger

def figures(out,case,original,corrected):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    folder=out/"figures_diagnostic";folder.mkdir(exist_ok=True)
    x=pd.date_range("2025-01-01",periods=8760,freq="h")
    hashes={}
    for k,threshold,label in (("min_v_pu",.95,"Minimum voltage [pu]"),("max_trafo_pct",100.,"Transformer loading [%]")):
        fig,ax=plt.subplots(figsize=(12,5))
        for rows,name in ((original,"Original"),(corrected,"Corrected 25%")):
            ax.plot(x,[float(r[k]) if r["status"]=="CONVERGED" else float("nan") for r in rows],lw=.6,label=name)
        ax.axhline(threshold,ls="--",color="black");ax.set_title(case+" | PF 0.98");ax.set_ylabel(label);ax.legend();ax.grid(alpha=.2)
        fig.autofmt_xdate();fig.tight_layout();p=folder/(case+"_"+k+".png");fig.savefig(p,dpi=150);plt.close(fig);hashes[p.name]=nov.digest(p)
    return hashes

def run(repo,receipt,prepared,v6):
    import pandapower as pp
    from run_epm_validation import build_net
    out=next((repo/f"{OUT_STEM}{i}" for i in range(1,100) if not (repo/f"{OUT_STEM}{i}").exists()),None)
    if out is None:raise FileExistsError("No unused output directory")
    out.mkdir();manifest=out/"RUN_MANIFEST.json"
    report=dict(receipt,status="INCOMPLETE_106039_RECIPROCAL_SS90_ANNUAL_DO_NOT_CLAIM",completed_cases={},outputs_sha256={},diagnostics_sha256={})
    def save():manifest.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save();ledger=[];count=0
    try:
        for case in CASES:
            plan=prepared[case];item=plan["item"];source=plan["source"];modified=plan["modified"]
            hw=item["case"]["hardware"];sha=item["case"]["target_energy_sha256"];trace=item["trace"];territory=item["territory"]
            net,meta=build_net(territory,"head")
            if set(meta["loads"])!=set(item["ids"]):raise ValueError("GIS load keys changed")
            original=[]
            for i,t in enumerate(source.index):
                r=source.iloc[i];value=v6.solve_ac_hour(net,meta,territory,t,trace.iloc[i],PF,float(r.inverter_ac_kw),float(hw["inverter_kva"]),float(r.pv_dc_available_kw),.25,9,"pvbess",pp)
                count+=1
                if abs(float(value["gross_demand_kw"])-float(r.demand_kw))>1e-5 or abs(float(value["inverter_ac_kw"])-float(r.inverter_ac_kw))>1e-5:
                    raise ValueError("Annual replay did not use exact source P")
                if str(t) in plan["old"]:annual.exact_ac_regression(value,plan["old"][str(t)],case+" "+str(t))
                original.append({"scenario":"original","source_grid_import_kw":float(r.grid_import_kw),"original_energy_sha256":sha,**value})
                if (i+1)%500==0:
                    report["new_AC_case_hours"]=count;save()
                    print(f"{case}: {i+1}/8760",flush=True)
            corrected,changes=replace_pair(original,plan["new"],modified,case,sha)
            a=annual.annual_summary(original);b=annual.annual_summary(corrected)
            delta=None
            if a["annual_losses_complete"] and b["annual_losses_complete"]:
                delta=b["annual_ac_network_losses_kwh"]-a["annual_ac_network_losses_kwh"]
                if abs(delta-sum(r["loss_delta_kw"] for r in changes))>1e-5:raise ValueError("Annual loss delta fails changed-hour closure")
            for rows,label in ((original,"ORIGINAL"),(corrected,"CORRECTED")):
                file=out/(case+"_"+label+"_8760_AC.csv");annual.save_csv(file,rows);report["outputs_sha256"][file.name]=nov.digest(file)
            ledger.extend(changes)
            report["diagnostics_sha256"].update(figures(out,case,original,corrected))
            report["completed_cases"][case]={"original":a,"corrected":b,"annual_loss_delta_kwh":delta,
                     "annual_energy_metrics":plan["energy"],"changed_hours":2,"cached_corrected_hours":2,
                     "annual_AC_verified":b["all_2025_model_main_band_pass"]}
            report["new_AC_case_hours"]=count;save()
        if count!=17520 or len(ledger)!=4:raise ValueError("Annual campaign count mismatch")
        file=out/"FOUR_CHANGED_AC_HOURS.csv";annual.save_csv(file,ledger);report["outputs_sha256"][file.name]=nov.digest(file)
        report.update(status="106039_RECIPROCAL_SS90_ANNUAL_PF98_COMPLETE_RESULTS_RECORDED",
                      new_AC_case_hours=count,cached_corrected_AC_hours=4,
                      annual_AC_verified=all(x["annual_AC_verified"] for x in report["completed_cases"].values()),
                      field_EPM_verified=False,loss_adjusted_economics_reoptimized=False)
        save();return report
    except Exception as exc:
        report.update(status="INCOMPLETE_106039_RECIPROCAL_SS90_ANNUAL_DO_NOT_CLAIM",new_AC_case_hours=count,failure=str(exc),traceback=traceback.format_exc());save();raise

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."))
    mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument("--preflight-only",action="store_true");mode.add_argument("--run-local",action="store_true")
    args=ap.parse_args(argv);repo=args.repo_root.resolve();receipt,prepared,v6=preflight(repo)
    print(json.dumps(receipt if args.preflight_only else run(repo,receipt,prepared,v6),indent=2,allow_nan=False))
if __name__=="__main__":main()
