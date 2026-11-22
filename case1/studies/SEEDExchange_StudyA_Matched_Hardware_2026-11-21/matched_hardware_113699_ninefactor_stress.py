#!/usr/bin/env python3
"""113699 A1: source-signed PF/length 3x3 bounded AC uncertainty screen.

Replay exactly the SAME source-ranked 2025 stress timestamps for two frozen
SOC schedules under 9 PF / assumed service length factor combinations.
Not full annual AC validation for any nonreference factor.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback
import numpy as np
import pandas as pd

HERE=Path("case1/studies/SEEDExchange_StudyA_Matched_Hardware_2026-11-21")
SOURCE_RUNNER=HERE/"matched_hardware_113699_annual_ac.py"
ORIGINS=("A0","A1")
PF=(.95,.98,1.00)
LENGTH=(1.0,1.3,1.6)
TOP_N=6
RESULT_PREFIX="StudyA_A0_A1_MatchedHardware_113699_NineFactorStress_v"
FULL={
 "A0":Path("StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A0_v1"),
 "A1":Path("StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A1_v1")}
MANIFEST_SHA_LF={
 "A0":"58386d883b49c7ef39de07fdc19cf79114edd2f85fdf2aae431ca3db71d7e120",
 "A1":"f8fd08a6b2bb50a91822bc76e4d2e5eee43441c6bcda7a37e1858ff426ea00f9"}
ANNUAL_AC_SHA_WINDOWS={
 "A0":"3a05d64b68cbb22e0cedf260da4d4d60da449eddb353d28e1d96e898fd05b8c2",
 "A1":"d56aed6424269ded726bca66873d54823f83e5ce311a810f495ae1f3849f7eec"}
BASE_COMPARE_TOL=3e-4

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda:f.read(1<<20),b""):
            h.update(data)
    return h.hexdigest()

def load_annual(repo):
    path=repo/SOURCE_RUNNER
    spec=importlib.util.spec_from_file_location("seed113699_factor_annual_source",path)
    if spec is None or spec.loader is None: raise FileNotFoundError(path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def soc_hourly_path(annual,origin):
    """Use the annual AC module's signed annual-SOC directory mapping."""
    if origin not in ORIGINS:
        raise ValueError("Unknown original SOC origin: "+str(origin))
    return Path(annual.SOURCE_DIRS[origin])/"annual_soc_reoptimized_2025.csv"

def choose_stress_hours(full,old_15):
    """Union of original 15 and ranked 2025 annual extremes from BOTH origins."""
    if set(full)!=set(ORIGINS): raise ValueError("Both signed hardware origins required")
    old_15=[str(t) for t in old_15]
    if len(old_15)!=15 or len(set(old_15))!=15:
        raise ValueError("Original 15-hour source roster invalid")
    reason={t:["SOURCE_ORIGINAL_15_HOURS"] for t in old_15}
    clock=None
    ranking=(("min_v_pu",True),("max_trafo_pct",False),
             ("max_line_pct",False),("pcc_kva",False),("loss_kw",False))
    for origin in ORIGINS:
        df=full[origin]
        if (len(df)!=8760 or df.status.ne("CONVERGED").any()
            or df.ac_feasible.astype(str).str.lower().ne("true").any()):
            raise ValueError("Original full-year AC source incomplete for "+origin)
        if df.timestamp_lst.duplicated().any():
            raise ValueError("Two source annual clocks disagree: duplicate timestamp in "+origin)
        timestamps=list(df.timestamp_lst)
        if clock is None: clock=timestamps
        if timestamps!=clock: raise ValueError("Two source annual clocks disagree")
        for field,ascending in ranking:
            numeric=pd.to_numeric(df[field],errors="raise")
            if not np.isfinite(numeric).all():
                raise ValueError("Invalid source annual value: "+field)
            sample=df.assign(_sort_value=numeric).sort_values(
                "_sort_value",ascending=ascending,kind="stable").head(TOP_N)
            for when in sample.timestamp_lst:
                label=origin+"_"+("MIN_" if ascending else "MAX_")+field
                reason.setdefault(str(when),[])
                if label not in reason[str(when)]: reason[str(when)].append(label)
    hours=sorted(reason)
    if not set(old_15).issubset(hours) or not set(hours).issubset(clock):
        raise ValueError("Original critical hours absent from verified annual source")
    if not 15<=len(hours)<=75:
        raise ValueError("Unexpected common stress hour count")
    return hours,{t:reason[t] for t in hours}

