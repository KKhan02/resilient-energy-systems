#!/usr/bin/env python3
"""Same-PV/BESS/inverter comparison: A0/A1 matched 34-house Study A.

A named transformer retains EXACT signed source hardware while receiving the
other assignment's household load. No historical files changed. No AC claim.
Reuses the signed first pilot. One reverse case first, then 16-case full batch.
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
PVBESS=Path("case1/studies/SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py")
FIXED=Path("case1/studies/ac_aware_redispatch_v1/fixed_hardware.py")
ROSTER=HERE/"MATCHED_HARDWARE_16_SOURCE_PLAN.csv"
SIGNED_PILOT=Path("StudyA_A0_A1_MatchedHardware_113699_Pilot_v1")
MODELLED=("106039","94022","113699","85398")
TIERS=("min_cost","ss90")
ASSIGNMENTS=("A0","A1")
SAME_92395={"min_cost":"energy_A0_92395_min_cost_four","ss90":"energy_A0_92395_ss90_four"}
BASE_PART=Path("case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01")
REVERSE_KEY="A0_113699_min_cost_to_A1"
PILOT_KEY="A1_113699_min_cost_to_A0"
VERSION_PREFIX={"reverse":"StudyA_A0_A1_MatchedHardware_ReversePilot_v",
                "full":"StudyA_A0_A1_MatchedHardware_Full_v"}
METRICS=("demand_kwh","grid_import_kwh","curtailed_pv_dc_kwh",
         "battery_discharge_dc_kwh","battery_charge_dc_kwh",
         "available_pv_dc_kwh")

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for data in iter(lambda:f.read(1<<20),b""):
            h.update(data)
    return h.hexdigest()

def checked_bytes(path,expected):
    """Exact SHA or only known Git LF representation of an original CRLF file."""
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()==expected:
        return "EXACT"
    if b"\r" not in raw and b"\n" in raw:
        if hashlib.sha256(raw.replace(b"\n",b"\r\n")).hexdigest()==expected:
            return "GIT_LF_EQUALS_SIGNED_CRLF"
    raise ValueError("Signed source differs: "+str(path))

def load_module(file,name):
    spec=importlib.util.spec_from_file_location(name,file)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(file)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def key(row):
    return f"{row['donor_assignment']}_{row['transformer']}_{row['tier']}_to_{row['target_assignment']}"

def hardware_fields(info):
    hw=info["hardware"]
    return {"pv_panels":int(hw["pv_panels"]),
            "battery_modules":int(hw["battery_modules"]),
            "battery_power_dc_kw":float(hw["battery_power_dc_kw"]),
            "inverter_kva":float(hw["inverter_kva"]),
            "transformer_kva_assumed_or_evidenced":float(hw["transformer_kva_assumed_or_evidenced"])}

def source_slug(row):
    return "energy_"+row["source_family"]

def load_roster(repo,manifest):
    rows=pd.read_csv(repo/ROSTER,dtype={"transformer":str}).to_dict("records")
    if len(rows)!=16 or len({key(r) for r in rows})!=16:
        raise ValueError("Exactly 16 distinct reciprocal source entries required")
    expected={f"{d}_{t}_{tier}_to_{'A1' if d=='A0' else 'A0'}"
              for d in ASSIGNMENTS for t in MODELLED for tier in TIERS}
    if {key(r) for r in rows}!=expected:
        raise ValueError("Source roster changes reciprocal experiment set")
    for row in rows:
        donor,target,tr=row["donor_assignment"],row["target_assignment"],row["transformer"]
        if (row["status"]!="NOT_EXECUTED" or row["AC_evidence"]!="PENDING" or
            row["pilot_priority"] not in ("FIRST_LOCAL_ENERGY_PILOT","AFTER_PILOT_AUDIT")):
            raise ValueError("This roster is a planned input, not a completed AC result")
        if (row["donor_house_ids"].split(";")!=manifest["groups"][donor][tr] or
            row["target_house_ids"].split(";")!=manifest["groups"][target][tr]):
            raise ValueError("Household membership changed in planned source roster")
    return rows

def validate_dispatch(frame,trace,hw,expected_metrics=None):
    required={"demand_kw","grid_import_kw","grid_export_kw","unserved_kw",
              "pv_dc_available_kw","curtailed_pv_dc_kw","battery_charge_dc_kw",
              "battery_discharge_dc_kw","inverter_ac_kw","battery_soc_usable_kwh"}
    if (not required.issubset(frame.columns) or len(frame)!=8760 or
        frame.index.has_duplicates or not frame.index.equals(trace.index)):
        raise ValueError("Missing columns or 2025 hourly trace")
    a=frame[list(required)].to_numpy(float)
    if not np.isfinite(a).all():
        raise ValueError("Nonfinite dispatch data")
    if np.max(np.abs(frame.demand_kw.to_numpy(float)-trace.sum(axis=1).to_numpy(float)))>1e-5:
        raise ValueError("Changed household demand/profile")
    if frame.grid_export_kw.abs().max()>1e-5 or frame.unserved_kw.abs().max()>1e-5:
        raise ValueError("Source or target violates zero export/ENS")
    if ((frame.battery_charge_dc_kw.to_numpy(float)>1e-5)&
        (frame.battery_discharge_dc_kw.to_numpy(float)>1e-5)).any():
        raise ValueError("Simultaneous battery charge/discharge")
    if frame.inverter_ac_kw.abs().max()>hw["inverter_kva"]+1e-5:
        raise ValueError("Inverter active-power rating")
    if (frame.battery_charge_dc_kw.max()>hw["battery_power_dc_kw"]+1e-5 or
        frame.battery_discharge_dc_kw.max()>hw["battery_power_dc_kw"]+1e-5):
        raise ValueError("Battery charge/discharge power")
    floor=hw["battery_modules"]*(17.3/4-(1-.20)*5.12)
    cap=hw["battery_modules"]*(17.3/4)
    soc=frame.battery_soc_usable_kwh.to_numpy(float)
    if soc.min()<floor-1e-5 or soc.max()>cap+1e-5:
        raise ValueError("Physical 20% SOC floor or nominal usable Store cap")
    eta=np.sqrt(.95)
    residual=soc-np.roll(soc,1)-eta*frame.battery_charge_dc_kw.to_numpy(float)+frame.battery_discharge_dc_kw.to_numpy(float)/eta
    if np.max(np.abs(residual))>1e-3:
        raise ValueError("Cyclic battery SOC energy balance")
    metrics={"demand_kwh":float(frame.demand_kw.sum()),
            "grid_import_kwh":float(frame.grid_import_kw.sum()),
            "curtailed_pv_dc_kwh":float(frame.curtailed_pv_dc_kw.sum()),
            "battery_discharge_dc_kwh":float(frame.battery_discharge_dc_kw.sum()),
            "battery_charge_dc_kwh":float(frame.battery_charge_dc_kw.sum()),
            "available_pv_dc_kwh":float(frame.pv_dc_available_kw.sum())}
    if expected_metrics is not None:
        for k in METRICS:
            if abs(metrics[k]-float(expected_metrics[k]))>2e-4:
                raise ValueError("Saved energy metrics differ: "+k)
    return metrics

def signed_energy(repo,pv,manifest,mapping,profiles,scenario,transformer,tier,kind):
    suffix="four" if kind=="four" else "ref"
    slug=f"energy_{scenario}_{transformer}_{tier}_{suffix}"
    folder=repo/BASE_PART/slug
    j=json.loads((folder/"energy_manifest.json").read_text(encoding="utf-8"))
    ids,trace=pv.source_trace(manifest,mapping,profiles,scenario,transformer)
    if (j.get("scenario")!=scenario or j.get("transformer")!=transformer or
        j.get("selected_house_ids")!=ids or j.get("hardware_selection_tier")!=tier or
        j.get("status") not in
            ("FULL_8760H_PYPSA_FIXED_HARDWARE_NOT_AC_VALIDATED",
             "FULL_8760H_NEW_FOUR_HOUSE_MILP_ENERGY_ONLY_NOT_AC_VALIDATED")):
        raise ValueError("Incorrect signed source cohort: "+slug)
    if (suffix=="four")!=(j["status"]=="FULL_8760H_NEW_FOUR_HOUSE_MILP_ENERGY_ONLY_NOT_AC_VALIDATED"):
        raise ValueError("Mixed four-house MILP and borrowed hardware sources: "+slug)
    if j["input_manifest_sha256"]!=sha(repo/pv.MANIFEST_REL):
        raise ValueError("Historical input manifest changed: "+slug)
    csv=folder/"energy_hourly_2025.csv"
    mode=checked_bytes(csv,j["energy_csv_sha256"])
    frame=pd.read_csv(csv,parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    hw=hardware_fields(j)
    metrics=validate_dispatch(frame,trace,hw,j["metrics"])
    summary=j.get("source_model_summary") or j.get("model_summary")
    if not summary or summary.get("status")!="OPTIMAL_ENERGY_ONLY_NO_AC_VALIDATION":
        raise ValueError("Original source model energy optimum missing: "+slug)
    return {"slug":slug,"json":j,"summary":summary,"hw":hw,"metrics":metrics,
            "csv_signed_sha256":j["energy_csv_sha256"],"manifest_checkout_sha256":sha(folder/"energy_manifest.json"),
            "source_csv_hash_mode":mode,"trace":trace}

def exact_device_pair(first,second):
    """Only all four converter/storage fields and rating match. No tolerance."""
    fields=("pv_panels","battery_modules","battery_power_dc_kw","inverter_kva",
            "transformer_kva_assumed_or_evidenced")
    return all(first["hw"][f]==second["hw"][f] for f in fields)

def signed_existing_cross_reuse(roster,originals):
    """Source-specific same-hardware opposite original energy for that same feeder."""
    cross={}
    for row in roster:
        k=key(row)
        opposite=next((z for z in roster
                      if z["donor_assignment"]==row["target_assignment"]
                      and z["transformer"]==row["transformer"]
                      and z["tier"]==row["tier"]),None)
        if opposite is None:raise ValueError("Missing opposite assignment")
        orig=originals[k]
        other=originals[key(opposite)]
        if exact_device_pair(orig,other):
            if (orig["json"]["original_pv_source_sha256"]!=
                other["json"]["original_pv_source_sha256"] or
                orig["json"]["input_manifest_sha256"]!=other["json"]["input_manifest_sha256"]):
                raise ValueError("Cannot reuse identical hardware with different solar/demand sources")
            if abs(float(orig["summary"]["annual_equipment_usd"])-
                   float(other["summary"]["annual_equipment_usd"]))>.02:
                raise ValueError("Same hardware annual equipment annuity differs")
            cross[k]=other
    return cross

def verify_pilot(repo,row,target_trace,source):
    folder=repo/SIGNED_PILOT
    manifest_path=folder/"RUN_MANIFEST.json"
    receipt=json.loads(manifest_path.read_text(encoding="utf-8"))
    if (receipt.get("status")!="ENERGY_ONLY_MATCHED_HARDWARE_PILOT_PASS_AC_PENDING" or
        receipt.get("new_annual_ac_cases")!=0 or
        receipt.get("target",{}).get("assignment")!="A0" or
        receipt.get("target",{}).get("transformer")!="113699" or
        receipt.get("target",{}).get("houses")!=row["target_house_ids"].split(";") or
        receipt.get("donor",{}).get("houses")!=row["donor_house_ids"].split(";") or
        receipt.get("exact_donor_hardware")!=source["json"]["hardware"] or
        receipt.get("source_evidence",{}).get("energy_csv_signed_sha256")!=source["csv_signed_sha256"]):
        raise ValueError("Original user pilot source/hardware no longer matches signed study")
    f=folder/"energy_hourly_2025.csv"
    mode=checked_bytes(f,receipt["target_energy_csv_sha256"])
    df=pd.read_csv(f,parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    result=validate_dispatch(df,target_trace,source["hw"],receipt["target_yearly_energy_metrics"])
    if abs(float(receipt["target_model_summary"]["annual_equipment_usd"])-
           float(source["summary"]["annual_equipment_usd"]))>.02:
        raise ValueError("Signed original pilot did not preserve hardware annuity")
    return {"sha":receipt["target_energy_csv_sha256"],
            "sha_mode":mode,"manifest_sha256":sha(manifest_path),
            "relative_csv":str((SIGNED_PILOT/"energy_hourly_2025.csv")).replace("\\","/"),
            "metrics":result,"summary":receipt["target_model_summary"]}

def preflight(repo):
    repo=Path(repo).resolve()
    if not (repo/".git").is_dir():
        raise ValueError("Must execute from the genuine Git checkout")
    pv=load_module(repo/PVBESS,"matched_hardware_signed_pvbess")
    manifest,v6,mapping,profiles=pv.secure_context(repo,repo/pv.MANIFEST_REL)
    solar,solar_path=pv.solar_per_unit(repo,profiles.index)
    roster=load_roster(repo,manifest)
    originals={}
    for row in roster:
        donor,tier,transformer=row["donor_assignment"],row["tier"],row["transformer"]
        kind="four" if row["source_family"].endswith("_four") else "ref"
        source=signed_energy(repo,pv,manifest,mapping,profiles,donor,transformer,tier,kind)
        if source["slug"]!=source_slug(row):
            raise ValueError("Source named equipment family differs: "+key(row))
        hw=source["hw"]
        for field,expected in (("pv_panels",row["pv_panels"]),
                               ("battery_modules",row["battery_modules"]),
                               ("battery_power_dc_kw",row["battery_power_dc_kw"]),
                               ("inverter_kva",row["inverter_kva"]),
                               ("transformer_kva_assumed_or_evidenced",row["transformer_assumed_kva"])):
            if abs(float(hw[field])-float(expected))>1e-7:
                raise ValueError("Hardware roster/source mismatch "+key(row)+"/"+field)
        if (source["json"]["original_pv_source_sha256"]!=sha(solar_path)):
            raise ValueError("Solar source checksum mismatch: "+key(row))
        originals[key(row)]=source
    shared={}
    for tier,slug in SAME_92395.items():
        v=signed_energy(repo,pv,manifest,mapping,profiles,"A0","92395",tier,"four")
        if v["slug"]!=slug:raise ValueError("Changed 92395 common STAR source")
        if v["json"]["original_pv_source_sha256"]!=sha(solar_path):
            raise ValueError("92395 signed solar mismatch")
        shared[tier]=v
    row=next(r for r in roster if key(r)==PILOT_KEY)
    _,pilot_trace=pv.source_trace(manifest,mapping,profiles,"A0","113699")
    pilot=verify_pilot(repo,row,pilot_trace,originals[PILOT_KEY])
    cross=signed_existing_cross_reuse(roster,originals)
    if PILOT_KEY in cross:
        raise ValueError("Original 113699 pilot must not be replaced by unrelated original hardware")
    if set(cross)!={"A0_106039_min_cost_to_A1","A1_106039_min_cost_to_A0"}:
        raise ValueError("Unexpected source-equivalent hardware pairs; reassess experiment")
    receipt={
        "status":"SIGNED_MATCHED_HARDWARE_16_SOURCE_PREFLIGHT_NO_NEW_SOLVES",
        "source_hardware_case_count":len(originals),
        "common_92395_STAR_reference_count":len(shared),
        "previous_source_matched_pilot_reused":PILOT_KEY,
        "preexisting_pilot_manifest_sha256":pilot["manifest_sha256"],
        "existing_exact_hardware_source_reuse":{
            k:v["csv_signed_sha256"] for k,v in cross.items()},
        "input_manifest_sha256":sha(repo/pv.MANIFEST_REL),
        "solar_sha256":sha(solar_path),
        "fixed_solver_sha256":sha(repo/FIXED),
        "source_roster_sha256":sha(repo/ROSTER),
        "source_manifest_shas":{k:v["manifest_checkout_sha256"] for k,v in originals.items()},
        "new_AC_cases":0,
        "main_network_AC_validated":False,
        "scope_comment":"A0 and A1 memberships share 34 distinct household profiles. 92395 unchanged proposed STAR."}
    return pv,v6,manifest,mapping,profiles,solar,roster,originals,shared,pilot,cross,receipt

def select_keys(roster,scope):
    keys=[key(x) for x in roster]
    return [REVERSE_KEY] if scope=="reverse" else keys

def output_path(repo,scope):
    stem=VERSION_PREFIX[scope]
    return next((repo/(stem+str(j)) for j in range(1,1000)
                 if not (repo/(stem+str(j))).exists()),None)

def result_for_source(row,original,target_model,metrics,csv_rel,signature,mode,method):
    return {"status":"COMPLETE_SOURCE_VERIFIED_ENERGY_ONLY_AC_PENDING",
            "source_case":key(row),"assignment_for_hardware":row["donor_assignment"],
            "assignment_for_load":row["target_assignment"],"transformer":row["transformer"],
            "tier":row["tier"],"origin_source_family":row["source_family"],
            "donor_house_ids":row["donor_house_ids"].split(";"),
            "target_house_ids":row["target_house_ids"].split(";"),
            "same_physical_transformer":True,"same_hardware":True,
            "hardware":original["hw"],
            "source_energy_csv_sha256":original["csv_signed_sha256"],
            "source_energy_manifest_sha256":original["manifest_checkout_sha256"],
            "target_energy_csv":csv_rel,"target_energy_sha256":signature,
            "target_energy_sha_mode":mode,
            "target_yearly_energy_metrics":metrics,
            "target_model_summary":target_model,
            "source_model_summary":original["summary"],
            "source_original_energy_metrics":original["metrics"],
            "method":method,
            "AC_verified":False}

def simulate_new(repo,pv,v6,trace,solar,original,out,casekey):
    fixed=load_module(repo/FIXED,"matched_hardware_fixed_hardware")
    h=original["hw"]
    hw=fixed.Hardware(
        panels=h["pv_panels"],battery_modules=h["battery_modules"],
        battery_power_dc_kw=h["battery_power_dc_kw"],
        inverter_kva=h["inverter_kva"],
        transformer_kva=h["transformer_kva_assumed_or_evidenced"],
        loading_pu=1.,load_pf=.98,export_policy="zero",
        annual_equipment_usd=float(original["summary"]["annual_equipment_usd"]),
        annual_total_usd=float(original["summary"]["annual_total_usd"]))
    frame,summary=fixed.solve_fixed(repo,hw,trace.sum(axis=1),
                                    solar,min_physical_soc=.20)
    frame.index.name="timestamp_lst"
    metrics=validate_dispatch(frame,trace,h)
    if abs(float(summary["annual_equipment_usd"])-
           float(original["summary"]["annual_equipment_usd"]))>.02:
        raise ValueError("Same equipment annuity changed")
    if abs(float(summary["annual_total_usd"])-
           float(summary["annual_equipment_usd"])-
           float(summary["annual_grid_import_usd"]))>.02:
        raise ValueError("Target total costs inconsistent")
    if abs(float(summary["annual_grid_import_usd"])-
           .29*metrics["grid_import_kwh"])>.02:
        raise ValueError("Unexpected grid tariff in source fixed LP")
    if abs(metrics["demand_kwh"]-len(trace.columns)*1898.)>.1:
        raise ValueError("Wrong household annual demand")
    dest=out/casekey
    if dest.exists():raise FileExistsError("Existing partial output: "+str(dest))
    dest.mkdir(parents=True,exist_ok=False)
    csv=dest/"energy_hourly_2025.csv"
    frame.to_csv(csv,float_format="%.10f")
    if "timestamp_lst" not in pd.read_csv(csv,nrows=1).columns:
        raise ValueError("Missing timestamp column in saved CSV")
    return metrics,summary,str(csv.relative_to(repo)).replace("\\","/"),sha(csv)

def save_case(out,casekey,row):
    folder=out/casekey
    folder.mkdir(exist_ok=True)
    receipt=folder/"CASE_RECEIPT.json"
    if receipt.exists():raise FileExistsError("Already saved complete case "+casekey)
    receipt.write_text(json.dumps(row,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def ensure_completed_case(repo,out,casekey,row,source,target_trace):
    receipt=out/casekey/"CASE_RECEIPT.json"
    if not receipt.is_file():
        raise ValueError("Missing saved case receipt: "+casekey)
    j=json.loads(receipt.read_text(encoding="utf-8"))
    if j!=row:
        raise ValueError("Top-level manifest and saved case receipt differ: "+casekey)
    if (j["source_energy_csv_sha256"]!=source["csv_signed_sha256"] or
        j["source_energy_manifest_sha256"]!=source["manifest_checkout_sha256"] or
        j["hardware"]!=source["hw"] or j["AC_verified"] is not False):
        raise ValueError("Source/hardware changed during resume")
    f=repo/j["target_energy_csv"]
    checked_bytes(f,j["target_energy_sha256"])
    frame=pd.read_csv(f,parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    validate_dispatch(frame,target_trace,source["hw"],j["target_yearly_energy_metrics"])
    return j

def csv_table(rows,path):
    cols=list(rows[0])
    pd.DataFrame(rows)[cols].to_csv(path,index=False,float_format="%.10f")
    return sha(path)

def recombine(originals,shared,completed,roster):
    result=[]
    for hardware_origin in ASSIGNMENTS:
        for tier in TIERS:
            for assignment in ASSIGNMENTS:
                pieces=[]
                for tr in MODELLED:
                    origin=next(r for r in roster if r["donor_assignment"]==hardware_origin
                                and r["tier"]==tier and r["transformer"]==tr)
                    original=originals[key(origin)]
                    if assignment==hardware_origin:
                        metrics=original["metrics"]
                        summary=original["summary"]
                    else:
                        receipt=completed[key(origin)]
                        metrics=receipt["target_yearly_energy_metrics"]
                        summary=receipt["target_model_summary"]
                    pieces.append((original["hw"],metrics,summary))
                q=shared[tier]
                pieces.append((q["hw"],q["metrics"],q["summary"]))
                total=lambda getter:sum(float(getter(item)) for item in pieces)
                demand=total(lambda x:x[1]["demand_kwh"])
                if abs(demand-64532.)>.1:
                    raise ValueError("34-house common population differs")
                imports=total(lambda x:x[1]["grid_import_kwh"])
                equipment=total(lambda x:x[2]["annual_equipment_usd"])
                gridcost=total(lambda x:x[2]["annual_grid_import_usd"])
                totalcost=total(lambda x:x[2]["annual_total_usd"])
                if abs(equipment+gridcost-totalcost)>.1:
                    raise ValueError("Incorrect component annualized cost sum")
                result.append({
                    "hardware_origin":hardware_origin,
                    "load_assignment":assignment,"tier":tier,
                    "households":34,"annual_demand_kwh":demand,
                    "pv_panels":int(total(lambda x:x[0]["pv_panels"])),
                    "battery_modules":int(total(lambda x:x[0]["battery_modules"])),
                    "inverter_kva_sum":total(lambda x:x[0]["inverter_kva"]),
                    "annual_grid_import_kwh":imports,
                    "self_sufficiency_pct":100*(1-imports/demand),
                    "annual_curtailment_dc_kwh":total(lambda x:x[1]["curtailed_pv_dc_kwh"]),
                    "annual_battery_discharge_dc_kwh":total(lambda x:x[1]["battery_discharge_dc_kwh"]),
                    "annual_equipment_usd":equipment,
                    "annual_grid_cost_usd":gridcost,
                    "annual_total_usd":totalcost,
                    "AC_verified":False,
                    "shared_92395_proposed_STAR":True})
    if len(result)!=8:raise ValueError("Missing matched portfolios")
    pairs=[]
    for origin in ASSIGNMENTS:
        for tier in TIERS:
            a=next(x for x in result if x["hardware_origin"]==origin
                   and x["tier"]==tier and x["load_assignment"]=="A0")
            b=next(x for x in result if x["hardware_origin"]==origin
                   and x["tier"]==tier and x["load_assignment"]=="A1")
            for k in ("pv_panels","battery_modules","inverter_kva_sum","annual_equipment_usd"):
                if abs(a[k]-b[k])>1e-6:
                    raise ValueError("Matched hardware not equal: "+origin+":"+tier+":"+k)
            pairs.append({"hardware_origin":origin,"tier":tier,
                "A0_annual_total_usd":a["annual_total_usd"],
                "A1_annual_total_usd":b["annual_total_usd"],
                "A1_minus_A0_annual_total_usd":b["annual_total_usd"]-a["annual_total_usd"],
                "A0_import_kwh":a["annual_grid_import_kwh"],
                "A1_import_kwh":b["annual_grid_import_kwh"],
                "A1_minus_A0_import_kwh":b["annual_grid_import_kwh"]-a["annual_grid_import_kwh"],
                "A1_minus_A0_curtailment_kwh":b["annual_curtailment_dc_kwh"]-a["annual_curtailment_dc_kwh"],
                "AC_verified":False})
    return result,pairs

def run(repo,scope="reverse",preflight_only=False,out=None,resume=False):
    repo=Path(repo).resolve()
    pv,v6,manifest,mapping,profiles,solar,roster,originals,shared,pilot,cross,receipt=preflight(repo)
    selected=select_keys(roster,scope)
    receipt.update({"scope":scope,"expected_case_count":len(selected),
                    "selected_case_keys":selected,
                    "expected_new_2025_LP_solves":len(selected)-
                        (1 if PILOT_KEY in selected else 0)-
                        sum(k in cross for k in selected),
                    "completed_cases":{},"errors":{},
                    "runner_sha256":sha(Path(__file__))})
    if preflight_only:
        return receipt
    if out is None:
        out=output_path(repo,scope)
        if out is None:raise FileExistsError("Output versions exhausted")
    else:
        out=Path(out)
        if not out.is_absolute():out=repo/out
        out=out.resolve()
    outmanifest=out/"RUN_MANIFEST.json"
    if resume:
        if not outmanifest.is_file():
            raise ValueError("--resume requires saved incomplete manifest")
        prev=json.loads(outmanifest.read_text(encoding="utf-8"))
        if prev.get("status")!="INCOMPLETE_MATCHED_HARDWARE_ENERGY":
            raise ValueError("Resume only unfinished output")
        for k in ("scope","expected_case_count","selected_case_keys","runner_sha256",
                  "source_roster_sha256","input_manifest_sha256","solar_sha256",
                  "fixed_solver_sha256","source_manifest_shas","preexisting_pilot_manifest_sha256",
                  "existing_exact_hardware_source_reuse"):
            if prev.get(k)!=receipt.get(k):
                raise ValueError("Source/runner identity changed: "+k)
        receipt=prev
    else:
        if out.exists():raise FileExistsError("Refuse overwrite: "+str(out))
        out.mkdir(parents=True)
        receipt["status"]="INCOMPLETE_MATCHED_HARDWARE_ENERGY"
        receipt["output_folder"]=str(out)
        outmanifest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    if not set(receipt["completed_cases"]).issubset(set(selected)):
        raise ValueError("Completed case outside selected scope")
    for r in roster:
        casekey=key(r)
        if casekey not in selected:continue
        original=originals[casekey]
        _,target_trace=pv.source_trace(manifest,mapping,profiles,
                                        r["target_assignment"],r["transformer"])
        if casekey in receipt["completed_cases"]:
            ensure_completed_case(repo,out,casekey,receipt["completed_cases"][casekey],
                                  original,target_trace)
            print("REUSED VERIFIED COMPLETED "+casekey,flush=True)
            continue
        if (out/casekey).exists():
            raise FileExistsError("Partial case output must be manually inspected: "+str(out/casekey))
        try:
            if casekey==PILOT_KEY:
                metrics=pilot["metrics"]
                summary=pilot["summary"]
                csv_rel=pilot["relative_csv"]
                checksha=pilot["sha"]
                mode="SIGNED_PREVIOUS_PILOT_REUSED_"+pilot["sha_mode"]
                method="PRIOR_USER_SIGNED_8760H_PILOT"
            elif casekey in cross:
                matched=cross[casekey]
                metrics=matched["metrics"]
                summary=matched["summary"]
                csv_rel=str((BASE_PART/matched["slug"]/"energy_hourly_2025.csv")).replace("\\","/")
                checksha=matched["csv_signed_sha256"]
                mode="SIGNED_SAME_HARDWARE_EXISTING_OPPOSITE_SOURCE_"+matched["source_csv_hash_mode"]
                method="ORIGINAL_SIGNED_EXACT_SAME_HARDWARE_AND_TARGET_FEEDER"
            else:
                metrics,summary,csv_rel,checksha=simulate_new(
                    repo,pv,v6,target_trace,solar,original,out,casekey)
                mode="NEW_USER_LOCAL_FIXED_HARDWARE_2025_LP"
                method="NEW_8760H_PYPSA_EXACT_SAME_HARDWARE"
            row=result_for_source(r,original,summary,metrics,csv_rel,checksha,mode,method)
            save_case(out,casekey,row)
            receipt["completed_cases"][casekey]=row
            outmanifest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",encoding="utf-8")
            print("COMPLETE "+casekey+" annual imports="+
                  f"{metrics['grid_import_kwh']:.4f} kWh",flush=True)
        except Exception as exc:
            receipt["errors"][casekey]={"type":type(exc).__name__,
                "message":str(exc),"traceback":traceback.format_exc()}
            outmanifest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",encoding="utf-8")
            raise
    if len(receipt["completed_cases"])!=len(selected) or receipt["errors"]:
        raise ValueError("Incomplete matched-hardware cases, do not claim pass")
    rows=[receipt["completed_cases"][k] for k in selected]
    summary=[{"case_id":k,"donor":x["assignment_for_hardware"],
             "target":x["assignment_for_load"],"transformer":x["transformer"],
             "tier":x["tier"],"pv_panels":x["hardware"]["pv_panels"],
             "battery_modules":x["hardware"]["battery_modules"],
             "battery_power_dc_kw":x["hardware"]["battery_power_dc_kw"],
             "inverter_kva":x["hardware"]["inverter_kva"],
             "annual_target_import_kwh":x["target_yearly_energy_metrics"]["grid_import_kwh"],
             "annual_target_curtailment_dc_kwh":x["target_yearly_energy_metrics"]["curtailed_pv_dc_kwh"],
             "annual_equipment_cost_usd":x["target_model_summary"]["annual_equipment_usd"],
             "annual_total_cost_usd":x["target_model_summary"]["annual_total_usd"],
             "method":x["method"],"AC_verified":False}
             for k,x in zip(selected,rows)]
    receipt["case_summary_sha256"]=csv_table(summary,out/"CONTROLLED_ENERGY_CASE_SUMMARY.csv")
    if scope=="full":
        portfolios,pairs=recombine(originals,shared,receipt["completed_cases"],roster)
        receipt["matched_34h_portfolio_sha256"]=csv_table(portfolios,
            out/"MATCHED_34HOUSE_ENERGY_PORTFOLIOS.csv")
        receipt["matched_34h_pair_sha256"]=csv_table(pairs,
            out/"MATCHED_A0_VS_A1_SAME_HARDWARE_PAIRS.csv")
        receipt["matched_portfolio_count"]=len(portfolios)
        receipt["paired_comparison_count"]=len(pairs)
    receipt["status"]=("ENERGY_ONLY_REVERSE_MATCHED_HARDWARE_PASS_AC_PENDING"
                    if scope=="reverse" else
                    "ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING")
    receipt["new_AC_cases"]=0
    receipt["completed_case_count"]=len(selected)
    outmanifest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return {"status":receipt["status"],"output":str(out),
            "completed":len(selected),"new_LP_solves":receipt["expected_new_2025_LP_solves"],
            "new_AC_cases":0}

def cli(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path.cwd())
    parser.add_argument("--scope",choices=("reverse","full"),default="reverse")
    parser.add_argument("--preflight-only",action="store_true")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--out",type=Path)
    a=parser.parse_args(argv)
    result=run(a.repo_root,a.scope,a.preflight_only,a.out,a.resume)
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":
    cli()
