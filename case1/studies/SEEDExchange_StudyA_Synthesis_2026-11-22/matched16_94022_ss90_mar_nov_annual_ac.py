#!/usr/bin/env python3
"""2025 AC baseline + four-hour corrected SS90 A0/94022 annual comparison.

ONE source-locked annual 8760-hour original AC evaluation per selected PF,
then EXACTLY four changed-P hours are re-evaluated with same stateless solver.
Unchanged 8756 hours inherit the exact original annual hourly AC results.
Never classify a previous 8/8 sampled pair result as annual AC validation.
No PyPSA reoptimization and no change to original signed files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import traceback

import numpy as np
import pandas as pd

import matched16_94022_mar_nov_ss90_ac as combined
import matched16_94022_nov_soc_shift_ac as nov

HERE = Path("case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22")
MARCH_RESULT = Path("StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v1")
NOV_RESULT = Path("StudyA_94022_Nov_DonorTarget_AC_Shift_v1")
MARCH_FRACTION = 0.50
NOV_FRACTION = 0.98
PF_OPTIONS = (0.98, 0.95)
HOURS = 8760
STATUS_PREFIX = "ANNUAL_94022_SS90_MARCH50_NOV98_PF"
MIN_V = 0.95
MAX_V = 1.05
MATCH_TOL = 3e-4
BASELINE_POINTS = (
    (combined.MARCH_DONOR, MARCH_RESULT, 0.0),
    (combined.MARCH_TARGET, MARCH_RESULT, 0.0),
    (nov.CASES[combined.CASE], NOV_RESULT, 0.0),
    (nov.TARGET, NOV_RESULT, 0.0),
)
CHANGED = tuple(sorted((
    combined.MARCH_DONOR, combined.MARCH_TARGET,
    nov.CASES[combined.CASE], nov.TARGET,
)))


def sha(path):
    return hashlib.sha256(nov.gate.required_file(path).read_bytes()).hexdigest()


def check_source_stateless(v6):
    """Fail closed if prior hourly-state-independence source assumption changes."""
    import inspect
    body=inspect.getsource(v6.solve_ac_hour)
    if (body.count("init='flat'") < 2
        or "inject_individual_loads(net,meta,loads,pf,root_factor)" not in body
        or "net.sgen.at[meta['inv'],'q_mvar']=0." not in body
        or "pp.runpp(" not in body):
        raise ValueError("AC solver's reset/flat independent hourly contract changed")
    return True


def extract_archived(repo, folder, manifest_key, name):
    manifest=nov.gate.read_json(repo/folder/"RUN_MANIFEST.json")
    if manifest.get("annual_AC_verified") is not False:
        raise ValueError("Archived prior sample incorrectly claims annual AC")
    path=repo/folder/name
    representation=nov.gate.signed_bytes(path,manifest[manifest_key])
    return nov.gate.read_csv(path),manifest,representation


def unique_archived(samples, case, hour, pf, fraction, stage):
    """Select the exact hardware case before matching the archived AC point.

    The November AC CSV contains both minimum-cost and SS90 case records at
    the same target timestamp, PF and transfer fraction. Without the case
    field those valid records collide or could be misattributed.
    """
    if not isinstance(case, str) or not case:
        raise ValueError("An explicit archived hardware case is required")
    selected=[r for r in samples
              if r["case"]==case
              and r["timestamp_lst"]==hour and r["point"]==stage
              and abs(float(r["pf"])-pf)<1e-9
              and abs(float(r["fraction"])-fraction)<1e-9]
    if len(selected)!=1:
        raise ValueError("Missing/duplicate archived local sample: "
                         +str((case,hour,pf,fraction,stage)))
    return selected[0]


def exact_ac_regression(actual, expected, context):
    if (actual["status"]!=expected["status"]
        or str(actual["ac_feasible"]).lower()!=str(expected["ac_feasible"]).lower()
        or abs(float(actual["inverter_ac_kw"])-float(expected["inverter_ac_kw"]))>1e-5):
        raise ValueError(context + ": AC P/status/feasible changed")
    for key in ("gross_demand_kw","min_v_pu","max_v_pu","max_trafo_pct",
                "max_line_pct","pcc_kva","loss_kw","q_selected_kvar"):
        if abs(float(actual[key])-float(expected[key]))>MATCH_TOL:
            raise ValueError(context + ": archived AC quantity changed: "+key)


def source_pilot_preflight(repo, pf):
    if pf not in PF_OPTIONS:
        raise ValueError("Only archived source PF 0.98 and 0.95 may run")
    repo=repo.resolve()
    receipt,item,v6=combined.prepare(repo)
    if receipt.get("status")!="SIGNED_94022_SS90_MARCH_PLUS_NOV_PREFLIGHT_NO_SOLVES":
        raise ValueError("Combined-source preflight not original")
    if not check_source_stateless(v6):
        raise ValueError("No independent source AC solver")
    mrows,mmanifest,mformat=extract_archived(
        repo,MARCH_RESULT,"march_ac_csv_sha256","MARCH_DONOR_TARGET_20_AC_CASEHOURS.csv")
    crows,cmanifest,cformat=extract_archived(
        repo,MARCH_RESULT,"candidate_csv_sha256","MARCH_CANDIDATES_5.csv")
    nrows,nmanifest,nformat=extract_archived(
        repo,NOV_RESULT,"ac_csv_sha256","DONOR_TARGET_AC_40_CASEHOURS.csv")
    if (mmanifest.get("status")!="94022_SS90_MARCH_PLUS_NOV_TWO_EVENT_LOCAL_AC_20_COMPLETE_NOT_ANNUAL"
        or mmanifest.get("new_pandapower_AC_case_hour_evaluations")!=20
        or mmanifest.get("combined_two_event_eight_of_eight_pass_candidates")!=3
        or nmanifest.get("local_pair_screen_pass_candidates")!=1
        or len(mrows)!=20 or len(crows)!=5 or len(nrows)!=40):
        raise ValueError("March/November source sample receipt changed")
    winning=[r for r in crows if (r["case"]==combined.CASE
             and abs(float(r["fraction"])-MARCH_FRACTION)<1e-9
             and r["two_dates_eight_of_eight_local_ac_pass"]=="True")]
    if len(winning)!=1:
        raise ValueError("No unique March .50 candidate passing eight archived points")
    frame, annual_stats=combined.validate_combined(
        item, item["march_max_dc"]*MARCH_FRACTION)
    source=item["source"]
    if not frame.index.equals(source.index) or len(frame)!=HOURS:
        raise ValueError("Annual original/corrected timebase changed")
    altered=[str(t) for t in frame.index[
       (frame["inverter_ac_kw"]-source["inverter_ac_kw"]).abs()>1e-7]]
    if altered!=list(CHANGED):
        raise ValueError("Expected exactly four source P changes, got "+str(altered))
    c=item["original"];ids=c["ids"]
    if len(ids)!=10 or c["case"]["transformer"]!="94022":
        raise ValueError("Wrong ten-house 94022 GIS population")
    if (abs(float(annual_stats["annual_import_kwh"])-4196.606410684601)>1e-5
        or annual_stats["min_store_kwh"]<1.374-1e-6):
        raise ValueError("Unexpected signed combined-year annual import or physical store floor")
    # Verify both accepted PF sample sets use exactly the resulting frame P.
    for stage,stamp in (("donor",combined.MARCH_DONOR),
                        ("target",combined.MARCH_TARGET)):
        expected=unique_archived(mrows,combined.CASE,stamp,pf,MARCH_FRACTION,stage)
        if (expected["ac_feasible"]!="True"
            or abs(float(expected["inverter_ac_kw"])-
                   float(frame.at[pd.Timestamp(stamp),"inverter_ac_kw"]))>1e-6):
            raise ValueError("March accepted AC P changed")
    for stage,stamp in (("donor",nov.CASES[combined.CASE]),
                        ("target",nov.TARGET)):
        expected=unique_archived(nrows,combined.CASE,stamp,pf,NOV_FRACTION,stage)
        if (expected["ac_feasible"]!="True"
            or abs(float(expected["inverter_ac_kw"])-
                   float(frame.at[pd.Timestamp(stamp),"inverter_ac_kw"]))>1e-6):
            raise ValueError("November accepted AC P changed")
    evidence={
      "status":"SIGNED_94022_SS90_MAR50_NOV98_ANNUAL_AC_PREFLIGHT_ZERO_NEW_AC",
      "pf":pf,"year":2025,"original_source_hours":HOURS,
      "unique_corrected_inverter_P_hours":len(altered),"altered_timestamps":altered,
      "original_energy_csv_sha256":c["case"]["target_energy_sha256"],
      "source_case":combined.CASE,
      "assignment":"A0","transformer":"94022","households":10,
      "assumed_transformer_kva":5.,
      "battery_modules":6,"min_physical_battery_SOC_model":0.20,
      "march_source_fraction":MARCH_FRACTION,
      "nov_source_fraction":NOV_FRACTION,
      "fixed_2025_combined_annual_energy_import_kwh":annual_stats["annual_import_kwh"],
      "fixed_2025_combined_annual_curtailment_dc_kwh":annual_stats["annual_curtail_dc_kwh"],
      "annual_battery_DC_discharge_kwh":annual_stats["annual_battery_discharge_dc_kwh"],
      "march_archive_AC_sha256":mmanifest["march_ac_csv_sha256"],
      "march_archive_signature_mode":mformat,
      "march_archive_candidate_sha256":cmanifest["candidate_csv_sha256"],
      "march_archive_candidate_signature_mode":cformat,
      "nov_archive_AC_sha256":nmanifest["ac_csv_sha256"],
      "nov_archive_signature_mode":nformat,
      "planned_source_original_annual_AC_case_hours":HOURS,
      "planned_extra_corrected_changed_AC_case_hours":len(CHANGED),
      "new_original_AC_case_hours":0,
      "new_corrected_AC_case_hours":0,
      "AC_solver_state_independent_flat_reset_source_confirmed":True,
      "annual_main_screen_0_95_1_05":True,
      "annual_AC_verified":False,"field_EPM_verified":False,
      "service_length_factor":1.0,"q_day_ratio":0.25,
      "interpretation":"No numerical annual AC executed in preflight; source-only fixed schedule"
    }
    return evidence,item,v6,source,frame,mrows,nrows


def annual_summary(records):
    if len(records)!=HOURS or len(set(x["timestamp_lst"] for x in records))!=HOURS:
        raise ValueError("Incomplete 2025 annual AC records")
    converged=[r for r in records if r["status"]=="CONVERGED"]
    failing=[r for r in converged if r["ac_feasible"] is False]
    metrics=lambda field,func:func(float(x[field]) for x in converged) if converged else None
    all_ok=len(converged)==HOURS and len(failing)==0
    return {
      "case_hour_records":len(records),
      "converged_hours":len(converged),
      "nonconverged_hours":HOURS-len(converged),
      "nonconverged_first_25":[r["timestamp_lst"] for r in records if r["status"]!="CONVERGED"][:25],
      "main_band_infeasible_hours":len(failing),
      "main_band_feasible_hours":len(converged)-len(failing),
      "violated_timestamps_first_100":[r["timestamp_lst"] for r in failing][:100],
      "undervoltage_under_095_hours":sum(int(r["voltage_below_095"]) for r in converged),
      "overvoltage_above_105_hours":sum(int(r["voltage_above_105"]) for r in converged),
      "over_transformer_100_hours":sum(int(r["trafo_over_100"]) for r in converged),
      "over_line_100_hours":sum(int(r["line_over_100"]) for r in converged),
      "optional_under_097_hours":sum(int(r["voltage_below_097"]) for r in converged),
      "optional_above_103_hours":sum(int(r["voltage_above_103"]) for r in converged),
      "minimum_voltage_pu":metrics("min_v_pu",min),
      "maximum_voltage_pu":metrics("max_v_pu",max),
      "maximum_trafo_loading_pct":metrics("max_trafo_pct",max),
      "maximum_line_loading_pct":metrics("max_line_pct",max),
      "annual_ac_network_losses_kwh":sum(float(r["loss_kw"]) for r in converged)
              if len(converged)==HOURS else None,
      "annual_losses_complete":len(converged)==HOURS,
      "all_2025_model_main_band_pass":all_ok,
      "field_evidence_certified":False,
      "source_grid_import_kwh_recomputed_loss_adjusted":False,
    }


def save_csv(path,records):
    import csv
    if not records: return
    header=sorted(set().union(*(r.keys() for r in records)))
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=header)
        w.writeheader();w.writerows(records)


def figures(base,corrected,out,pf):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder=out/"figures_diagnostic"
    folder.mkdir(exist_ok=False)
    stamps=pd.date_range("2025-01-01",periods=HOURS,freq="h")
    original_v=np.array([float(x["min_v_pu"]) if x["status"]=="CONVERGED" else np.nan
                         for x in base])
    corrected_v=np.array([float(x["min_v_pu"]) if x["status"]=="CONVERGED" else np.nan
                          for x in corrected])
    paths={}
    fig,ax=plt.subplots(figsize=(12,5.5))
    ax.plot(stamps,original_v,label="Original fixed-hardware annual P",lw=.6,alpha=.65)
    ax.plot(stamps,corrected_v,label="March50 + November98 shifted P",lw=.6,alpha=.7)
    ax.axhline(.95,c="black",ls="--",lw=.8,label="Research min 0.95 pu")
    for t in CHANGED:ax.axvline(pd.Timestamp(t),c="gray",lw=.5,ls=":")
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax.set(title=f"94022 A0 ten houses | 2025 min voltage | PF {pf}",
           xlabel="2025 model local time",ylabel="Minimum house voltage [pu]")
    fig.autofmt_xdate();fig.tight_layout()
    path=folder/"annual_min_voltage_comparison.png";fig.savefig(path,dpi=160);plt.close(fig)
    paths[path.name]=sha(path)
    fig,ax=plt.subplots(figsize=(10,5))
    changed=[i for i,t in enumerate(stamps) if str(t) in CHANGED]
    x=np.arange(len(changed))
    ax.bar(x-.18,original_v[changed],.35,label="Original")
    ax.bar(x+.18,corrected_v[changed],.35,label="Corrected")
    ax.axhline(.95,c="black",lw=.8,ls="--",label="0.95 pu")
    ax.set_xticks(x,[str(stamps[i])[5:16] for i in changed],rotation=20)
    ax.set_ylim(.94,max(1.0,np.nanmax(corrected_v[changed])+.01))
    ax.set(ylabel="Minimum house voltage [pu]",title=f"Four modified AC hours, PF {pf}")
    ax.grid(axis="y",alpha=.2);ax.legend()
    fig.tight_layout()
    path=folder/"changed_four_hours_voltage.png";fig.savefig(path,dpi=160);plt.close(fig)
    paths[path.name]=sha(path)
    return paths


def run(repo,pf,receipt,item,v6,original,modified,march_rows,nov_rows):
    import pandapower as pp
    from run_epm_validation import build_net
    repo=repo.resolve()
    suffix=f"PF{int(round(pf*100))}"
    stem=f"StudyA_94022_SS90_MarNov_AnnualAC_{suffix}_v"
    out=next((repo/f"{stem}{i}" for i in range(1,101)
              if not (repo/f"{stem}{i}").exists()),None)
    if out is None: raise FileExistsError("No unused annual AC output folder")
    out.mkdir()
    report=dict(receipt,status="INCOMPLETE_94022_ANNUAL_AC_DO_NOT_CLAIM",
                output_folder=str(out),pf=pf,new_original_AC_case_hours=0,
                new_corrected_AC_case_hours=0)
    manifest=out/"RUN_MANIFEST.json"
    def save():manifest.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save()
    baseline=[]
    try:
        c=item["original"];hw=item["hw"];trace=c["trace"]
        territory=c["territory"]
        net,meta=build_net(territory,"head")
        if set(meta["loads"])!=set(c["ids"]) or not trace.index.equals(original.index):
            raise ValueError("Original household profile or GIS node path changed")
        if list(map(str,original.index)) != [str(t) for t in pd.date_range("2025-01-01",periods=HOURS,freq="h")]:
            raise ValueError("2025 model source timebase changed")
        for i,t in enumerate(original.index):
            row=original.iloc[i]
            value=v6.solve_ac_hour(net,meta,territory,t,trace.iloc[i],pf,
                    float(row.inverter_ac_kw),float(hw["inverter_kva"]),
                    float(row.pv_dc_available_kw),0.25,9,"pvbess",pp)
            if (abs(float(value["gross_demand_kw"])-float(row.demand_kw))>1e-5
                or abs(float(value["inverter_ac_kw"])-float(row.inverter_ac_kw))>1e-5):
                raise ValueError("Full 8760 original AC did not use signed per-home demand and P")
            baseline.append({"scenario":"original","source_grid_import_kw":float(row.grid_import_kw),
                             "original_energy_sha256":receipt["original_energy_csv_sha256"],
                             **value})
            stamp=str(t)
            if stamp in CHANGED:
                stage="donor" if t.hour==17 else "target"
                old=unique_archived(march_rows if t.month==3 else nov_rows,
                      combined.CASE,stamp,pf,0.0,stage)
                exact_ac_regression(value,old,"Signed baseline "+stamp)
            if (i+1)%500==0:
                report["new_original_AC_case_hours"]=i+1
                save_csv(out/"PARTIAL_BASELINE_AC_CHECKPOINT_DO_NOT_CLAIM.csv",baseline)
                save()
                print(f"94022 source original AC PF{pf} {i+1}/{HOURS}",flush=True)
        report["new_original_AC_case_hours"]=HOURS
        original_summary=annual_summary(baseline)
        save_csv(out/"ORIGINAL_2025_8760_AC.csv",baseline)
        save()
        new_rows=[dict(r) for r in baseline]
        changed_metrics=[]
        for stamp in CHANGED:
            t=pd.Timestamp(stamp)
            i=original.index.get_loc(t)
            src=modified.iloc[i]
            value=v6.solve_ac_hour(net,meta,territory,t,trace.iloc[i],pf,
                    float(src.inverter_ac_kw),float(hw["inverter_kva"]),
                    float(src.pv_dc_available_kw),0.25,9,"pvbess",pp)
            expected=unique_archived(march_rows if t.month==3 else nov_rows,
                  combined.CASE,stamp,pf,MARCH_FRACTION if t.month==3 else NOV_FRACTION,
                  "donor" if t.hour==17 else "target")
            exact_ac_regression(value,expected,"Corrected archived "+stamp)
            changed_metrics.append({
               "timestamp_lst":stamp,"pf":pf,
               "original_P_kw":float(original.iloc[i].inverter_ac_kw),
               "corrected_P_kw":float(src.inverter_ac_kw),
               "original_voltage_pu":float(baseline[i]["min_v_pu"]),
               "corrected_voltage_pu":float(value["min_v_pu"]),
               "original_transformer_pct":float(baseline[i]["max_trafo_pct"]),
               "corrected_transformer_pct":float(value["max_trafo_pct"]),
               "original_loss_kw":float(baseline[i]["loss_kw"]),
               "corrected_loss_kw":float(value["loss_kw"]),
               "loss_delta_kw":float(value["loss_kw"])-float(baseline[i]["loss_kw"]),
               "archived_fraction":MARCH_FRACTION if t.month==3 else NOV_FRACTION,
               "source_original_energy_sha256":receipt["original_energy_csv_sha256"]
            })
            new_rows[i]={**baseline[i],
                        "scenario":"corrected_four_hour_redispatch",
                        "source_grid_import_kw":float(src.grid_import_kw),
                        **value}
            report["new_corrected_AC_case_hours"]=len(changed_metrics)
            save()
        if len(changed_metrics)!=4 or len(new_rows)!=HOURS:
            raise ValueError("Incorrect annual corrected AC source sample count")
        corrected_summary=annual_summary(new_rows)
        save_csv(out/"CORRECTED_2025_8760_AC.csv",new_rows)
        save_csv(out/"FOUR_CHANGED_AC_HOURS.csv",changed_metrics)
        if original_summary["annual_losses_complete"] and corrected_summary["annual_losses_complete"]:
            changed_loss_sum=sum(float(x["loss_delta_kw"]) for x in changed_metrics)
            full_year_loss_diff=(
                float(corrected_summary["annual_ac_network_losses_kwh"])
                -float(original_summary["annual_ac_network_losses_kwh"]))
            if abs(changed_loss_sum-full_year_loss_diff)>1e-5:
                raise ValueError("Annual AC losses delta does not close four-hour substitutions")
        plot_sha=figures(baseline,new_rows,out,pf)
        files={name:sha(out/name) for name in (
          "ORIGINAL_2025_8760_AC.csv","CORRECTED_2025_8760_AC.csv",
          "FOUR_CHANGED_AC_HOURS.csv")}
        if original_summary["nonconverged_hours"] or corrected_summary["nonconverged_hours"]:
            status=f"{STATUS_PREFIX}{int(pf*100)}_NONCONVERGED_DO_NOT_CLAIM"
        elif corrected_summary["all_2025_model_main_band_pass"]:
            status=f"{STATUS_PREFIX}{int(pf*100)}_COMPLETE_MAIN_BAND_PASS"
        else:
            status=f"{STATUS_PREFIX}{int(pf*100)}_COMPLETE_VIOLATIONS_RECORDED"
        report.update(status=status,annual_original_AC_scanned=True,
           annual_corrected_AC_reconstructed_from_exact_original_plus_4_resolves=True,
           annual_corrected_AC_scanned_or_validly_reused=True,
           source_stateless_independence_preserved=True,
           corrected_source_changed_hours=4,
           original_annual_summary=original_summary,corrected_annual_summary=corrected_summary,
           annual_ac_loss_delta_kwh=(
             corrected_summary["annual_ac_network_losses_kwh"]
             -original_summary["annual_ac_network_losses_kwh"]
             if original_summary["annual_losses_complete"] and corrected_summary["annual_losses_complete"]
             else None),
           annual_model_main_band_pass=corrected_summary["all_2025_model_main_band_pass"],
           annual_AC_verified=corrected_summary["all_2025_model_main_band_pass"],
           annual_AC_case_hour_records_per_scenario=8760,
           input_original_AC_computed=HOURS,corrected_new_AC_computed=4,
           diagnostics_sha256=plot_sha,outputs_sha256=files,
           field_EPM_verified=False,annual_grid_import_including_AC_losses_reoptimized=False,
           installation_cost_or_tariff_updated=False)
        save()
        return {"status":status,"output":str(out),"pf":pf,"original":original_summary,
                "corrected":corrected_summary,
                "loss_delta_kwh":report["annual_ac_loss_delta_kwh"],
                "annual_AC_verified":report["annual_AC_verified"]}
    except Exception as exc:
        report.update(status="INCOMPLETE_94022_ANNUAL_AC_DO_NOT_CLAIM",
             new_original_AC_case_hours=len(baseline),
             failure={"type":type(exc).__name__,"message":str(exc),
                      "traceback":traceback.format_exc()})
        if baseline:
            save_csv(out/"PARTIAL_BASELINE_AC_CHECKPOINT_DO_NOT_CLAIM.csv",baseline)
        save()
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    parser.add_argument("--pf",type=float,choices=PF_OPTIONS,default=0.98)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only",action="store_true")
    modes.add_argument("--run-local",action="store_true")
    args=parser.parse_args(argv)
    result,item,v6,original,modified,mar,novrows=source_pilot_preflight(args.repo_root,args.pf)
    out=(result if args.preflight_only else
         run(args.repo_root,args.pf,result,item,v6,original,modified,mar,novrows))
    print(json.dumps(out,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
