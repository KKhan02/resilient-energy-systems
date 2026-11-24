#!/usr/bin/env python3
"""A1-origin SS90, four-house A0 113699 reference-year AC.
Single remaining direct annual reciprocal gap for the selected portfolio.
No new investment optimization, battery shift, physical network or PF assumption.
"""
from __future__ import annotations
import argparse
import json
import traceback
from pathlib import Path
import matched16_reciprocal12_p2p3_ac_screen as sample
import matched16_94022_nov_soc_shift_ac as nov
import matched16_94022_ss90_mar_nov_annual_ac as annual

gate=nov.gate
CASE="A1_113699_ss90_to_A0"
ARCHIVE=Path("StudyA_Reciprocal12_P2P3_AC_Screen_v1")
OUT_STEM="StudyA_113699_A0_SS90_Reciprocal_AnnualAC_PF98_v"
PF=.98
HOURS=8760

def select_benchmarks(rows, planned, sha):
    selected=[r for r in rows if r["case"]==CASE and float(r["pf"])==PF]
    expected={r["timestamp_lst"] for r in planned if r["case"]==CASE}
    if len(selected)!=25 or len(expected)!=25 or {r["timestamp_lst"] for r in selected}!=expected:
        raise ValueError("Expected exact 25 archived PF98 benchmark hours")
    if any(r["source_sha256"]!=sha or r["status"]!="CONVERGED" or r["ac_feasible"]!="True" for r in selected):
        raise ValueError("Archived benchmark source or pass status changed")
    return {r["timestamp_lst"]:r for r in selected}

