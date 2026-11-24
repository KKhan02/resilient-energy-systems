#!/usr/bin/env python3
"""Six source-locked thermal event pairs on 106039/113699, not annual AC.
Reuse tested fixed-hardware chronological DC shift and original v6 AC logic.
"""
from __future__ import annotations
import argparse
import json
import traceback
from pathlib import Path
import matched16_94022_nov_soc_shift_ac as nov

gate=nov.gate
PF=nov.PF
FRACTIONS=nov.SAMPLE_FRACTIONS
EVENTS={
    "A0_106039_ss90_to_A1": [
        [
            "2025-11-27 18:00:00",
            "2025-11-27 20:00:00"
        ]
    ],
    "A1_106039_ss90_to_A0": [
        [
            "2025-11-27 18:00:00",
            "2025-11-27 20:00:00"
        ]
    ],
    "A0_113699_min_cost_to_A1": [
        [
            "2025-03-14 17:00:00",
            "2025-03-14 19:00:00"
        ],
        [
            "2025-11-30 17:00:00",
            "2025-11-30 20:00:00"
        ]
    ],
    "A0_113699_ss90_to_A1": [
        [
            "2025-03-14 17:00:00",
            "2025-03-14 19:00:00"
        ],
        [
            "2025-11-30 17:00:00",
            "2025-11-30 20:00:00"
        ]
    ]
}
OUT_STEM="StudyA_Reciprocal_P1_Thermal_DonorTarget_v"

def event_keys():
    return {(case, donor, target) for case, pairs in EVENTS.items() for donor,target in pairs}

def check_register(rows):
    selected=[r for r in rows if r["case"] in EVENTS]
    keys={(r["case"],r["best_donor_hour"],r["event"]) for r in selected}
    if len(selected)!=6 or keys!=event_keys():
        raise ValueError("Signed six thermal event identities changed")
    return {(r["case"],r["event"]):r for r in selected}

def choose_combined(rows, case):
    chosen=[]
    for donor,target in EVENTS[case]:
        options=[r for r in rows if r["case"]==case and r["target_time"]==target
                 and r["pair_4of4_AC_screen_pass"] is True]
        if not options:
            return None
        chosen.append(min(options,key=lambda r:r["fraction"]))
    return chosen

def combined_frame(source, choices):
    frame=source
    prev=None
    for x in sorted(choices,key=lambda r:r["donor_time"]):
        if prev is not None and x["donor_time"]<=prev:
            raise ValueError("Combined donor target windows overlap")
        frame=nov.transfer(frame,x["donor_time"],x["target_time"],x["moved_dc_kw"])
        prev=x["target_time"]
    return frame

