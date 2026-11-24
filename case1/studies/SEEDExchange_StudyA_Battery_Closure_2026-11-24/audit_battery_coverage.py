#!/usr/bin/env python3
"""Read-only Study A battery coverage audit. No PyPSA or pandapower solves."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
import pandas as pd

BASE = Path("case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01")
MATCH = Path("StudyA_A0_A1_MatchedHardware_Full_v1")
FRONT = Path("StudyA_A1_106039_Utilization_v1")
INPUT_SHA = "2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69"
IDX = pd.date_range("2025-01-01", periods=8760, freq="h")
ETA = math.sqrt(.95)
TOL = 1e-5
FIELDS = ("demand_kw", "pv_dc_available_kw", "grid_import_kw",
          "curtailed_pv_dc_kw", "battery_charge_dc_kw", "battery_discharge_dc_kw",
          "battery_soc_usable_kwh", "inverter_ac_kw", "grid_export_kw", "unserved_kw")
FRONT_CASES = ("MC_B9", "MC_B10", "MC_P33", "MC_P37", "SS_B9", "SS_B10",
               "SS_B9_POWER16", "SS_P41_KEEP20", "SS_P45", "SS_P45_B9")

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

def signed(p, expected):
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() == expected:
        return "EXACT"
    if b"\r" not in raw:
        alt = raw.replace(b"\n", b"\r\n")
    elif b"\r" not in raw.replace(b"\r\n", b"") and b"\n" not in raw.replace(b"\r\n", b""):
        alt = raw.replace(b"\r\n", b"\n")
    else:
        raise ValueError("Mixed newline signature: " + str(p))
    if hashlib.sha256(alt).hexdigest() != expected:
        raise ValueError("Source signature mismatch: " + str(p))
    return "EXACT_NEWLINE_NORMALIZATION"

def read_frame(p):
    f = pd.read_csv(p, parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
    if not f.index.equals(IDX):
        raise ValueError("Wrong 2025 hourly chronology: " + str(p))
    return f

def native_names():
    for a in ("A0", "A1"):
        for t in ("106039", "94022", "113699", "85398", "92395"):
            if a == "A1" and t == "92395":
                continue
            suffix = "four" if a == "A0" and t in ("113699","85398","92395") else "ref"
            for tier in ("min_cost","ss90"):
                yield f"{a}_{t}_{tier}_{suffix}"

def reciprocal_names():
    for a, b in (("A0","A1"),("A1","A0")):
        for t in ("106039","94022","113699","85398"):
            for tier in ("min_cost","ss90"):
                yield f"{a}_{t}_{tier}_to_{b}"

def scalar_proxy(f, kva, pf):
    q = f.demand_kw.to_numpy(float)*math.sqrt(1/pf**2-1)
    return np.hypot(f.grid_import_kw.to_numpy(float), q)/kva*100.

def check_dispatch(f, hw, start, cyclic=False):
    if not set(FIELDS).issubset(f.columns):
        raise ValueError("Required energy columns missing")
    vals = f[list(FIELDS)].to_numpy(float)
    if not np.isfinite(vals).all() or vals.min() < -TOL:
        raise ValueError("Nonfinite or negative source flow")
    n = int(hw["battery_modules"])
    floor, ceiling = n*.229, n*4.325
    p = min(float(hw["battery_power_dc_kw"]), n*2.24)
    c,d,e = [f[k].to_numpy(float) for k in ("battery_charge_dc_kw",
                                          "battery_discharge_dc_kw","battery_soc_usable_kwh")]
    if min(n,p) <= 0 or not floor-TOL <= start <= ceiling+TOL:
        raise ValueError("Invalid hardware or initial Store")
    if e.min()<floor-TOL or e.max()>ceiling+TOL or max(c.max(),d.max())>p+TOL:
        raise ValueError("Store or declared continuous battery limit")
    if ((c>TOL)&(d>TOL)).any() or f.inverter_ac_kw.max()>float(hw["inverter_kva"])+TOL:
        raise ValueError("Simultaneous cycling or inverter limit")
    if max(f.grid_export_kw.abs().max(),f.unserved_kw.abs().max())>TOL:
        raise ValueError("Export or ENS differs")
    ac = f.inverter_ac_kw + f.grid_import_kw-f.demand_kw
    dc = f.pv_dc_available_kw-f.curtailed_pv_dc_kw+d-c-f.inverter_ac_kw/.95
    soc = e-np.r_[start,e[:-1]]-ETA*c+d/ETA
    if max(ac.abs().max(),dc.abs().max(),np.abs(soc).max())>TOL:
        raise ValueError("AC/DC/Store conservation")
    if cyclic and abs(e[-1]-start)>TOL:
        raise ValueError("Noncyclic optimized source")
    return float(e[-1]-start)

def describe(f, hw):
    n=int(hw["battery_modules"])
    p=min(float(hw["battery_power_dc_kw"]),n*2.24)
    floor, ceiling=n*.229,n*4.325
    spill=f.curtailed_pv_dc_kw.clip(lower=0).to_numpy(float)
    e=f.battery_soc_usable_kwh.to_numpy(float)
    c=f.battery_charge_dc_kw.to_numpy(float)
    d=f.battery_discharge_dc_kw.to_numpy(float)
    # These are overlapping observations, NOT a causal partition of curtailment.
    # The additional-charge bound is instantaneous, not a feasible annual schedule.
    power_headroom=np.maximum(0,p-c)
    store_headroom=np.maximum(0,(ceiling-e)/ETA)
    bound=np.where(d>TOL,0,np.minimum(spill,np.minimum(power_headroom,store_headroom)))
    r=dict(import_ac_kwh=float(f.grid_import_kw.sum()),curtail_dc_kwh=float(spill.sum()),
           available_pv_dc_kwh=float(f.pv_dc_available_kw.sum()),
           discharge_dc_kwh=float(d.sum()),charge_dc_kwh=float(c.sum()),
           store_equivalent_discharge_cycles=float(d.sum()/ETA/(n*4.096)),
           curtailed_hours=int((spill>TOL).sum()),
           spill_at_end_floor_kwh=float(spill[e<=floor+TOL].sum()),
           spill_at_end_ceiling_kwh=float(spill[e>=ceiling-TOL].sum()),
           spill_at_charge_cap_kwh=float(spill[c>=p-TOL].sum()),
           spill_while_charging_idle_kwh=float(spill[c<=TOL].sum()),
           instantaneous_extra_charge_upper_sum_dc_kwh=float(bound.sum()),
           spill_during_import_kwh=float(spill[f.grid_import_kw.to_numpy(float)>TOL].sum()))
    r["curtail_fraction_pct"]=100*r["curtail_dc_kwh"]/r["available_pv_dc_kwh"]
    for pf in (.95,.98,1.0):
        key=f"pf{round(pf*100):03d}"
        load=scalar_proxy(f,float(hw["transformer_kva_assumed_or_evidenced"]),pf)
        r[key+"_proxy_overload_hours"]=int((load>100+TOL).sum())
        r[key+"_proxy_peak_pct"]=float(load.max())
    return r

def roster(repo):
    native={}
    for k in native_names():
        root=repo/BASE/f"energy_{k}"
        m=read_json(root/"energy_manifest.json")
        if m["input_manifest_sha256"]!=INPUT_SHA:
            raise ValueError("Different native input: "+k)
        croot=repo/BASE/f"causal_{k}"
        cm=read_json(croot/"causal_summary.json")
        if m["selected_house_ids"]!=cm["selected_houses"]:
            raise ValueError("Causal membership mismatch: "+k)
        signed(root/"energy_manifest.json",cm.get("reference_energy_manifest_sha256") or cm["source_energy_manifest_sha256"])
        item=dict(case=k,family="native",hw=m["hardware"],houses=m["selected_house_ids"],
                  source=root/"energy_hourly_2025.csv",sha=m["energy_csv_sha256"],
                  causal=croot/"causal_pv_first_2025.csv",causal_sha=cm["output_sha256"])
        native[k]=item
        yield item
    top=read_json(repo/MATCH/"RUN_MANIFEST.json")
    if top["input_manifest_sha256"]!=INPUT_SHA or set(top["selected_case_keys"])!=set(reciprocal_names()):
        raise ValueError("Wrong reciprocal source manifest")
    for k in reciprocal_names():
        r=read_json(repo/MATCH/k/"CASE_RECEIPT.json")
        if r!=top["completed_cases"][k] or r["source_case"]!=k or not r["same_hardware"] or not r["same_physical_transformer"]:
            raise ValueError("Reciprocal receipt differs: "+k)
        src=repo/r["target_energy_csv"]
        if not src.resolve().is_relative_to(repo.resolve()):
            raise ValueError("Reciprocal path outside repo")
        yield dict(case=k,family="reciprocal",hw=r["hardware"],houses=r["target_house_ids"],
                   source=src,sha=r["target_energy_sha256"],causal=None,causal_sha=None)
    for k in FRONT_CASES:
        root=repo/FRONT/f"energy_{k}"
        m=read_json(root/"energy_manifest.json")
        if m["input_manifest_sha256"]!=INPUT_SHA or m["scenario"]!="A1" or m["transformer"]!="106039":
            raise ValueError("Unexpected frontier source")
        yield dict(case=k,family="frontier",hw=m["hardware"],houses=m["selected_house_ids"],
                   source=root/"energy_hourly_2025.csv",sha=m["energy_csv_sha256"],causal=None,causal_sha=None)

def run(repo,out,preflight=False):
    sys.path.insert(0,str(repo/"case1/studies/SEEDExchange_StudyA_v6_LocalRunner"))
    from seed_study_a_v6 import causal_pv_first_dispatch
    items=list(roster(repo))
    if len(items)!=44:
        raise ValueError("Unexpected roster size")
    rows=[]; cache={}; months=[]; pre=[]
    for a in items:
        mode=signed(a["source"],a["sha"])
        f=read_frame(a["source"])
        hw=a["hw"]; start=float(f.battery_soc_usable_kwh.iloc[-1])
        check_dispatch(f,hw,start,True)
        if abs(f.demand_kw.sum()-1898*len(a["houses"]))>1e-4:
            raise ValueError("Annual household demand mismatch: "+a["case"])
        identity=(a["sha"],tuple(a["houses"]),tuple(sorted(hw.items())))
        if a["causal"] is not None:
            signed(a["causal"],a["causal_sha"])
        pre.append(dict(case=a["case"],family=a["family"],source_sha=a["sha"],signature_mode=mode))
        if preflight:
            continue
        if identity in cache:
            g, origin=cache[identity]
            origin="EXACT_SOURCE_REUSE:"+origin
        elif a["causal"] is not None:
            g=read_frame(a["causal"])
            origin="ARCHIVED_NATIVE_CAUSAL"
        elif a["case"]=="MC_P33":
            # Already-completed diagnostic; read archived output, then validate chronology,
            # energy conservation and source input equality. Archive has no output signature
            # in its diagnostic manifest, so label that limitation explicitly.
            folder=repo/"StudyA_A1_106039_PV_Priority_Audit_Local_v1"
            dm=read_json(folder/"DIAGNOSTIC_MANIFEST.json")
            if dm["source_provenance"]["MC_P33"]["signed_csv_SHA256"]!=a["sha"]:
                raise ValueError("P33 signed source differs")
            g=read_frame(folder/"MC_P33_CAUSAL_PV_FIRST_8760.csv").assign(
                demand_kw=f.demand_kw,pv_dc_available_kw=f.pv_dc_available_kw,
                grid_export_kw=0.,unserved_kw=0.)
            origin="ARCHIVED_P33_DIAGNOSTIC_OUTPUT_HASH_NOT_IN_MANIFEST"
        else:
            g=causal_pv_first_dispatch(f.demand_kw.to_numpy(),f.pv_dc_available_kw.to_numpy(),
                                      start,hw["pv_panels"],hw["battery_modules"],
                                      hw["inverter_kva"],hw["battery_power_dc_kw"])
            g.index=f.index
            origin="NEW_CAUSAL_DIAGNOSTIC_EXISTING_V6_FUNCTION"
        if not g.index.equals(f.index) or any(not np.allclose(g[k],f[k],rtol=0,atol=TOL)
            for k in ("demand_kw","pv_dc_available_kw")):
            raise ValueError("Causal source changed")
        terminal=check_dispatch(g,hw,start)
        if identity not in cache:
            cache[identity]=(g,a["case"])
        rec=dict(case=a["case"],family=a["family"],households=len(a["houses"]),
                 pv_panels=hw["pv_panels"],battery_modules=hw["battery_modules"],
                 battery_power_dc_kw=hw["battery_power_dc_kw"],inverter_kva=hw["inverter_kva"],
                 transformer_kva=hw["transformer_kva_assumed_or_evidenced"],
                 source_sha=a["sha"],signature_mode=mode,causal_origin=origin,
                 terminal_minus_initial_kwh=terminal,cyclic_comparable=abs(terminal)<=TOL,
                 changed_inverter_hours=int(((f.inverter_ac_kw-g.inverter_ac_kw).abs()>TOL).sum()),
                 changed_charge_hours=int(((f.battery_charge_dc_kw-g.battery_charge_dc_kw).abs()>TOL).sum()),
                 changed_curtail_hours=int(((f.curtailed_pv_dc_kw-g.curtailed_pv_dc_kw).abs()>TOL).sum()))
        for label,frame in (("source",f),("causal",g)):
            rec.update({label+"_"+k:v for k,v in describe(frame,hw).items()})
        rec["delta_import_ac_kwh"]=rec["causal_import_ac_kwh"]-rec["source_import_ac_kwh"]
        rec["delta_curtail_dc_kwh"]=rec["causal_curtail_dc_kwh"]-rec["source_curtail_dc_kwh"]
        rows.append(rec)
        for month in range(1,13):
            mask=f.index.month==month
            months.append(dict(case=a["case"],month=month,source_import_ac_kwh=float(f.loc[mask,"grid_import_kw"].sum()),
               causal_import_ac_kwh=float(g.loc[mask,"grid_import_kw"].sum()),
               source_curtail_dc_kwh=float(f.loc[mask,"curtailed_pv_dc_kw"].sum()),
               causal_curtail_dc_kwh=float(g.loc[mask,"curtailed_pv_dc_kw"].sum())))
    if preflight:
        return dict(status="SIGNED_44_SOURCE_PREFLIGHT_NO_NEW_SOLVES",rows=len(pre))
    out.mkdir(parents=False,exist_ok=False)
    pd.DataFrame(rows).to_csv(out/"BATTERY_DISPATCH_COVERAGE.csv",index=False)
    pd.DataFrame(months).to_csv(out/"MONTHLY_DISPATCH_COMPARISON.csv",index=False)
    result=dict(status="COMPLETE_ENERGY_ONLY_BATTERY_COVERAGE_AC_PENDING",
        rows=len(rows),unique_source_identity_count=len(cache),monthly_rows=len(months),
        source_status=pre,not_AC_validation=True,not_new_LP=True,
        causal_origin_counts=pd.Series([r["causal_origin"].split(":")[0] for r in rows]).value_counts().to_dict())
    (out/"RUN_MANIFEST.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--out",type=Path)
    p.add_argument("--preflight-only",action="store_true")
    a=p.parse_args()
    if not a.preflight_only and (a.out is None or a.out.exists()):
        p.error("Specify a fresh output directory")
    print(json.dumps(run(a.repo_root.resolve(),a.out,a.preflight_only),indent=2))
