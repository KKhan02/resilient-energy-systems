#!/usr/bin/env python3
"""Two residual 106039 A0 events: 40 bounded AC points then annual reuse.
Do not alter previous annual archive or rerun unchanged 8756 hours.
"""
from __future__ import annotations
import argparse
import json
import traceback
from pathlib import Path
import matched16_106039_ss90_reciprocal_annual as prior

nov=prior.nov
gate=prior.gate
annual=prior.annual
thermal=prior.thermal
CASE="A1_106039_ss90_to_A0"
ARCHIVE=Path("StudyA_106039_Reciprocal_SS90_AnnualAC_PF98_v1")
OUT_STEM="StudyA_106039_A0_SS90_Residual2_AnnualAC_PF98_v"
EVENTS=(("2025-09-30 19:00:00","2025-09-30 20:00:00",4.6073349392),
        ("2025-11-15 19:00:00","2025-11-15 20:00:00",4.941285400947368))
FRACTIONS=(0.,.25,.5,.75,.98)
PF=(.98,.95)
STAMPS={t for d,t,_ in EVENTS}
CHANGED={t for d,t,_ in EVENTS for t in (d,t)}

def select_choices(pairs):
    selected=[]
    for donor,target,_ in EVENTS:
        good=[r for r in pairs if r["donor_time"]==donor and r["target_time"]==target
              and r["pair_4of4_AC_screen_pass"] is True]
        if not good:return None
        selected.append(min(good,key=lambda x:x["fraction"]))
    return selected

def summary(rows):
    return annual.annual_summary([{**r,"ac_feasible":prior.bool_ac(r["ac_feasible"])} for r in rows])

def year_index(rows):
    import pandas as pd
    stamps=[r["timestamp_lst"] for r in rows]
    if stamps!=list(map(str,pd.date_range("2025-01-01",periods=8760,freq="h"))):
        raise ValueError("Annual archive must contain all ordered 2025 hours")
    if any(r["status"]!="CONVERGED" for r in rows):
        raise ValueError("Annual source contains nonconverged records")
    return {t:i for i,t in enumerate(stamps)}

def check_archive(original,previous,plan,sha):
    import pandas as pd
    index=year_index(previous);year_index(original)
    changed={r["timestamp_lst"] for r,q in zip(original,previous) if r!=q}
    if changed!=set(plan["changed"]):
        raise ValueError("Expected previous two-row correction only")
    for rows,frame in ((original,plan["source"]),(previous,plan["modified"])):
        for row in rows:
            t=pd.Timestamp(row["timestamp_lst"])
            if row["original_energy_sha256"]!=sha or abs(float(row["load_pf"])-.98)>1e-9:
                raise ValueError("Annual source hash/PF mismatch")
            for ac,energy,tol in (("inverter_ac_kw","inverter_ac_kw",1e-6),
                                  ("gross_demand_kw","demand_kw",1e-5),
                                  ("source_grid_import_kw","grid_import_kw",1e-6)):
                if abs(float(row[ac])-float(frame.at[t,energy]))>tol:
                    raise ValueError("Annual source P/load/import mismatch: "+str(t))
    if {r["timestamp_lst"] for r in previous if not prior.bool_ac(r["ac_feasible"])}!=STAMPS:
        raise ValueError("Residual annual failure set changed")
    for t,row in plan["new"].items():
        annual.exact_ac_regression(previous[index[t]],row,"Prior 25% correction "+t)
    return index