def summary_for_factor(rows,origin,pf,lf):
    if rows.timestamp_lst.duplicated().any(): raise ValueError("Duplicated sampled hours")
    good=rows.status.eq("CONVERGED")
    valid=rows.loc[good]
    failed=valid.ac_feasible.astype(str).str.lower().eq("false")
    def count(field): return int(valid[field].sum())
    return dict(origin=origin,pf=float(pf),service_factor=float(lf),
        sampled_hours=len(rows),converged_hours=int(good.sum()),
        nonconverged_hours=int((~good).sum()),
        main_feasible_hours=int(good.sum()-failed.sum()),
        main_infeasible_hours=int(failed.sum()),
        trafo_over_100_hours=count("trafo_over_100"),
        line_over_100_hours=count("line_over_100"),
        voltage_below_095_hours=count("voltage_below_095"),
        voltage_above_105_hours=count("voltage_above_105"),
        strict_below_097_hours=count("voltage_below_097"),
        strict_above_103_hours=count("voltage_above_103"),
        minimum_voltage_pu=float(valid.min_v_pu.min()) if len(valid) else None,
        maximum_transformer_pct=float(valid.max_trafo_pct.max()) if len(valid) else None,
        maximum_line_pct=float(valid.max_line_pct.max()) if len(valid) else None,
        sampled_loss_kw_sum_NOT_ANNUAL=float(valid.loss_kw.sum()) if len(valid) else None,
        all_sampled_hours_main_feasible=bool(good.all() and not failed.any()),
        all_sampled_hours_strict_voltage=bool(good.all() and
            not valid.voltage_below_097.any() and not valid.voltage_above_103.any()),
        annual_AC_verified_for_this_factor=False,
        first_failed_hours=valid.loc[failed,"timestamp_lst"].astype(str).tolist()[:20],
        first_nonconverged_hours=rows.loc[~good,"timestamp_lst"].astype(str).tolist()[:20])

def verify_reference(replay,original):
    """PF .98 and service factor 1.0 must reproduce the archived annual AC data."""
    for row in replay.to_dict("records"):
        t=row["timestamp_lst"]
        src=original.loc[t]
        if (row["status"]!="CONVERGED" or row["ac_feasible"] is not True
            or str(src["status"])!="CONVERGED"
            or str(src["ac_feasible"]).lower()!="true"):
            raise ValueError("Reference AC status mismatch: "+t)
        for key in ("gross_demand_kw","inverter_ac_kw","min_v_pu","max_v_pu",
                    "max_trafo_pct","max_line_pct","loss_kw","pcc_kva","q_selected_kvar"):
            if abs(float(row[key])-float(src[key]))>BASE_COMPARE_TOL:
                raise ValueError("Reference AC field mismatch "+t+" "+key)
    return len(replay)

def next_folder(repo):
    for n in range(1,1000):
        path=repo/(RESULT_PREFIX+str(n))
        if not path.exists(): return path
    raise FileExistsError("All result versions exhausted")

