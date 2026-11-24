#!/usr/bin/env python3
"""Source-locked residual three-evening 94022 SS90 SOC+AC correction pilot.

Original signed A0 94022 ten-house SS90 frozen source. Holds already tested
March28 50% and November27 98% discharge transfers fixed. Adds November16
19->20, November29 17->19 and 18->20 donor-target transfers TOGETHER,
checking every 2025 hourly SOC/DC/AC energy and device constraint before AC.

Default --preflight-only: no new pandapower AC solves, no output changes.
--run-local: 5 candidate joint fractions x 6 changed hours x 2 PF = 60
new AC case-hour samples, new unique versioned diagnostic folder.
Source 2025 annual original PF.98 baseline must match prior 8760 AC archive.
A 20/20 all-sampled pass does not prove 8760 corrected AC or field EPM approval.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import traceback
import pandas as pd

import matched16_94022_ss90_mar_nov_annual_ac as annual
import matched16_94022_mar_nov_ss90_ac as march
import matched16_94022_nov_soc_shift_ac as nov

YEAR=2025
CASE=march.CASE
PF=(.98,.95)
SAMPLES=(0.,.25,.5,.75,.98)
BASELINE=Path("StudyA_94022_SS90_MarNov_AnnualAC_PF98_v1")
SOURCE_FROZEN=nov.FROZEN
OUT_PREFIX="StudyA_94022_SS90_Remaining3_Pair_AC_v"
EVENTS=(
    ("nov16", "2025-11-16 19:00:00", "2025-11-16 20:00:00"),
    ("nov29_19", "2025-11-29 17:00:00", "2025-11-29 19:00:00"),
    ("nov29_20", "2025-11-29 18:00:00", "2025-11-29 20:00:00"),
)
SOURCE_TIMES=tuple(sorted({t for _,d,z in EVENTS for t in (d,z)}))
BASE_TOL=annual.MATCH_TOL


def check_event_layout(events=EVENTS):
    """Distinct donor and sink P positions, and same-day 12h donor windows."""
    if len(events)!=3 or len({e[0] for e in events})!=3:
        raise ValueError("Exactly three named residual target events required")
    donors=[x[1] for x in events];targets=[x[2] for x in events]
    if len(set(donors))!=3 or len(set(targets))!=3 or set(donors)&set(targets):
        raise ValueError("Residual donors and targets must be distinct unique hours")
    for _,a,b in events:
        d,t=pd.Timestamp(a),pd.Timestamp(b)
        if d.date()!=t.date() or d>=t or (t-d).total_seconds()>12*3600:
            raise ValueError("All donor shifts must precede same-day target within 12h")
    if len(SOURCE_TIMES)!=6:
        raise ValueError("Expected exactly six changed additional P source hours")
    if set(SOURCE_TIMES) & set(annual.CHANGED):
        raise ValueError("Additional evening corrections would overwrite prior accepted shifts")
    return True


def source_candidate(base, frozen, hw, max_by_event, fraction):
    """Three simultaneous discharge swaps; full-year chronology checked afterward."""
    if not math.isfinite(fraction) or fraction<0 or fraction>=1:
        raise ValueError("Candidate fraction must be finite in [0,1)")
    candidate=base.copy(deep=True)
    shifts=[]
    for event,donor,target in EVENTS:
        x=float(max_by_event[event])*fraction
        candidate=nov.transfer(candidate,donor,target,x)
        shifts.append({"event":event,"source_hour":donor,"target_hour":target,
                       "moved_dc_kw":x,"added_target_inverter_ac_kw":x*nov.ETA_INV})
    metrics=nov.check_year(candidate,int(hw["battery_modules"]),
                           float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
    frozen_metrics=frozen["original"]["annual"]
    for k in ("annual_import_kwh","annual_battery_discharge_dc_kwh","annual_curtail_dc_kwh"):
        nov.same_total(metrics,frozen_metrics,k)
    if abs(float(metrics["year_end_store_kwh"]) -
           float(frozen_metrics["year_end_store_kwh"]))>1e-6:
        raise ValueError("Combined discharge swaps change year-end cyclic SOC")
    # Prevent future accidental changes to four already accepted March+Nov27 P.
    for stamp in annual.CHANGED:
        t=pd.Timestamp(stamp)
        if abs(float(candidate.at[t,"inverter_ac_kw"])-float(base.at[t,"inverter_ac_kw"]))>1e-8:
            raise ValueError("Original March/Nov27 8/8 source-P evidence invalidated")
    altered=[str(t) for t in candidate.index[
        (candidate.inverter_ac_kw - frozen["source"].inverter_ac_kw).abs()>1e-7]]
    expected=sorted(set(annual.CHANGED)| (set(SOURCE_TIMES) if fraction else set()))
    if altered!=expected:
        raise ValueError("2025 source-P source variation not exactly expected P hours")
    return candidate,metrics,shifts


def preflight(repo):
    repo=repo.resolve()
    check_event_layout()
    # Proven source-only signed March/Nov27 8760h schedule and accepted 8 point PF samples.
    r,item,v6,original,base,march_rows,nov_rows=annual.source_pilot_preflight(repo,.98)
    hw=item["hw"]; c=item["original"]
    if r["status"]!="SIGNED_94022_SS90_MAR50_NOV98_ANNUAL_AC_PREFLIGHT_ZERO_NEW_AC":
        raise ValueError("Prior two-date SS90 preflight status changed")
    if r["source_case"]!=CASE or len(c["ids"])!=10:
        raise ValueError("Wrong signed A0 ten-house 94022 SS90 source")
    if len(base)!=8760 or not base.index.equals(original.index):
        raise ValueError("Original and corrected source 2025 chronology mismatch")
    for pf in PF:
        for stage,stamp in (("donor",march.MARCH_DONOR),("target",march.MARCH_TARGET)):
            saved=annual.unique_archived(march_rows,CASE,stamp,pf,annual.MARCH_FRACTION,stage)
            if saved["ac_feasible"]!="True":
                raise ValueError("Earlier March AC sample failed after source changes")
            if abs(float(saved["inverter_ac_kw"])-float(base.at[pd.Timestamp(stamp),"inverter_ac_kw"]))>1e-6:
                raise ValueError("Earlier March reference P changed")
        for stage,stamp in (("donor",nov.CASES[CASE]),("target",nov.TARGET)):
            saved=annual.unique_archived(nov_rows,CASE,stamp,pf,annual.NOV_FRACTION,stage)
            if saved["ac_feasible"]!="True":
                raise ValueError("Earlier November AC sample failed after source changes")
            if abs(float(saved["inverter_ac_kw"])-float(base.at[pd.Timestamp(stamp),"inverter_ac_kw"]))>1e-6:
                raise ValueError("Earlier November reference P changed")
    # Exact 8760 archived original source AC, not the corrected output reinterpreted
    # as original. Preserve the file SHA independent of CRLF Git normalization.
    receipt=nov.gate.read_json(repo/BASELINE/"RUN_MANIFEST.json")
    if (receipt.get("status")!="ANNUAL_94022_SS90_MARCH50_NOV98_PF98_COMPLETE_VIOLATIONS_RECORDED"
        or receipt.get("new_original_AC_case_hours")!=8760
        or receipt.get("new_corrected_AC_case_hours")!=4
        or receipt.get("original_source_hours")!=8760
        or receipt.get("original_energy_csv_sha256")!=c["case"]["target_energy_sha256"]
        or receipt.get("original_annual_summary",{}).get("main_band_infeasible_hours")!=5
        or receipt.get("corrected_annual_summary",{}).get("main_band_infeasible_hours")!=3
        or receipt.get("pf")!=.98):
        raise ValueError("Previously archived PF98 annual AC baseline changed")
    raw_path=repo/BASELINE/"ORIGINAL_2025_8760_AC.csv"
    source_mode=nov.gate.signed_bytes(raw_path,receipt["outputs_sha256"]["ORIGINAL_2025_8760_AC.csv"])
    archive=nov.gate.read_csv(raw_path)
    if (len(archive)!=8760 or len({x["timestamp_lst"] for x in archive})!=8760
        or [x["timestamp_lst"] for x in archive]!=[str(t) for t in original.index]):
        raise ValueError("Original 2025 PF98 AC archive timebase/duplicates mismatch")
    baseline_map={x["timestamp_lst"]:x for x in archive}
    for stamp in SOURCE_TIMES:
        t=pd.Timestamp(stamp);row=baseline_map[stamp]
        if (row["status"]!="CONVERGED"
            or abs(float(row["inverter_ac_kw"])-float(original.at[t,"inverter_ac_kw"]))>1e-6
            or abs(float(row["gross_demand_kw"])-float(c["trace"].loc[t].sum()))>1e-5):
            raise ValueError("Remaining hour original PF98 annual AC source mismatch")
    caps={event:nov.bound_one_donor(original,donor,target,hw,pf=.95)
          for event,donor,target in EVENTS}
    if any(x<=1e-7 or not math.isfinite(x) for x in caps.values()):
        raise ValueError("One or more same-day original source donor capacities unavailable")
    frames={}
    roster=[]
    for frac in SAMPLES:
        df,metrics,shifts=source_candidate(base,item,hw,caps,frac)
        frames[frac]=df
        roster.append({"fraction":frac,"annual_2025_SOC_AC_DC_valid":True,
                       "annual_import_kwh":metrics["annual_import_kwh"],
                       "min_store_kwh":metrics["min_store_kwh"],
                       "max_store_kwh":metrics["max_store_kwh"],
                       "changed_inverter_hour_count":len(annual.CHANGED)+
                                   (len(SOURCE_TIMES) if frac else 0),
                       "shifts":shifts})
    report=dict(
        status="SIGNED_94022_SS90_REMAINING3_MULTI_DONOR_PREFLIGHT_NO_NEW_AC",
        original_pf98_annual_AC_source=receipt["outputs_sha256"]["ORIGINAL_2025_8760_AC.csv"],
        original_pf98_annual_AC_source_signature_mode=source_mode,
        frozen_energy_source_sha256=c["case"]["target_energy_sha256"],
        hardware_source=CASE, load_assignment="A0",
        transformer="94022",assumed_trafo_kva=float(hw["transformer_kva_assumed_or_evidenced"]),
        target_households=10,battery_modules=int(hw["battery_modules"]),
        annual_source_hours=8760,
        original_2025_energy_import_kwh=item["original"]["annual"]["annual_import_kwh"],
        existing_March50_Nov27_98_AC_source_points_reused=8,
        previous_year_annual_original_pf98_AC_8760_source_checked=True,
        selected_3_additional_events=[{"event":e,"donor":d,"target":z,
                  "single_donor_DC_cap_before_joint_check_kW":caps[e]}
                 for e,d,z in EVENTS],
        source_only_caps_are_not_joint_AC_feasible=True,
        joint_candidate_2025_energy_ROSTER=roster,
        additional_changed_hour_times=list(SOURCE_TIMES),
        fractions=list(SAMPLES),PF=list(PF),
        new_AC_hours_planned=len(SAMPLES)*len(SOURCE_TIMES)*len(PF),
        new_AC_hours_executed=0,
        old_8_source_AC_points_not_rerun=True,
        annual_2025_corrected_AC_verified=False,
        field_utility_EPM_verified=False,
        source_AC_model_service_factor=1.0,
        AC_main_band="0.95 to 1.05 pu / 100 percent thermal",
        research_scope="bounded six-hour new AC samples, NOT new annual AC",
    )
    return report,{"source":original,"base":base,"frames":frames,
                   "caps":caps,"case":c,"hw":hw,"original_archive":baseline_map,
                   "old_item":item},v6


def save_csv(path,rows):
    if not rows:return
    columns=sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader();writer.writerows(rows)


def plots(folder,rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dest=folder/"figures_diagnostic"
    dest.mkdir()
    sig={}
    for typ,name in (("target","three_residual_target_min_voltage.png"),
                     ("donor","three_residual_donor_min_voltage.png")):
        fig,ax=plt.subplots(figsize=(11,5.5))
        for hour in SOURCE_TIMES:
            stage="donor" if hour in {a for _,a,_ in EVENTS} else "target"
            if stage!=typ:continue
            for pf in PF:
                selected=[r for r in rows if r["timestamp_lst"]==hour
                          and r["point"]==typ and float(r["pf"])==pf]
                if selected:
                    ax.plot([float(r["fraction"]) for r in selected],
                            [float(r["min_v_pu"]) if r["status"]=="CONVERGED" else math.nan
                             for r in selected],
                            marker="o",label=f"{hour[5:16]} PF {pf:.2f}")
        ax.axhline(.95,color="black",linestyle="--",linewidth=.8,label=".95 pu screen")
        ax.grid(alpha=.25);ax.set_xlabel("Common fraction of each isolated donor DC bound")
        ax.set_ylabel("Minimum household voltage [pu]")
        ax.set_title("94022 A0 10-house SS90 | 16 + 29 Nov 2025 | signed fixed hardware")
        ax.legend(fontsize=8,ncol=2);fig.tight_layout()
        target=dest/name;fig.savefig(target,dpi=160);plt.close(fig)
        sig[name]=nov.digest(target)
    return sig


def run_local(repo,receipt,item,v6):
    import pandapower as pp
    from run_epm_validation import build_net
    repo=repo.resolve()
    path=next((repo/f"{OUT_PREFIX}{n}" for n in range(1,101)
               if not (repo/f"{OUT_PREFIX}{n}").exists()),None)
    if path is None:
        raise FileExistsError("No free versioned output directory")
    path.mkdir()
    document=dict(receipt,status="INCOMPLETE_REMAINING3_94022_AC_DO_NOT_CLAIM")
    manifest=path/"RUN_MANIFEST.json"
    def save():manifest.write_text(json.dumps(document,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save()
    records,grouped=[],[]
    try:
        c=item["case"];hw=item["hw"];terr=c["territory"];trace=c["trace"]
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(c["ids"]):
            raise ValueError("Signed ten-house GIS keys not equal AC network household keys")
        for frac in SAMPLES:
            frame=item["frames"][frac]
            passed=[]
            for pf in PF:
                for hour in SOURCE_TIMES:
                    t=pd.Timestamp(hour)
                    point="donor" if hour in {a for _,a,_ in EVENTS} else "target"
                    value=v6.solve_ac_hour(net,meta,terr,t,trace.loc[t],pf,
                       float(frame.at[t,"inverter_ac_kw"]),float(hw["inverter_kva"]),
                       float(frame.at[t,"pv_dc_available_kw"]),.25,9,"pvbess",pp)
                    if (abs(float(value["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5
                        or abs(float(value["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-6):
                        raise ValueError("Actual residual source AC P/demand mismatch")
                    if frac==0 and pf==.98:
                        prior=item["original_archive"][hour]
                        annual.exact_ac_regression(value,prior,"Prior original PF98 annual AC "+hour)
                    accept=(value["status"]=="CONVERGED" and value["ac_feasible"] is True)
                    passed.append(accept)
                    records.append({"scenario":"remaining3_SS90_source_joint_shift",
                       "case":CASE,"fraction":frac,"pf":pf,"point":point,
                       "source_annual_SOC_AC_DC_valid":True,
                       "frozen_source_energy_sha256":receipt["frozen_energy_source_sha256"],
                       "source_pf98_original_annual_AC_SHA":receipt["original_pf98_annual_AC_source"],
                       **value})
                    print(f"94022 remaining3 AC {len(records)}/60 | common fraction {frac} | "
                          f"{hour} | PF{pf:.2f}",flush=True)
            grouped.append({
                 "fraction":frac,
                 "joint_2025_battery_and_energy_valid":True,
                 "new_6_changed_hours_ac_pass_12of12":all(passed),
                 "new_ac_pass_count":sum(passed),
                 "new_ac_checked_count":12,
                 "earlier_March_Nov27_8of8_reused_valid":True,
                 "20of20_selected_AC_pass":all(passed),
                 "2025_annual_model_AC_verified":False,
                 **{f"shift_dc_{e}":item["caps"][e]*frac for e,_,_ in EVENTS},
                 **{f"target_added_ac_{e}":item["caps"][e]*frac*nov.ETA_INV for e,_,_ in EVENTS},
            })
        if len(records)!=60 or len(grouped)!=5:
            raise ValueError("Incomplete bounded residual AC source study")
        document.update(
          status="REMAINING3_94022_SS90_JOINT_AC_SAMPLED_60_COMPLETE_NOT_ANNUAL",
          new_AC_hours_executed=60,
          AC_converged_casehours=sum(r["status"]=="CONVERGED" for r in records),
          AC_infeasible_casehours=sum(r["ac_feasible"] is False for r in records),
          new_12of12_AC_pass_candidates=sum(x["new_6_changed_hours_ac_pass_12of12"] for x in grouped),
          all_selected_20of20_pass_candidates=sum(x["20of20_selected_AC_pass"] for x in grouped),
          candidate_summary=grouped,annual_2025_corrected_AC_verified=False)
        acpath=path/"REMAINING3_DONOR_TARGET_60_AC_CASEHOURS.csv"
        summary=path/"JOINT_CANDIDATES_5.csv"
        save_csv(acpath,records);save_csv(summary,grouped)
        document["ac_csv_sha256"]=nov.digest(acpath)
        document["candidate_csv_sha256"]=nov.digest(summary)
        document["diagnostic_png_sha256"]=plots(path,records)
        save()
        return {"status":document["status"],"folder":str(path),
                "new_AC_casehours":60,
                "converged":document["AC_converged_casehours"],
                "new_local_12of12_pass_count":document["new_12of12_AC_pass_candidates"],
                "20of20_selected_pass_count":document["all_selected_20of20_pass_candidates"],
                "2025_annual_model_AC_verified":False}
    except Exception as exc:
        document.update(status="INCOMPLETE_REMAINING3_94022_AC_DO_NOT_CLAIM",
                        new_AC_hours_executed=len(records),
                        failure={"error":type(exc).__name__,"message":str(exc),
                                 "traceback":traceback.format_exc()})
        if records:save_csv(path/"PARTIAL_UNVERIFIED_AC_RESULTS.csv",records)
        save()
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only",action="store_true")
    modes.add_argument("--run-local",action="store_true")
    args=parser.parse_args(argv)
    receipt,item,v6=preflight(args.repo_root)
    result=receipt if args.preflight_only else run_local(args.repo_root,receipt,item,v6)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