def preflight(repo):
    import pandas as pd
    base,plans,v6=prior.preflight(repo)
    plan=plans[CASE];item=plan["item"];source=plan["source"];previous_frame=plan["modified"]
    sha=item["case"]["target_energy_sha256"]
    manifest=gate.read_json(repo/ARCHIVE/"RUN_MANIFEST.json")
    if (manifest["status"]!="106039_RECIPROCAL_SS90_ANNUAL_PF98_COMPLETE_RESULTS_RECORDED"
        or manifest["new_AC_case_hours"]!=17520 or manifest["cached_corrected_AC_hours"]!=4
        or manifest["stateless_solver_confirmed"] is not True):
        raise ValueError("Prior annual archive receipt changed")
    rows=[];signatures={}
    for label in ("ORIGINAL","CORRECTED"):
        name=CASE+"_"+label+"_8760_AC.csv";path=repo/ARCHIVE/name
        signatures[name]=gate.signed_bytes(path,manifest["outputs_sha256"][name])
        rows.append(gate.read_csv(path))
    original,previous=rows;index=check_archive(original,previous,plan,sha)
    old=summary(previous);ref=manifest["completed_cases"][CASE]["corrected"]
    if old["main_band_infeasible_hours"]!=2 or abs(old["annual_ac_network_losses_kwh"]-ref["annual_ac_network_losses_kwh"])>1e-6:
        raise ValueError("Prior corrected annual summary mismatch")
    events=[]
    for donor,target,expected in EVENTS:
        cap=nov.bound_one_donor(previous_frame,donor,target,item["case"]["hardware"])
        if abs(cap-expected)>1e-7:
            raise ValueError("Independent residual donor cap differs")
        for fraction in FRACTIONS:
            thermal.check_energy(nov.transfer(previous_frame,donor,target,cap*fraction),item)
        events.append({"donor":donor,"target":target,"cap_dc_kw":cap,
                       "previous_target_trafo_pct":float(previous[index[target]]["max_trafo_pct"])})
    doc={"status":"SIGNED_106039_A0_RESIDUAL2_PREFLIGHT_NO_AC","case":CASE,"pf_reference":.98,
         "PF":list(PF),"length_factor":1.0,"events":events,"candidate_pairs":10,
         "planned_new_AC_case_hours":40,"new_AC_case_hours":0,"annual_AC_verified":False,
         "field_EPM_verified":False,"source_energy_sha256":sha,"archive_signatures":signatures,
         "source_solver_stateless":True,"prior_annual_summary":old}
    return doc,plan,v6,original,previous,index

def merge_selected(previous,selected,frame,source_sha):
    import pandas as pd
    index=year_index(previous)
    if set(selected)!=CHANGED:
        raise ValueError("Exactly four residual AC hours required")
    new=[dict(r) for r in previous];ledger=[]
    for stamp,r in sorted(selected.items()):
        prior.validate_row(r,frame,stamp,source_sha)
        if not prior.bool_ac(r["ac_feasible"]):
            raise ValueError("Selected residual AC point infeasible")
        i=index[stamp];old=previous[i];t=pd.Timestamp(stamp)
        if abs(float(old["inverter_ac_kw"])-float(r["inverter_ac_kw"]))<=1e-7:
            raise ValueError("Expected nonzero source P change")
        v=prior.clean_ac(r)
        if not set(v).issubset(old):
            raise ValueError("New AC record schema does not match archive")
        new[i]={**old,**v,"scenario":"corrected_three_event_source_locked",
                "source_grid_import_kw":float(frame.at[t,"grid_import_kw"])}
        ledger.append({"timestamp_lst":stamp,"original_prior_P_kw":float(old["inverter_ac_kw"]),
                       "new_P_kw":float(r["inverter_ac_kw"]),
                       "prior_min_v_pu":float(old["min_v_pu"]),"new_min_v_pu":float(r["min_v_pu"]),
                       "prior_trafo_pct":float(old["max_trafo_pct"]),"new_trafo_pct":float(r["max_trafo_pct"]),
                       "loss_delta_kw":float(r["loss_kw"])-float(old["loss_kw"])})
    if sum(a!=b for a,b in zip(previous,new))!=4:
        raise ValueError("Four-row substitution contract failed")
    return new,ledger

