#!/usr/bin/env python3
"""Annual AC replay of source-signed 113699 A1 full-2025 cyclic-SOC redispatch.

One frozen hardware origin at a time, using original EPM GIS pandapower proxy.
The annual LP and 15-hour AC files are immutable inputs. User-local execution.
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
SOC_CODE = HERE / "matched_hardware_113699_soc_corridor.py"
SOURCE_DIRS = {
    "A0": Path("StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A0_v1"),
    "A1": Path("StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A1_v1"),
}
# Git-normalized SHA for each signed immutable successful SOC source manifest.
SOURCE_MANIFEST_GIT_SHA = {
    "A0": "0216f11e4c1a2cbc3c6d990b837b61e733082fb0d54add3da66c6942f7bc98e6",
    "A1": "6a5f4792364b995efa43c13d0634e0de5c1f4f0ec95dd4c0d8421f4b5846b3d3",
}
SOURCE_ANNUAL_CRLF_SHA = {
    "A0": "52f88c39afe089e2206e666c706fd8c41ccab0543377f1c9e3086cb5c43ba04d",
    "A1": "4f3b9687e54ae04aa3d77c8a30a1803c6d1988fb1a82227a729b781124d8402b",
}
SOURCE_15H_CRLF_SHA = {
    "A0": "ebdf4f137ce4a8edd5f5add005f32439a2009bab04e08233d472e1e62ad65491",
    "A1": "a344d97679637214ac78f88a3c1bf0c1ed0096b60a2251089f8cbb473bd87725",
}
RESULT_STEM = "StudyA_A0_A1_MatchedHardware_113699_AnnualAC_"
REPLAY_PF = .98
SERVICE_FACTOR = 1.0
Q_DAYLIGHT_RATIO = .25
COMPARE_TOL = 3e-4
REQUIRED_HOURS = 8760


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_lf_sha(path):
    original = Path(path).read_bytes()
    if b"\r" in original.replace(b"\r\n", b""):
        raise ValueError("Source manifest has unexpected lone carriage return")
    return hashlib.sha256(original.replace(b"\r\n", b"\n")).hexdigest()


def verified_crlf_source(path, expected):
    original = Path(path).read_bytes()
    if hashlib.sha256(original).hexdigest() == expected:
        return "EXACT_SIGNED"
    if b"\r" not in original and b"\n" in original:
        if hashlib.sha256(original.replace(b"\n", b"\r\n")).hexdigest() == expected:
            return "GIT_LF_EQUALS_SIGNED_CRLF"
    raise ValueError("Previously audited signed result differs: " + str(path))


def load_soc_module(repo):
    path = repo / SOC_CODE
    spec = importlib.util.spec_from_file_location("annual_113699_soc_source", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def exact_source_15_ac_check(saved, prior):
    """Require 15 distinct tested source hours, same P, AC metadata and timestamps."""
    if (len(saved) != 15 or saved.timestamp_lst.duplicated().any()
        or saved.status.ne("CONVERGED").any()
        or saved.ac_feasible.astype(str).str.lower().ne("true").any()
        or saved.assignment.ne("A1").any()):
        raise ValueError("Original 15-hour signed AC replay is not the approved source")
    prior_ts = [str(x["timestamp_lst"]) for x in prior["sampled_timestamps"]]
    if list(saved.timestamp_lst) != prior_ts:
        raise ValueError("Original 15-hour source AC timestamp selection changed")
    if len(set(prior_ts)) != 15:
        raise ValueError("Duplicate original 15-hour timestamp")
    return prior_ts


def validate_replay_15(replayed, original, tolerance=COMPARE_TOL):
    """Compare only identical recorded 15h source points; no annual shortcuts."""
    for ts, source in original.set_index("timestamp_lst").iterrows():
        matching = replayed[replayed.timestamp_lst == ts]
        if len(matching) != 1:
            raise ValueError("Missing saved 15h source AC replay timestamp: " + ts)
        check = matching.iloc[0]
        if check.status != source.status or bool(check.ac_feasible) != bool(source.ac_feasible):
            raise ValueError("Existing 15h AC feasibility not reproducible: " + ts)
        if abs(float(check.inverter_ac_kw) - float(source.inverter_ac_kw)) > 1e-5:
            raise ValueError("Changed AC inverter reference at " + ts)
        for k in ("gross_demand_kw", "min_v_pu", "max_v_pu", "max_trafo_pct",
                  "max_line_pct", "pcc_kva", "loss_kw", "q_selected_kvar"):
            if abs(float(check[k]) - float(source[k])) > tolerance:
                raise ValueError("Original 15h AC rerun differs at " + ts + "/" + k)


def annual_summary(frame, origin):
    if len(frame) != REQUIRED_HOURS:
        raise ValueError("Incomplete annual AC replay")
    converged = frame.status.eq("CONVERGED")
    valid = frame[converged]
    rejected = valid.ac_feasible.astype(str).str.lower().eq("false")
    invalid_index = frame.loc[~converged, "timestamp_lst"].astype(str).tolist()
    rejected_index = valid.loc[rejected, "timestamp_lst"].astype(str).tolist()
    result = {
        "origin": origin, "sampled_year": 2025, "hourly_records": len(frame),
        "converged_hours": int(converged.sum()),
        "nonconverged_hours": int((~converged).sum()),
        "model_main_band_feasible_hours": int((~rejected).sum()),
        "model_main_band_infeasible_hours": int(rejected.sum()),
        "model_trafo_over_100_hours": int(valid.trafo_over_100.sum()),
        "model_line_over_100_hours": int(valid.line_over_100.sum()),
        "model_voltage_under_095_hours": int(valid.voltage_below_095.sum()),
        "model_voltage_over_105_hours": int(valid.voltage_above_105.sum()),
        "optional_strict_voltage_under_097_hours": int(valid.voltage_below_097.sum()),
        "optional_strict_voltage_over_103_hours": int(valid.voltage_above_103.sum()),
        "worst_main_band_failed_timestamps_first_100": rejected_index[:100],
        "nonconverged_timestamps_first_100": invalid_index[:100],
        "minimum_model_voltage_pu": float(valid.min_v_pu.min()) if len(valid) else None,
        "maximum_model_voltage_pu": float(valid.max_v_pu.max()) if len(valid) else None,
        "maximum_model_trafo_pct": float(valid.max_trafo_pct.max()) if len(valid) else None,
        "maximum_model_line_pct": float(valid.max_line_pct.max()) if len(valid) else None,
        "annual_model_ac_losses_kwh": (
            float(valid.loss_kw.sum()) if len(valid) == REQUIRED_HOURS else None),
        "annual_model_losses_valid": bool(len(valid) == REQUIRED_HOURS),
        "annual_AC_all_hours_pass_main_research_screen":
            bool(converged.all() and not rejected.any()),
        "strict_097_103_research_screen_pass": bool(
            converged.all() and valid.voltage_below_097.sum() == 0
            and valid.voltage_above_103.sum() == 0),
        "field_verified": False,
    }
    if len(valid) + len(invalid_index) != REQUIRED_HOURS:
        raise AssertionError("AC convergence accounting lost a 2025 hour")
    return result


def preflight(repo):
    repo = Path(repo).resolve()
    if not (repo / ".git").is_dir():
        raise ValueError("Only genuine original Git repository checkout is supported")
    soc = load_soc_module(repo)
    sweep, rec, v6, cases, geometry, _solar, _plans, _orig, baseline = soc.build_plan(repo)
    if baseline.get("status") != "SIGNED_113699_SAMPLED_P_TO_ANNUAL_SOC_PREFLIGHT_NO_NEW_LP_OR_AC":
        raise ValueError("Source P-envelope/SOC provenance changed")
    original_ac_json = json.loads((repo / soc.BASE_AC_FOLDER / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    if (original_ac_json.get("status") != "BOUNDED_AC_VIOLATIONS_RECORDED_ANNUAL_PENDING"
        or original_ac_json.get("selected_unique_2025_hours") != 15):
        raise ValueError("Original 15-hour model reference changed")
    verified = {}
    for origin, folder in SOURCE_DIRS.items():
        mpath = repo / folder / "RUN_MANIFEST.json"
        if not mpath.is_file() or git_lf_sha(mpath) != SOURCE_MANIFEST_GIT_SHA[origin]:
            raise ValueError("Annual SOC origin source receipt changed: " + origin)
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        expected_status = "ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_PASS_ANNUAL_AC_PENDING"
        if (manifest.get("status") != expected_status or manifest.get("origin") != origin
            or manifest.get("new_LP_solves") != 1 or manifest.get("new_AC_solves") != 15
            or manifest.get("original_15_sample_AC_feasible") != 15
            or manifest.get("original_15_sample_AC_infeasible") != 0
            or manifest.get("annual_AC_feasible") is not False
            or manifest.get("new_annual_energy_hourly_sha256") != SOURCE_ANNUAL_CRLF_SHA[origin]
            or manifest.get("sampled_ac_sha256") != SOURCE_15H_CRLF_SHA[origin]
            or manifest.get("source_case_yearly_energy_SHA", {}).get(origin) !=
                cases[origin + "_hardware_on_A1"]["source_csv_sha256"]):
            raise ValueError("Previously completed SOC reoptimization receipt invalid: " + origin)
        annual_path = repo / folder / "annual_soc_reoptimized_2025.csv"
        sample_ac_path = repo / folder / "ac_original_15_stress_hours.csv"
        annual_mode = verified_crlf_source(annual_path, SOURCE_ANNUAL_CRLF_SHA[origin])
        sampled_mode = verified_crlf_source(sample_ac_path, SOURCE_15H_CRLF_SHA[origin])
        old = cases[origin + "_hardware_on_A1"]
        new = pd.read_csv(annual_path, parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
        result = rec.validate_dispatch(new, old["trace"], old["hardware"], manifest["yearly_new_metrics"])
        if (not new.index.equals(old["energy"].index) or len(new) != REQUIRED_HOURS
            or abs(result["grid_import_kwh"] - float(manifest["yearly_new_metrics"]["grid_import_kwh"])) > .0002):
            raise ValueError("Annual SOC source 8760h timebase or energy changed: " + origin)
        source_ac = pd.read_csv(sample_ac_path)
        exact_source_15_ac_check(source_ac, original_ac_json)
        for ts,row in source_ac.set_index("timestamp_lst").iterrows():
            if (abs(float(row["new_inverter_p_ac_kw"]) -
                   float(new.at[pd.Timestamp(ts), "inverter_ac_kw"])) > 1e-6
                or str(row["origin"]) != origin):
                raise ValueError("Original 15-hour AC source inverter did not use annual LP output")
        for name, digest in manifest["diagnostic_plot_sha256"].items():
            if sha(repo / folder / "figures_diagnostic" / name) != digest:
                raise ValueError("Original signed SOC diagnostic PNG changed: " + name)
        verified[origin] = {
            "status": manifest["status"],
            "new_annual_energy_sha256": SOURCE_ANNUAL_CRLF_SHA[origin],
            "annual_source_signature_representation": annual_mode,
            "sampled_15_AC_sha256": SOURCE_15H_CRLF_SHA[origin],
            "15_AC_signature_representation": sampled_mode,
            "annual_year": 2025, "hours": len(new), "source_AC_sample_hours": 15,
            "unchanged_equipment": old["hardware"],
            "annual_import_kwh": result["grid_import_kwh"],
            "annual_cost_usd_model": manifest["yearly_new_model_summary"]["annual_total_usd"],
            "signed_manifest_git_lf_sha256": SOURCE_MANIFEST_GIT_SHA[origin],
            "new_schedule_inverter_changed_hours":
                int(manifest["changed_inverter_hour_count"]),
        }
    receipt = {
        "status": "SIGNED_TWO_113699_SOC_RESULTS_ANNUAL_AC_SOURCE_PREFLIGHT_NO_NEW_SOLVES",
        "assignment": "A1", "transformer": "113699",
        "replay_2025_hours_per_origin": REQUIRED_HOURS,
        "original_common_stress_hours": 15,
        "model": "EPM GIS original six-house radial balanced pandapower A1",
        "transformer_kva": 3.0, "nameplate_evidenced": False,
        "service_multiplier": SERVICE_FACTOR, "pf": REPLAY_PF,
        "daylight_Q_ratio": Q_DAYLIGHT_RATIO, "night_Q_off": True,
        "source": "Fixed-hardware complete annual cyclic SOC LP, not AC-corrected LP",
        "source_original_full_energy_lf_sha": baseline["original_full_energy_manifest_git_lf_sha256"],
        "source_SOC_result_commit": "c3653a557bf0584c74e29ea895e9905a1248f523",
        "source_verified": verified,
        "new_AC_solves": 0,
        "field_AC_verified": False,
        "annual_AC_verified": False,
        "AC_screen": "0.95..1.05pu and 100% line/transformer research limit",
        "strict_097_103_screen": "SEPARATE",
        "interpretation": "Actual sampled 2025 full AC replay needed, not an energy-only proof"}
    return soc, v6, cases, geometry, receipt


def selected_output(repo, origin, requested=None):
    if requested is not None:
        p = requested if requested.is_absolute() else repo / requested
        p = p.resolve()
        if p.exists() or p.parent != repo:
            raise FileExistsError("Use only a new repository-root result directory")
        return p
    for i in range(1,1000):
        p = repo / (RESULT_STEM + origin + "_v" + str(i))
        if not p.exists():
            return p
    raise FileExistsError("All annual AC output versions are in use")


def plot_annual_ac(records, folder, origin):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder.mkdir(parents=True,exist_ok=False)
    paths = {}
    for value, title, limit, name in (
        ("min_v_pu", "Minimum household voltage (pu)", .95, "annual_min_voltage.png"),
        ("max_trafo_pct", "Maximum transformer loading (%)", 100., "annual_transformer_loading.png"),
    ):
        fig, ax = plt.subplots(figsize=(11,5.5))
        good = records[records.status.eq("CONVERGED")]
        ax.plot(pd.to_datetime(good.timestamp_lst), good[value], linewidth=.6,
                label="Full-year 2025, source-equivalent six-house A1")
        ax.axhline(limit, linewidth=.8, linestyle="--", label="Model research limit")
        ax.set_title("113699 A1, original " + origin + " hardware, yearly corrected SOC replay")
        ax.set_ylabel(title)
        ax.set_xlabel("2025 local model time")
        ax.grid(alpha=.25)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(folder / name, dpi=170)
        plt.close(fig)
        paths[name] = sha(folder / name)
    return paths


def run(repo, origin=None, out=None, preflight_only=False):
    repo = Path(repo).resolve()
    soc, v6, cases, geo, source = preflight(repo)
    if preflight_only:
        return source
    if origin not in SOURCE_DIRS:
        raise ValueError("Choose --origin A0 or --origin A1 for an independent full annual AC replay")
    import pandapower as pp
    target = selected_output(repo, origin, out)
    target.mkdir(parents=True,exist_ok=False)
    manifest_path = target / "RUN_MANIFEST.json"
    report = dict(source)
    report.update(status="INCOMPLETE_113699_ANNUAL_AC_DO_NOT_CLAIM",
                  origin=origin, output_folder=str(target),
                  new_AC_solves=0, annual_AC_verified=False)
    def save():
        manifest_path.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",
                                 encoding="utf-8")
    save()
    try:
        annual_folder = repo / SOURCE_DIRS[origin]
        prior = pd.read_csv(annual_folder/"ac_original_15_stress_hours.csv")
        new = pd.read_csv(annual_folder/"annual_soc_reoptimized_2025.csv",
                          parse_dates=["timestamp_lst"]).set_index("timestamp_lst")
        case = cases[origin+"_hardware_on_A1"]
        trace = case["trace"]
        if len(new)!=REQUIRED_HOURS or not new.index.equals(trace.index):
            raise ValueError("Source annual dispatch is incomplete/shifted")
        terrain, net, meta, _ = geo["A1"]
        records=[]
        for i, t in enumerate(new.index):
            hour=new.iloc[i]
            value=v6.solve_ac_hour(
                net,meta,terrain,t,trace.iloc[i],REPLAY_PF,
                float(hour.inverter_ac_kw),float(case["hardware"]["inverter_kva"]),
                float(hour.pv_dc_available_kw),Q_DAYLIGHT_RATIO,9,"pvbess",pp)
            records.append({"origin":origin,"assignment":"A1",
                "timestamp_lst":str(t),"source_energy_inverter_ac_kw":float(hour.inverter_ac_kw),
                "source_energy_grid_import_kw":float(hour.grid_import_kw),**value})
            if (i+1)%500==0:
                print("113699",origin,"annual AC",i+1,"/",REQUIRED_HOURS,flush=True)
        rows=pd.DataFrame(records)
        if (len(rows)!=REQUIRED_HOURS or rows.timestamp_lst.duplicated().any()
            or list(rows.timestamp_lst)!=list(new.index.astype(str))):
            raise ValueError("Annual power-flow case coverage differs from source 2025 hours")
        if np.max(np.abs(rows.gross_demand_kw.to_numpy(float) -
                         trace.sum(axis=1).to_numpy(float))) > 1e-5:
            raise ValueError("Annual pandapower gross demand differs from 6 named houses")
        if np.max(np.abs(rows.inverter_ac_kw.to_numpy(float) -
                         new.inverter_ac_kw.to_numpy(float))) > 1e-5:
            raise ValueError("Annual pandapower inverter P differs from signed SOC dispatch")
        validate_replay_15(rows,prior)
        outfile=target/"annual_ac_hourly_2025.csv"
        rows.to_csv(outfile,index=False,float_format="%.10f")
        all_summary=annual_summary(rows,origin)
        figures=plot_annual_ac(rows,target/"figures_diagnostic",origin)
        report.update(
            status=("ANNUAL_113699_MODEL_AC_NONCONVERGENCE_RECORDED"
                    if all_summary["nonconverged_hours"] else
                    "ANNUAL_113699_MODEL_AC_MAIN_BAND_VIOLATIONS"
                    if all_summary["model_main_band_infeasible_hours"] else
                    "ANNUAL_113699_MODEL_AC_MAIN_BAND_PASS_STRICT_SEPARATE"),
            new_AC_solves=REQUIRED_HOURS,
            annual_AC_verified=bool(
                all_summary["annual_AC_all_hours_pass_main_research_screen"]),
            source_validation_replayed_15h=True,
            annual_ac_hourly_sha256=sha(outfile),
            diagnostics_sha256=figures,
            annual_summary=all_summary,
            historical_AC_baseline_full_year_available=False,
            annual_cost_with_AC_losses_recomputed=False,
            real_EPM_utility_approval=False)
        save()
        return {"status":report["status"],"origin":origin,
                "output":str(target),"2025_AC_hours":REQUIRED_HOURS,
                "AC_feasible_hours":all_summary["model_main_band_feasible_hours"],
                "AC_infeasible_hours":all_summary["model_main_band_infeasible_hours"],
                "nonconverged_hours":all_summary["nonconverged_hours"],
                "annual_AC_verified":report["annual_AC_verified"],
                "real_EPM_utility_approval":False}
    except Exception as ex:
        report["status"]="INCOMPLETE_113699_ANNUAL_AC_DO_NOT_CLAIM"
        report["failure"]={"type":type(ex).__name__,"message":str(ex),
                           "traceback":traceback.format_exc()}
        save()
        raise


def cli(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--origin",choices=tuple(SOURCE_DIRS))
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    print(json.dumps(run(args.repo_root,args.origin,args.out,args.preflight_only),
                     indent=2,allow_nan=False))


if __name__=="__main__":
    cli()
