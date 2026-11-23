#!/usr/bin/env python3
"""94022 reciprocal P1 Nov 27 donor/target AC shift, full-year SOC checked.

No historical files are modified. --preflight-only performs signature,
geometry, donor-envelope and frozen-dispatch validation with ZERO AC solves.
--run-local performs up to 40 bounded AC case-hour calculations (more runpp
calls may occur inside Q control) and saves a new versioned diagnostic folder.
The paired-hour result is NOT an annual AC feasibility certification.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback

import matched16_original_ac_input_preflight as gate

BASE = Path("case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22")
PV_CODE = Path("case1/studies/SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py")
FROZEN = Path("StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json")
P1 = Path("StudyA_Reciprocal12_P1_AC_Pilot_v1")
DONOR_REGISTER = BASE / "RECIPROCAL_P1_TEN_FAILED_EVENT_DONOR_CAP_2026-11-23.csv"
CLOSURE_REGISTER = BASE / "RECIPROCAL_P1_SIX_ANNUAL_BATTERY_CLOSURE_2026-11-23.csv"
OUT_PREFIX = "StudyA_94022_Nov_DonorTarget_AC_Shift_v"
CASES = {
    "A1_94022_min_cost_to_A0": "2025-11-27 13:00:00",
    "A1_94022_ss90_to_A0": "2025-11-27 17:00:00",
}
TARGET = "2025-11-27 20:00:00"
PF = (0.98, 0.95)
SAMPLE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 0.98)
ETA_INV = 0.95
ETA_BAT = math.sqrt(0.95)
MODEL_STORE_KWH_PER_MODULE = 4.325
PHYSICAL_FLOOR_MODEL_PER_MODULE = 4.325 - 0.8 * 5.12
PF_PROXY = 0.95
TOL = 5e-5
REPLAY_TOL = 2e-4


def load_module(path, alias):
    file = gate.required_file(path)
    spec = importlib.util.spec_from_file_location(alias, file)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


def digest(path):
    return hashlib.sha256(gate.required_file(path).read_bytes()).hexdigest()


def check_year(df, modules, bank_dc_kw, inverter_kva):
    """Independent strict 8760h cyclic model algebra, not a field SOC certificate."""
    import numpy as np
    import pandas as pd
    expected = pd.date_range("2025-01-01", periods=8760, freq="h")
    if len(df) != 8760 or not df.index.equals(expected):
        raise ValueError("Annual 2025 hourly timestamps not complete/ordered")
    required = ("demand_kw", "inverter_ac_kw", "grid_import_kw",
        "grid_export_kw", "unserved_kw", "pv_dc_generated_kw",
        "pv_dc_available_kw", "battery_discharge_dc_kw",
        "battery_charge_dc_kw", "battery_soc_usable_kwh",
        "curtailed_pv_dc_kw")
    if any(c not in df for c in required):
        raise ValueError("Missing frozen battery/source energy columns")
    values = df[list(required)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite original or shifted annual energy")
    v = lambda c: df[c].to_numpy(dtype=float)
    ac = v("inverter_ac_kw") + v("grid_import_kw") + v("unserved_kw") - v("grid_export_kw") - v("demand_kw")
    dc = (v("pv_dc_generated_kw") + v("battery_discharge_dc_kw")
          - v("battery_charge_dc_kw") - v("inverter_ac_kw") / ETA_INV)
    e = v("battery_soc_usable_kwh")
    prev = np.roll(e, 1)
    conservation = e - prev - ETA_BAT * v("battery_charge_dc_kw") + v("battery_discharge_dc_kw") / ETA_BAT
    cap = modules * MODEL_STORE_KWH_PER_MODULE
    floor = modules * PHYSICAL_FLOOR_MODEL_PER_MODULE
    errors = {
        "max_ac_power_balance_kw": float(np.max(np.abs(ac))),
        "max_dc_power_balance_kw": float(np.max(np.abs(dc))),
        "max_cyclic_store_error_kwh": float(np.max(np.abs(conservation))),
        "max_export_kw": float(np.max(np.abs(v("grid_export_kw")))),
        "max_unserved_kw": float(np.max(np.abs(v("unserved_kw")))),
        "min_store_kwh": float(e.min()), "max_store_kwh": float(e.max()),
        "bank_peak_dc_kw": float(max(v("battery_discharge_dc_kw").max(),
                                      v("battery_charge_dc_kw").max())),
        "inverter_peak_p_kw": float(v("inverter_ac_kw").max()),
        "annual_import_kwh": float(v("grid_import_kw").sum()),
        "annual_battery_discharge_dc_kwh": float(v("battery_discharge_dc_kw").sum()),
        "annual_curtail_dc_kwh": float(v("curtailed_pv_dc_kw").sum()),
        "initial_store_kwh_end_hour0": float(e[0]),
        "year_end_store_kwh": float(e[-1]),
        "module_floor_kwh": floor, "module_store_cap_kwh": cap,
    }
    if (max(errors[k] for k in ("max_ac_power_balance_kw", "max_dc_power_balance_kw",
                                "max_cyclic_store_error_kwh", "max_export_kw",
                                "max_unserved_kw")) > TOL
        or e.min() < floor-TOL or e.max() > cap+TOL
        or v("battery_discharge_dc_kw").min() < -TOL
        or v("battery_charge_dc_kw").min() < -TOL
        or v("grid_import_kw").min() < -TOL
        or v("inverter_ac_kw").min() < -TOL
        or errors["bank_peak_dc_kw"] > bank_dc_kw+TOL
        or errors["inverter_peak_p_kw"] > inverter_kva+TOL):
        raise ValueError("Annual battery SOC, power, DC or AC closure violated")
    return errors


def bound_one_donor(df, donor, target, hardware, pf=PF_PROXY):
    """Isolated DC donor-shift limit only; AC feeder losses deliberately omitted."""
    import pandas as pd
    a, b = pd.Timestamp(donor), pd.Timestamp(target)
    if (a not in df.index or b not in df.index or a >= b
        or a.date() != b.date() or (b-a).total_seconds() > 12 * 3600):
        raise ValueError("Donor must be within the same preceding 12h")
    d, t = df.loc[a], df.loc[b]
    if float(t["pv_dc_available_kw"]) > 1e-8:
        raise ValueError("Target should be dark, fixed-P source shift only")
    modules = int(hardware["battery_modules"])
    cap = modules * MODEL_STORE_KWH_PER_MODULE
    q_d = float(d["demand_kw"]) * math.tan(math.acos(pf))
    trafo_kva = float(hardware["transformer_kva_assumed_or_evidenced"])
    if q_d > trafo_kva:
        return 0.0
    p_grid_cap = math.sqrt(max(0.0, trafo_kva**2 - q_d**2))
    import_headroom_dc = max(0.0, (p_grid_cap - float(d["grid_import_kw"])) / ETA_INV)
    window = df.loc[a:b].iloc[:-1]["battery_soc_usable_kwh"]
    store_headroom_dc = max(0.0, float((cap-window).min())) * ETA_BAT
    bank_remaining = max(0.0, float(hardware["battery_power_dc_kw"]) -
                         float(t["battery_discharge_dc_kw"]))
    inv_remaining = max(0.0, (float(hardware["inverter_kva"]) -
                              float(t["inverter_ac_kw"])) / ETA_INV)
    zero_export = max(0.0, float(t["grid_import_kw"]) / ETA_INV)
    return max(0.0, min(float(d["battery_discharge_dc_kw"]), import_headroom_dc,
                        store_headroom_dc, bank_remaining, inv_remaining, zero_export))


def transfer(df, donor, target, amount_dc):
    """Exact same-year two-hour DC discharge deferral and intervening SOC retention."""
    import pandas as pd
    d, t = pd.Timestamp(donor), pd.Timestamp(target)
    x = float(amount_dc)
    if x < 0 or not math.isfinite(x) or d not in df.index or t not in df.index or d >= t:
        raise ValueError("Invalid discharge transfer")
    if x > float(df.at[d, "battery_discharge_dc_kw"])+1e-8:
        raise ValueError("Cannot shift more than original donor DC discharge")
    out = df.copy(deep=True)
    if x == 0:
        return out
    for hour, sign in ((d,-1),(t,1)):
        out.at[hour, "battery_discharge_dc_kw"] += sign*x
        out.at[hour, "inverter_ac_kw"] += sign*ETA_INV*x
        out.at[hour, "grid_import_kw"] -= sign*ETA_INV*x
        if "pcc_p_kw" in out:
            out.at[hour, "pcc_p_kw"] = (out.at[hour,"grid_import_kw"] -
                                       out.at[hour,"grid_export_kw"])
        if {"pcc_p_kw","pcc_q_kvar_proxy","pcc_kva_proxy"}.issubset(out.columns):
            out.at[hour, "pcc_kva_proxy"] = math.hypot(
                float(out.at[hour,"pcc_p_kw"]),float(out.at[hour,"pcc_q_kvar_proxy"]))
    mask = (out.index >= d) & (out.index < t)
    out.loc[mask, "battery_soc_usable_kwh"] += x / ETA_BAT
    return out


def same_total(a,b,key,tol=1e-5):
    if abs(float(a[key])-float(b[key])) > tol:
        raise ValueError("Annual source total changed: "+key)


def preflight(repo):
    import pandas as pd
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise ValueError("Use the real GitLab repository checkout")
    frozen = gate.read_json(repo/FROZEN)
    if (frozen.get("status") != "ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING"
        or len(frozen.get("completed_cases",{})) != 16):
        raise ValueError("Frozen matched hardware manifest changed")
    pilot_manifest = gate.read_json(repo/P1/"RUN_MANIFEST.json")
    if (pilot_manifest.get("status") != "P1_TARGETED_36_AC_CASEHOURS_RECORDED_NOT_ANNUAL"
        or pilot_manifest.get("new_AC_case_hour_evaluations") != 36
        or pilot_manifest.get("infeasible") != 20
        or pilot_manifest.get("annual_AC_verified") is not False):
        raise ValueError("Signed 36-case-hour P1 source receipt changed")
    gate.signed_bytes(repo/P1/"TARGETED_36_AC_CASEHOURS.csv",
                      pilot_manifest["targeted_ac_csv_sha256"])
    ac = gate.read_csv(repo/P1/"TARGETED_36_AC_CASEHOURS.csv")
    if len(ac) != 36:
        raise ValueError("Original P1 AC row count changed")
    source_reg = gate.read_csv(repo/DONOR_REGISTER)
    closure = gate.read_csv(repo/CLOSURE_REGISTER)
    if len(source_reg)!=10 or len(closure)!=6:
        raise ValueError("Prior signed donor and closure register populations changed")
    if len({(x["case"],x["event"]) for x in source_reg})!=10:
        raise ValueError("Duplicate donor cap event")
    pv = load_module(repo/PV_CODE, "verified_94022_nov_original_pvbess")
    m,v6,mapping,profiles = pv.secure_context(repo,repo/pv.MANIFEST_REL)
    v6.repo_modules(repo)
    prepared, receipt_cases = {}, []
    for name, donor in CASES.items():
        c = frozen["completed_cases"][name]
        if (c["source_case"] != name or c["AC_verified"] is not False
            or c["transformer"]!="94022" or c["assignment_for_load"]!="A0"
            or c["assignment_for_hardware"]!="A1"):
            raise ValueError("Unexpected 94022 frozen reciprocal case")
        ids, trace = pv.source_trace(m,mapping,profiles,"A0","94022")
        if ids != c["target_house_ids"] or len(ids)!=10:
            raise ValueError("94022 signed household cohort mismatch")
        territory = v6.new_territory(repo,"A0","94022",ids,1.0)
        if sorted(x["house"] for x in territory.attachments) != sorted(ids):
            raise ValueError("Original EPM GIS household attachment changed")
        if abs(float(territory.trafo["kva"]) -
               float(c["hardware"]["transformer_kva_assumed_or_evidenced"])) > 1e-8:
            raise ValueError("Different 94022 transformer nameplate proxy")
        source_path = gate.relative_file(repo,c["target_energy_csv"])
        source_signature_mode = gate.signed_bytes(source_path,c["target_energy_sha256"])
        frame = pd.read_csv(gate.required_file(source_path),parse_dates=["timestamp_lst"])
        if frame.timestamp_lst.duplicated().any():
            raise ValueError("Duplicate annual source timestamps")
        frame = frame.set_index("timestamp_lst")
        hw = c["hardware"]
        original = check_year(frame,int(hw["battery_modules"]),
                              float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
        if max(abs(float(frame.loc[t,"demand_kw"])-float(trace.loc[t].sum()))
               for t in (pd.Timestamp(donor),pd.Timestamp(TARGET))) > 1e-6:
            raise ValueError("Signed annual loads differ from GIS individual household traces")
        cap = bound_one_donor(frame,donor,TARGET,hw)
        recs = [x for x in source_reg if x["case"]==name and x["event"]==TARGET]
        if (len(recs)!=1 or recs[0]["best_donor_hour"]!=donor
            or abs(cap - float(recs[0]["max_individual_donor_shift_dc_kw"])) > 1e-7):
            raise ValueError("Independently recomputed donor cap differs from prior register")
        previous = [r for r in ac if r["case"]==name and r["timestamp_lst"]==TARGET]
        if (len(previous)!=2 or {float(r["pf"]) for r in previous}!=set(PF)
            or not all(r["ac_feasible"]=="False" and r["status"]=="CONVERGED" for r in previous)):
            raise ValueError("Saved AC failure history changed")
        for row in previous:
            if (abs(float(row["inverter_ac_kw"])-float(frame.at[pd.Timestamp(TARGET),"inverter_ac_kw"]))>1e-7
                or abs(float(row["gross_demand_kw"])-float(frame.at[pd.Timestamp(TARGET),"demand_kw"]))>1e-6
                or row["source_sha256"]!=c["target_energy_sha256"]):
                raise ValueError("Saved baseline AC not from frozen target P")
        # Independent annual audit ledger is checked against computed source.
        reference = [r for r in closure if r["case"]==name]
        if len(reference)!=1 or abs(float(reference[0]["annual_min_store_kwh"]) -
                                    original["min_store_kwh"])>1e-7:
            raise ValueError("Independent original battery closure ledger changed")
        prepared[name]={"case":c,"ids":ids,"trace":trace,"territory":territory,
                        "source":frame,"annual":original,"donor":donor,
                        "target":TARGET,"upper_dc":cap,
                        "baseline_target_ac":{float(x["pf"]):x for x in previous}}
        receipt_cases.append({
            "case":name,"donor":donor,"target":TARGET,"upper_dc_kw":cap,
            "upper_added_ac_kw":ETA_INV*cap,
            "original_annual_import_kwh":original["annual_import_kwh"],
            "original_annual_store_floor_kwh":original["module_floor_kwh"],
            "original_energy_csv_sha256":c["target_energy_sha256"],
            "source_signature_mode":source_signature_mode,
            "households":len(ids),
            "assumed_transformer_kva":float(territory.trafo["kva"]),
            "battery_module_count":int(hw["battery_modules"]),
            "bank_discharge_dc_kw":float(hw["battery_power_dc_kw"]),
            "inverter_rating_kva":float(hw["inverter_kva"]),
        })
    return {
        "status":"SIGNED_94022_TWO_HARDWARE_DONOR_TARGET_PREFLIGHT_NO_SOLVES",
        "case_count":2,"candidate_count":2*len(SAMPLE_FRACTIONS),
        "planned_case_hour_AC_evaluations":2*len(SAMPLE_FRACTIONS)*len(PF)*2,
        "actual_new_case_hour_AC_evaluations":0,
        "fractions":list(SAMPLE_FRACTIONS),"PF":list(PF),
        "source_2025_hours_per_case":8760,"battery_physical_soc_min_model":0.20,
        "donor_proxy_PF":PF_PROXY,"daylight_q_ratio":0.25,
        "length_factor":1.0,"source_annual_dispatch_modified":False,
        "field_network_verified":False,"annual_AC_verified":False,
        "interpretation":"Source signed fixed-hardware individual donor/target screen only",
        "cases":receipt_cases
    },prepared,v6


def save_csv(path, rows):
    if not rows: return
    columns = sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w", newline="",encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns,extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def figures(out, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    diagnostic = out/"figures_diagnostic"
    diagnostic.mkdir(exist_ok=False)
    hashes={}
    for field,limit,label,filename in (
        ("min_v_pu",0.95,"Minimum house voltage [pu]","minimum_voltage_vs_shift.png"),
        ("max_trafo_pct",100.,"Transformer loading [%]","transformer_loading_vs_shift.png")):
        fig, ax=plt.subplots(figsize=(10,5))
        for tier in ("min_cost","ss90"):
            for pf in PF:
                for point in ("donor","target"):
                    selected=[r for r in rows if r["tier"]==tier and r["pf"]==pf
                              and r["point"]==point and r["status"]=="CONVERGED"]
                    if selected:
                        ax.plot([r["added_target_ac_kw"] for r in selected],
                                [r[field] for r in selected],marker="o",
                                label=f"{tier}, PF {pf}, {point}")
        ax.axhline(limit,color="black",linestyle="--",linewidth=1,label="main screen")
        ax.set_xlabel("Target-hour extra inverter AC P [kW]")
        ax.set_ylabel(label)
        ax.set_title("94022 reciprocal P1 Nov 27, original provisional GIS, no annual AC")
        ax.legend(fontsize=7,ncol=2)
        ax.grid(alpha=.25);fig.tight_layout()
        path=diagnostic/filename
        fig.savefig(path,dpi=160)
        plt.close(fig)
        hashes[filename]=digest(path)
    return hashes


def run_local(repo, preflight, prepared, v6):
    """One preverified same-hardware DC pair at a time; all 2025 constraints audited."""
    import pandas as pd
    import pandapower as pp
    from run_epm_validation import build_net
    repo=repo.resolve()
    output=next((repo/f"{OUT_PREFIX}{i}" for i in range(1,100)
                 if not (repo/f"{OUT_PREFIX}{i}").exists()),None)
    if output is None: raise FileExistsError("No unused versioned AC result folder")
    output.mkdir()
    manifest=output/"RUN_MANIFEST.json"
    doc=dict(preflight,status="INCOMPLETE_94022_NOV_DO_NOT_CLAIM")
    manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    rows,summary=[],[]
    try:
        for name in sorted(prepared):
            item=prepared[name]; case=item["case"]; hw=case["hardware"]
            net,meta=build_net(item["territory"],"head")
            if set(meta["loads"])!=set(item["ids"]):
                raise ValueError("Pandapower household keys do not match signed GIS")
            source=item["source"]
            for fraction in SAMPLE_FRACTIONS:
                x=float(item["upper_dc"])*fraction
                shifted=transfer(source,item["donor"],TARGET,x)
                evidence=check_year(shifted,int(hw["battery_modules"]),
                                    float(hw["battery_power_dc_kw"]),float(hw["inverter_kva"]))
                for field in ("annual_import_kwh","annual_battery_discharge_dc_kwh",
                              "annual_curtail_dc_kwh"):
                    same_total(evidence,item["annual"],field)
                if abs(float(evidence["year_end_store_kwh"]) -
                       float(item["annual"]["year_end_store_kwh"]))>1e-5:
                    raise ValueError("Annual terminal Store energy changed")
                if x and (abs(float(shifted.at[pd.Timestamp(item["donor"]),"inverter_ac_kw"])-
                              float(source.at[pd.Timestamp(item["donor"]),"inverter_ac_kw"])+ETA_INV*x)>1e-6
                    or abs(float(shifted.at[pd.Timestamp(TARGET),"inverter_ac_kw"]) -
                           float(source.at[pd.Timestamp(TARGET),"inverter_ac_kw"])-ETA_INV*x)>1e-6):
                    raise ValueError("Exact signed source P transfer was not applied")
                condition=[]
                for pf in PF:
                    for stage,stamp in (("donor",item["donor"]),("target",TARGET)):
                        t=pd.Timestamp(stamp)
                        result=v6.solve_ac_hour(
                            net,meta,item["territory"],t,item["trace"].loc[t],
                            pf,float(shifted.at[t,"inverter_ac_kw"]),
                            float(hw["inverter_kva"]),
                            float(shifted.at[t,"pv_dc_available_kw"]),
                            0.25,9,"pvbess",pp)
                        if (abs(float(result["gross_demand_kw"])-
                                float(source.at[t,"demand_kw"]))>1e-5
                            or abs(float(result["inverter_ac_kw"])-
                                   float(shifted.at[t,"inverter_ac_kw"]))>1e-5):
                            raise ValueError("Actual AC replay did not apply exact shifted P")
                        if fraction==0 and stage=="target":
                            prior=item["baseline_target_ac"][pf]
                            for field in ("min_v_pu","max_v_pu","max_trafo_pct",
                                          "max_line_pct","loss_kw","pcc_kva","q_selected_kvar"):
                                if (result["status"]!="CONVERGED"
                                    or abs(float(result[field])-float(prior[field])) > REPLAY_TOL):
                                    raise ValueError("Original P1 AC target regression failed: "
                                                     +name+"/"+str(pf)+"/"+field)
                        accept=(result["status"]=="CONVERGED" and result["ac_feasible"] is True)
                        condition.append(accept)
                        rows.append({"case":name,"tier":case["tier"],
                                     "point":stage,"donor_time":item["donor"],
                                     "target_time":TARGET,"pf":pf,"fraction":fraction,
                                     "moved_dc_kw":x,"added_target_ac_kw":ETA_INV*x,
                                     "original_source_energy_sha256":case["target_energy_sha256"],
                                     "annual_candidate_soc_valid":True,
                                     "pair_local_AC_verified_only":True,
                                     **result})
                        print(f"94022 Nov AC {len(rows)}/40 | {name} | "
                              f"fraction={fraction} | {stage} | PF={pf}",flush=True)
                summary.append({"case":name,"tier":case["tier"],"fraction":fraction,
                                "moved_dc_kw":x,"added_target_ac_kw":ETA_INV*x,
                                "annual_soc_and_energy_valid":True,
                                "pair_4of4_AC_screen_pass":all(condition),
                                "passed_local_AC_points":sum(condition),
                                "checked_local_AC_points":4,
                                "annual_AC_verified":False})
        if len(rows)!=40 or len(summary)!=10:
            raise ValueError("Incomplete experiment sample populations")
        doc.update(status="94022_NOV_TWO_PAIR_AC_SWEEP_COMPLETE_NOT_ANNUAL",
                   actual_new_case_hour_AC_evaluations=len(rows),
                   tested_2025_annual_soc_schedules=len(summary),
                   AC_converged_case_hours=sum(r["status"]=="CONVERGED" for r in rows),
                   AC_failed_main_screen=sum(r["ac_feasible"] is False for r in rows),
                   local_pair_screen_pass_candidates=sum(x["pair_4of4_AC_screen_pass"] for x in summary),
                   candidate_summary=summary,
                   annual_AC_verified=False,field_network_verified=False)
        acfile=output/"DONOR_TARGET_AC_40_CASEHOURS.csv"
        save_csv(acfile,rows);doc["ac_csv_sha256"]=digest(acfile)
        summaryfile=output/"PAIR_CANDIDATES_10.csv"
        save_csv(summaryfile,summary);doc["candidate_summary_sha256"]=digest(summaryfile)
        doc["diagnostic_png_sha256"]=figures(output,rows)
        manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        return {"status":doc["status"],"output":str(output),
                "AC_case_hour_evaluations":len(rows),
                "AC_converged":doc["AC_converged_case_hours"],
                "failed_main_screen":doc["AC_failed_main_screen"],
                "candidate_local_pair_pass":doc["local_pair_screen_pass_candidates"],
                "annual_AC_verified":False}
    except Exception as exc:
        doc.update(status="INCOMPLETE_94022_NOV_DO_NOT_CLAIM",
                   actual_new_case_hour_AC_evaluations=len(rows),
                   recorded_pair_candidates=len(summary),
                   failure={"type":type(exc).__name__,"message":str(exc),
                            "traceback":traceback.format_exc()})
        if rows: save_csv(output/"PARTIAL_UNVERIFIED_AC_ROWS.csv",rows)
        manifest.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only",action="store_true")
    mode.add_argument("--run-local",action="store_true")
    args=parser.parse_args(argv)
    receipt,cases,v6=preflight(args.repo_root)
    output=receipt if args.preflight_only else run_local(args.repo_root,receipt,cases,v6)
    print(json.dumps(output,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