def figures(out,rows,previous,corrected):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    folder=out/"figures_diagnostic";folder.mkdir()
    hashes={}
    for k,limit,label in (("min_v_pu",.95,"Minimum voltage [pu]"),("max_trafo_pct",100,"Transformer loading [%]")):
        fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
        for ax,(donor,target,_) in zip(axes,EVENTS):
            for pf in PF:
                for point in ("donor","target"):
                    q=[r for r in rows if r["target_time"]==target and r["pf"]==pf and r["point"]==point and r["status"]=="CONVERGED"]
                    ax.plot([100*r["fraction"] for r in q],[float(r[k]) for r in q],marker="o",label=f"{pf} {point}")
            ax.axhline(limit,ls="--",color="black");ax.set_title(target[5:16]);ax.set_xlabel("DC donor cap [%]");ax.set_ylabel(label);ax.legend(fontsize=8);ax.grid(alpha=.2)
        fig.tight_layout();p=folder/(k+"_residual_pairs.png");fig.savefig(p,dpi=150);plt.close(fig);hashes[p.name]=nov.digest(p)
        if corrected is not None:
            fig,ax=plt.subplots(figsize=(12,5));t=pd.date_range("2025-01-01",periods=8760,freq="h")
            for q,name in ((previous,"Prior November correction"),(corrected,"All three events corrected")):
                ax.plot(t,[float(r[k]) for r in q],lw=.65,label=name)
            ax.axhline(limit,ls="--",color="black");ax.set_title("106039 A0 twelve households, PF 0.98, cached annual reuse");ax.set_ylabel(label);ax.legend();ax.grid(alpha=.2);fig.autofmt_xdate();fig.tight_layout()
            p=folder/(k+"_annual_reconstruction.png");fig.savefig(p,dpi=150);plt.close(fig);hashes[p.name]=nov.digest(p)
    return hashes

