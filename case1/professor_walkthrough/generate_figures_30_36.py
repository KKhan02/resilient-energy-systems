#!/usr/bin/env python3
"""Reproduce walkthrough figures 30-35 and render reference portfolio figure 36.
Read-only numerical evidence; no power flow, optimization, or manual SVG drawing.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SOURCES = {
    "pairs": ("StudyA_A0_A1_MatchedHardware_Full_v1/MATCHED_A0_VS_A1_SAME_HARDWARE_PAIRS.csv", "aaebbc8ae3c7d958dd966c0683bb1a2140e1a652d1b65bc5f92d3b2f67e96ee6"),
    "stress": ("StudyA_A0_A1_MatchedHardware_113699_NineFactorStress_v1/factor_ac_hourly.csv", "6bc4d39d4371b57cdcf1fff3c1f841f46d20c259f376eaf015525492859210b4"),
    "architecture": ("case1/studies/SEEDExchange_StudyA_Matched_Cohort_2026-11-21/A0_A1_34H_MATCHED_SOURCE_ENERGY.csv", "37251e8653600ff5e21e6781f963d190c8a335524aa90b3b67d2fde0805f8748"),
    "timing": ("case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/FIGURE_MC_P33_2025_01_13.csv", "83eb2d230a36167f79c325612fe0f58973b05895e4710c6ac29119d7f0279fa2"),
    "sizing": ("case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/SIZING_DELTA_FIGURE_SOURCE_2026-11-25.csv", "d9b70f6b4c8947d1645a10049a168b395e03e00af24968d4eb43bafc23f5e5f5"),
    "reserve": ("case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/FULL_NIGHT_FIGURE_SOURCE_2026-11-25.csv", "c33524a2ac355e86c7012798a35fef8a5a186a57ecd7ac88f8922bff05000f50"),
    "annual_small": ("StudyA_113699_Sizing_AnnualAC_v1/ANNUAL_AC_SUMMARY.csv", "aa1d3bd2dbc2f9cc5b724a627643f0a4d58b7e86dec94f9001406b39156739be"),
    "annual_large": ("StudyA_94022_FullNight_Reserve_v1/ANNUAL_AC_SUMMARY.csv", "54ac9e13b24e709adcf5fd744977256376151cb33a6f3e7e1ed42a0b40b758ee"),
}
FIGURES = {
    "30_matched_assignment_energy": ["pairs"],
    "31_113699_sampled_ac_robustness": ["stress"],
    "32_architecture_energy_frontier": ["architecture"],
    "33_pv_first_curtailment_timing": ["timing"],
    "34_targeted_sizing_two_territories": ["sizing"],
    "35_94022_full_night_reserve": ["reserve"],
    "36_eight_design_reference_portfolio": ["annual_small", "annual_large"],
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def checked(repo, rel, expected):
    raw = (repo / rel).read_bytes()
    got = sha(raw)
    mode = "exact"
    if got != expected:
        lf = raw.replace(b"\r\n", b"\n")
        require(b"\r" not in lf and (b"\r" not in raw or b"\n" not in raw.replace(b"\r\n", b"")), "Mixed newline source: " + rel)
        require(expected in (sha(lf), sha(lf.replace(b"\n", b"\r\n"))), "Source SHA mismatch: " + rel)
        mode = "newline normalization only"
    return pd.read_csv(io.BytesIO(raw)), {"path": rel, "git_blob_content_sha256": expected, "local_sha256": got, "match": mode}

def validate(data):
    counts = {"pairs":4,"stress":450,"architecture":4,"timing":24,"sizing":9,"reserve":3,"annual_small":5,"annual_large":3}
    for key,n in counts.items():
        require(len(data[key])==n, "Unexpected row count: "+key)
    x=data["pairs"]
    require(not x.duplicated(["hardware_origin","tier"]).any(), "Duplicate matched pair")
    for q in ("annual_total_usd","import_kwh"):
        require(np.allclose(x["A1_"+q]-x["A0_"+q],x["A1_minus_A0_"+q],rtol=0,atol=1e-7), "Matched delta mismatch")
    x=data["stress"]
    require(x.status.eq("CONVERGED").all() and not x.duplicated(["hardware_origin","assignment","pf","service_length_factor","timestamp_lst"]).any(), "Bad sampled AC identity")
    require(len(x.groupby(["hardware_origin","pf","service_length_factor"]))==18 and x.groupby(["hardware_origin","pf","service_length_factor"]).size().eq(25).all(), "Incomplete stress grid")
    require((x.min_v_pu<.95).sum()==12, "Sampled undervoltage count changed")
    x=data["architecture"]
    require(x.houses.eq(34).all() and x.annual_demand_kwh.eq(64532).all(), "Population changed")
    require(pd.to_datetime(data["timing"].timestamp_lst).equals(pd.Series(pd.date_range("2025-01-13",periods=24,freq="h"))), "Figure day chronology changed")
    x=data["reserve"]
    require(x.case.tolist()==["5B","6B","7B"] and x.corrected_failures.eq(0).all() and x.changed_p_hours.sum()==81 and (x.changed_p_hours+x.reused_ac_hours).eq(8760).all(), "Reserve closure changed")
    for k in ("annual_small","annual_large"):
        x=data[k]
        require(x.case.is_unique and x.converged_hours.eq(8760).all() and x.main_band_infeasible_hours.eq(0).all(), "Reference annual closure changed: "+k)
        require(x.minimum_voltage_pu.ge(.95).all() and x.maximum_voltage_pu.le(1.05).all() and x.maximum_trafo_loading_pct.le(100).all() and x.maximum_line_loading_pct.le(100).all(), "Reference limits changed: "+k)

def finish(fig, out, name, title, caption):
    fig.suptitle(title, fontsize=14)
    fig.text(.04,.02,caption,fontsize=8,wrap=True)
    fig.tight_layout(rect=[0,.07,1,.94])
    for ext in ("png","svg"):
        fig.savefig(out/(name+"."+ext),dpi=180,bbox_inches="tight")
    plt.close(fig)

def render(data,out):
    plt.rcParams.update({"font.size":10,"axes.grid":True,"grid.alpha":.22,"axes.axisbelow":True})
    x=data["pairs"]
    labels=x.hardware_origin+" / "+x.tier
    fig,ax=plt.subplots(1,2,figsize=(11,4.7))
    for a,col,unit in zip(ax,["A1_minus_A0_import_kwh","A1_minus_A0_annual_total_usd"],["Annual import difference (kWh)","Annual cost difference (USD)"]):
        a.bar(labels,x[col]);a.axhline(0,color="0.3",linewidth=.8);a.set_ylabel(unit);a.tick_params(axis="x",rotation=22)
    finish(fig,out,"30_matched_assignment_energy","34-house matched equipment | A1 minus A0","Energy only. Identical equipment within each pair; common hypothetical 92395 STAR.")
    x=data["stress"]
    fig,ax=plt.subplots(1,2,figsize=(11,4.6),sharey=True)
    for a,(origin,g) in zip(ax,x.groupby("hardware_origin")):
        for pf,z in g.groupby("pf"):
            q=z.groupby("service_length_factor").min_v_pu.min()
            a.plot(q.index,q.values,"o-",label=f"PF {pf:.2f}")
        a.axhline(.95,ls="--",color="0.3");a.set(title="Hardware origin "+origin,xlabel="Service length multiplier",ylabel="Minimum sampled voltage (pu)",xticks=[1,1.3,1.6]);a.legend()
    finish(fig,out,"31_113699_sampled_ac_robustness","113699 | Matched-hardware sampled robustness","25 common hours per factor and hardware origin. Sampled, not annual certification.")
    x=data["architecture"]
    fig,ax=plt.subplots(1,2,figsize=(11,4.6))
    for assignment,g in x.groupby("scenario"):
        ax[0].plot(g.grid_import_kwh,g.annualized_equipment_plus_import_usd,"o-",label=assignment)
        for row in g.itertuples():
            ax[0].annotate(row.tier,(row.grid_import_kwh,row.annualized_equipment_plus_import_usd),xytext=(4,4),textcoords="offset points")
    ax[0].set(xlabel="Annual grid imports (kWh)",ylabel="Annual model cost (USD)");ax[0].legend()
    ax[1].bar(x.scenario+" / "+x.tier,x.curtailment_dc_kwh);ax[1].set_ylabel("Annual DC PV curtailment (kWh)");ax[1].tick_params(axis="x",rotation=22)
    finish(fig,out,"32_architecture_energy_frontier","34-house architecture-specific energy comparison","Energy only; equipment differs. Same 64,532 kWh annual household demand.")
    x=data["timing"];h=pd.to_datetime(x.timestamp_lst).dt.hour
    fig,ax=plt.subplots(3,1,figsize=(10,8),sharex=True)
    for a,suffix,unit in zip(ax,["charge_dc_kw","curtail_dc_kw","store_end_kwh"],["DC charge (kW)","DC curtailment (kW)","Usable Store (kWh)"]):
        a.step(h,x["source_"+suffix],where="post",label="Original optimized")
        a.step(h,x["pv_first_"+suffix],where="post",label="PV-first diagnostic",ls="--");a.set_ylabel(unit);a.legend()
    ax[-1].set(xlabel="Hour, LST",xticks=range(0,24,2))
    finish(fig,out,"33_pv_first_curtailment_timing","MC_P33 | 13 January 2025","Diagnostic charging rule; same annual import/spill, two proxy-limit breaches in the annual run.")
    x=data["sizing"]
    fig,ax=plt.subplots(2,3,figsize=(14,8))
    for axes,(family,g) in zip(ax,x.groupby("family",sort=False)):
        g=g[g.AC_status.eq("NEW_ENERGY_ONLY")]
        labels=g.case.str.replace("113699_","",regex=False).str.replace("94022_","",regex=False)
        for a,col,unit in zip(axes,["delta_model_usd","delta_import_ac_kwh","delta_spill_dc_kwh"],["Annual cost delta (USD)","Annual import delta (kWh)","Annual DC spill delta (kWh)"]):
            a.bar(labels,g[col]);a.axhline(0,color="0.3",linewidth=.8);a.set(title=family,ylabel=unit);a.tick_params(axis="x",rotation=24)
    finish(fig,out,"34_targeted_sizing_two_territories","Two-territory fixed-hardware sizing screen","Historical energy-only screen. Separate later reference AC results are in Figure 36.")
    x=data["reserve"];k=np.arange(len(x))
    fig,ax=plt.subplots(1,2,figsize=(11,4.7))
    ax[0].bar(k-.17,x.prior_failures,.34,label="Before");ax[0].bar(k+.17,x.corrected_failures,.34,label="Corrected")
    ax[0].set(xticks=k,xticklabels=x.case,ylabel="Annual violation hours");ax[0].legend()
    ax[1].plot(k,x.prior_min_v_pu,"o-",label="Before");ax[1].plot(k,x.corrected_min_v_pu,"o-",label="Corrected");ax[1].axhline(.95,ls="--",color="0.3",label="Lower limit")
    ax[1].set(xticks=k,xticklabels=x.case,ylabel="Annual minimum voltage (pu)");ax[1].legend()
    finish(fig,out,"35_94022_full_night_reserve","94022 A0 | Full-night reserve correction","2025; ten households; PF 0.98; length x1.0; unchanged hardware and annual energy-model cost. Offline dispatch.")
    fig,ax=plt.subplots(2,3,figsize=(14,8))
    for axes,key,title in zip(ax,["annual_small","annual_large"],["113699 / four households","94022 / ten households"]):
        g=data[key];labels=g.case.replace({"A1_94022_min_cost_to_A0":"5B","94022_B6":"6B","94022_B7":"7B"}).str.replace("113699_","",regex=False)
        for a,col,unit in zip(axes,["all_losses_purchased_cost_sensitivity_usd","annual_curtail_dc_kwh","minimum_voltage_pu"],["Annual cost sensitivity (USD)","Annual DC curtailment (kWh)","Minimum annual voltage (pu)"]):
            if col=="minimum_voltage_pu":
                a.plot(labels,g[col],"o");a.axhline(.95,ls="--",color="0.3");a.axhline(.97,ls=":",color="0.3");a.set_ylim(.945,1.005)
            else:
                a.bar(labels,g[col])
            a.set(title=title,ylabel=unit);a.tick_params(axis="x",rotation=24)
    finish(fig,out,"36_eight_design_reference_portfolio","Eight sizing alternatives | Annual reference AC pass","All eight pass 8,760 reference hours. PF 0.98, length x1.0. Cost assumes all AC losses purchased; not an optimized loss-aware objective. No stress or field certification.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    args=p.parse_args()
    require(not args.out.exists(),"Choose fresh output directory")
    data={};sources={}
    for key,(rel,h) in SOURCES.items():
        data[key],sources[key]=checked(args.repo_root,rel,h)
    validate(data)
    print("SOURCE AND DATA VALIDATION PASSED: 8 CSVs; figures 30-36",flush=True)
    if args.preflight_only:
        return
    args.out.mkdir(parents=True,exist_ok=False)
    render(data,args.out)
    files={f.name:sha(f.read_bytes()) for f in args.out.iterdir() if f.suffix in (".png",".svg")}
    require(len(files)==2*len(FIGURES),"Incomplete plot output")
    manifest={"status":"COMPLETE_PYTHON_DATA_FIGURES","sources":sources,"figure_sources":FIGURES,"output_sha256":files,"python_script_sha256":sha(Path(__file__).read_bytes()),"matplotlib":matplotlib.__version__,"pandas":pd.__version__,"no_new_simulations":True,"field_verified":False}
    (args.out/"FIGURE_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":
    main()
