#!/usr/bin/env python3
"""Two decision-led local fixed-hardware sizing pilots, no new network model."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from audit_battery_coverage import signed, read_frame, check_dispatch, describe, read_json

MATCH=Path("StudyA_A0_A1_MatchedHardware_Full_v1")
COVER=Path("StudyA_Battery_Coverage_v1")
PVBESS=Path("case1/studies/SEEDExchange_StudyA_PVBESS_v1")
FIXED=Path("case1/studies/ac_aware_redispatch_v1")
FRONT=Path("case1/studies/SEEDExchange_StudyA_Utilization_Frontier_v1")
FAMILIES={
    "oversize":("A1_113699_ss90_to_A0","113699","8d71e1c5e3064303f290a0b728b8b6ae91ec88e8130ec36c2ea9d92770035a98",
                (26,5,8.748521194607399,7.6,3.)),
    "constraint":("A1_94022_min_cost_to_A0","94022","66b3af49a0ec2a00b81872140c42e19a592e694c2bd66053228b45c38ea8056b",
                  (27,5,8.610383666211986,8.,5.)),
}
# Only one variable changes except for explicitly joint P20_B4.
# Keep DC power fixed, including in module-count changes.
PLAN={
    "oversize":[("P22",22,5),("P20",20,5),("P18",18,5),("B4",26,4),("P20_B4",20,4)],
    "constraint":[("B6",27,6),("B7",27,7)],
}

def hardware_tuple(h):
    return (int(h["pv_panels"]),int(h["battery_modules"]),float(h["battery_power_dc_kw"]),
            float(h["inverter_kva"]),float(h["transformer_kva_assumed_or_evidenced"]))

def designs(family):
    _,_,_,ref=FAMILIES[family]
    for label,p,m in PLAN[family]:
        yield label,dict(pv_panels=p,battery_modules=m,battery_power_dc_kw=ref[2],
            inverter_kva=ref[3],transformer_kva_assumed_or_evidenced=ref[4])

def device_input(h):
    return dict(panels=h["pv_panels"],modules=h["battery_modules"],
        battery_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"])

def validate_comparison(f,hw,demand,solar):
    if len(f)!=8760 or not f.index.equals(demand.index) or not f.index.equals(solar.index):
        raise ValueError("Source chronology differs")
    if not np.allclose(f.demand_kw,demand,rtol=0,atol=1e-5):
        raise ValueError("Changed household demand")
    if not np.allclose(f.pv_dc_available_kw,solar*hw["pv_panels"]*.435,rtol=0,atol=1e-5):
        raise ValueError("Changed solar scaling")
    check_dispatch(f,hw,float(f.battery_soc_usable_kwh.iloc[-1]),True)

def context(repo):
    for folder in (PVBESS,FIXED,FRONT):
        sys.path.insert(0,str(repo/folder))
    import study_a_pvbess as st
    import fixed_hardware as fh
    from run_a1_106039_frontier import validate_device
    m,_,mapping,profiles=st.secure_context(repo,repo/st.MANIFEST_REL)
    solar,solar_path=st.solar_per_unit(repo,profiles.index)
    top=read_json(repo/MATCH/"RUN_MANIFEST.json")
    signed(repo/st.MANIFEST_REL,top["input_manifest_sha256"])
    signed(solar_path,top["solar_sha256"])
    cov=read_json(repo/COVER/"RUN_MANIFEST.json")
    if cov["status"]!="COMPLETE_ENERGY_ONLY_BATTERY_COVERAGE_AC_PENDING" or cov["rows"]!=44:
        raise ValueError("Coverage receipt missing")
    table=pd.read_csv(repo/COVER/"BATTERY_DISPATCH_COVERAGE.csv")
    return st,fh,m,mapping,profiles,solar,top,table,validate_device

def preflight(repo,scope):
    st,fh,m,mapping,profiles,solar,top,table,validate_device=context(repo)
    contexts={}
    for family in (FAMILIES if scope=="both" else [scope]):
        k,t,signature,expected=FAMILIES[family]
        r=read_json(repo/MATCH/k/"CASE_RECEIPT.json")
        if r!=top["completed_cases"][k] or r["target_energy_sha256"]!=signature or hardware_tuple(r["hardware"])!=expected:
            raise ValueError("Source identity changed: "+k)
        houses,trace=st.source_trace(m,mapping,profiles,"A0",t)
        if houses!=r["target_house_ids"] or r["assignment_for_load"]!="A0":
            raise ValueError("Changed cohort")
        demand=trace.sum(axis=1)
        src=repo/r["target_energy_csv"]; mode=signed(src,signature)
        f=read_frame(src)
        validate_comparison(f,r["hardware"],demand,solar)
        row=table[table.case==k]
        if len(row)!=1 or row.iloc[0].source_sha!=signature:
            raise ValueError("Coverage source mismatch")
        for col,field in (("source_import_ac_kwh","grid_import_kw"),("source_curtail_dc_kwh","curtailed_pv_dc_kw")):
            if abs(float(row.iloc[0][col])-float(f[field].sum()))>1e-5:
                raise ValueError("Coverage totals mismatch")
        validate_device(device_input(r["hardware"]))
        for label,h in designs(family):
            validate_device(device_input(h))
            if hardware_tuple(h)==expected:
                raise ValueError("Duplicate reference")
            # Exact cohort/hardware reuse guard over known native and reciprocal inventory.
            for _,z in table.iterrows():
                other=str(z.case)
                is_a0=(other.startswith("A0_") and "_to_" not in other) or other.endswith("_to_A0")
                if is_a0 and f"_{t}_" in other:
                    hw2=(int(z.pv_panels),int(z.battery_modules),float(z.battery_power_dc_kw),float(z.inverter_kva),float(z.transformer_kva))
                    if np.allclose(hardware_tuple(h),hw2,rtol=0,atol=1e-8):
                        raise ValueError("Existing design found, reuse instead: "+other)
        contexts[family]=(k,t,r,houses,demand,solar,f,mode)
    return fh,contexts

def summary(case,family,role,h,f,model_summary):
    rec=dict(case=case,family=family,role=role,**h)
    rec.update(describe(f,h))
    rec.update(annual_equipment_usd=float(model_summary["annual_equipment_usd"]),
        annual_grid_cost_usd=float(model_summary["annual_grid_import_usd"]),
        annual_total_usd=float(model_summary["annual_total_usd"]),
        self_sufficiency_pct=100*(1-f.grid_import_kw.sum()/f.demand_kw.sum()),
        annual_demand_kwh=float(f.demand_kw.sum()),
        AC_verified=False)
    if abs(rec["annual_total_usd"]-rec["annual_equipment_usd"]-rec["annual_grid_cost_usd"])>1e-4:
        raise ValueError("Cost closure")
    return rec

def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument("--repo-root",type=Path,default=Path("."))
    pa.add_argument("--scope",choices=["oversize","constraint","both"],default="both")
    pa.add_argument("--preflight-only",action="store_true")
    pa.add_argument("--out",type=Path)
    a=pa.parse_args()
    repo=a.repo_root.resolve()
    fh,contexts=preflight(repo,a.scope)
    expected=sum(len(PLAN[x]) for x in contexts)
    print(json.dumps(dict(status="SIGNED_SIZING_PILOT_PREFLIGHT",families=list(contexts),new_LPs=expected),indent=2),flush=True)
    if a.preflight_only:
        return
    if a.out is None or a.out.exists():
        pa.error("Choose a fresh output folder")
    a.out.mkdir(parents=False,exist_ok=False)
    rows=[]; failures=[]; sources={}
    for family,(k,t,r,houses,demand,solar,f,mode) in contexts.items():
        sources[family]=dict(case=k,sha=r["target_energy_sha256"],signature_mode=mode,house_ids=houses)
        rows.append(summary(k,family,"SIGNED_REFERENCE_ENERGY",r["hardware"],f,r["target_model_summary"]))
        for label,h in designs(family):
            case=t+"_"+label
            print("SIZING",case,flush=True)
            try:
                hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
                    battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
                    transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,
                    load_pf=.98,export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
                g,sm=fh.solve_fixed(repo,hw,demand,solar,min_physical_soc=.20)
                g.index.name="timestamp_lst"
                validate_comparison(g,h,demand,solar)
                row=summary(case,family,"NEW_FIXED_HARDWARE_ENERGY_ONLY",h,g,sm)
                folder=a.out/case; folder.mkdir()
                path=folder/"energy_hourly_2025.csv"
                g.to_csv(path,float_format="%.10f")
                import hashlib
                meta=dict(status="FULL_8760H_FIXED_HARDWARE_FRONTIER_ENERGY_ONLY",
                    case_id=case,scenario="A0",transformer=t,selected_house_ids=houses,
                    hardware=h,source_case=k,source_energy_sha256=r["target_energy_sha256"],
                    energy_csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    input_manifest_sha256="2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69",
                    model_summary=sm,metrics=row,AC_verified=False)
                (folder/"energy_manifest.json").write_text(json.dumps(meta,indent=2,allow_nan=False)+"\n",encoding="utf-8")
                rows.append(row)
            except Exception as exc:
                failures.append(dict(case=case,error=repr(exc)))
                print("UNRESOLVED",case,repr(exc),flush=True)
    pd.DataFrame(rows).to_csv(a.out/"SIZING_SUMMARY.csv",index=False)
    receipt=dict(status="COMPLETE_ENERGY_ONLY_SIZING_PILOT" if not failures else "PARTIAL_SIZING_PILOT",
        expected_new=expected,completed_new=len(rows)-len(contexts),sources=sources,errors=failures,
        no_new_AC=True,not_field_certified=True)
    (a.out/"RUN_MANIFEST.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))
    if failures:sys.exit(2)

if __name__=="__main__":
    main()
