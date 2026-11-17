#!/usr/bin/env python3
"""Read-only, reproducible Study A demand/GIS preflight, executed by user.

No PyPSA, pandapower AC, optimization, or edits to the GitLab checkout.
The paired nearest-transformer scenario is only a geographic hypothesis.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"
GISREL = Path("case1/studies/epm_gis_pandapower_v1")
HOUSES = GISREL / "data/houses_candidate_associations.csv"
TRAFOS = GISREL / "data/transformers_evidence.csv"
GEOJSON = GISREL / "data/epm_network_relevant_sanitized.geojson"
LEGACY_20 = Path("Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv")
PREBASE = GISREL / "outputs/preflight_base/house_assignments.csv"
PRENEAR = GISREL / "outputs/preflight_nearest/house_assignments.csv"
EXPECTED_SHA = {
    str(HOUSES): "ad830d00739180d41755605b79d3091abbd9d4e3804779d526f8b33012cf50b9",
    str(TRAFOS): "ca65a576a04db1f2e352233a9420ef88311d1cfa1429abf4b7c2d95812634891",
    str(GEOJSON): "adfa33a8a01b0b33ee449c69924515fed05ad49665868e8c1ae8ba5d047c1bab",
    str(LEGACY_20): "276d3d782e3610196463704899c1026abc568a35cdbc32117a34367cd0c4b265",
    "Demand_curve.xlsx": "2710abade11c0fdec22d785d442a11f0ca6676867251c44aaaeac388dc09c595",
    "SimulacionTampico1k(1).xml": "a1581b77ba06289436d5a0742d27947ed2007698eaf5d01b5dd098cbaf9425ef",
}
CORE7 = ("H03", "H06", "H26", "H27", "H28", "H34", "H35")
CORE9_MORE = ("H01", "H02")
CORE12 = ("H11", "H13", "H16", "H17", "H18", "H19", "H20", "H21", "H22", "H23", "H24", "H25")
CANDIDATE_MOVES = {"H03": "113699", "H06": "113699", "H13": "85398"}
NORTH_EXCLUDED = "NORTH_25KVA"
MAIN_TRAFO_IDS = ("94022", "106039", "113699", "85398", "92395", "98380")
PF_VALUES = (.95, .98, 1.0)
SOURCE_COLUMNS = {"excel": "excel", "homer": "homer"}


def digest(path: Path) -> str:
    hh = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(2**20), b""):
            hh.update(buf)
    return hh.hexdigest()


def load_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required local checkout source: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows: list[dict], columns: list[str] | None = None):
    if not rows:
        raise ValueError(f"Refusing to save empty result: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns or list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def check_hash(path: Path, expected: str, *, mandatory=True) -> dict:
    if not path.is_file():
        if mandatory:
            raise FileNotFoundError(f"Required source not in your checkout: {path}")
        return {"status": "MISSING", "expected": expected, "path": str(path)}
    actual = digest(path)
    if actual != expected:
        raise ValueError(
            f"Source hash mismatch. Do not silently substitute changed inputs:\n{path}\n"
            f"expected: {expected}\nactual:   {actual}"
        )
    return {"status": "HASH_MATCH", "sha256": actual, "path": str(path)}


def workbook_raw_profiles(path: Path = DATA / "demand_excel_seasonal_24h.csv") -> dict[str, np.ndarray]:
    rows = load_csv(path)
    if len(rows) != 24 or [int(x["hour"]) for x in rows] != list(range(24)):
        raise ValueError("Workbook extraction must have 24 ordered hourly rows (0..23)")
    cols = ("sep_nov", "dec_feb", "mar_may", "jun_aug")
    curves = {k: np.array([float(r[k]) for r in rows]) for k in cols}
    if any(np.any(c < 0) or not np.all(np.isfinite(c)) for c in curves.values()):
        raise ValueError("Bad seasonal workbook profile")
    return curves


def xml_load_model(path: Path = DATA / "SimulacionTampico1k(1).xml"):
    root = ET.parse(path).getroot().find("system_description")
    if root is None:
        raise ValueError("Missing HOMER system_description")
    primary = root.find("primary_load")
    daily = float(primary.findtext("data/monthly/daily_noise")) / 100.0
    hourly = float(primary.findtext("data/monthly/hourly_noise")) / 100.0
    daily_4hh = float(primary.findtext("scaled_annual_average"))
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    curves = {}
    for n, month in enumerate(months, 1):
        wk = np.fromstring(primary.findtext(f"data/monthly/daily_profiles/{month}/weekday/float_array"), sep=" ")
        we = np.fromstring(primary.findtext(f"data/monthly/daily_profiles/{month}/weekend/float_array"), sep=" ")
        if wk.size != 24 or we.size != 24:
            raise ValueError(f"Wrong monthly HOMER profile length: {month}")
        curves[n] = (wk / 4.0, we / 4.0)
    if not np.isclose(daily, .20) or not np.isclose(hourly, .25) or not np.isclose(daily_4hh, 20.8):
        raise ValueError("Original HOMER stochastic and annual-energy assumptions changed")
    return curves, daily, hourly, daily_4hh*365/4


def baseline_profile(index: pd.DatetimeIndex, mode: str, seasonal: dict, xml_curves: dict, annual_target: float) -> pd.Series:
    rows = np.empty(len(index), dtype=float)
    month_to_season = {1:"dec_feb",2:"dec_feb",3:"mar_may",4:"mar_may",5:"mar_may",6:"jun_aug",7:"jun_aug",8:"jun_aug",9:"sep_nov",10:"sep_nov",11:"sep_nov",12:"dec_feb"}
    for i, ts in enumerate(index):
        if mode == "excel":
            rows[i] = seasonal[month_to_season[ts.month]][ts.hour]
        elif mode == "homer":
            rows[i] = xml_curves[ts.month][ts.weekday() >= 5][ts.hour]
        else:
            raise ValueError(mode)
    rows *= annual_target / rows.sum()
    return pd.Series(rows, index=index, dtype=float)


def make_profiles(mode: str, *, n=35, seed=20250913):
    """Replicates notebook v18 random draw sequence, using selected unrounded/rounded source curve."""
    if n != 35: raise ValueError("Study A paired 35-property comparison requires n=35")
    index = pd.date_range("2025-01-01 00:00", "2025-12-31 23:00", freq="h")
    seasonal = workbook_raw_profiles()
    xml_curves, sd_day, sd_hour, target = xml_load_model()
    expected = baseline_profile(index, mode, seasonal, xml_curves, target)
    day_codes = index.dayofyear.to_numpy() - 1
    rngs = [np.random.default_rng(x) for x in np.random.SeedSequence(seed).spawn(n)]
    data = {"timestamp": index}
    for n1, rng in enumerate(rngs, 1):
        daily_delta = rng.normal(loc=0.0, scale=sd_day, size=365)
        timestep_delta = rng.normal(loc=0.0, scale=sd_hour, size=len(index))
        varied = expected.to_numpy(dtype=float) * np.maximum(1.0 + daily_delta[day_codes] + timestep_delta, 0.0)
        varied *= target / varied.sum()
        data[f"house_{n1}_kw"] = varied
    out = pd.DataFrame(data)
    assert len(out)==8760
    assert np.allclose(out.loc[:, "house_1_kw":"house_35_kw"].sum().to_numpy(), target, rtol=0, atol=1e-9)
    return out, target


def compare_sources(seasonal: dict, xml_curves: dict):
    names = {1:"dec_feb",2:"dec_feb",3:"mar_may",4:"mar_may",5:"mar_may",6:"jun_aug",7:"jun_aug",8:"jun_aug",9:"sep_nov",10:"sep_nov",11:"sep_nov",12:"dec_feb"}
    rows=[]; summary=[]
    for mon in range(1,13):
        excel=seasonal[names[mon]]
        xml=xml_curves[mon][0]
        for h,(a,b) in enumerate(zip(excel,xml)):
            rows.append({"month":mon,"hour_0_23":h,"excel_1hh_kw":float(a),"homer_1hh_kw":float(b),"difference_kw":float(a-b)})
        summary.append({"month":mon,"excel_period":names[mon],"excel_kwh_per_day":float(excel.sum()),
                        "homer_kwh_per_day":float(xml.sum()),"hourly_max_abs_diff_kw":float(np.abs(excel-xml).max()),
                        "hourly_mean_abs_diff_kw":float(np.abs(excel-xml).mean())})
    return rows, summary


def fixed_house_profile_mapping(houses: list[dict]):
    ordered=list(CORE7)+list(CORE9_MORE)+list(CORE12)
    if len(ordered)!=21 or len(set(ordered))!=21:
        raise AssertionError("Historic cohort source mapping changed")
    by_id={h["house_id"]:h for h in houses}
    if len(by_id)!=35 or len(houses)!=35 or set(ordered)-set(by_id):
        raise ValueError("Expected exactly 35 unique existing mapped GIS candidate homes")
    ordered.extend(sorted(set(by_id)-set(ordered)))
    if len(ordered)!=35:raise AssertionError("Bad independent profile allocation")
    mapping={hid:n for n,hid in enumerate(ordered,1)}
    return mapping


def haversine_m(lat1,lon1,lat2,lon2):
    r=6371000.0
    phi1,phi2=np.deg2rad([lat1,lat2]);dp=phi2-phi1;dl=np.deg2rad(lon2-lon1)
    a=np.sin(dp/2)**2+np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
    return float(2*r*np.arcsin(np.sqrt(a)))


def paired_assignments(houses: list[dict], trafos: list[dict]):
    by_trafo={x["transformer_number"]:x for x in trafos if x["transformer_number"] in MAIN_TRAFO_IDS}
    if len(by_trafo)!=6 or NORTH_EXCLUDED in by_trafo: raise ValueError("Expected six approved EPM candidate transformers only")
    rows=[]; expected_moves={}
    for h in sorted(houses,key=lambda x:x["house_id"]):
        hid=h["house_id"]; original=h["transformer_number"]
        if original not in by_trafo:raise ValueError(f"Unexpected excluded or unsupported original transformer: {original}")
        ranked=sorted(((haversine_m(float(h["latitude"]),float(h["longitude"]),float(t["latitude"]),float(t["longitude"])),tn)
                    for tn,t in by_trafo.items()))
        nearest=ranked[0][1]
        if nearest != original:expected_moves[hid]=nearest
        for case,target in (("A0_original",original),("A1_nearest_point",nearest)):
            rows.append({"scenario":case,"house":hid,"transformer":target,"original_transformer":original,
                         "changed_from_original":int(original!=target),"source_assignment_status":h["assignment_status"],
                         "distance_to_selected_transformer_m":round(next(distance for distance,tn in ranked if tn==target),3),
                         "house_latitude":h["latitude"],"house_longitude":h["longitude"],
                         "evidence_label":"PROVISIONAL_ORIGINAL" if case=="A0_original" else "UNVERIFIED_GEOGRAPHIC_HYPOTHESIS"})
    if expected_moves != CANDIDATE_MOVES:
        raise ValueError(f"Nearest point reassignment differs from approved hypothesis: {expected_moves}")
    assert len(rows)==70
    for case in ("A0_original","A1_nearest_point"):
        assert len({r["house"] for r in rows if r["scenario"]==case})==35
    return rows


def crosscheck_archived_20(repo: Path, homer_35: pd.DataFrame):
    path=repo/LEGACY_20
    status={"path":str(path),"description":"historical original 8,760 x 20 stochastic household streams"}
    if not path.is_file():
        status["status"]="MISSING_IN_LOCAL_CHECKOUT"
        return status
    status["sha256"]=digest(path)
    if status["sha256"] != EXPECTED_SHA[str(LEGACY_20)]:
        status["status"]="SOURCE_HASH_MISMATCH"
        return status
    wanted=[f"house_{i}_kw" for i in range(1,21)]
    historical=pd.read_csv(path,usecols=["timestamp"]+wanted)
    if len(historical)!=8760:
        status["status"]="BAD_HISTORICAL_ROW_COUNT";return status
    equal_ts=(historical["timestamp"].astype(str).values==homer_35["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").values).all()
    arr1=historical[wanted].to_numpy(dtype=float)
    arr2=homer_35[wanted].to_numpy(dtype=float)
    diff=np.abs(arr1-arr2)
    status.update({"timestamp_match":bool(equal_ts),"max_abs_kw":float(np.max(diff)),"compared_values":int(diff.size),
                   "status":"MATCH_FULL_8760x20" if equal_ts and np.max(diff) < 1e-12 else "MISMATCH"})
    return status


def gis_preflight(repo: Path, assignment_rows: list[dict]):
    """Read-only test of saved EPM geometry and candidates; no pandapower solving."""
    sys.path.insert(0,str(repo/GISREL))
    try:
        import epm_topology as topo
        from shapely.geometry import Point
    finally:
        sys.path.pop(0)
    houses,transformers,lv=topo.read_data()
    available={str(k) for k in transformers}
    if not set(MAIN_TRAFO_IDS).issubset(available):raise ValueError("GIS transformer inventory incomplete")
    rows=[]; cases=[]
    for a in assignment_rows:
        hid=a["house"]; tr_id=a["transformer"]
        segs=[s for s in lv if str(s["node"])==str(transformers[tr_id]["epm_node"])]
        rec=dict(a)
        if not segs:
            rec.update({"nearest_gis_lv_segment":"", "straight_to_gis_lv_m":"", "connection_status":"NO_EXPORTED_LV_SEGMENT"})
        else:
            pt=Point(houses[hid]["x"],houses[hid]["y"])
            seg=min(segs,key=lambda s:(pt.distance(s["geom"]),s["fid"]))
            rec.update({"nearest_gis_lv_segment":seg["fid"],"straight_to_gis_lv_m":round(float(pt.distance(seg["geom"])),3),
                        "connection_status":"GEOGRAPHIC_ASSUMED_ATTACH_NOT_FIELD_VERIFIED"})
        rows.append(rec)
    for scenario in ("A0_original","A1_nearest_point"):
        for tr in MAIN_TRAFO_IDS:
            selection=[x for x in rows if x["scenario"]==scenario and x["transformer"]==tr]
            record={"scenario":scenario,"transformer":tr,"house_count":len(selection),"eligible_n_ge_4":len(selection)>=4,
                    "missing_lv_houses":sum(x["connection_status"]=="NO_EXPORTED_LV_SEGMENT" for x in selection),
                    "ac_result_status":"NOT_RUN_NO_POWER_FLOW"}
            if len(selection)<4: record["gis_status"]="SUPPORT_ONLY_N_LT_4";cases.append(record);continue
            if record["missing_lv_houses"]:
                record["gis_status"]="BLOCKED_MISSING_MAPPED_LV";cases.append(record);continue
            # Preserve source GIS lengths; only service taps are inferred.
            attach=[{"house":x["house"],"original":x["original_transformer"],"transformer":tr,
                     "segment_id":x["nearest_gis_lv_segment"],"source_status":x["source_assignment_status"],
                     "changed":bool(x["changed_from_original"])} for x in selection]
            try:
                territory=topo.build_territory(tr,houses,transformers,lv,attach,service_factor=1.0)
                if territory is None:
                    record["gis_status"]="BLOCKED_NO_TERRITORY"
                else:
                    metrics=territory.metrics()
                    record.update({"gis_status":"GRAPH_PREFLIGHT_PASSED_NOT_AC", "gis_line_count":metrics["gis_lines"],
                                   "gis_length_m":metrics["mapped_lv_m"],"assumed_service_length_m":metrics["assumed_service_m"],
                                   "connected":metrics["graph_connected"],"tree":metrics["tree"]})
                    if not(metrics["graph_connected"] and metrics["tree"]):record["gis_status"]="GRAPH_REVIEW_REQUIRED"
            except Exception as exc:
                record["gis_status"]="GRAPH_REVIEW_REQUIRED"
                record["error"]=repr(exc)
            cases.append(record)
    return rows,cases


def build_gross_screen(profiles: pd.DataFrame, assignments: list[dict], profile_map: dict, kva_map: dict, mode: str):
    p_by_hid={hid:profiles[f"house_{idx}_kw"].to_numpy(dtype=float) for hid,idx in profile_map.items()}
    rows=[]; series={"timestamp":profiles["timestamp"]}
    for scenario in ("A0_original","A1_nearest_point"):
        for trafo in MAIN_TRAFO_IDS:
            ids=sorted(x["house"] for x in assignments if x["scenario"]==scenario and x["transformer"]==trafo)
            p=np.sum([p_by_hid[hid] for hid in ids],axis=0) if ids else np.zeros(8760,dtype=float)
            assert len(p)==8760 and np.all(p>=0)
            for pf in PF_VALUES:
                s=p/pf
                rating=kva_map[trafo]
                over=s>rating
                rows.append({"demand_source":mode,"scenario":scenario,"transformer":trafo,
                             "house_count":len(ids),"eligible_n_ge_4":int(len(ids)>=4),
                             "rating_kva":rating,"rating_evidence":"ASSUMED_5KVA_NOT_CERTIFIED" if trafo=="106039" else "ARCHIVED_RESEARCH_ASSET_EVIDENCE_NOT_FIELD_CERTIFIED",
                             "load_pf":pf,"gross_annual_kwh":round(float(p.sum()),10),
                             "gross_peak_kw":round(float(p.max()),10),"gross_peak_kva":round(float(s.max()),10),
                             "gross_exceedance_hours":int(over.sum()),"gross_max_over_kva":round(float(max(0.0, np.max(s-rating))),10),
                             "result_type":"LOAD_ONLY_PF_TRANSFORMER_SCALAR_NOT_AC_NOT_PV_BESS"})
            series[f"{scenario}_{trafo}_gross_kw"]=p
    return rows,pd.DataFrame(series)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,required=True,help="Path to up-to-date local GitLab checkout")
    ap.add_argument("--outdir",type=Path,required=True,help="NEW output directory below local project root")
    ap.add_argument("--skip-gis",action="store_true",help="Demand/proximity output only; list GIS as NOT_RUN")
    args=ap.parse_args()
    repo=args.repo_root.resolve();out=args.outdir.resolve()
    try:out.relative_to(repo)
    except ValueError:ap.error("Output must be inside the local project root")
    if out.exists():ap.error("Output path already exists; choose a fresh project-contained folder")
    if not (repo/".git").is_dir():ap.error("--repo-root must be an actual local Git checkout")
    source_state={}
    for relative in (HOUSES,TRAFOS,GEOJSON):
        file=repo/relative
        source_state[str(relative)]=check_hash(file,EXPECTED_SHA[str(relative)])
    for file in ("Demand_curve.xlsx","SimulacionTampico1k(1).xml"):
        source_state[file]=check_hash(DATA/file,EXPECTED_SHA[file])
    houses=load_csv(repo/HOUSES); trafos=load_csv(repo/TRAFOS)
    seasonal=workbook_raw_profiles();xml_curves,dd,hd,target=xml_load_model()
    comparison, comp_summary = compare_sources(seasonal,xml_curves)
    profile_map=fixed_house_profile_mapping(houses)
    assign=paired_assignments(houses,trafos)
    ratings={x["transformer_number"]:float(x["kva"]) for x in trafos if x["transformer_number"] in MAIN_TRAFO_IDS}
    if ratings["106039"]!=5.0:raise ValueError("Approved hypothetical transformer 106039 study rating changed")
    out.mkdir(parents=True)
    save_csv(out/"source_24h_comparison.csv",comparison)
    save_csv(out/"source_12_month_summary.csv",comp_summary)
    save_csv(out/"paired_house_transformer_assignments.csv",assign)
    save_csv(out/"fixed_house_to_profile_map.csv",[
        {"house":h,"profile_index":j,"profile_column":f"house_{j}_kw",
         "mapping":"same physical house gets same profile across A0 and A1; all distinct; not metered"}
        for h,j in sorted(profile_map.items())])
    if args.skip_gis:
        gis_rows=[]
        gis_cases=[{"scenario":sc,"transformer":tr,"gis_status":"NOT_RUN_REQUESTED_SKIP"}
                   for sc in ("A0_original","A1_nearest_point") for tr in MAIN_TRAFO_IDS]
    else:
        try:
            gis_rows,gis_cases=gis_preflight(repo,assign)
        except ImportError as exc:
            gis_rows=[]
            gis_cases=[{"scenario":sc,"transformer":tr,"gis_status":"NOT_RUN_MISSING_GIS_DEPENDENCIES", "error":str(exc)}
                   for sc in ("A0_original","A1_nearest_point") for tr in MAIN_TRAFO_IDS]
    if gis_rows:save_csv(out/"gis_source_connection_audit.csv",gis_rows)
    save_csv(out/"gis_graph_preflight_cases.csv",gis_cases)
    gis_lookup={(x["scenario"],x["transformer"]):x["gis_status"] for x in gis_cases}
    annual_queue=[]
    for scenario in ("A0_original","A1_nearest_point"):
        for tr in MAIN_TRAFO_IDS:
            names=sorted(x["house"] for x in assign if x["scenario"]==scenario and x["transformer"]==tr)
            if len(names)<4:continue
            status=gis_lookup[(scenario,tr)]
            annual_queue.append({
                "study":"A_existing_EPM_GIS", "scenario":scenario,"transformer":tr,
                "house_count":len(names),"house_ids":";".join(names),
                "model_house_profiles":"household_profiles_2025_excel_35.csv; household_profiles_2025_homer_35.csv",
                "GIS_graph_status":status,"original_historical_7_9_12_runs":"INDEPENDENT_REFERENCE_NOT_NEW_PAIR",
                "hardware_selection":"TARGETED_NEW_4_HOME_HARDWARE" if len(names)==4 else "REVIEW_ARCHIVED_5_15_EQUIPMENT_ONLY_AS_INITIAL_CANDIDATES",
                "manufacturer_SOC_8760_dispatch":"NOT_RUN_AWAITING_SOURCE_TOPOLOGY_AND_HARDWARE_REVIEW",
                "annual_AC_pandapower":"NOT_RUN_AWAITING_USER_DISPATCH_AND_VALID_GIS",
                "battery_optimization":"CROSS_STUDY_APPROVED_NOT_RUN_FOR_THIS_SCENARIO",
                "criteria":"main 0.95-1.05pu; PF0.95/0.98/1.00; service x1.0/1.3/1.6; 20pct min SOC; zero export; no grid charge; night Q off",
            })
    save_csv(out/"annual_pvbess_ac_run_matrix.csv",annual_queue)
    all_gross=[]; historical_status={}
    for mode in ("homer","excel"):
        ts, year_target=make_profiles(mode)
        ts.to_csv(out/f"household_profiles_2025_{mode}_35.csv",index=False,float_format="%.17g")
        rows,series=build_gross_screen(ts,assign,profile_map,ratings,mode)
        all_gross.extend(rows)
        series.to_csv(out/f"hourly_transformer_gross_kw_{mode}.csv",index=False,float_format="%.17g")
        if mode=="homer":
            historical_status=crosscheck_archived_20(repo,ts)
    save_csv(out/"gross_load_pf_sensitivity.csv",all_gross)
    if historical_status.get("status") == "MISMATCH":
        raise ValueError("Original twenty profile values DO NOT MATCH. Inspect source and method; do not interpret generated screens")
    counts=Counter((x["scenario"],x["transformer"]) for x in assign)
    incomplete=[x for x in gis_cases if x.get("gis_status") != "GRAPH_PREFLIGHT_PASSED_NOT_AC" and x.get("eligible_n_ge_4")]
    summary={"status":"COMPLETED_LOAD_ONLY_LOCAL_PREFLIGHT_NOT_AC","utc_run":datetime.now(timezone.utc).isoformat(),
             "user_execute_required":True,"repo_root":str(repo),"output":str(out),"source_sha256":source_state,
             "excel_relative_source":"Demand_curve.xlsx!Tabelle1 F5:I28 (full-precision seasonal 24-hour profiles)",
             "homer_source":"SimulacionTampico1k(1).xml primary_load; original 20 profiles historical match-only",
             "annual_energy_target_per_synthetic_house_kwh":target,
             "stochastic_seed":20250913,"daily_sigma":dd,"hour_sigma":hd,
             "scenario_house_counts":{sc:{tr:counts.get((sc,tr),0) for tr in MAIN_TRAFO_IDS} for sc in ("A0_original","A1_nearest_point")},
             "only_geographic_changes":CANDIDATE_MOVES,"historical_original_20_profile_check":historical_status,
             "gis_cases":gis_cases,"number_gis_cases_needing_review":len(incomplete),
             "pv_bess_optimization":"NOT_RUN", "pandapower_annual_ac":"NOT_RUN",
             "explicit_exclusion":"NORTH_25KVA", "physical_connections_verified":False,
             "notes":["Gross transformer kVA=P/PF only, not AC, excludes PV/BESS/losses/other utility customers",
                      "CSV Excel extraction and original workbook SHA are fixed so no installed Excel reader is needed at runtime",
                      "Excel and HOMER modes are separate demand-source sensitivities, not interchangeable historical trajectories",
                      "Source association of H25 may be a facility; H14/H15 are unverifiable; 92395 has no exported LV sections",
                      "Inverter/conductor limits, grid export, no grid charging and manufacturer 20% SOC belong to future PV+BESS annual dispatch"]}
    (out/"preflight_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf8")
    print("Study A LOCAL read-only source/GIS preflight written under",out)
    print("Historical 20-profile comparison:",historical_status.get("status"))
    print("GIS status:",[(x["scenario"],x["transformer"],x["gis_status"]) for x in gis_cases])
    print("PV+BESS dispatch NOT RUN. pandapower annual AC NOT RUN. No GitLab changes.")

if __name__=="__main__":
    main()
