#!/usr/bin/env python3
"""Controlled Study A annual stress execution on the restricted Windows runner.
No optimization, no new network assumptions, no repository write or external upload.
"""
import csv
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np
import pandas as pd
from audit_battery_coverage import signed

ROOT=Path.cwd()
OUT=ROOT/"remote-research"
STUDY=Path(__file__).resolve().parent
REF=ROOT/"StudyA_94022_Physical_AnnualReference_v1"
SAMPLE=ROOT/"StudyA_94022_Matched_Physical_Options_v1"
STRESS=OUT/"StudyA_94022_Physical_AnnualStress_v1"
BASE="eff7dae3ce320afbe6a8fc9ebbabb34202db1484"
REF_HASHES={
"head_hypothetical_R050_94022_B6_ANNUAL_AC.csv":"0c10bae296c4e9179e4ce6b425d26c222ece79564007b2e249d0bd63c7066d53",
"head_hypothetical_R050_94022_B7_ANNUAL_AC.csv":"1a9371942388b5b8cf7ecb2f813f679f24f745e0306dfbbd27aef83ca34af5d0",
"head_hypothetical_R050_A1_94022_min_cost_to_A0_ANNUAL_AC.csv":"a8db04148133dece0b7f6ea185b4612be09745bf10bf88f4681438b9dc71ef74",
"middle_94022_B6_ANNUAL_AC.csv":"5d768a7b21d45c6339942556e0c387d5bf429a70a294343f4975392a5068a68b",
"middle_94022_B7_ANNUAL_AC.csv":"594c88b4fc8371ef61a5ac71444490fc4e90570b6d34cb1b68cc4437cdd8f8d0",
"middle_A1_94022_min_cost_to_A0_ANNUAL_AC.csv":"9264809bc07c5380357a41eb02659a7ef055a97beabb4415e10b0a1abeb1177e",
"OPTION_AC_SUMMARY.csv":"204dbbbafe91837dc2c3dd7ef31d6f7f8a5c80f3b263c3b6b335616e4b6ee705"}
OPTIONS=("middle","head_hypothetical_R050")
CASES=("A1_94022_min_cost_to_A0","94022_B6","94022_B7")
SAMPLE_HASH="1bdae29216e3ca4f694d06894ab1861e296ed357b8951a605804a61201be2111"
METRICS=("min_v_pu","max_v_pu","max_trafo_pct","max_line_pct","loss_kw","pcc_kva","q_selected_kvar")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def receipt(path):
    m=json.loads((path/"RUN_MANIFEST.json").read_text(encoding="utf-8"))
    if m["status"]!="COMPLETE_SELECTED_OPTION_ANNUAL" or m["new_AC_case_hours"]!=52560 or m["completed_case_factors"]!=6 or m["annual_to_sample_regressions"]!=402 or m["endpoint_regressions"]!=36:
        raise ValueError("Incomplete annual receipt "+str(path))
    if path==REF and m["output_sha256"]!=REF_HASHES:
        raise ValueError("Reference receipt changed")
    if set(m["output_sha256"])!=set(REF_HASHES):raise ValueError("Unexpected annual file set")
    for k,v in m["output_sha256"].items():signed(path/k,v)
    return m