def check_energy(frame, item):
    hw=item["case"]["hardware"]
    evidence=nov.check_year(frame,int(hw["battery_modules"]),float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
    for k in ("annual_import_kwh","annual_battery_discharge_dc_kwh","annual_curtail_dc_kwh","year_end_store_kwh"):
        nov.same_total(evidence,item["annual"],k)
    return evidence

def preflight(repo):
    import pandas as pd
    repo=repo.resolve()
    if not (repo/".git").exists():
        raise ValueError("Use actual GitLab checkout")
    frozen=gate.read_json(repo/nov.FROZEN)
    if frozen["status"]!="ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING" or len(frozen["completed_cases"])!=16:
        raise ValueError("Frozen case population changed")
    pilot=gate.read_json(repo/nov.P1/"RUN_MANIFEST.json")
    if pilot["status"]!="P1_TARGETED_36_AC_CASEHOURS_RECORDED_NOT_ANNUAL" or pilot["new_AC_case_hour_evaluations"]!=36 or pilot["infeasible"]!=20:
        raise ValueError("Original P1 receipt changed")
    acpath=repo/nov.P1/"TARGETED_36_AC_CASEHOURS.csv"
    gate.signed_bytes(acpath,pilot["targeted_ac_csv_sha256"])
    ac=gate.read_csv(acpath)
    if len(ac)!=36:
        raise ValueError("Original P1 AC row population changed")
    reg=gate.read_csv(repo/nov.DONOR_REGISTER)
    if len(reg)!=10:
        raise ValueError("Donor ledger changed")
    lookup=check_register(reg)
    closure=gate.read_csv(repo/nov.CLOSURE_REGISTER)
    if len(closure)!=6:
        raise ValueError("Closure register changed")
    gate.signed_bytes(repo/gate.INPUT_MANIFEST,gate.INPUT_SHA)
    pv=nov.load_module(repo/nov.PV_CODE,"verified_reciprocal_thermal_pvbess")
    m,v6,mapping,profiles=pv.secure_context(repo,repo/pv.MANIFEST_REL)
    v6.repo_modules(repo)
    prepared={}
    info=[]
    for name,pairs in EVENTS.items():
        c=frozen["completed_cases"][name]
        tr=name.split("_")[1]; origin=name[:2]; target_assignment=name[-2:]
        if (c["source_case"]!=name or c["AC_verified"] is not False
            or str(c["transformer"])!=tr or c["assignment_for_load"]!=target_assignment
            or c["assignment_for_hardware"]!=origin):
            raise ValueError("Frozen thermal case identity changed")
        ids,trace=pv.source_trace(m,mapping,profiles,target_assignment,tr)
        if ids!=c["target_house_ids"]:
            raise ValueError("Signed household cohort mismatch")
        terr=v6.new_territory(repo,target_assignment,tr,ids,1.0)
        hw=c["hardware"]
        if sorted(x["house"] for x in terr.attachments)!=sorted(ids) or abs(float(terr.trafo["kva"])-float(hw["transformer_kva_assumed_or_evidenced"]))>1e-8:
            raise ValueError("Signed GIS/transformer assumption mismatch")
        path=gate.relative_file(repo,c["target_energy_csv"])
        sig=gate.signed_bytes(path,c["target_energy_sha256"])
        frame=pd.read_csv(gate.required_file(path),parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
        annual=nov.check_year(frame,int(hw["battery_modules"]),float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
        ref=[r for r in closure if r["case"]==name]
        if len(ref)!=1 or abs(float(ref[0]["annual_min_store_kwh"])-annual["min_store_kwh"])>1e-7:
            raise ValueError("Independent source SOC closure ledger changed")
        item={"case":c,"ids":ids,"trace":trace,"territory":terr,"source":frame,"annual":annual,"events":[]}
        for donor,target in pairs:
            d,t=pd.Timestamp(donor),pd.Timestamp(target)
            if any(abs(float(frame.at[x,"demand_kw"])-float(trace.loc[x].sum()))>1e-6 for x in (d,t)):
                raise ValueError("GIS load mismatch at donor/target")
            cap=nov.bound_one_donor(frame,donor,target,hw)
            rr=lookup[(name,target)]
            if rr["source_2025_sha256"]!=c["target_energy_sha256"] or abs(cap-float(rr["max_individual_donor_shift_dc_kw"]))>1e-7 or cap<=0:
                raise ValueError("Signed donor cap mismatch")
            previous=[r for r in ac if r["case"]==name and r["timestamp_lst"]==target]
            if len(previous)!=2 or {float(r["pf"]) for r in previous}!=set(PF):
                raise ValueError("Prior AC target PF mismatch")
            for r in previous:
                if (r["source_sha256"]!=c["target_energy_sha256"] or r["status"]!="CONVERGED"
                    or r["ac_feasible"]!="False" or float(r["max_trafo_pct"])<=100
                    or abs(float(r["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-7
                    or abs(float(r["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-6):
                    raise ValueError("Prior thermal baseline mismatch")
            for fraction in FRACTIONS:
                check_energy(nov.transfer(frame,donor,target,cap*fraction),item)
            item["events"].append({"donor":donor,"target":target,"cap":cap,"baseline":{float(r["pf"]):r for r in previous}})
            info.append({"case":name,"donor":donor,"target":target,"cap_dc_kw":cap,"source_sha256":c["target_energy_sha256"],"signature_mode":sig})
        prepared[name]=item
    return {"status":"SIGNED_P1_THERMAL_SIX_EVENTS_PREFLIGHT_NO_AC","cases":4,"events":6,"candidate_pairs":30,
            "planned_AC_case_hours":120,"new_AC_case_hours":0,"PF":list(PF),"fractions":list(FRACTIONS),
            "length_factor":1.0,"annual_AC_verified":False,"field_EPM_verified":False,"source_events":info},prepared,v6

def figures(out,rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder=out/"figures_diagnostic";folder.mkdir()
    hashes={}
    for field,limit,label in (("min_v_pu",.95,"Minimum voltage [pu]"),("max_trafo_pct",100,"Transformer loading [%]")):
        fig,axes=plt.subplots(3,2,figsize=(12,11),sharex=True)
        for ax,(case,donor,target) in zip(axes.ravel(),sorted(event_keys())):
            for pf in PF:
                for point in ("donor","target"):
                    vals=[r for r in rows if r["case"]==case and r["target_time"]==target and r["pf"]==pf and r["point"]==point and r["status"]=="CONVERGED"]
                    ax.plot([100*r["fraction"] for r in vals],[r[field] for r in vals],marker="o",label=f"{pf} {point}")
            ax.axhline(limit,ls="--",color="black");ax.set_title(case+" / "+target[5:16],fontsize=8);ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(fontsize=7)
        fig.supxlabel("Fraction of isolated DC donor cap [%]");fig.tight_layout()
        path=folder/(field+".png");fig.savefig(path,dpi=150);plt.close(fig);hashes[path.name]=nov.digest(path)
    return hashes

def run_local(repo,receipt,prepared,v6):
    import pandas as pd
    import pandapower as pp
    from run_epm_validation import build_net
    out=next((repo/f"{OUT_STEM}{i}" for i in range(1,100) if not (repo/f"{OUT_STEM}{i}").exists()),None)
    if out is None: raise FileExistsError("No unused result directory")
    out.mkdir();manifest=out/"RUN_MANIFEST.json"
    doc=dict(receipt,status="INCOMPLETE_P1_THERMAL_DO_NOT_CLAIM")
    def save(): manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save();rows=[];pairs=[];combined=[]
    try:
        for name,item in sorted(prepared.items()):
            c=item["case"];hw=c["hardware"];net,meta=build_net(item["territory"],"head")
            if set(meta["loads"])!=set(item["ids"]):raise ValueError("GIS load IDs changed")
            for e in item["events"]:
                donor,target=e["donor"],e["target"]
                for fraction in FRACTIONS:
                    x=e["cap"]*fraction
                    frame=nov.transfer(item["source"],donor,target,x)
                    check_energy(frame,item)
                    accepted=[]
                    for pf in PF:
                        for point,stamp in (("donor",donor),("target",target)):
                            t=pd.Timestamp(stamp)
                            r=v6.solve_ac_hour(net,meta,item["territory"],t,item["trace"].loc[t],pf,float(frame.at[t,"inverter_ac_kw"]),float(hw["inverter_kva"]),float(frame.at[t,"pv_dc_available_kw"]),.25,9,"pvbess",pp)
                            if abs(float(r["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5 or abs(float(r["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-5:
                                raise ValueError("Actual AC P replay mismatch")
                            if fraction==0 and point=="target":
                                prior=e["baseline"][pf]
                                for k in ("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw","pcc_kva","q_selected_kvar"):
                                    if r["status"]!="CONVERGED" or abs(float(r[k])-float(prior[k]))>nov.REPLAY_TOL:
                                        raise ValueError("Original AC regression failed: "+name+"/"+target+"/"+k)
                            accepted.append(r["status"]=="CONVERGED" and r["ac_feasible"] is True)
                            rows.append({"case":name,"donor_time":donor,"target_time":target,"point":point,"pf":pf,"fraction":fraction,"moved_dc_kw":x,"source_sha256":c["target_energy_sha256"],**r})
                            print(f"Thermal AC {len(rows)}/120 | {name} | {point} | {fraction} | PF {pf}",flush=True)
                    pairs.append({"case":name,"donor_time":donor,"target_time":target,"fraction":fraction,"moved_dc_kw":x,"pair_4of4_AC_screen_pass":all(accepted),"passed_local_AC_points":sum(accepted)})
            choices=choose_combined(pairs,name)
            if choices is None:
                combined.append({"case":name,"all_event_pairs_pass":False,"combined_annual_SOC_valid":False,"choices":[]})
            else:
                frame=combined_frame(item["source"],choices)
                metrics=check_energy(frame,item)
                # The chosen disjoint event windows leave each accepted AC P unchanged.
                for q in choices:
                    single=nov.transfer(item["source"],q["donor_time"],q["target_time"],q["moved_dc_kw"])
                    for stamp in (q["donor_time"],q["target_time"]):
                        t=pd.Timestamp(stamp)
                        if abs(float(frame.at[t,"inverter_ac_kw"])-float(single.at[t,"inverter_ac_kw"]))>1e-8:
                            raise ValueError("Combined schedule changed accepted AC P")
                combined.append({"case":name,"all_event_pairs_pass":True,"combined_annual_SOC_valid":True,"choices":choices,"annual_energy_metrics":metrics})
        if len(rows)!=120 or len(pairs)!=30 or len(combined)!=4:raise ValueError("Incomplete thermal experiment")
        a=out/"DONOR_TARGET_120_AC_CASEHOURS.csv";b=out/"PAIR_CANDIDATES_30.csv"
        nov.save_csv(a,rows);nov.save_csv(b,pairs)
        doc.update(status="P1_THERMAL_120_AC_COMPLETE_NOT_ANNUAL",new_AC_case_hours=len(rows),
                   converged=sum(r["status"]=="CONVERGED" for r in rows),
                   infeasible=sum(r["status"]=="CONVERGED" and r["ac_feasible"] is False for r in rows),
                   combined_candidates=combined,outputs_sha256={a.name:nov.digest(a),b.name:nov.digest(b)},
                   diagnostic_png_sha256=figures(out,rows))
        save()
        return doc
    except Exception as exc:
        doc.update(status="INCOMPLETE_P1_THERMAL_DO_NOT_CLAIM",new_AC_case_hours=len(rows),failure=str(exc),traceback=traceback.format_exc())
        save();raise

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."))
    mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument("--preflight-only",action="store_true");mode.add_argument("--run-local",action="store_true")
    args=ap.parse_args(argv);repo=args.repo_root.resolve();receipt,prepared,v6=preflight(repo)
    result=receipt if args.preflight_only else run_local(repo,receipt,prepared,v6)
    print(json.dumps(result,indent=2,allow_nan=False))

if __name__=="__main__":main()