def preflight(repo):
    repo=Path(repo).resolve()
    if not (repo/".git").is_dir():
        raise ValueError("Use actual Git checkout")
    annual=load_annual(repo)
    soc,v6,cases,geometry,original=annual.preflight(repo)
    if original.get("status")!="SIGNED_TWO_113699_SOC_RESULTS_ANNUAL_AC_SOURCE_PREFLIGHT_NO_NEW_SOLVES":
        raise ValueError("Original annual SOC source checks did not pass")
    first=json.loads((repo/soc.BASE_AC_FOLDER/"RUN_MANIFEST.json").read_text(encoding="utf-8"))
    old15=[str(x["timestamp_lst"]) for x in first["sampled_timestamps"]]
    frames={}
    source={}
    for origin in ORIGINS:
        folder=repo/FULL[origin]
        manifest=folder/"RUN_MANIFEST.json"
        if annual.git_lf_sha(manifest)!=MANIFEST_SHA_LF[origin]:
            raise ValueError("Completed full-2025 AC source manifest changed: "+origin)
        j=json.loads(manifest.read_text(encoding="utf-8"))
        if (j.get("status")!="ANNUAL_113699_MODEL_AC_MAIN_BAND_PASS_STRICT_SEPARATE"
            or j.get("new_AC_solves")!=8760
            or j.get("annual_AC_verified") is not True
            or j.get("annual_ac_hourly_sha256")!=ANNUAL_AC_SHA_WINDOWS[origin]
            or j["annual_summary"].get("converged_hours")!=8760
            or j["annual_summary"].get("model_main_band_feasible_hours")!=8760
            or j.get("field_AC_verified") is not False):
            raise ValueError("Expected 8760-hour model AC source no longer matches")
        hourly=folder/"annual_ac_hourly_2025.csv"
        mode=annual.verified_crlf_source(hourly,ANNUAL_AC_SHA_WINDOWS[origin])
        frame=pd.read_csv(hourly)
        energy=pd.read_csv(repo/soc_hourly_path(annual,origin),
                           parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
        if (len(frame)!=8760 or len(energy)!=8760
            or list(frame.timestamp_lst)!=list(energy.index.astype(str))
            or np.max(np.abs(frame.inverter_ac_kw.to_numpy(float)-
                             energy.inverter_ac_kw.to_numpy(float)))>1e-6):
            raise ValueError("Full 2025 AC source does not correspond to fixed SOC dispatch")
        frames[origin]=frame
        source[origin]={
            "original_annual_AC_manifest_git_lf_sha256":MANIFEST_SHA_LF[origin],
            "original_annual_AC_hourly_signed_sha256":ANNUAL_AC_SHA_WINDOWS[origin],
            "source_signature_mode":mode,"main_AC_8760_pass":True,
            "optional_097_low_voltage_hours":j["annual_summary"]["optional_strict_voltage_under_097_hours"]}
    hours,reasons=choose_stress_hours(frames,old15)
    receipt=dict(
        status="SIGNED_TWO_8760H_AC_SOURCES_NINEFACTOR_STRESS_PREFLIGHT_NO_SOLVES",
        source_commit="f580c39349478f0bccafddbf697a93bb0b8bb4b4",
        source_lineage=source,origin_hardware=list(ORIGINS),
        assignment="A1",transformer="113699",nameplate="3 kVA ASSUMED NOT FIELD VERIFIED",
        source_phase_topology="ORIGINAL EPM GIS BALANCED PROXY, SERVICE TAPS INFERRED",
        pf_factors=list(PF),length_factors=list(LENGTH),
        daylight_q_ratio=.25,night_q_off=True,
        source_2025_hours_per_origin=8760,
        original_reference_selected_15_hours=old15,
        source_ranked_common_hours=hours,selection_reasons=reasons,
        selected_hour_count=len(hours),factor_cases=18,
        planned_AC_solves=len(hours)*18,new_AC_solves=0,
        annual_AC_verified_for_nine_factors=False,
        method="Ninefactor common sampled-hours stress screen, not nine annual AC replays")
    return annual,soc,v6,cases,geometry,frames,hours,receipt

def plots(summary,out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out.mkdir(exist_ok=False)
    result={}
    for metric,threshold,label,name in (
        ("maximum_transformer_pct",100.,"Transformer loading (%)","max_transformer.png"),
        ("minimum_voltage_pu",.95,"Lowest household voltage (pu)","min_voltage.png")):
        fig,ax=plt.subplots(figsize=(8.5,5.3))
        for origin in ORIGINS:
            for pf in PF:
                data=summary.loc[(summary.origin==origin)&(summary.pf==pf)].sort_values("service_factor")
                ax.plot(data.service_factor,data[metric],marker="o",label=origin+" PF "+str(pf))
        ax.axhline(threshold,linestyle="--",linewidth=.9,label="Main AC research bound")
        ax.set(xlabel="Provisional service cable length multiplier",ylabel=label)
        ax.set_title("113699 six-house A1 common high-stress AC hours")
        ax.grid(alpha=.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out/name,dpi=165)
        plt.close(fig)
        result[name]=sha(out/name)
    return result

def run(repo,preflight_only=False):
    repo=Path(repo).resolve()
    annual,soc,v6,cases,geometry,original,hours,receipt=preflight(repo)
    if preflight_only: return receipt
    import pandapower as pp
    from run_epm_validation import build_net
    output=next_folder(repo)
    output.mkdir(exist_ok=False)
    manifest=output/"RUN_MANIFEST.json"
    doc=dict(receipt,status="INCOMPLETE_NINEFACTOR_STRESS_NOT_VALIDATED",new_AC_solves=0)
    def save():manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save()
    try:
        territory_by_factor={}
        houses=list(cases["A0_hardware_on_A1"]["trace"].columns)
        for lf in LENGTH:
            if lf==1.0:
                territory_by_factor[lf]=geometry["A1"][:3]
            else:
                territory=v6.new_territory(repo,"A1","113699",houses,lf)
                network,meta=build_net(territory,"head")
                if set(meta["loads"])!=set(houses):
                    raise ValueError("Original six-house A1 GIS membership changed")
                territory_by_factor[lf]=(territory,network,meta)
        outputs=[]; summ=[]
        for origin in ORIGINS:
            trace=cases[origin+"_hardware_on_A1"]["trace"]
            hardware=cases[origin+"_hardware_on_A1"]["hardware"]
            energy=pd.read_csv(repo/soc_hourly_path(annual,origin),
                               parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
            signed=original[origin].set_index("timestamp_lst")
            if not energy.index.equals(trace.index):
                raise ValueError("Annual energy and individual loads not aligned")
            for pf in PF:
                for lf in LENGTH:
                    territory,network,meta=territory_by_factor[lf]
                    group=[]
                    for time in hours:
                        t=pd.Timestamp(time)
                        point=v6.solve_ac_hour(network,meta,territory,t,trace.loc[t],pf,
                             float(energy.at[t,"inverter_ac_kw"]),
                             float(hardware["inverter_kva"]),
                             float(energy.at[t,"pv_dc_available_kw"]),
                             .25,9,"pvbess",pp)
                        result={"hardware_origin":origin,"assignment":"A1",
                                "pf":pf,"service_length_factor":lf,**point}
                        group.append(result);outputs.append(result)
                    frame=pd.DataFrame(group)
                    if list(frame.timestamp_lst)!=hours:
                        raise ValueError("Unexpected common sampled timebase")
                    if pf==.98 and lf==1.0 and verify_reference(frame,signed)!=len(hours):
                        raise ValueError("Unreproduced original PF .98 length 1.0 source")
                    info=summary_for_factor(frame,origin,pf,lf)
                    summ.append(info)
                    print("NINEFACT 113699",origin,"PF",pf,"L",lf,"AC",
                          info["main_feasible_hours"],"/",len(hours),
                          "nonconverged",info["nonconverged_hours"],flush=True)
        rows=pd.DataFrame(outputs)
        groups=pd.DataFrame(summ)
        if (len(rows)!=receipt["planned_AC_solves"] or len(groups)!=18
            or rows.duplicated(["hardware_origin","pf","service_length_factor","timestamp_lst"]).any()):
            raise ValueError("Missing or duplicate common AC factor samples")
        csv=output/"factor_ac_hourly.csv"
        groups_csv=output/"factor_summary.csv"
        rows.to_csv(csv,index=False,float_format="%.10f")
        groups.to_csv(groups_csv,index=False,float_format="%.10f")
        fig=plots(groups,output/"figures_diagnostic")
        doc.update(status=(
            "SAMPLED_NINEFACTOR_NONCONVERGENCE_RECORDED"
            if int(groups.nonconverged_hours.sum()) else
            "SAMPLED_NINEFACTOR_MAIN_BAND_VIOLATIONS_RECORDED"
            if int(groups.main_infeasible_hours.sum()) else
            "SAMPLED_NINEFACTOR_MAIN_BAND_PASS_ANNUAL_SENSITIVITY_UNTESTED"),
            new_AC_solves=len(rows),factor_groups=18,
            reference_pf098_length1_reproduced=True,
            ac_sample_csv_sha256=sha(csv),
            factor_summary_csv_sha256=sha(groups_csv),
            diagnostic_png_sha256=fig,
            all_factor_results=summ,
            sampled_main_infeasible_case_hours=int(groups.main_infeasible_hours.sum()),
            sampled_nonconverged_case_hours=int(groups.nonconverged_hours.sum()),
            annual_AC_verified_for_nine_factors=False,
            field_utility_approved=False)
        save()
        return dict(status=doc["status"],output=str(output),factor_groups=18,
                    AC_solves=len(rows),sampled_common_hours=len(hours),
                    main_failed_case_hours=doc["sampled_main_infeasible_case_hours"],
                    annual_AC_verified_for_nine_factors=False)
    except Exception as e:
        doc["status"]="INCOMPLETE_NINEFACTOR_STRESS_NOT_VALIDATED"
        doc["failure"]=dict(type=type(e).__name__,message=str(e),
                            traceback=traceback.format_exc())
        save()
        raise

def cli(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--preflight-only",action="store_true")
    args=p.parse_args(argv)
    print(json.dumps(run(args.repo_root,args.preflight_only),indent=2,allow_nan=False))

if __name__=="__main__":
    cli()
