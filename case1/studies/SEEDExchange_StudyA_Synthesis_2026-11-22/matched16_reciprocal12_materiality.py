#!/usr/bin/env python3
"""Read-only 12 unmatched reciprocal 2025 energy/AC materiality screen.

No pandapower or PyPSA run. Output consists of a signed-source 12-case register,
25 deterministic, source-grounded target hours per case, and a SHA receipt.
Transformer apparent-power proxies omit network losses and inverter daylight Q.
Do not interpret either proxy as a solved AC limit or physical nameplate.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import matched16_original_ac_input_preflight as src

OUT = "StudyA_Reciprocal12_Source_Materiality_v"
MATCHED = {
    "A0_106039_min_cost_to_A1", "A1_106039_min_cost_to_A0",
    "A1_85398_min_cost_to_A0", "A1_85398_ss90_to_A0",
}
# Original-archive stress markers, NOT observations of any reciprocal schedule.
ARCHIVE_ANCHORS = {
    "94022": (
        "2025-03-28 20:00:00", "2025-11-16 20:00:00",
        "2025-11-27 20:00:00", "2025-11-29 19:00:00",
        "2025-11-29 20:00:00",
    ),
    "113699": (
        "2025-03-14 19:00:00", "2025-03-30 19:00:00",
        "2025-11-30 20:00:00",
    ),
    "106039": ("2025-10-13 20:00:00", "2025-11-27 20:00:00"),
    "85398": (),
}
PRIORITY_DESCRIPTIONS = {
    ("94022", "A0"): ("P1", "A0 original-feeder voltage concern; physical H01/H06 services unresolved"),
    ("94022", "A1"): ("P2", "Existing A1 native AC evidence cannot certify transferred hardware"),
    ("113699", "A1"): ("P1", "PF 0.95 sampled undervoltage; prior corrected annual AC used different P schedule"),
    ("113699", "A0"): ("P3", "Four-home target; no 113699 A0-origin 4-home full-year AC transfer"),
    ("106039", "A0"): ("P1", "SS90 target, assumed 5 kVA and low PF night-headroom vulnerability"),
    ("106039", "A1"): ("P1", "SS90 target, assumed 5 kVA and low PF night-headroom vulnerability"),
    ("85398", "A1"): ("P2", "H13 moved-service association is not utility-verified"),
}
REGISTER_FIELDS = (
    "reciprocal_case", "hardware_origin", "target_assignment", "transformer",
    "hardware_tier", "households", "source_energy_2025_hours", "source_energy_sha256",
    "annual_demand_kwh", "annual_grid_import_kwh", "annual_curtailment_dc_kwh",
    "assumed_transformer_kva", "pv_panels", "battery_modules",
    "battery_power_dc_kw", "inverter_kva", "nighttime_hours_PV_zero",
    "max_night_PCC_S_proxy_pf098_kva", "max_night_PCC_S_proxy_pf095_kva",
    "night_proxy_above_assumed_kva_pf098_hours",
    "night_proxy_above_assumed_kva_pf095_hours",
    "night_proxy_above_90pct_assumed_kva_pf095_hours",
    "max_grid_import_kw", "max_gross_demand_kw",
    "source_only_priority_band", "source_only_priority_reason",
    "exact_original_AC_source_family_match", "new_AC_solves",
    "field_EPM_nameplate_or_service_verified",
)
HOUR_FIELDS = (
    "reciprocal_case", "transformer", "target_assignment", "timestamp_lst",
    "selection_reason", "gross_demand_kw", "inverter_ac_kw", "grid_import_kw",
    "pv_dc_available_kw", "night_Q_disabled_source_rule",
    "night_PCC_S_proxy_pf098_kva", "night_PCC_S_proxy_pf095_kva",
    "assumed_transformer_kva", "AC_solved", "EPM_verified",
)


def scalar(row, key):
    try:
        val = float(row[key])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError("Missing or invalid source energy value: " + key) from err
    if not math.isfinite(val):
        raise ValueError("Nonfinite source energy value: " + key)
    return val


def nighttime_proxy(import_kw, demand_kw, power_factor):
    """Source P/Q approximation at night only, not a feeder power flow."""
    if not 0 < power_factor <= 1:
        raise ValueError("Invalid power factor")
    if min(import_kw, demand_kw) < -1e-8:
        raise ValueError("Negative source net import or load")
    return math.hypot(import_kw, demand_kw * math.tan(math.acos(power_factor)))


def choose_hours(rows, transformer, count=25):
    """Anchor existing model stress dates, then select deterministic new target hours."""
    if len(rows) != 8760 or not 1 <= count <= len(rows):
        raise ValueError("Full 2025 source needed for stress-hour selection")
    by_ts = {r["timestamp_lst"]: r for r in rows}
    if len(by_ts) != len(rows):
        raise ValueError("Duplicate source hour")
    chosen = {}
    def take(ts, reason):
        if ts in by_ts and ts not in chosen and len(chosen) < count:
            chosen[ts] = reason
            return True
        return False
    for ts in ARCHIVE_ANCHORS[transformer]:
        if ts not in by_ts:
            raise ValueError("Missing pinned previous-model stress timestamp")
        take(ts, "OTHER_EQUIPMENT_ARCHIVE_STRESS")
    source_night = [r for r in rows if scalar(r, "pv_dc_available_kw") <= 1e-9]
    if len(source_night) < 20:
        raise ValueError("Suspiciously few verified 2025 night hours")
    buckets = (
        ("NIGHT_PCC_PF095_PROXY_PEAK", 6,
         sorted(source_night, key=lambda r: (
             -nighttime_proxy(scalar(r, "grid_import_kw"), scalar(r, "demand_kw"), .95),
             r["timestamp_lst"]))),
        ("GROSS_LOAD_PEAK", 6,
         sorted(rows, key=lambda r: (-scalar(r, "demand_kw"), r["timestamp_lst"]))),
        ("PV_AVAILABILITY_PEAK", 4,
         sorted(rows, key=lambda r: (-scalar(r, "pv_dc_available_kw"), r["timestamp_lst"]))),
        ("GRID_IMPORT_PEAK", 4,
         sorted(rows, key=lambda r: (-scalar(r, "grid_import_kw"), r["timestamp_lst"]))),
    )
    for reason, quota, ordered in buckets:
        added = 0
        for r in ordered:
            if len(chosen) >= count or added >= quota:
                break
            if take(r["timestamp_lst"], reason):
                added += 1
    # Fill the remaining slots deterministically if peaks/categories overlap.
    for r in sorted(rows, key=lambda r: (-scalar(r, "demand_kw"),
                                          r["timestamp_lst"])):
        if len(chosen) == count:
            break
        take(r["timestamp_lst"], "GROSS_LOAD_SECONDARY")
    if len(chosen) != count:
        raise ValueError("Could not select required number of distinct hours")
    return sorted(chosen.items())


def analyze_case(c, data):
    src.validate_year(data, src.ENERGY_KEYS)
    case_id, transformer, target = c["source_case"], str(c["transformer"]), c["assignment_for_load"]
    if (case_id in MATCHED or transformer not in ARCHIVE_ANCHORS
            or (transformer, target) not in PRIORITY_DESCRIPTIONS):
        raise ValueError("Not one of 12 unmatched reciprocal target cases")
    hw = c["hardware"]
    assumed_kva = float(hw["transformer_kva_assumed_or_evidenced"])
    if assumed_kva <= 0:
        raise ValueError("Assumed transformer kVA invalid")
    p98 = p95 = p95near = 0
    max98 = max95 = maximp = maxload = 0.
    night = 0
    for r in data:
        load, imp, pv = (scalar(r, col) for col in (
            "demand_kw", "grid_import_kw", "pv_dc_available_kw"))
        for col in ("grid_export_kw", "unserved_kw"):
            if abs(scalar(r, col)) > 1e-5:
                raise ValueError("Source no-export/no-unserved policy changed")
        if load < -1e-8 or imp < -1e-8 or pv < -1e-8:
            raise ValueError("Negative source load/import/PV")
        maximp, maxload = max(maximp, imp), max(maxload, load)
        if pv <= 1e-9:
            night += 1
            a98, a95 = nighttime_proxy(imp, load, .98), nighttime_proxy(imp, load, .95)
            max98, max95 = max(max98, a98), max(max95, a95)
            p98 += a98 > assumed_kva + 1e-6
            p95 += a95 > assumed_kva + 1e-6
            p95near += a95 > .9 * assumed_kva
    if night != 4353:
        raise ValueError("NASA PV 2025 nighttime source-hour count changed")
    if abs(sum(scalar(r, "grid_import_kw") for r in data) -
           c["target_yearly_energy_metrics"]["grid_import_kwh"]) > 1e-4:
        raise ValueError("Annual import differs from signed reciprocal manifest")
    band, reason = PRIORITY_DESCRIPTIONS[(transformer, target)]
    record = {
        "reciprocal_case": case_id, "hardware_origin": c["assignment_for_hardware"],
        "target_assignment": target, "transformer": transformer,
        "hardware_tier": c["tier"], "households": len(c["target_house_ids"]),
        "source_energy_2025_hours": len(data),
        "source_energy_sha256": c["target_energy_sha256"],
        "annual_demand_kwh": c["target_yearly_energy_metrics"]["demand_kwh"],
        "annual_grid_import_kwh": c["target_yearly_energy_metrics"]["grid_import_kwh"],
        "annual_curtailment_dc_kwh": c["target_yearly_energy_metrics"]["curtailed_pv_dc_kwh"],
        "assumed_transformer_kva": assumed_kva,
        "pv_panels": hw["pv_panels"], "battery_modules": hw["battery_modules"],
        "battery_power_dc_kw": hw["battery_power_dc_kw"], "inverter_kva": hw["inverter_kva"],
        "nighttime_hours_PV_zero": night,
        "max_night_PCC_S_proxy_pf098_kva": max98,
        "max_night_PCC_S_proxy_pf095_kva": max95,
        "night_proxy_above_assumed_kva_pf098_hours": p98,
        "night_proxy_above_assumed_kva_pf095_hours": p95,
        "night_proxy_above_90pct_assumed_kva_pf095_hours": p95near,
        "max_grid_import_kw": maximp, "max_gross_demand_kw": maxload,
        "source_only_priority_band": band, "source_only_priority_reason": reason,
        "exact_original_AC_source_family_match": False, "new_AC_solves": 0,
        "field_EPM_nameplate_or_service_verified": False,
    }
    by_ts = {r["timestamp_lst"]: r for r in data}
    selection = []
    for ts, why in choose_hours(data, transformer):
        r = by_ts[ts]
        load, imp, pv = (scalar(r, f) for f in
                         ("demand_kw", "grid_import_kw", "pv_dc_available_kw"))
        night_flag = pv <= 1e-9
        selection.append({
            "reciprocal_case": case_id, "transformer": transformer,
            "target_assignment": target, "timestamp_lst": ts,
            "selection_reason": why, "gross_demand_kw": load,
            "inverter_ac_kw": scalar(r, "inverter_ac_kw"),
            "grid_import_kw": imp, "pv_dc_available_kw": pv,
            "night_Q_disabled_source_rule": night_flag,
            "night_PCC_S_proxy_pf098_kva":
                nighttime_proxy(imp, load, .98) if night_flag else "",
            "night_PCC_S_proxy_pf095_kva":
                nighttime_proxy(imp, load, .95) if night_flag else "",
            "assumed_transformer_kva": assumed_kva,
            "AC_solved": False, "EPM_verified": False,
        })
    return record, selection


def inspect(repo):
    full = src.read_json(repo / src.SOURCE_MANIFEST)
    cases = full.get("completed_cases")
    if (full.get("status") != "ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING"
            or not isinstance(cases, dict) or len(cases) != 16):
        raise ValueError("Original 16-case reciprocal manifest unexpectedly changed")
    src.signed_bytes(repo / src.INPUT_MANIFEST, src.INPUT_SHA)
    if src.read_json(repo / src.INPUT_MANIFEST).get("2025_hours") != 8760:
        raise ValueError("Original profile source changed")
    if not MATCHED.issubset(set(cases)) or len(set(cases) - MATCHED) != 12:
        raise ValueError("Four original-source matches and 12 unmatched cases required")
    registers, hours = [], []
    for name in sorted(set(cases)-MATCHED):
        c = cases[name]
        path = src.relative_file(repo, c["target_energy_csv"])
        src.signed_bytes(path, c["target_energy_sha256"])
        data = src.read_csv(path)
        rec, selected = analyze_case(c, data)
        registers.append(rec)
        hours.extend(selected)
    if (len(registers) != 12 or len(hours) != 300
            or sum(r["source_energy_2025_hours"] for r in registers) != 105120
            or sum(r["night_proxy_above_assumed_kva_pf095_hours"] for r in registers) != 2):
        raise ValueError("12-case source evidence/register count mismatch")
    return {"status":"RECIPROCAL12_SOURCE_ONLY_MATERIALITY_AND_25H_PRIORITIZATION",
            "original_reciprocal_cases":16,"already_original_AC_source_matched":4,
            "unmatched_2025_energy_cases":12,"signed_2025_hours_checked":105120,
            "prioritized_target_hours":300,"AC_solver_calls":0,
            "SOC_corrected_AC_reuse_certified_hours":0,
            "actual_EPM_feeder_verified":False,
            "priority_counts":{tier:sum(r["source_only_priority_band"]==tier
                                       for r in registers) for tier in ("P1","P2","P3")},
            "register":registers,"selected_hours":hours}


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    repo=args.repo_root.resolve()
    result=inspect(repo)
    if args.dry_run:
        print(json.dumps({k:v for k,v in result.items()
                          if k not in ("register","selected_hours")},indent=2))
        return 0
    out=next((repo/(OUT+str(i)) for i in range(1,1000)
              if not (repo/(OUT+str(i))).exists()),None)
    if out is None:
        raise ValueError("No unused output version")
    out.mkdir(parents=False)
    reg=out/"UNMATCHED12_SOURCE_MATERIALITY.csv"
    selected=out/"TARGETED_25H_HOUR_SELECTION.csv"
    write_csv(reg,result["register"],REGISTER_FIELDS)
    write_csv(selected,result["selected_hours"],HOUR_FIELDS)
    result["source_register_sha256"]=src.sha256(reg.read_bytes())
    result["source_hour_selection_sha256"]=src.sha256(selected.read_bytes())
    del result["register"]
    del result["selected_hours"]
    (out/"RUN_MANIFEST.json").write_text(
        json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({"status":result["status"],"output":str(out),
          "cases":12,"verified_hours":105120,
          "selected_stress_hours":300,"AC_solver_calls":0,
          "corrected_AC_reuse_certified":0},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
