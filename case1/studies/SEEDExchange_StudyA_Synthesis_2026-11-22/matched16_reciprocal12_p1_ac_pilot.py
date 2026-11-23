#!/usr/bin/env python3
"""Strict source-checked, optional 36-case-hour reciprocal P1 AC diagnostic.

--preflight-only NEVER invokes pandapower, --run-pilot is explicit.
The 36 case-hour evaluations may each require multiple internal pp.runpp
calls for Q search. Do not interpret a completed pilot as annual AC feasibility.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import matched16_original_ac_input_preflight as source

FROZEN = Path("StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json")
MATERIALITY = Path("StudyA_Reciprocal12_Source_Materiality_v1")
PV_CODE = Path("case1/studies/SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py")
OUT_STEM = "StudyA_Reciprocal12_P1_AC_Pilot_v"
PF = (.98, .95)
Q_RATIO = .25
ANCHORS = {
    "A1_94022_min_cost_to_A0": ("2025-03-28 20:00:00", "2025-11-27 20:00:00"),
    "A1_94022_ss90_to_A0": ("2025-03-28 20:00:00", "2025-11-27 20:00:00"),
    "A0_113699_min_cost_to_A1": ("2025-03-14 19:00:00", "2025-03-30 19:00:00",
                                  "2025-11-30 20:00:00"),
    "A0_113699_ss90_to_A1": ("2025-03-14 19:00:00", "2025-03-30 19:00:00",
                              "2025-11-30 20:00:00"),
    "A0_106039_ss90_to_A1": ("2025-11-27 20:00:00",),
    "A1_106039_ss90_to_A0": ("2025-11-27 20:00:00",),
}

def digest(path):
    return hashlib.sha256(source.required_file(path).read_bytes()).hexdigest()

def choose_case(case, rows):
    if case not in ANCHORS:
        raise ValueError("Unapproved case")
    if len(rows) != 25:
        raise ValueError("Expected 25 source-selected hours")
    index = {x["timestamp_lst"]: x for x in rows}
    if len(index) != 25 or any(x["reciprocal_case"] != case for x in rows):
        raise ValueError("Duplicate source timestamp or wrong case")
    chosen = []
    for ts in ANCHORS[case]:
        if ts not in index:
            raise ValueError("Missing archived stress timestamp")
        row = index[ts]
        if (float(row["pv_dc_available_kw"]) > 1e-9
            or row["night_Q_disabled_source_rule"] != "True"):
            raise ValueError("Archived stress input is not night Q-off")
        chosen.append((row, "ARCHIVED_NIGHT_STRESS"))
    daylight = [x for x in rows if x["selection_reason"] == "PV_AVAILABILITY_PEAK"
                and float(x["pv_dc_available_kw"]) > 1e-9]
    if not daylight:
        raise ValueError("No source-selected daytime PV peak")
    high = sorted(daylight, key=lambda x: (-float(x["pv_dc_available_kw"]),
                                          x["timestamp_lst"]))[0]
    if high["timestamp_lst"] in ANCHORS[case] or high["night_Q_disabled_source_rule"] != "False":
        raise ValueError("Daytime solar or night-Q flag mismatch")
    chosen.append((high, "DAYLIGHT_PV_Q_CHECK"))
    return chosen

def choose_all(register, selections):
    if len(register) != 12 or len(selections) != 300:
        raise ValueError("Signed 12-case materiality receipt population changed")
    case_register = {r["reciprocal_case"]: r for r in register}
    if len(case_register) != 12:
        raise ValueError("Duplicate materiality case")
    p1 = {name for name, r in case_register.items()
          if r["source_only_priority_band"] == "P1"}
    if p1 != set(ANCHORS):
        raise ValueError("Priority set changed; new independent review required")
    by_case = {}
    for row in selections:
        by_case.setdefault(row["reciprocal_case"], []).append(row)
    if set(by_case) != set(case_register) or any(len(v) != 25 for v in by_case.values()):
        raise ValueError("Case-hour register changed")
    events = []
    for case in sorted(ANCHORS):
        for row, reason in choose_case(case, by_case[case]):
            if row["transformer"] != case_register[case]["transformer"]:
                raise ValueError("Selected transformer differs from case register")
            events.append((case, row, reason))
    if len(events) != 18:
        raise ValueError("Expected exactly 18 selected P1 case-hours")
    return events

def load_python(path, name):
    spec = importlib.util.spec_from_file_location(name, source.required_file(path))
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def preflight(repo):
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise ValueError("Use the real GitLab checkout, including .git")
    receipt = source.read_json(repo / MATERIALITY / "RUN_MANIFEST.json")
    if (receipt["status"] != "RECIPROCAL12_SOURCE_ONLY_MATERIALITY_AND_25H_PRIORITIZATION"
        or tuple(receipt[k] for k in ("unmatched_2025_energy_cases",
                                      "signed_2025_hours_checked",
                                      "prioritized_target_hours", "AC_solver_calls"))
            != (12, 105120, 300, 0)):
        raise ValueError("Materiality receipt is not the signed original")
    regfile = repo / MATERIALITY / "UNMATCHED12_SOURCE_MATERIALITY.csv"
    eventsfile = repo / MATERIALITY / "TARGETED_25H_HOUR_SELECTION.csv"
    source.signed_bytes(regfile, receipt["source_register_sha256"])
    source.signed_bytes(eventsfile, receipt["source_hour_selection_sha256"])
    register, selected = source.read_csv(regfile), source.read_csv(eventsfile)
    targets = choose_all(register, selected)
    cases = source.read_json(repo / FROZEN)
    if (cases["status"] != "ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING"
        or len(cases["completed_cases"]) != 16):
        raise ValueError("Frozen reciprocal source manifest changed")
    source.signed_bytes(repo / source.INPUT_MANIFEST, source.INPUT_SHA)
    pv = load_python(repo / PV_CODE, "reciprocal_p1_verified_pvbess")
    m, v6, mapping, profiles = pv.secure_context(repo, repo / pv.MANIFEST_REL)
    groups, archived, evidence = {}, {}, []
    for case in sorted(ANCHORS):
        c = cases["completed_cases"][case]
        r = next(x for x in register if x["reciprocal_case"] == case)
        tr, target = str(c["transformer"]), c["assignment_for_load"]
        if (c["source_case"] != case or c["AC_verified"] is not False
            or r["transformer"] != tr or r["target_assignment"] != target
            or r["source_energy_sha256"] != c["target_energy_sha256"]
            or r["source_only_priority_band"] != "P1"):
            raise ValueError("Frozen energy case identity differs from selection")
        ids, trace = pv.source_trace(m, mapping, profiles, target, tr)
        if ids != c["target_house_ids"] or len(ids) != int(r["households"]):
            raise ValueError("Target case/source profile household mismatch")
        terr = v6.new_territory(repo, target, tr, ids, 1.0)
        if sorted(a["house"] for a in terr.attachments) != sorted(ids):
            raise ValueError("GIS builder lost selected household attachment")
        if abs(float(terr.trafo["kva"]) -
               float(c["hardware"]["transformer_kva_assumed_or_evidenced"])) > 1e-9:
            raise ValueError("GIS transformer assumption differs from fixed hardware")
        path = source.relative_file(repo, c["target_energy_csv"])
        mode = source.signed_bytes(path, c["target_energy_sha256"])
        energy = source.read_csv(path)
        source.validate_year(energy, source.ENERGY_KEYS)
        archived[case] = {row["timestamp_lst"]: row for row in energy}
        groups[case] = (terr, ids, trace, c)
        evidence.append({"case": case, "transformer": tr, "assignment": target,
                         "households": len(ids), "energy_sha256": c["target_energy_sha256"],
                         "signature_mode": mode, "GIS_nodes": len(terr.graph.nodes),
                         "GIS_edges": len(terr.graph.edges),
                         "assumed_transformer_kva": float(terr.trafo["kva"])})
    import pandas as pd
    planned = []
    for case, sel, reason in targets:
        terr, ids, trace, c = groups[case]
        ts = sel["timestamp_lst"]
        row = archived[case][ts]
        for selected_key, energy_key in (
            ("gross_demand_kw", "demand_kw"), ("inverter_ac_kw", "inverter_ac_kw"),
            ("grid_import_kw", "grid_import_kw"),
            ("pv_dc_available_kw", "pv_dc_available_kw")):
            if abs(float(sel[selected_key]) - float(row[energy_key])) > 1e-7:
                raise ValueError("Materiality source hour differs from signed annual P")
        demand, inv, imported = (float(row[k]) for k in
                                 ("demand_kw", "inverter_ac_kw", "grid_import_kw"))
        if (abs(float(trace.loc[pd.Timestamp(ts)].sum()) - demand) > 1e-5
            or abs(demand - inv - imported + float(row["grid_export_kw"])) > 2e-4
            or not all(math.isfinite(x) for x in (demand, inv, imported))
            or inv < -1e-7 or inv > float(c["hardware"]["inverter_kva"]) + 1e-6):
            raise ValueError("Exact individual demand/PCC active-power source mismatch")
        pv_dc = float(row["pv_dc_available_kw"])
        night = pv_dc <= 1e-9
        if str(night) != sel["night_Q_disabled_source_rule"]:
            raise ValueError("PV daylight and source Q eligibility disagree")
        planned.append({"case": case, "transformer": str(c["transformer"]),
                        "target_assignment": c["assignment_for_load"],
                        "hardware_origin": c["assignment_for_hardware"],
                        "tier": c["tier"], "timestamp_lst": ts, "reason": reason,
                        "demand_kw": demand, "inverter_ac_kw": inv,
                        "grid_import_kw": imported, "pv_dc_available_kw": pv_dc,
                        "night_q_disabled": night,
                        "inverter_kva": float(c["hardware"]["inverter_kva"]),
                        "assumed_transformer_kva": float(terr.trafo["kva"]),
                        "source_sha256": c["target_energy_sha256"]})
    doc = {"status": "P1_RECIPROCAL12_SIGNED_GIS_PQ_PREFLIGHT_NO_AC",
           "cases": 6, "case_hours_selected": len(planned),
           "planned_AC_case_hour_evaluations": len(planned)*2,
           "new_AC_case_hour_evaluations": 0, "PF": list(PF),
           "length_factor": 1.0, "daytime_Q_ratio": Q_RATIO,
           "night_Q_disabled": True,
           "pandapower_internal_solver_calls": "NOT_COUNTED",
           "annual_AC_verified": False, "field_EPM_verified": False,
           "GIS_source_provenance": evidence, "selected_source_events": planned}
    return doc, planned, groups, v6

def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def draw_diagnostics(out, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder = out / "figures_diagnostic"
    folder.mkdir()
    events = sorted({(r["case"], r["timestamp_lst"]) for r in rows})
    ix = {event: i for i, event in enumerate(events)}
    hashes = {}
    for metric, limit, ylab, filename in (
        ("min_v_pu", .95, "minimum house voltage [pu]", "min_voltage.png"),
        ("max_trafo_pct", 100., "assumed transformer loading [%]", "trafo_loading.png")):
        fig, ax = plt.subplots(figsize=(16, 5))
        for pf, shift in ((.98, -.1), (.95, .1)):
            good = [r for r in rows if r["pf"] == pf
                    and r["status"] == "CONVERGED" and r[metric] is not None]
            ax.scatter([ix[(r["case"], r["timestamp_lst"])] + shift for r in good],
                       [float(r[metric]) for r in good], label=f"PF {pf}")
        ax.axhline(limit, linestyle="--", label="research screen")
        ax.set_xticks(range(len(events)))
        ax.set_xticklabels([f"{c.split('_')[0]} {c.split('_')[1]} / {ts[5:16]}"
                            for c, ts in events], rotation=75, ha="right", fontsize=7)
        ax.set_ylabel(ylab)
        ax.set_title("Study A reciprocal P1 pilot, 18 case-hours, model assumptions")
        ax.legend()
        fig.tight_layout()
        path = folder / filename
        fig.savefig(path, dpi=150)
        plt.close(fig)
        hashes[filename] = file_sha(path)
    return hashes

def pilot(repo, receipt, planned, groups, v6):
    from run_epm_validation import build_net
    import pandapower as pp
    import pandas as pd
    out = next((repo / f"{OUT_STEM}{i}" for i in range(1, 100)
                if not (repo / f"{OUT_STEM}{i}").exists()), None)
    if out is None:
        raise ValueError("No unused versioned output directory")
    out.mkdir()
    manifest = out / "RUN_MANIFEST.json"
    doc = dict(receipt)
    doc.update(status="INCOMPLETE_P1_AC_PILOT_DO_NOT_CLAIM", new_AC_case_hour_evaluations=0)
    manifest.write_text(json.dumps(doc, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    results = []
    try:
        for case in sorted(ANCHORS):
            terr, ids, trace, frozen = groups[case]
            net, meta = build_net(terr, "head")
            if set(meta["loads"]) != set(ids):
                raise ValueError("Pandapower GIS load IDs differ from selected households")
            for x in (e for e in planned if e["case"] == case):
                t = pd.Timestamp(x["timestamp_lst"])
                for pf in PF:
                    r = v6.solve_ac_hour(net, meta, terr, t, trace.loc[t], pf,
                                         x["inverter_ac_kw"], x["inverter_kva"],
                                         x["pv_dc_available_kw"], Q_RATIO, 9,
                                         "pvbess", pp)
                    if (abs(float(r["gross_demand_kw"]) - x["demand_kw"]) > 1e-5
                        or abs(float(r["inverter_ac_kw"]) - x["inverter_ac_kw"]) > 1e-5):
                        raise ValueError("New AC replay did not use exact saved P demand")
                    results.append({**x, "pf": pf, "length_factor": 1.0,
                                    "daytime_q_ratio": Q_RATIO, **r})
                    print(f"AC pilot {len(results)}/36 {case} {t} PF {pf}", flush=True)
        if len(results) != 36:
            raise ValueError("Incomplete number of P1 AC source case-hours")
        converged = [r for r in results if r["status"] == "CONVERGED"]
        doc.update(status="P1_TARGETED_36_AC_CASEHOURS_RECORDED_NOT_ANNUAL",
                   new_AC_case_hour_evaluations=36, converged=len(converged),
                   nonconverged=36-len(converged),
                   infeasible=sum(r["ac_feasible"] is False for r in converged),
                   annual_AC_verified=False, field_EPM_verified=False)
        fields = sorted(set().union(*(set(x) for x in results)))
        path = out / "TARGETED_36_AC_CASEHOURS.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)
        doc["targeted_ac_csv_sha256"] = file_sha(path)
        doc["figures_diagnostic_sha256"] = draw_diagnostics(out, results)
        manifest.write_text(json.dumps(doc, indent=2, allow_nan=False)+"\n",
                            encoding="utf-8")
        return {"status":doc["status"],"output":str(out),"evaluations":36,
                "converged":doc["converged"],"infeasible":doc["infeasible"],
                "nonconverged":doc["nonconverged"],"annual_AC_verified":False}
    except Exception as err:
        doc.update(status="INCOMPLETE_P1_AC_PILOT_DO_NOT_CLAIM",
                   new_AC_case_hour_evaluations=len(results),
                   failure=f"{type(err).__name__}: {err}")
        manifest.write_text(json.dumps(doc, indent=2, allow_nan=False)+"\n",
                            encoding="utf-8")
        raise

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only",action="store_true")
    mode.add_argument("--run-pilot",action="store_true")
    args = parser.parse_args(argv)
    doc, planned, groups, v6 = preflight(args.repo_root)
    value = doc if args.preflight_only else pilot(args.repo_root.resolve(),doc,planned,groups,v6)
    print(json.dumps(value,indent=2,allow_nan=False))

if __name__ == "__main__":
    main()
