#!/usr/bin/env python3
"""Study A matched-hardware control, A1 -> A0 113699 min-cost single-feeder pilot.

Fix all PV/BESS/inverter equipment at the SAME transformer when customer
membership changes. All 2025 load and solar source evidence remains signed.
This runs one 8,760-hour PyPSA energy dispatch, not an AC validation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PVBESS=Path("case1/studies/SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py")
FIXED=Path("case1/studies/ac_aware_redispatch_v1/fixed_hardware.py")
TRIAL_CASE={"donor":"A1","target":"A0","transformer":"113699",
            "tier":"min_cost","donor_suffix":"ref",
            "target_suffix":"four"}
OUTPUT_STEM="StudyA_A0_A1_MatchedHardware_113699_Pilot_v"

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def signed_bytes(path,sha_expected):
    """Accept exact original SHA, or only Git LF bytes reconstructing signed CRLF."""
    b=Path(path).read_bytes()
    if hashlib.sha256(b).hexdigest()==sha_expected:
        return "EXACT"
    if b"\r" not in b and b"\n" in b:
        if hashlib.sha256(b.replace(b"\n",b"\r\n")).hexdigest()==sha_expected:
            return "SIGNED_CRLF_RECONSTRUCTED_FROM_GIT_LF"
    raise ValueError("Source SHA mismatch: "+str(path))

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

def donor_path(repo,pv):
    return repo/pv.BASE_REL/"energy_A1_113699_min_cost_ref"

def signed_donor(repo,pv,m,mapping,profiles):
    """Check donor hourly source and physical rating, without editing the donor."""
    ids,load=pv.source_trace(m,mapping,profiles,"A1","113699")
    folder=donor_path(repo,pv)
    meta=json.loads((folder/"energy_manifest.json").read_text(encoding="utf-8"))
    source_file=folder/"energy_hourly_2025.csv"
    csv_mode=signed_bytes(source_file,meta["energy_csv_sha256"])
    manifest_mode=signed_bytes(repo/pv.MANIFEST_REL,meta["input_manifest_sha256"])
    if (meta.get("scenario")!="A1" or meta.get("transformer")!="113699" or
        meta.get("selected_house_ids")!=ids or meta.get("hardware_selection_tier")!="min_cost" or
        meta.get("status")!="FULL_8760H_PYPSA_FIXED_HARDWARE_NOT_AC_VALIDATED"):
        raise ValueError("Unexpected source donor identity or status")
    hw=meta["hardware"]
    required=("pv_panels","battery_modules","battery_power_dc_kw",
              "inverter_kva","transformer_kva_assumed_or_evidenced")
    if not all(k in hw for k in required):
        raise ValueError("Incomplete donor hardware specification")
    if (int(hw["pv_panels"])!=20 or int(hw["battery_modules"])!=4 or
        abs(float(hw["battery_power_dc_kw"])-6.439699033049508)>1e-7 or
        float(hw["inverter_kva"])!=6 or
        float(hw["transformer_kva_assumed_or_evidenced"])!=3):
        raise ValueError("The known A1 113699 source hardware has changed")
    if float(hw["battery_power_dc_kw"]) > int(hw["battery_modules"])*2.24+1e-8:
        raise ValueError("Source exceeds manufacturer continuous battery power screen")
    f=pd.read_csv(source_file,parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    if len(f)!=8760 or not f.index.equals(load.index) or f.index.has_duplicates:
        raise ValueError("Original donor dispatch timebase incomplete")
    if (np.max(np.abs(f.demand_kw.to_numpy(float)-load.sum(axis=1).to_numpy(float)))>1e-5
        or f.grid_export_kw.abs().max()>1e-5 or f.unserved_kw.abs().max()>1e-5):
        raise ValueError("Donor energy chronology or zero-export/no-ENS checks failed")
    summary=meta.get("source_model_summary") or meta.get("model_summary")
    if not summary or not np.isfinite(float(summary["annual_equipment_usd"])):
        raise ValueError("Missing donor annualized hardware equipment source")
    return meta,summary,{"energy_csv_signed_sha256":meta["energy_csv_sha256"],
                        "energy_sha_mode":csv_mode,
                        "source_manifest_sha_mode":manifest_mode,
                        "energy_manifest_checkout_sha256":digest(folder/"energy_manifest.json")}

def preflight(repo):
    repo=repo.resolve()
    if not (repo/".git").is_dir():
        raise ValueError("Use the full original Git checkout")
    pv=module(repo/PVBESS,"signed_matched_hardware_studya")
    m,v6,mapping,profiles=pv.secure_context(repo,repo/pv.MANIFEST_REL)
    source,summary,checks=signed_donor(repo,pv,m,mapping,profiles)
    old_ids,old_trace=pv.source_trace(m,mapping,profiles,"A0","113699")
    new_ids,new_trace=pv.source_trace(m,mapping,profiles,"A1","113699")
    assert len(old_ids)==4 and len(new_ids)==6
    assert set(new_ids)-set(old_ids)=={"H03","H06"}
    assert set(old_ids).issubset(set(new_ids))
    assert abs(old_trace.to_numpy(float).sum()-4*1898.)<.1
    assert abs(new_trace.to_numpy(float).sum()-6*1898.)<.1
    solar,solar_path=pv.solar_per_unit(repo,old_trace.index)
    solar_mode=signed_bytes(solar_path,source["original_pv_source_sha256"])
    report={
       "status":"SIGNED_MATCHED_HARDWARE_PILOT_PREFLIGHT_PASS_NO_SOLVE",
       "donor":{"assignment":"A1","transformer":"113699",
                "houses":new_ids,"annual_demand_kwh":float(new_trace.to_numpy(float).sum())},
       "target":{"assignment":"A0","transformer":"113699",
                 "houses":old_ids,"annual_demand_kwh":float(old_trace.to_numpy(float).sum())},
       "same_unchanged_transformer":"113699",
       "exact_donor_hardware":source["hardware"],
       "source_original_annual_equipment_usd":float(summary["annual_equipment_usd"]),
       "source_evidence":checks,
       "solar_mode":solar_mode,
       "input_manifest_signed_sha256":source["input_manifest_sha256"],
       "solar_signed_sha256":source["original_pv_source_sha256"],
       "source_original_solver_sha256":source.get("source_model_sha256"),
       "assumptions":{"battery_min_physical_soc":.20,
         "zero_export":True,"zero_unserved":True,"annual_hours":8760,
         "source_household_profiles":"signed 2025 distinct profiles",
         "new_annual_ac_cases":0,"grid_stress_pf":.98},
       "interpretation":"New cohort energy LP only. NO new annual pandapower AC, no same-population combined result, no field feasibility."}
    return pv,v6,source,summary,old_trace,solar,report

def choose_output(repo):
    return next((repo/(OUTPUT_STEM+str(i)) for i in range(1,1000)
                 if not (repo/(OUTPUT_STEM+str(i))).exists()),None)

def run(repo,out=None,preflight_only=False):
    pv,v6,source,source_summary,trace,solar,report=preflight(repo)
    if preflight_only:
        return report
    if out is None:
        out=choose_output(repo)
        if out is None:raise FileExistsError("No unused versioned output")
    else:
        out=Path(out)
        if not out.is_absolute():out=repo/out
        out=out.resolve()
    if out.exists():raise FileExistsError("Refuse to overwrite: "+str(out))
    fixed=module(repo/FIXED,"matched_hardware_fixed_original")
    hw=source["hardware"]
    original=fixed.Hardware(
        panels=int(hw["pv_panels"]),battery_modules=int(hw["battery_modules"]),
        battery_power_dc_kw=float(hw["battery_power_dc_kw"]),
        inverter_kva=float(hw["inverter_kva"]),
        transformer_kva=float(hw["transformer_kva_assumed_or_evidenced"]),
        loading_pu=1.0,load_pf=.98,export_policy="zero",
        annual_equipment_usd=float(source_summary["annual_equipment_usd"]),
        annual_total_usd=float(source_summary["annual_total_usd"]))
    frame,model_summary=fixed.solve_fixed(
        repo,original,trace.sum(axis=1),solar,min_physical_soc=.20)
    frame.index.name="timestamp_lst"
    if len(frame)!=8760 or not frame.index.equals(trace.index):
        raise ValueError("Target PyPSA energy dispatch missing timestamps")
    if (np.max(np.abs(frame.demand_kw.to_numpy(float)-
                       trace.sum(axis=1).to_numpy(float)))>1e-5 or
        frame.grid_export_kw.abs().max()>1e-5 or
        frame.unserved_kw.abs().max()>1e-5):
        raise ValueError("Target dispatch does not balance signed demand")
    if (abs(float(model_summary["annual_equipment_usd"])-
            float(source_summary["annual_equipment_usd"]))>.02):
        raise ValueError("Hardware annuity changed despite identical fixed device ratings")
    metric=v6.metrics_for_dispatch(frame,int(hw["battery_modules"]))
    for k in ("grid_import_kwh","available_pv_dc_kwh","curtailed_pv_dc_kwh"):
        if not np.isfinite(float(metric[k])):raise ValueError("Nonfinite "+k)
    out.mkdir(parents=True,exist_ok=False)
    csv_path=out/"energy_hourly_2025.csv"
    frame.to_csv(csv_path,float_format="%.10f")
    receipt={**report,
      "status":"ENERGY_ONLY_MATCHED_HARDWARE_PILOT_PASS_AC_PENDING",
      "output_folder":str(out),
      "target_yearly_energy_metrics":metric,
      "target_model_summary":model_summary,
      "target_energy_csv_sha256":digest(csv_path),
      "runner_sha256":digest(Path(__file__)),
      "source_fixed_model_sha256":digest(repo/FIXED),
      "new_annual_ac_cases":0,
      "source_hardware_unchanged":True}
    (out/"RUN_MANIFEST.json").write_text(
        json.dumps(receipt,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return {"status":receipt["status"],"out":str(out),
            "target_households":len(report["target"]["houses"]),
            "grid_import_kwh":metric["grid_import_kwh"],
            "curtailment_kwh":metric["curtailed_pv_dc_kwh"],
            "annual_cost_usd":float(model_summary["annual_total_usd"]),
            "ac_cases":0}

def cli(argv=None):
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument("--repo-root",type=Path,default=Path.cwd())
    pa.add_argument("--out",type=Path)
    pa.add_argument("--preflight-only",action="store_true")
    args=pa.parse_args(argv)
    print(json.dumps(run(args.repo_root.resolve(),args.out,args.preflight_only),
                     indent=2,allow_nan=False))
if __name__=="__main__":
    cli()