def preflight(repo):
    import pandas as pd
    receipt,planned,groups,v6=sample.preflight(repo)
    if receipt["status"]!="P2P3_RECIPROCAL12_SIGNED_GIS_PQ_PREFLIGHT_NO_AC":
        raise ValueError("Prior signed materiality preflight changed")
    annual.check_source_stateless(v6)
    terr,ids,trace,c=groups[CASE];hw=c["hardware"]
    if (c["assignment_for_load"]!="A0" or c["assignment_for_hardware"]!="A1"
        or str(c["transformer"])!="113699" or c["tier"]!="ss90" or len(ids)!=4
        or abs(float(terr.trafo["kva"])-3.)>1e-9):
        raise ValueError("Frozen four-house target identity changed")
    path=gate.relative_file(repo,c["target_energy_csv"]);sha=c["target_energy_sha256"]
    sig=gate.signed_bytes(path,sha)
    frame=pd.read_csv(gate.required_file(path),parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    energy=nov.check_year(frame,int(hw["battery_modules"]),float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
    if not trace.index.equals(frame.index) or (trace.sum(axis=1)-frame.demand_kw).abs().max()>1e-5:
        raise ValueError("Annual individual demand profile mismatch")
    m=gate.read_json(repo/ARCHIVE/"RUN_MANIFEST.json")
    if (m["status"]!="P2P3_TARGETED_300_AC_CASEHOURS_RECORDED_NOT_ANNUAL"
        or m["new_AC_case_hour_evaluations"]!=300 or m["converged"]!=300 or m["infeasible"]!=0
        or m["annual_AC_verified"] is not False):
        raise ValueError("Archived P2/P3 receipt changed")
    acpath=repo/ARCHIVE/"TARGETED_300_AC_CASEHOURS.csv"
    benchsig=gate.signed_bytes(acpath,m["targeted_ac_csv_sha256"])
    rows=gate.read_csv(acpath)
    if len(rows)!=300:
        raise ValueError("Sample archive row count changed")
    benchmark=select_benchmarks(rows,planned,sha)
    for stamp,row in benchmark.items():
        t=pd.Timestamp(stamp)
        if abs(float(row["inverter_ac_kw"])-float(frame.at[t,"inverter_ac_kw"]))>1e-6 or abs(float(row["gross_demand_kw"])-float(frame.at[t,"demand_kw"]))>1e-5:
            raise ValueError("Sample benchmark source P/load mismatch")
    doc={"status":"SIGNED_113699_A0_SS90_PORTFOLIO_ANNUAL_PREFLIGHT_NO_AC",
         "case":CASE,"pf":PF,"length_factor":1.,"households":ids,"assumed_trafo_kva":3.,
         "source_energy_sha256":sha,"source_signature":sig,"benchmark_signature":benchsig,
         "benchmark_count":25,"planned_new_AC_case_hours":HOURS,"new_AC_case_hours":0,
         "annual_AC_verified":False,"field_EPM_verified":False,"annual_energy_metrics":energy}
    return doc,terr,ids,trace,c,frame,benchmark,v6

def run(repo,doc,terr,ids,trace,c,frame,benchmark,v6):
    import pandapower as pp
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from run_epm_validation import build_net
    out=next((repo/f"{OUT_STEM}{i}" for i in range(1,100) if not (repo/f"{OUT_STEM}{i}").exists()),None)
    if out is None:raise FileExistsError("No unused result version")
    out.mkdir();manifest=out/"RUN_MANIFEST.json"
    report=dict(doc,status="INCOMPLETE_113699_A0_SS90_ANNUAL_DO_NOT_CLAIM")
    def save():manifest.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    save();rows=[];checks=0
    try:
        net,meta=build_net(terr,"head")
        if set(meta["loads"])!=set(ids):raise ValueError("GIS load keys changed")
        for i,t in enumerate(frame.index):
            e=frame.iloc[i]
            r=v6.solve_ac_hour(net,meta,terr,t,trace.iloc[i],PF,float(e.inverter_ac_kw),
                              float(c["hardware"]["inverter_kva"]),float(e.pv_dc_available_kw),.25,9,"pvbess",pp)
            if abs(float(r["gross_demand_kw"])-float(e.demand_kw))>1e-5 or abs(float(r["inverter_ac_kw"])-float(e.inverter_ac_kw))>1e-5:
                raise ValueError("Annual source P/load mismatch")
            if str(t) in benchmark:
                annual.exact_ac_regression(r,benchmark[str(t)],CASE+" "+str(t));checks+=1
            rows.append({"case":CASE,"source_energy_sha256":c["target_energy_sha256"],
                         "source_grid_import_kw":float(e.grid_import_kw),**r})
            if (i+1)%500==0:
                report["new_AC_case_hours"]=i+1;save()
                print(f"{CASE}: {i+1}/{HOURS}",flush=True)
        if len(rows)!=HOURS or checks!=25:raise ValueError("Annual or benchmark coverage incomplete")
        result=annual.annual_summary(rows)
        path=out/"ANNUAL_2025_8760_AC.csv";annual.save_csv(path,rows)
        folder=out/"figures_diagnostic";folder.mkdir();figures={}
        for k,limit,label in (("min_v_pu",.95,"Minimum voltage [pu]"),("max_trafo_pct",100.,"Transformer loading [%]")):
            fig,ax=plt.subplots(figsize=(12,5))
            ax.plot(frame.index,[float(r[k]) if r["status"]=="CONVERGED" else float("nan") for r in rows],lw=.65)
            ax.axhline(limit,ls="--",color="black");ax.set_title(CASE+" | PF 0.98");ax.set_ylabel(label);ax.grid(alpha=.2)
            fig.autofmt_xdate();fig.tight_layout();p=folder/(k+".png");fig.savefig(p,dpi=150);plt.close(fig);figures[p.name]=nov.digest(p)
        report.update(status="113699_A0_SS90_RECIPROCAL_ANNUAL_PF98_RESULTS_RECORDED",
                      new_AC_case_hours=HOURS,benchmark_regressions_passed=checks,annual_summary=result,
                      annual_AC_verified=result["all_2025_model_main_band_pass"],
                      outputs_sha256={path.name:nov.digest(path)},diagnostics_sha256=figures,
                      loss_adjusted_economics_reoptimized=False,field_EPM_verified=False)
        save();return report
    except Exception as exc:
        report.update(status="INCOMPLETE_113699_A0_SS90_ANNUAL_DO_NOT_CLAIM",
                      new_AC_case_hours=len(rows),failure=str(exc),traceback=traceback.format_exc())
        save();raise

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."))
    mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument("--preflight-only",action="store_true");mode.add_argument("--run-local",action="store_true")
    args=ap.parse_args(argv);repo=args.repo_root.resolve();data=preflight(repo)
    print(json.dumps(data[0] if args.preflight_only else run(repo,*data),indent=2,allow_nan=False))
if __name__=="__main__":main()