def run(repo,receipt,plan,v6,original,previous,index):
    import pandas as pd
    import pandapower as pp
    from run_epm_validation import build_net
    item=plan["item"];base=plan["modified"];hw=item["case"]["hardware"];sha=receipt["source_energy_sha256"]
    out=next((repo/f"{OUT_STEM}{i}" for i in range(1,100) if not (repo/f"{OUT_STEM}{i}").exists()),None)
    if out is None:raise FileExistsError("No unused output version")
    out.mkdir();manifest=out/"RUN_MANIFEST.json";doc=dict(receipt,status="INCOMPLETE_106039_RESIDUAL2_DO_NOT_CLAIM",outputs_sha256={})
    def save():manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    def csvfile(name,rows):
        p=out/name;annual.save_csv(p,rows);doc["outputs_sha256"][name]=nov.digest(p)
    save();rows=[];pairs=[]
    try:
        net,meta=build_net(item["territory"],"head")
        if set(meta["loads"])!=set(item["ids"]):raise ValueError("GIS load keys changed")
        for e in receipt["events"]:
            donor,target=e["donor"],e["target"]
            for frac in FRACTIONS:
                moved=e["cap_dc_kw"]*frac
                frame=nov.transfer(base,donor,target,moved);thermal.check_energy(frame,item)
                passed=[]
                for pf in PF:
                    for point,stamp in (("donor",donor),("target",target)):
                        t=pd.Timestamp(stamp)
                        v=v6.solve_ac_hour(net,meta,item["territory"],t,item["trace"].loc[t],pf,float(frame.at[t,"inverter_ac_kw"]),float(hw["inverter_kva"]),float(frame.at[t,"pv_dc_available_kw"]),.25,9,"pvbess",pp)
                        if abs(float(v["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5 or abs(float(v["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-5:
                            raise ValueError("AC replay P mismatch")
                        if frac==0 and pf==.98:annual.exact_ac_regression(v,previous[index[stamp]],"Annual baseline "+stamp)
                        passed.append(v["status"]=="CONVERGED" and v["ac_feasible"] is True)
                        rows.append({"case":CASE,"donor_time":donor,"target_time":target,"point":point,"pf":pf,"fraction":frac,"moved_dc_kw":moved,"source_sha256":sha,**v})
                        print(f"Residual AC {len(rows)}/40 | {target} | {frac} | {pf} | {point}",flush=True)
                pairs.append({"case":CASE,"donor_time":donor,"target_time":target,"fraction":frac,"moved_dc_kw":moved,"pair_4of4_AC_screen_pass":all(passed),"passed_local_AC_points":sum(passed)})
        if len(rows)!=40 or len(pairs)!=10:raise ValueError("Incomplete residual campaign")
        csvfile("DONOR_TARGET_40_AC_CASEHOURS.csv",rows);csvfile("PAIR_CANDIDATES_10.csv",pairs)
        choices=select_choices(pairs);corrected=None
        doc.update(new_AC_case_hours=40,converged=sum(r["status"]=="CONVERGED" for r in rows),
                   selected_pairs=choices,annual_AC_verified=False)
        if choices is None:
            doc["status"]="106039_RESIDUAL2_PILOT_COMPLETE_NO_COMBINED_PASS"
        else:
            frame=thermal.combined_frame(base,choices);energy=thermal.check_energy(frame,item)
            changed={str(t) for t in base.index[(base.inverter_ac_kw-frame.inverter_ac_kw).abs()>1e-7]}
            if changed!=CHANGED:raise ValueError("Combined annual P changes not exactly four residual hours")
            if {str(t) for t in frame.index[(plan["source"].inverter_ac_kw-frame.inverter_ac_kw).abs()>1e-7]}!=CHANGED|set(plan["changed"]):
                raise ValueError("Expected six changed hours vs frozen original")
            selected={}
            for c in choices:
                for q in rows:
                    if q["target_time"]==c["target_time"] and q["fraction"]==c["fraction"] and q["pf"]==.98:
                        if q["timestamp_lst"] in selected:raise ValueError("Duplicate selected AC row")
                        selected[q["timestamp_lst"]]=q
            corrected,ledger=merge_selected(previous,selected,frame,sha)
            for r in corrected:
                t=pd.Timestamp(r["timestamp_lst"])
                if abs(float(r["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-6 or abs(float(r["source_grid_import_kw"])-float(frame.at[t,"grid_import_kw"]))>1e-6 or abs(float(r["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5:
                    raise ValueError("Reconstructed annual source parity failure")
            a,b=summary(previous),summary(corrected)
            delta=b["annual_ac_network_losses_kwh"]-a["annual_ac_network_losses_kwh"]
            if abs(delta-sum(r["loss_delta_kw"] for r in ledger))>1e-6:raise ValueError("Loss delta closure failed")
            csvfile("CORRECTED_2025_8760_AC.csv",corrected);csvfile("FOUR_NEW_CHANGED_AC_HOURS.csv",ledger)
            doc.update(status="106039_RESIDUAL2_ANNUAL_RECONSTRUCTION_COMPLETE",
                       annual_AC_verified=b["all_2025_model_main_band_pass"],
                       annual_summary=b,annual_energy_metrics=energy,
                       reused_prior_AC_hours=8756,cached_new_AC_hours=4,
                       changed_P_hours_vs_original=6,annual_loss_delta_kwh=delta)
        doc["diagnostics_sha256"]=figures(out,rows,previous,corrected)
        save();return doc
    except Exception as exc:
        doc.update(status="INCOMPLETE_106039_RESIDUAL2_DO_NOT_CLAIM",new_AC_case_hours=len(rows),failure=str(exc),traceback=traceback.format_exc())
        save();raise

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."))
    mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument("--preflight-only",action="store_true");mode.add_argument("--run-local",action="store_true")
    args=ap.parse_args(argv);repo=args.repo_root.resolve();data=preflight(repo)
    print(json.dumps(data[0] if args.preflight_only else run(repo,*data),indent=2,allow_nan=False))
if __name__=="__main__":main()
