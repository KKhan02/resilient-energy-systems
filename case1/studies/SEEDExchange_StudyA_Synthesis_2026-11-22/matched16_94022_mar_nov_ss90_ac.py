#!/usr/bin/env python3
"""94022 SS90 combined 28-March and accepted 27-Nov battery/AC validation.

Preflight reads signed archives and recomputes annual chronology; ZERO new AC.
Explicit --run-local runs 20 bounded AC case-hours on the March donor/target,
reuses November's four verified AC rows only after exact P/geometry matching,
and verifies every full-year battery/SOC transition for each combined schedule.
It does not claim full-year AC or a field-verified EPM configuration.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import traceback

import matched16_94022_nov_soc_shift_ac as nov

BASE = nov.BASE
NOV_RUN = Path("StudyA_94022_Nov_DonorTarget_AC_Shift_v1")
MARCH_DONOR = "2025-03-28 17:00:00"
MARCH_TARGET = "2025-03-28 20:00:00"
CASE = "A1_94022_ss90_to_A0"
NOV_FRACTION = 0.98
PF = (0.98, 0.95)
MARCH_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 0.98)
OUT_PREFIX = "StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v"
BASE_TOL = 2e-4


def digest(path):
    return hashlib.sha256(nov.gate.required_file(path).read_bytes()).hexdigest()


def read_signed_csv(repo, folder, name, expected_sha):
    path=repo/folder/name
    mode=nov.gate.signed_bytes(path,expected_sha)
    return nov.gate.read_csv(path),mode


def check_november_archive(rows, frozen_sha, case, t_donor, t_target, energy):
    """Reject any claimed Nov success without exactly four valid saved PF/stage inputs."""
    import pandas as pd
    chosen=[r for r in rows if (r["case"]==case
             and abs(float(r["fraction"])-NOV_FRACTION)<1e-10)]
    if len(chosen)!=4 or {
       (r["point"],float(r["pf"])) for r in chosen
       }!={("donor",0.98),("donor",0.95),("target",0.98),("target",0.95)}:
        raise ValueError("No unique November four-row accepted SS90 archive")
    for r in chosen:
        ts=t_donor if r["point"]=="donor" else t_target
        t=pd.Timestamp(ts)
        if (r["timestamp_lst"]!=ts or r["status"]!="CONVERGED"
            or r["ac_feasible"]!="True"
            or r["original_source_energy_sha256"]!=frozen_sha
            or abs(float(r["inverter_ac_kw"])-float(energy.at[t,"inverter_ac_kw"]))>1e-6
            or abs(float(r["gross_demand_kw"])-float(energy.at[t,"demand_kw"]))>1e-6):
            raise ValueError("November accepted row is not aligned with combined source P and demand")
    return chosen


def prepare(repo):
    import pandas as pd
    repo=repo.resolve()
    original_receipt,prepared,v6=nov.preflight(repo)
    c=prepared[CASE]
    hw=c["case"]["hardware"]
    original=c["source"]
    # Earlier November study is immutable signed evidence.
    mj=nov.gate.read_json(repo/NOV_RUN/"RUN_MANIFEST.json")
    if (mj.get("status")!="94022_NOV_TWO_PAIR_AC_SWEEP_COMPLETE_NOT_ANNUAL"
        or mj.get("actual_new_case_hour_AC_evaluations")!=40
        or mj.get("local_pair_screen_pass_candidates")!=1
        or mj.get("annual_AC_verified") is not False):
        raise ValueError("November signed result status changed")
    novrows,modenov=read_signed_csv(repo,NOV_RUN,"DONOR_TARGET_AC_40_CASEHOURS.csv",mj["ac_csv_sha256"])
    novcases,modecases=read_signed_csv(repo,NOV_RUN,"PAIR_CANDIDATES_10.csv",mj["candidate_summary_sha256"])
    if len(novrows)!=40 or len(novcases)!=10:
        raise ValueError("Original November archive row count changed")
    winners=[r for r in novcases if r["case"]==CASE and
        abs(float(r["fraction"])-NOV_FRACTION)<1e-10 and
        r["pair_4of4_AC_screen_pass"]=="True" and r["annual_soc_and_energy_valid"]=="True"]
    if len(winners)!=1 or abs(float(winners[0]["added_target_ac_kw"]) -
                             c["upper_dc"]*NOV_FRACTION*nov.ETA_INV)>1e-6:
        raise ValueError("November SS90 98pct result no longer verified")
    oldnov=nov.transfer(original,c["donor"],nov.TARGET,c["upper_dc"]*NOV_FRACTION)
    oldnovstats=nov.check_year(oldnov,int(hw["battery_modules"]),
                               float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
    for field in ("annual_import_kwh","annual_battery_discharge_dc_kwh","annual_curtail_dc_kwh"):
        nov.same_total(oldnovstats,c["annual"],field)
    novaccepted=check_november_archive(
        novrows,c["case"]["target_energy_sha256"],CASE,c["donor"],nov.TARGET,oldnov)
    # March source only. Frozen P1 36-case-hour AC baseline and 10-event donor ledger.
    p1_manifest=nov.gate.read_json(repo/nov.P1/"RUN_MANIFEST.json")
    p1=nov.gate.read_csv(repo/nov.P1/"TARGETED_36_AC_CASEHOURS.csv")
    originalmarch=[r for r in p1 if r["case"]==CASE and r["timestamp_lst"]==MARCH_TARGET]
    if (len(originalmarch)!=2 or {float(r["pf"]) for r in originalmarch}!=set(PF)
        or any(r["status"]!="CONVERGED" or r["ac_feasible"]!="False"
               or r["source_sha256"]!=c["case"]["target_energy_sha256"] for r in originalmarch)):
        raise ValueError("Original March P1 failure rows changed")
    for r in originalmarch:
        t=pd.Timestamp(MARCH_TARGET)
        if (abs(float(r["inverter_ac_kw"])-float(original.at[t,"inverter_ac_kw"]))>1e-7
            or abs(float(r["gross_demand_kw"])-float(original.at[t,"demand_kw"]))>1e-6):
            raise ValueError("March P1 target from different source dispatch")
    ledger=nov.gate.read_csv(repo/nov.DONOR_REGISTER)
    entry=[r for r in ledger if r["case"]==CASE and r["event"]==MARCH_TARGET]
    if len(entry)!=1 or entry[0]["best_donor_hour"]!=MARCH_DONOR:
        raise ValueError("March 17:00 donor source-locked roster changed")
    upper=nov.bound_one_donor(original,MARCH_DONOR,MARCH_TARGET,hw,pf=.95)
    if (abs(float(entry[0]["max_individual_donor_shift_dc_kw"])-upper)>1e-7
        or upper<=0 or upper>float(original.at[pd.Timestamp(MARCH_DONOR),"battery_discharge_dc_kw"])+1e-7):
        raise ValueError("March donor DC limit changed")
    if (oldnov.loc[pd.Timestamp(MARCH_DONOR):pd.Timestamp(MARCH_TARGET)]
        ["inverter_ac_kw"].sub(original.loc[
         pd.Timestamp(MARCH_DONOR):pd.Timestamp(MARCH_TARGET)]["inverter_ac_kw"])
        .abs().max()>1e-8):
        raise ValueError("November source shift changed March donor/target interval")
    receipt={
       "status":"SIGNED_94022_SS90_MARCH_PLUS_NOV_PREFLIGHT_NO_SOLVES",
       "case":CASE,"source_target_assignment":"A0",
       "original_hardware_assignment":"A1","households":10,
       "march_donor":MARCH_DONOR,"march_target":MARCH_TARGET,
       "march_upper_dc_kw":upper,
       "march_upper_added_ac_kw":upper*nov.ETA_INV,
       "march_fractions":list(MARCH_FRACTIONS),
       "nov_donor":c["donor"],"nov_target":nov.TARGET,
       "nov_fixed_fraction":NOV_FRACTION,
       "nov_fixed_shift_dc_kw":c["upper_dc"]*NOV_FRACTION,
       "nov_fixed_extra_inverter_ac_kw":c["upper_dc"]*NOV_FRACTION*nov.ETA_INV,
       "nov_existing_ac_evaluations_reused":len(novaccepted),
       "nov_source_ac_csv_signature_mode":modenov,
       "nov_source_candidate_csv_signature_mode":modecases,
       "march_source_p1_manifest_csv_sha256":p1_manifest["targeted_ac_csv_sha256"],
       "original_signed_annual_energy_sha256":c["case"]["target_energy_sha256"],
       "original_source_energy_signature_mode":next(
         x["source_signature_mode"] for x in original_receipt["cases"] if x["case"]==CASE),
       "PF":list(PF),"service_factor":1.0,
       "main_voltage_min_pu":0.95,"main_voltage_max_pu":1.05,
       "battery_physical_min_soc_model":0.20,
       "original_nov_case_hour_AC_pass_reused_only_if_same_P_and_GIS":True,
       "annual_SOC_reaudited":True,"annual_AC_verified":False,
       "field_EPM_verified":False,
       "original_hardware_modified":False,
       "new_pandapower_AC_case_hour_evaluations":0,
       "planned_new_pandapower_AC_case_hour_evaluations":len(MARCH_FRACTIONS)*len(PF)*2,
       "interpretation":"Combined March-November two-event chronological source validation, not full-year AC",
    }
    return receipt,{"source":original,"oldnov":oldnov,
                    "original":c,"hw":hw,"p1march":originalmarch,
                    "novarchive":novaccepted,"march_max_dc":upper},v6


def validate_combined(item,amount):
    """Apply March source transfer atop Nov accepted shift, close all 8760h."""
    from pandas import Timestamp
    original=item["original"]
    hw=item["hw"]
    frame=nov.transfer(item["oldnov"],MARCH_DONOR,MARCH_TARGET,float(amount))
    stats=nov.check_year(frame,int(hw["battery_modules"]),
                         float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
    for key in ("annual_import_kwh","annual_battery_discharge_dc_kwh","annual_curtail_dc_kwh"):
        nov.same_total(stats,original["annual"],key)
    nov.same_total(stats,nov.check_year(item["oldnov"],int(hw["battery_modules"]),
             float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"])),"annual_import_kwh")
    if abs(stats["year_end_store_kwh"]-original["annual"]["year_end_store_kwh"])>1e-6:
        raise ValueError("Annual cyclic final Store energy changed")
    # The two daily event windows are independent. No edited November power may
    # be silently changed while the accepted November AC sample is reused.
    for r in item["novarchive"]:
        t=Timestamp(r["timestamp_lst"])
        if (abs(float(r["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-6
            or abs(float(r["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-6):
            raise ValueError("March shift invalidates November accepted AC reuse")
    return frame,stats


def write_csv(path,rows):
    cols=sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)


def plot_figures(out,rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder=out/"figures_diagnostic"
    folder.mkdir()
    hashes={}
    for y,limit,filename,units in (
       ("min_v_pu",0.95,"march_min_voltage_vs_shift.png","Minimum house voltage [pu]"),
       ("max_trafo_pct",100.,"march_trafo_loading_vs_shift.png","Transformer loading [%]")):
        fig,ax=plt.subplots(figsize=(9,5))
        for pf in PF:
            for stage in ("donor","target"):
                subset=[r for r in rows if r["point"]==stage and float(r["pf"])==pf]
                ax.plot([r["added_march_target_ac_kw"] for r in subset],
                        [r[y] for r in subset],marker="o",label=f"{stage} PF {pf:.2f}")
        ax.axhline(limit,color="black",linestyle="--",label="Main research limit")
        ax.grid(alpha=.3);ax.legend()
        ax.set_title("94022 A0 ten-house SS90 | 28 March 2025 | Nov correction retained")
        ax.set_xlabel("Additional March 20:00 inverter AC P [kW]")
        ax.set_ylabel(units)
        fig.tight_layout()
        f=folder/filename;fig.savefig(f,dpi=160);plt.close(fig)
        hashes[filename]=digest(f)
    return hashes


def run_local(repo,receipt,item,v6):
    import pandas as pd
    import pandapower as pp
    from run_epm_validation import build_net
    repo=repo.resolve()
    out=next((repo/f"{OUT_PREFIX}{i}" for i in range(1,101)
              if not (repo/f"{OUT_PREFIX}{i}").exists()),None)
    if out is None:
        raise FileExistsError("No free versioned output directory")
    out.mkdir()
    meta=dict(receipt,status="INCOMPLETE_94022_MARCH_NOV_DO_NOT_CLAIM")
    manifest=out/"RUN_MANIFEST.json"
    def save():manifest.write_text(json.dumps(meta,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save()
    acrows,candidates=[],[]
    try:
        c=item["original"];hw=item["hw"]
        net,nm=build_net(c["territory"],"head")
        if set(nm["loads"])!=set(c["ids"]):
            raise ValueError("Signed GIS 94022 household nodes changed")
        for frac in MARCH_FRACTIONS:
            x=float(item["march_max_dc"])*frac
            frame,energy=validate_combined(item,x)
            if any(abs(float(frame.at[pd.Timestamp(t),"inverter_ac_kw"])-
                       float(item["oldnov"].at[pd.Timestamp(t),"inverter_ac_kw"]))>1e-6
                   for t in (c["donor"],nov.TARGET)):
                raise ValueError("March candidate unexpectedly modified November P")
            pass4=[]
            for pf in PF:
                for stage,time in (("donor",MARCH_DONOR),("target",MARCH_TARGET)):
                    t=pd.Timestamp(time)
                    r=v6.solve_ac_hour(net,nm,c["territory"],t,c["trace"].loc[t],
                      pf,float(frame.at[t,"inverter_ac_kw"]),float(hw["inverter_kva"]),
                      float(frame.at[t,"pv_dc_available_kw"]),0.25,9,"pvbess",pp)
                    if (abs(float(r["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5
                       or abs(float(r["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-5):
                        raise ValueError("March AC solver did not use exact signed candidate P")
                    if frac==0 and stage=="target":
                        prior=next(r0 for r0 in item["p1march"] if float(r0["pf"])==pf)
                        for key in ("min_v_pu","max_v_pu","max_trafo_pct",
                                    "max_line_pct","loss_kw","pcc_kva","q_selected_kvar"):
                            if r["status"]!="CONVERGED" or abs(float(r[key])-float(prior[key]))>BASE_TOL:
                                raise ValueError("March P1 archived original baseline mismatch: "+key)
                    valid=r["status"]=="CONVERGED" and r["ac_feasible"] is True
                    pass4.append(valid)
                    acrows.append({"case":CASE,"tier":"ss90","fraction":frac,
                      "march_donor":MARCH_DONOR,"march_target":MARCH_TARGET,
                      "nov_accepted_fraction":NOV_FRACTION,
                      "point":stage,"pf":pf,"shifted_march_dc_kw":x,
                      "added_march_target_ac_kw":x*nov.ETA_INV,
                      "annual_2025_combined_SOC_valid":True,
                      "original_energy_sha256":c["case"]["target_energy_sha256"],
                      **r})
                    print(f"94022 March+Nov {len(acrows)}/20 | fraction {frac:.2f}"
                          f" | {stage} | PF {pf:.2f}",flush=True)
            candidates.append({"case":CASE,"fraction":frac,
              "march_shift_dc_kw":x,"added_march_target_ac_kw":x*nov.ETA_INV,
              "annual_2025_combined_SOC_valid":True,
              "march_four_ac_pass":all(pass4),
              "march_four_ac_pass_count":sum(pass4),
              "nov_archived_four_ac_pass":len(item["novarchive"])==4,
              "two_dates_eight_of_eight_local_ac_pass":all(pass4) and len(item["novarchive"])==4,
              "changed_2025_hour_count":len([i for i in range(len(frame)) if (
               abs(float(frame.iloc[i]["inverter_ac_kw"])-float(item["source"].iloc[i]["inverter_ac_kw"]))>1e-6)]),
              "annual_import_kwh":energy["annual_import_kwh"],
              "annual_AC_verified":False})
        if len(acrows)!=20 or len(candidates)!=5:
            raise ValueError("Incomplete signed March source-local AC experiment")
        meta.update(status="94022_SS90_MARCH_PLUS_NOV_TWO_EVENT_LOCAL_AC_20_COMPLETE_NOT_ANNUAL",
          new_pandapower_AC_case_hour_evaluations=20,
          March_AC_converged=sum(r["status"]=="CONVERGED" for r in acrows),
          March_AC_infeasible=sum(r["ac_feasible"] is False for r in acrows),
          candidate_annual_SOC_valid_count=5,
          March_pair_pass_candidates=sum(x["march_four_ac_pass"] for x in candidates),
          combined_two_event_eight_of_eight_pass_candidates=sum(
                x["two_dates_eight_of_eight_local_ac_pass"] for x in candidates),
          candidate_summary=candidates,
          annual_AC_verified=False,field_EPM_verified=False)
        filename=out/"MARCH_DONOR_TARGET_20_AC_CASEHOURS.csv"
        write_csv(filename,acrows);meta["march_ac_csv_sha256"]=digest(filename)
        filename2=out/"MARCH_CANDIDATES_5.csv"
        write_csv(filename2,candidates);meta["candidate_csv_sha256"]=digest(filename2)
        meta["diagnostic_png_sha256"]=plot_figures(out,acrows)
        save()
        return {"status":meta["status"],"out":str(out),"AC_case_hours":20,
           "march_pair_pass":meta["March_pair_pass_candidates"],
           "both_dates_8of8_local_pass":meta["combined_two_event_eight_of_eight_pass_candidates"],
           "annual_AC_verified":False}
    except Exception as exc:
        meta.update(status="INCOMPLETE_94022_MARCH_NOV_DO_NOT_CLAIM",
          new_pandapower_AC_case_hour_evaluations=len(acrows),
          error={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()})
        if acrows:write_csv(out/"PARTIAL_AC_DO_NOT_INTERPRET.csv",acrows)
        save()
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--preflight-only",action="store_true")
    action.add_argument("--run-local",action="store_true")
    args=parser.parse_args(argv)
    receipt,data,v6=prepare(args.repo_root)
    result=receipt if args.preflight_only else run_local(args.repo_root,receipt,data,v6)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
