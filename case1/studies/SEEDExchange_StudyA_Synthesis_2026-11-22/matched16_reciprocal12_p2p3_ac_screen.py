#!/usr/bin/env python3
"""Study A reciprocal P2/P3, signed original schedules, 150 hours x two PF.

Uses the existing P1 input-validation pattern and same original v6 AC solver.
No new PyPSA optimization or annual AC claim. No output written at preflight.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import matched16_reciprocal12_p1_ac_pilot as p1
import matched16_original_ac_input_preflight as source

FROZEN = p1.FROZEN
MATERIALITY = p1.MATERIALITY
PV_CODE = p1.PV_CODE
OUT_STEM = "StudyA_Reciprocal12_P2P3_AC_Screen_v"
PF = p1.PF
Q_RATIO = p1.Q_RATIO
CASES = {
    "A0_94022_min_cost_to_A1": "P2",
    "A0_94022_ss90_to_A1": "P2",
    "A0_85398_min_cost_to_A1": "P2",
    "A0_85398_ss90_to_A1": "P2",
    "A1_113699_min_cost_to_A0": "P3",
    "A1_113699_ss90_to_A0": "P3"
}
load_python = p1.load_python
file_sha = p1.file_sha

def choose_all(register, selections):
    if len(register) != 12 or len(selections) != 300:
        raise ValueError("Expected signed 12-case 300-hour source selection")
    reg = {r["reciprocal_case"]: r for r in register}
    if len(reg) != 12 or set(reg) != (set(p1.ANCHORS) | set(CASES)):
        raise ValueError("Incorrect or duplicate frozen source case")
    if any(reg[c]["source_only_priority_band"] != "P1" for c in p1.ANCHORS):
        raise ValueError("Previously screened P1 set changed")
    if any(reg[c]["source_only_priority_band"] != band for c,band in CASES.items()):
        raise ValueError("P2/P3 source priority band changed")
    by_case = {c: [] for c in reg}
    for row in selections:
        c = row["reciprocal_case"]
        if c not in reg:
            raise ValueError("Unknown source case selection")
        if row["transformer"] != reg[c]["transformer"] or row["target_assignment"] != reg[c]["target_assignment"]:
            raise ValueError("Source selection territory or assignment mismatch")
        by_case[c].append(row)
    for c, rows in by_case.items():
        if len(rows) != 25 or len({r["timestamp_lst"] for r in rows}) != 25:
            raise ValueError("Each source family must have 25 unique selected hours")
    return [(c,row,row["selection_reason"]) for c in sorted(CASES)
            for row in sorted(by_case[c],key=lambda x:x["timestamp_lst"])]

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
    pv = load_python(repo / PV_CODE, "reciprocal_p2p3_verified_pvbess")
    m, v6, mapping, profiles = pv.secure_context(repo, repo / pv.MANIFEST_REL)
    groups, archived, evidence = {}, {}, []
    for case in sorted(CASES):
        c = cases["completed_cases"][case]
        r = next(x for x in register if x["reciprocal_case"] == case)
        tr, target = str(c["transformer"]), c["assignment_for_load"]
        if (c["source_case"] != case or c["AC_verified"] is not False
            or r["transformer"] != tr or r["target_assignment"] != target
            or r["source_energy_sha256"] != c["target_energy_sha256"]
            or r["source_only_priority_band"] != CASES[case]):
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
    if len(planned) != 150:
        raise ValueError("Expected 150 distinct source case-hours")
    doc = {"status": "P2P3_RECIPROCAL12_SIGNED_GIS_PQ_PREFLIGHT_NO_AC",
           "cases": 6, "case_hours_selected": len(planned),
           "planned_AC_case_hour_evaluations": len(planned)*2,
           "new_AC_case_hour_evaluations": 0, "PF": list(PF),
           "length_factor": 1.0, "daytime_Q_ratio": Q_RATIO,
           "night_Q_disabled": True,
           "pandapower_internal_solver_calls": "NOT_COUNTED",
           "annual_AC_verified": False, "field_EPM_verified": False,
           "GIS_source_provenance": evidence, "selected_source_events": planned}
    return doc, planned, groups, v6

def draw_diagnostics(out, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder = out / "figures_diagnostic"
    folder.mkdir()
    events = sorted({r["case"] for r in rows})
    ix = {event: i for i, event in enumerate(events)}
    hashes = {}
    for metric, limit, ylab, filename in (
        ("min_v_pu", .95, "minimum house voltage [pu]", "min_voltage.png"),
        ("max_trafo_pct", 100., "assumed transformer loading [%]", "trafo_loading.png")):
        fig, ax = plt.subplots(figsize=(12, 5))
        for pf, shift in ((.98, -.1), (.95, .1)):
            good = [r for r in rows if r["pf"] == pf
                    and r["status"] == "CONVERGED" and r[metric] is not None]
            ax.scatter([ix[r["case"]] + shift for r in good],
                       [float(r[metric]) for r in good], label=f"PF {pf}")
        ax.axhline(limit, linestyle="--", label="research screen")
        ax.set_xticks(range(len(events)))
        ax.set_xticklabels([c.replace("_to_", " to ") for c in events], rotation=75, ha="right", fontsize=7)
        ax.set_ylabel(ylab)
        ax.set_title("Study A reciprocal P2/P3: 25 selected hours per case, not annual")
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
    doc.update(status="INCOMPLETE_P2P3_AC_SCREEN_DO_NOT_CLAIM", new_AC_case_hour_evaluations=0)
    manifest.write_text(json.dumps(doc, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    results = []
    try:
        for case in sorted(CASES):
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
                    print(f"AC pilot {len(results)}/300 {case} {t} PF {pf}", flush=True)
        if len(results) != 300:
            raise ValueError("Incomplete number of P2/P3 AC source case-hours")
        converged = [r for r in results if r["status"] == "CONVERGED"]
        doc.update(status="P2P3_TARGETED_300_AC_CASEHOURS_RECORDED_NOT_ANNUAL",
                   new_AC_case_hour_evaluations=300, converged=len(converged),
                   nonconverged=300-len(converged),
                   infeasible=sum(r["ac_feasible"] is False for r in converged),
                   annual_AC_verified=False, field_EPM_verified=False)
        case_summary = []
        for case in sorted(CASES):
            for pf in PF:
                rows = [r for r in results if r["case"] == case and r["pf"] == pf]
                good = [r for r in rows if r["status"] == "CONVERGED"]
                if len(rows) != 25 or len({r["timestamp_lst"] for r in rows}) != 25:
                    raise ValueError("Incomplete/duplicate case PF sample population")
                case_summary.append({
                    "case": case, "priority_band": CASES[case], "pf": pf,
                    "selected_hours": 25, "converged": len(good),
                    "nonconverged": 25-len(good),
                    "main_band_failures": sum(r["ac_feasible"] is False for r in good),
                    "min_v_pu": min((float(r["min_v_pu"]) for r in good),default=None),
                    "max_trafo_pct": max((float(r["max_trafo_pct"]) for r in good),default=None),
                    "max_line_pct": max((float(r["max_line_pct"]) for r in good),default=None),
                    "annual_AC_verified": False,
                })
        summary_path = out / "CASE_PF_SUMMARY_12.csv"
        with summary_path.open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(case_summary[0]))
            writer.writeheader()
            writer.writerows(case_summary)
        doc["case_pf_summary_sha256"] = file_sha(summary_path)
        doc["case_pf_summary"] = case_summary
        fields = sorted(set().union(*(set(x) for x in results)))
        path = out / "TARGETED_300_AC_CASEHOURS.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)
        doc["targeted_ac_csv_sha256"] = file_sha(path)
        doc["figures_diagnostic_sha256"] = draw_diagnostics(out, results)
        manifest.write_text(json.dumps(doc, indent=2, allow_nan=False)+"\n",
                            encoding="utf-8")
        return {"status":doc["status"],"output":str(out),"evaluations":300,
                "converged":doc["converged"],"infeasible":doc["infeasible"],
                "nonconverged":doc["nonconverged"],"annual_AC_verified":False}
    except Exception as err:
        doc.update(status="INCOMPLETE_P2P3_AC_SCREEN_DO_NOT_CLAIM",
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
