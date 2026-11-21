#!/usr/bin/env python3
"""113699 A1 fixed-hardware annual SOC rescheduling at signed AC-tested night P points.

One 8760-hour PyPSA LP per explicit --origin A0 or A1. Exactly the frozen
equipment and original source profiles; no original results are overwritten.
AC rechecks cover only 15 preselected stress hours. NOT annual AC validation.
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

HERE = Path("case1/studies/SEEDExchange_StudyA_Matched_Hardware_2026-11-21")
ENVELOPE_RUNNER = HERE / "matched_hardware_ac113699_p_envelope.py"
SWEEP_FOLDER = Path("StudyA_A0_A1_MatchedHardware_AC113699_P_Envelope_v1")
BASE_AC_FOLDER = Path("StudyA_A0_A1_MatchedHardware_AC113699_Pilot_v1")
FULL_FOLDER = Path("StudyA_A0_A1_MatchedHardware_Full_v1")
SWEEP_MANIFEST_GIT_LF_SHA = "3de00d2760b98b75af4f6ca2e2adae5425e7cf3261e8fca3594c250777fb702f"
SWEEP_CSV_SIGNED_SHA = "8c400fdf5bc011a5ff838ae1b05f2426a70abd8fc84cd682c7a9d94fdcfadbb0"
SELECTED_INDEX = 3
ORIGINS = ("A0", "A1")
TR = "113699"
RESULT_PREFIX = "StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_"
AC_P_TOL = .0005
COST_TOL_USD = 1.
SOURCE_PF = .98


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


def target_from_sample(row, group, origin, hour):
    """Pick only the exact source-AC-tested index3 P, not an invented interpolation."""
    if (len(group) != 41 or set(group.sample_number.astype(int)) != set(range(41))
        or (group.status != "CONVERGED").any()
        or not (group.night_reactive_disabled.astype(str).str.lower() == "true").all()
        or (group.q_selected_kvar.abs() > 1e-8).any()):
        raise ValueError("Changed or incomplete 41-point nighttime AC source: "+origin+"/"+hour)
    if (group.hardware_origin != origin).any() or (group.timestamp_lst != hour).any():
        raise ValueError("Source sweep group not the selected case-hour")
    zero = group[group.sample_number == 0].iloc[0]
    if (abs(float(zero.p_sample_ac_kw)) > 1e-9
        or str(zero.ac_feasible).lower() != "false"):
        raise ValueError("Original P=0 overloaded source is missing")
    selected = group[group.sample_number == SELECTED_INDEX].iloc[0]
    if (str(selected.ac_feasible).lower() != "true"
        or float(selected.max_trafo_pct) > 94.5
        or float(selected.min_v_pu) < .95
        or float(selected.max_v_pu) > 1.05
        or float(selected.max_line_pct) > 100
        or not 0 < float(selected.p_sample_ac_kw) <= float(selected.demand_kw)):
        raise ValueError("Selected P is not an AC passing / adequately buffered source sample")
    return {
        "hardware_origin":origin, "timestamp_lst":hour,
        "sample_index":SELECTED_INDEX,
        "fixed_inverter_p_ac_kw":float(selected.p_sample_ac_kw),
        "original_AC_trafo_pct":float(zero.max_trafo_pct),
        "sampled_AC_trafo_pct":float(selected.max_trafo_pct),
        "sampled_AC_min_v_pu":float(selected.min_v_pu),
        "sampled_AC_max_line_pct":float(selected.max_line_pct),
        "sampled_AC_pcc_kva":float(selected.pcc_kva),
        "sampled_AC_feasible_main_095_105":True,
        "sampled_AC_feasible_STRICT_097_103":bool(
            float(selected.min_v_pu) >= .97 and float(selected.max_v_pu) <= 1.03),
        "sampled_AC_not_proof_of_annual_feasibility":True}


def build_plan(repo):
    repo = Path(repo).resolve()
    if not (repo / ".git").is_dir():
        raise ValueError("Execute inside the original repository checkout")
    sweep = load_module(repo / ENVELOPE_RUNNER, "soc_113699_source_envelope")
    v6, cases, geometry, source_failure_rows, old = sweep.preflight(repo)
    manifest_file = repo / SWEEP_FOLDER / "RUN_MANIFEST.json"
    csv_file = repo / SWEEP_FOLDER / "AC_P_SWEEP_SAMPLES.csv"
    if (not manifest_file.is_file()
        or sweep.git_lf_sha(manifest_file) != SWEEP_MANIFEST_GIT_LF_SHA):
        raise ValueError("Independently audited 123-point manifest changed")
    j = json.loads(manifest_file.read_text(encoding="utf-8"))
    if (j.get("status") != "SAMPLED_AC_P_CANDIDATES_FOUND_SOC_AND_ANNUAL_PENDING"
        or j.get("ac_samples_sha256") != SWEEP_CSV_SIGNED_SHA
        or j.get("new_ac_solver_calls") != 123
        or j.get("nonconverged_sample_points") != 0
        or j.get("unresolved_case_hours") != 0
        or j.get("SOC_schedule_changed") is not False
        or j.get("hardware_changed") is not False
        or j.get("annual_AC_feasible") is not False
        or len(j.get("sampled_hour_results", [])) != 3
        or j.get("original_ac_manifest_lf_sha256") != old["original_ac_manifest_lf_sha256"]
        or j.get("original_ac_csv_signed_sha256") != old["original_ac_csv_signed_sha256"]):
        raise ValueError("Original nighttime P-sweep is not the audited result")
    source_hash_mode = sweep.signed_text_mode(csv_file, SWEEP_CSV_SIGNED_SHA)
    df = pd.read_csv(csv_file)
    if (len(df) != 123 or df.status.ne("CONVERGED").any()
        or df.duplicated(["hardware_origin","timestamp_lst","sample_number"]).any()
        or df.assignment.ne("A1").any()
        or df.SOC_chronology_reoptimized.astype(str).str.lower().ne("false").any()
        or df.ac_feasible.astype(str).str.lower().eq("true").sum() != 120):
        raise ValueError("Unexpected AC-envelope source sample roster or classification")
    plans = {}
    for origin in ORIGINS:
        old_hours = [x for x in j["failure_case_hours"] if x["hardware_origin"] == origin]
        expected = sweep.EXPECTED_FAILURES[origin]
        if [x["timestamp_lst"] for x in old_hours] != list(expected):
            raise ValueError("Wrong saved original failed-hour roster: "+origin)
        selected = []
        for t in expected:
            part = df[(df.hardware_origin == origin) & (df.timestamp_lst == t)]
            selected.append(target_from_sample(None, part, origin, t))
            source_e = cases[origin + "_hardware_on_A1"]["energy"].loc[pd.Timestamp(t)]
            if (abs(float(source_e.inverter_ac_kw)) > 1e-7
                or abs(float(source_e.pv_dc_available_kw)) > 1e-7):
                raise ValueError("Historical failed hour no longer has zero P / zero PV")
        plans[origin] = selected
    if sorted([(x["hardware_origin"],x["timestamp_lst"])
               for entries in plans.values() for x in entries]) != sorted(
            [(x["hardware_origin"],x["timestamp_lst"])
             for x in j["failure_case_hours"]]):
        raise ValueError("Signed P-corridor selections do not cover all original failures")
    full = json.loads((repo / FULL_FOLDER / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    source_summaries = {}
    for origin in ORIGINS:
        case = cases[origin + "_hardware_on_A1"]
        source_receipt = full["completed_cases"][case["key"]]
        source_summary = (source_receipt["target_model_summary"]
                          if origin == "A0" else source_receipt["source_model_summary"])
        source_hw = case["hardware"]
        if (source_summary.get("status") != "OPTIMAL_ENERGY_ONLY_NO_AC_VALIDATION"
            or source_summary.get("export_policy") != "zero"
            or abs(float(source_summary["transformer_assumed_kva"]) - 3.) > 1e-8
            or abs(float(source_summary["transformer_loading_screen_pu"]) - 1.) > 1e-8
            or abs(float(source_summary["battery_power_dc_kw"]) -
                   float(source_hw["battery_power_dc_kw"])) > 1e-7
            or abs(float(source_summary["inverter_ac_kva_assumed_unity_pf"]) -
                   float(source_hw["inverter_kva"])) > 1e-7
            or abs(float(source_summary["grid_import_kwh"]) -
                   float(case["energy"].grid_import_kw.sum())) > .002):
            raise ValueError("Original same-equipment economic baseline changed: "+origin)
        source_summaries[origin] = source_summary
    rec = sweep.load_previous(repo).load_recip(repo)
    pv = rec.load_module(repo / rec.PVBESS, "soc_corridor_113699_original_pv")
    solar, solar_path = pv.solar_per_unit(repo, cases["A0_hardware_on_A1"]["trace"].index)
    if sha(solar_path) != full["solar_sha256"]:
        raise ValueError("Original 2025 NASA PV source changed")
    sources = {
        "status": "SIGNED_113699_SAMPLED_P_TO_ANNUAL_SOC_PREFLIGHT_NO_NEW_LP_OR_AC",
        "input_sweep_result_commit": "00a11b1c2a948360701744189bb2657c7a77f613",
        "input_sweep_manifest_git_lf_sha256": SWEEP_MANIFEST_GIT_LF_SHA,
        "input_sweep_samples_original_sha256": SWEEP_CSV_SIGNED_SHA,
        "input_sweep_csv_hash_mode": source_hash_mode,
        "input_sweep_runner_sha256": sha(repo / ENVELOPE_RUNNER),
        "signed_NASA_pv_source_sha256":sha(solar_path),
        "original_full_energy_manifest_git_lf_sha256": old["signed_energy_source_manifest_lf_sha256"],
        "source_AC_limit": "0.95..1.05 pu and <=100% assumed transformer/conductor loading",
        "strict_voltage_097_screen": "SEPARATE, NOT PROVEN; NOV 30 MAX P STILL ONLY 0.969546 pu",
        "sampled_points_not_interpolated":True,
        "target_inverter_P_exactly_source_sampled":True,
        "annual_source_hours":8760, "assumed_transformer_kva":3.,
        "source_assignment":"A1", "pf":SOURCE_PF, "service_factor":1.,
        "night_Q":"OFF", "original_hardware_frozen":True,
        "battery_physical_min_soc":.20, "cyclic_store":True,
        "export_policy":"zero", "unserved_policy":"none",
        "new_LP_solves":0, "new_AC_solves":0, "annual_AC_feasible":False,
        "sampled_hour_P_targets":plans,
        "source_case_hw":{o:cases[o+"_hardware_on_A1"]["hardware"] for o in ORIGINS},
        "source_case_yearly_energy_SHA":{o:cases[o+"_hardware_on_A1"]["source_csv_sha256"] for o in ORIGINS},
        "source_case_original_annual_summary":source_summaries,
        "method":"Full 8760h fixed hardware PyPSA LP, equal-P targets at original sampled points; subsequent 15h AC only"}
    return sweep, rec, v6, cases, geometry, solar, plans, source_summaries, sources


def output_path(repo, origin, specified=None):
    if specified is not None:
        out = specified if specified.is_absolute() else repo / specified
        out = out.resolve()
        if out.exists() or out.parent != repo:
            raise FileExistsError("Require an unused repository-root result folder")
        return out
    for n in range(1,1000):
        out = repo / (RESULT_PREFIX + origin + "_v" + str(n))
        if not out.exists():
            return out
    raise FileExistsError("No free annual SOC experiment version")


def source_equipment(fixed, data, original):
    return fixed.Hardware(
        panels=int(data["pv_panels"]),
        battery_modules=int(data["battery_modules"]),
        battery_power_dc_kw=float(data["battery_power_dc_kw"]),
        inverter_kva=float(data["inverter_kva"]),
        transformer_kva=float(data["transformer_kva_assumed_or_evidenced"]),
        loading_pu=1., load_pf=SOURCE_PF, export_policy="zero",
        annual_equipment_usd=float(original["annual_equipment_usd"]),
        annual_total_usd=float(original["annual_total_usd"]))


def soc_diagnostics(earlier, updated, points, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out.mkdir(exist_ok=False)
    hashes = {}
    for x in points:
        target = pd.Timestamp(x["timestamp_lst"])
        focus = (earlier.index >= target - pd.Timedelta(hours=12)) & (
            earlier.index <= target + pd.Timedelta(hours=12))
        fig, ax = plt.subplots(figsize=(11,5))
        ax.plot(earlier.index[focus], earlier.loc[focus, "battery_soc_usable_kwh"],
                label="signed original SOC", linewidth=1.3)
        ax.plot(updated.index[focus], updated.loc[focus, "battery_soc_usable_kwh"],
                label="reoptimized SOC", linewidth=1.3)
        ax.axvline(target, linestyle="--", linewidth=.8, label="AC corridor hour")
        ax.set_title("113699 A1 same-equipment 2025 SOC, " + x["timestamp_lst"])
        ax.set_ylabel("Original model usable Store energy (kWh)")
        ax.set_xlabel("2025 local time")
        ax.grid(alpha=.3)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        name = "soc_" + target.strftime("%Y%m%d_%H") + ".png"
        fig.savefig(out / name, dpi=170)
        plt.close(fig)
        hashes[name] = sha(out / name)
    return hashes


def run(repo, origin=None, out=None, preflight_only=False):
    repo = Path(repo).resolve()
    sweep, rec, v6, cases, geometry, solar, plans, originals, source = build_plan(repo)
    if preflight_only:
        return source
    if origin not in ORIGINS:
        raise ValueError("Choose --origin A0 or --origin A1 for one annual solve at a time")
    result = output_path(repo, origin, out)
    result.mkdir(parents=True, exist_ok=False)
    receipt = dict(source, status="INCOMPLETE_SOC_CORRIDOR_NO_AC_CLAIM",
                   origin=origin, output_folder=str(result), new_LP_solves=0, new_AC_solves=0)
    manifest_file = result / "RUN_MANIFEST.json"
    def save():
        manifest_file.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n",encoding="utf-8")
    save()
    try:
        fixed = rec.load_module(repo / rec.FIXED, "soc_113699_unmodified_fixed_hardware")
        original = cases[origin + "_hardware_on_A1"]
        hw = source_equipment(fixed, original["hardware"], originals[origin])
        demand = original["trace"].sum(axis=1)
        corridors = {
            pd.Timestamp(x["timestamp_lst"]):
                (x["fixed_inverter_p_ac_kw"], x["fixed_inverter_p_ac_kw"])
            for x in plans[origin]}
        if len(corridors) != len(plans[origin]) or not demand.index.equals(solar.index):
            raise ValueError("Misaligned source timestamps or duplicate P constraints")
        updated, model_summary = fixed.solve_fixed(
            repo, hw, demand, solar, corridors=corridors,
            min_physical_soc=.20)
        updated.index.name = "timestamp_lst"
        metrics = rec.validate_dispatch(updated, original["trace"], original["hardware"])
        if (abs(float(model_summary["annual_equipment_usd"]) -
                float(originals[origin]["annual_equipment_usd"])) > .02
            or abs(float(model_summary["annual_total_usd"]) -
                   (float(model_summary["annual_equipment_usd"]) +
                    float(model_summary["annual_grid_import_usd"]))) > .02
            or float(model_summary["annual_total_usd"]) <
                 float(originals[origin]["annual_total_usd"]) - COST_TOL_USD
            or abs(float(model_summary["annual_grid_import_usd"]) -
                   .29 * metrics["grid_import_kwh"]) > .02):
            raise ValueError("Source model hardware or annual baseline tariff/objective changed")
        for target, (lo, hi) in corridors.items():
            actual = float(updated.at[target, "inverter_ac_kw"])
            if abs(actual - lo) > AC_P_TOL or lo != hi:
                raise ValueError("Annual LP did not reproduce exact tested P target at "+str(target))
            if (float(updated.at[target,"battery_charge_dc_kw"]) > 1e-6
                or float(updated.at[target,"pv_dc_available_kw"]) > 1e-6):
                raise ValueError("Nightly corridor not served solely by battery DC dispatch")
        annual_file = result / "annual_soc_reoptimized_2025.csv"
        updated.to_csv(annual_file, float_format="%.10f")
        if sha(annual_file) != sha(annual_file):
            raise AssertionError("Unexpected CSV mutation")
        reloaded = pd.read_csv(annual_file, parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
        rec.validate_dispatch(reloaded, original["trace"], original["hardware"])
        ac_source = json.loads((repo / BASE_AC_FOLDER / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
        sample_hours = [pd.Timestamp(x["timestamp_lst"]) for x in ac_source["sampled_timestamps"]]
        if len(sample_hours) != 15 or len(set(sample_hours)) != 15:
            raise ValueError("Original bounded AC stress roster changed")
        import pandapower as pp
        territory, net, meta, _ = geometry["A1"]
        check = []
        for ts in sample_hours:
            hour = updated.loc[ts]
            result_at_hour = v6.solve_ac_hour(
                net, meta, territory, ts, original["trace"].loc[ts], SOURCE_PF,
                float(hour.inverter_ac_kw), float(hw.inverter_kva),
                float(hour.pv_dc_available_kw), .25, 9, "pvbess", pp)
            check.append({
                "origin":origin, "assignment":"A1", "timestamp_lst":str(ts),
                "new_inverter_p_ac_kw":float(hour.inverter_ac_kw),
                "original_inverter_p_ac_kw":float(original["energy"].at[ts,"inverter_ac_kw"]),
                "corridor_enforced":ts in corridors,
                **result_at_hour})
        check_frame = pd.DataFrame(check)
        if (len(check_frame) != 15 or check_frame.status.ne("CONVERGED").any()):
            raise ValueError("15-hour AC independent check missing or nonconvergent")
        for sample in plans[origin]:
            target = sample["timestamp_lst"]
            single = check_frame[check_frame.timestamp_lst == target]
            if len(single)!=1 or single.iloc[0].ac_feasible != True:
                raise ValueError("Reoptimized dispatch fails its source-tested corridor at "+target)
            r = single.iloc[0]
            if abs(float(r.max_trafo_pct) - sample["sampled_AC_trafo_pct"]) > .02:
                raise ValueError("Signed AC P sample transformer result cannot be reproduced")
            if abs(float(r.min_v_pu) - sample["sampled_AC_min_v_pu"]) > .0002:
                raise ValueError("Signed AC P sample voltage cannot be reproduced")
        ac_file=result/"ac_original_15_stress_hours.csv"
        check_frame.to_csv(ac_file,index=False,float_format="%.10f")
        diag=soc_diagnostics(original["energy"],updated,plans[origin],result/"figures_diagnostic")
        receipt.update(
            source_energy_hourly_sha256=original["source_csv_sha256"],
            new_annual_energy_hourly_sha256=sha(annual_file),
            sampled_ac_sha256=sha(ac_file),
            diagnostic_plot_sha256=diag,
            new_LP_solves=1, new_AC_solves=15,
            yearly_new_model_summary=model_summary,
            yearly_new_metrics=metrics,
            original_annual_grid_import_kwh=float(original["energy"].grid_import_kw.sum()),
            delta_annual_grid_import_kwh=float(metrics["grid_import_kwh"] -
                original["energy"].grid_import_kw.sum()),
            delta_annual_total_usd=float(model_summary["annual_total_usd"] -
                originals[origin]["annual_total_usd"]),
            changed_inverter_hour_count=int(np.sum(np.abs(
                updated.inverter_ac_kw.to_numpy(float) -
                original["energy"].inverter_ac_kw.to_numpy(float)) > 1e-5)),
            changed_soc_hour_count=int(np.sum(np.abs(
                updated.battery_soc_usable_kwh.to_numpy(float) -
                original["energy"].battery_soc_usable_kwh.to_numpy(float)) > 1e-5)),
            original_15_sample_AC_feasible=int(check_frame.ac_feasible.eq(True).sum()),
            original_15_sample_AC_infeasible=int(check_frame.ac_feasible.eq(False).sum()),
            original_15_sample_max_transformer_pct=float(check_frame.max_trafo_pct.max()),
            original_15_sample_min_voltage_pu=float(check_frame.min_v_pu.min()),
            original_15_strict_below_097_hours=int(check_frame.voltage_below_097.sum()),
            annual_AC_feasible=False,
            status=("ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_PASS_ANNUAL_AC_PENDING"
                    if check_frame.ac_feasible.eq(True).all() else
                    "ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_VIOLATIONS_ANNUAL_AC_PENDING"))
        save()
        print("Annual LP and independent 15 AC samples complete for",origin,flush=True)
        return {"status":receipt["status"], "origin":origin, "output":str(result),
                "LP_solves":1, "AC_sample_hours":15,
                "AC_sample_feasible":receipt["original_15_sample_AC_feasible"],
                "delta_yearly_USD":receipt["delta_annual_total_usd"],
                "annual_AC_feasible":False}
    except Exception as exc:
        receipt["status"]="INCOMPLETE_SOC_CORRIDOR_DO_NOT_CLAIM"
        receipt["failure"]={"type":type(exc).__name__,"message":str(exc),
                            "traceback":traceback.format_exc()}
        save()
        raise


def cli(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--origin",choices=ORIGINS)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    print(json.dumps(run(args.repo_root,args.origin,args.out,args.preflight_only),
                     indent=2,allow_nan=False))


if __name__=="__main__":
    cli()