def audit(path,pf,length,sample):
    m=receipt(path)
    if m["factors"]!=[[pf,length]] or set(m["options"])!=set(OPTIONS) or set(m["cases"])!=set(CASES):
        raise ValueError("Annual factor/option identity changed")
    summary=pd.read_csv(path/"OPTION_AC_SUMMARY.csv")
    if len(summary)!=6 or summary.duplicated(["option","case"]).any():
        raise ValueError("Annual summary coverage")
    result=[]
    for opt in OPTIONS:
        for case in CASES:
            file=path/(opt+"_"+case+"_ANNUAL_AC.csv")
            z=pd.read_csv(file,parse_dates=["timestamp_lst"],keep_default_na=False)
            if len(z)!=8760 or not pd.DatetimeIndex(z.timestamp_lst).equals(pd.date_range("2025-01-01",periods=8760,freq="h")):
                raise ValueError("Annual timebase "+case)
            if not z.option.eq(opt).all() or not z.case.eq(case).all() or not z.pf.eq(pf).all() or not z.length_factor.eq(length).all() or not z.load_pf.eq(pf).all():
                raise ValueError("Annual identity")
            if not z.status.eq("CONVERGED").all():raise ValueError("Nonconverged AC rows; preserve output as diagnostic")
            if not np.isfinite(z[list(METRICS)].to_numpy(dtype=float)).all():raise ValueError("Nonfinite AC metric")
            if not np.allclose(z.gross_demand_kw-z.inverter_ac_kw,z.source_grid_import_kw,rtol=0,atol=1e-7):
                raise ValueError("Source power balance")
            if not z.loc[z.night_reactive_disabled,"q_selected_kvar"].abs().le(1e-9).all():raise ValueError("Night Q")
            low=z.min_v_pu.lt(.95);high=z.max_v_pu.gt(1.05);trafo=z.max_trafo_pct.gt(100);line=z.max_line_pct.gt(100)
            strict=z.ac_feasible & ~(low|high|trafo|line)
            if not np.array_equal(strict,z.strict_feasible):raise ValueError("Strict AC flag")
            q=sample[(sample.option==opt)&(sample.case==case)&(sample.pf==pf)&(sample.length_factor==length)].set_index("timestamp_lst")
            if len(q)!=67:raise ValueError("Sample coverage")
            matched=z.set_index("timestamp_lst").loc[q.index]
            if not matched.source_energy_sha256.eq(q.source_energy_sha256).all() or z.source_energy_sha256.nunique()!=1:
                raise ValueError("Signed energy identity")
            if not np.array_equal(matched.strict_feasible,q.strict_feasible) or not np.array_equal(matched.night_reactive_disabled,q.night_reactive_disabled):
                raise ValueError("Sample strict flags")
            delta=float(np.max(np.abs(matched[list(METRICS)].to_numpy(dtype=float)-q[list(METRICS)].to_numpy(dtype=float))))
            if delta>1e-6:raise ValueError("Sample metric parity")
            row=summary[(summary.option==opt)&(summary.case==case)].iloc[0]
            failed=~strict
            metrics=dict(option=opt,case=case,pf=pf,length_factor=length,hours=len(z),converged=int(z.status.eq("CONVERGED").sum()),
                         strict_failures=int(failed.sum()),night_failures=int((failed&z.night_reactive_disabled).sum()),
                         daylight_failures=int((failed&~z.night_reactive_disabled).sum()),low_voltage_hours=int(low.sum()),
                         high_voltage_hours=int(high.sum()),transformer_overload_hours=int(trafo.sum()),line_overload_hours=int(line.sum()),
                         minimum_voltage_pu=float(z.min_v_pu.min()),maximum_voltage_pu=float(z.max_v_pu.max()),
                         peak_transformer_pct=float(z.max_trafo_pct.max()),peak_line_pct=float(z.max_line_pct.max()),
                         losses_kwh=float(z.loss_kw.sum()),sample_max_abs_error=delta,
                         input_energy_sha256=str(z.source_energy_sha256.iloc[0]),output_sha256=sha(file))
            for k,v in (("strict_exact_failed_hours",metrics["strict_failures"]),("strict_exact_night_failed_hours",metrics["night_failures"]),
                        ("strict_exact_daylight_failed_hours",metrics["daylight_failures"]),("sample_regressions",67),("converged_hours",8760)):
                if int(row[k])!=v:raise ValueError("Annual summary count "+k)
            for k,v in (("minimum_voltage_pu",metrics["minimum_voltage_pu"]),("maximum_voltage_pu",metrics["maximum_voltage_pu"]),
                        ("maximum_trafo_loading_pct",metrics["peak_transformer_pct"]),("maximum_line_loading_pct",metrics["peak_line_pct"]),
                        ("annual_ac_network_losses_kwh",metrics["losses_kwh"])):
                if abs(float(row[k])-v)>1e-8:raise ValueError("Annual summary metric "+k)
            if failed.any():
                metrics["worst_voltage_time"]=str(z.loc[z.min_v_pu.idxmin(),"timestamp_lst"])
                metrics["failed_timestamps_first_20"]=list(z.loc[failed,"timestamp_lst"].astype(str).head(20))
            result.append(metrics)
    return result

def run(args,label):
    start=time.perf_counter()
    p=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8",errors="replace")
    (OUT/(label+".log")).write_text(p.stdout,encoding="utf-8")
    print(p.stdout,flush=True)
    print(label+" duration_s="+str(round(time.perf_counter()-start,3)),flush=True)
    if p.returncode:raise RuntimeError(label+" failed with exit "+str(p.returncode))

def figure(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    labels=["5B","6B","7B"]
    x=np.arange(3)
    for j,opt in enumerate(OPTIONS):
        for i,factor in enumerate((.98,.95)):
            data=[next(r for r in rows if r["case"]==c and r["option"]==opt and r["pf"]==factor) for c in CASES]
            name=("Middle" if opt=="middle" else "Hypothetical R×0.5")+" | PF "+str(factor)
            offset=(j*2+i-1.5)*.18
            ax[0].bar(x+offset,[v["minimum_voltage_pu"] for v in data],width=.18,label=name)
            ax[1].bar(x+offset,[v["losses_kwh"] for v in data],width=.18,label=name)
    for a in ax:a.set_xticks(x,labels);a.set_xlabel("Battery design");a.legend(fontsize=7)
    ax[0].axhline(.95,ls="--",color="firebrick");ax[0].set_ylim(min(.93,min(v["minimum_voltage_pu"] for v in rows)-.002),1.)
    ax[0].set_ylabel("Annual minimum voltage (pu)");ax[1].set_ylabel("Annual AC losses (kWh)")
    fig.suptitle("Study A | 94022 annual fixed-dispatch alternatives\nReference PF 0.98 / length ×1.0; stress PF 0.95 / length ×1.6; hypothetical GIS proxy")
    folder=OUT/"figure_41";folder.mkdir()
    for ext in ("png","svg"):fig.savefig(folder/("41_annual_physical_options."+ext),dpi=180,bbox_inches="tight")
    plt.close(fig)

def main():
    OUT.mkdir(exist_ok=False)
    start=time.perf_counter()
    report=dict(status="INCOMPLETE",source_research_commit=BASE,execution_commit=os.environ.get("CI_COMMIT_SHA"),
        job_id=os.environ.get("CI_JOB_ID"),pipeline_id=os.environ.get("CI_PIPELINE_ID"),runner_id=os.environ.get("CI_RUNNER_ID"),
        session_id=os.environ.get("RUNNER_VERIFIED_SESSION_ID"),python=sys.version,platform=platform.platform(),
        assumptions=dict(territory="A0 94022 ten-house proxy",options=list(OPTIONS),factors=[[.98,1.],[.95,1.6]],cases=list(CASES),
                         frozen_dispatch=True,night_Q_disabled=True,zero_export_energy_schedule=True,field_verified=False,no_new_LP=True),
        package_versions={},warnings=[],limitations=["Balanced provisional GIS proxy; no field certification, construction specification or network investment cost.",
        "Reference audited from existing files, not rerun. Stress results depend on source schedules, not causal control.",
        "Energy imports have not been reoptimized for AC losses."])
    try:
        if platform.system()!="Windows" or os.environ.get("CI_RUNNER_ID")!="60033802" or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0" or sys.version_info[:3]!=(3,12,9):
            raise RuntimeError("Unexpected validated execution environment")
        for package in ("pandapower","pypsa","highspy","numpy","scipy","pandas","matplotlib","numba","linopy"):
            report["package_versions"][package]=metadata.version(package)
        signed(SAMPLE/"OPTION_AC_HOURLY.csv",SAMPLE_HASH)
        sample=pd.read_csv(SAMPLE/"OPTION_AC_HOURLY.csv",parse_dates=["timestamp_lst"])
        if len(sample)!=5427:raise ValueError("Sample coverage")
        report["reference"]=audit(REF,.98,1.,sample)
        run(["-m","unittest","discover","-s",STUDY,"-p","test_sizing_option_annual_gate.py","-v"],"regression_tests")
        args=[STUDY/"sizing_matched_physical_options.py","--repo-root",".","--scope","annual","--options",*OPTIONS,"--pf","0.95","--length","1.6"]
        run([*args,"--preflight-only"],"stress_preflight")
        run([*args,"--out",STRESS],"stress_execution")
        report["stress"]=audit(STRESS,.95,1.6,sample)
        figure(report["reference"]+report["stress"])
        report["status"]="COMPLETE_AUDITED_ANNUAL_COMPARISON"
    except Exception as e:
        report["error"]=repr(e);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name!="REMOTE_REPORT.json"}
        save(OUT/"REMOTE_REPORT.json",report)
        print("RESEARCH_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"]=="COMPLETE_AUDITED_ANNUAL_COMPARISON" else 1
if __name__=="__main__":raise SystemExit(main())
