#!/usr/bin/env python3
"""Reproduce EXISTING image-trace lengths and historic cluster counts.

Source-only audit, Python standard library, no pandapower, no altered inputs.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / "Energy Community - San Rafael"
PACKAGE = ORIGINAL / "SanRafael_Reproducible_Model_Package_v2"

def csv_rows(rel):
    with (PACKAGE / rel).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))

def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def traced_length(rel, scale_pixels, scale_metres):
    pts = csv_rows(rel)
    xy = [(float(p["x_px"]),float(p["y_px"])) for p in pts]
    pixels = sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a,b in zip(xy,xy[1:]))
    return dict(points=len(xy),image_polyline_pixels=pixels,
                derived_length_m=pixels*scale_metres/scale_pixels)

def audit():
    a = csv_rows("04_grid_data/san_rafael_epm_asset_94022.csv")
    assert len(a)==1
    asset=a[0]
    assert (asset["asset"],asset["node"],asset["circuit"],asset["rating_kva"]) == (
        "Transformer 94022","931076","221-12","5")
    houses=csv_rows("05_spatial_grouping/san_rafael_house_image_coordinates.csv")
    house_ids=sorted(int(x["house_id"]) for x in houses)
    assert house_ids == list(range(1,36))
    latlon_count=sum(bool(x["lat"].strip()) and bool(x["lon"].strip()) for x in houses)
    assert latlon_count == 0
    scales={x["calibration_id"]: x for x in csv_rows("05_spatial_grouping/scale_calibration.csv")}
    def route(kind,rel):
        s=scales[kind]
        return traced_length(rel,float(s["scale_px"]),float(s["scale_m"]))
    lv=route("secondary_30m_map","05_spatial_grouping/secondary_trace_points_94022.csv")
    mv=route("primary_100m_map","05_spatial_grouping/primary_trace_points_94022.csv")
    previous=csv_rows("07_generated_spatial/measured_line_lengths.csv")
    assert abs(lv["derived_length_m"]-float(next(x for x in previous if "Secondary" in x["section"])["length_m"])) < 1e-6
    assert abs(mv["derived_length_m"]-float(next(x for x in previous if "Primary" in x["section"])["length_m"])) < 1e-6
    geometry=csv_rows("04_grid_data/san_rafael_epm_local_geometry_v2.csv")
    lv_register=float(next(x for x in geometry if x["section_id"]=="LV_LOCAL_01")["length_m"])
    mv_register=float(next(x for x in geometry if x["section_id"]=="MV_LOCAL_01")["length_m"])
    groups={}
    for count in [4,5,6,7,8]:
        rel="05_spatial_grouping/san_rafael_case_"+str(count)+"_houses_max_"
        members=csv_rows(rel+"house_groups.csv")
        candidates=csv_rows(rel+"transformers.csv")
        assert sorted(int(x["house_id"]) for x in members)==list(range(1,36))
        group_ids=set(x["group_id"] for x in members)
        sizes=sorted((sum(x["group_id"]==g for x in members) for g in group_ids), reverse=True)
        assert len(group_ids)==len(candidates) and max(sizes)<=count
        assert all("candidate" in x["status"] for x in candidates)
        groups[str(count)]={"candidate_transformers":len(candidates),"group_sizes":sizes,
                            "house_count":sum(sizes),
                            "classification":"hypothetical proximity grouping not EPM allocation"}
    def notebook(name):
        path=ORIGINAL/name
        doc=json.loads(path.read_text(encoding="utf-8"))
        return {"file":str(path.relative_to(ROOT)),
                "cells":len(doc["cells"]),
                "heading":"".join(doc["cells"][0]["source"]).splitlines()[0],
                "sha256":hash_file(path)}
    older_pypsa=notebook("SanRafael_PyPSA_Scenarios.ipynb")
    older_pp=notebook("SanRafael_pandapower_Grid_Check.ipynb")
    # Both latest uploaded notebook revisions already exist under case1/legacy/.
    newer_paths = {
        "pypsa_v18": ROOT / "case1/legacy/SanRafael_PyPSA_Scenarios_v18_uncertainty.ipynb",
        "pandapower_v5": ROOT / "case1/legacy/SanRafael_pandapower_Grid_Check_v5_uncertainty.ipynb",
    }
    expected = {
        "pypsa_v18": ("0ed79c7cd19de757fb3daf7177752c6a5df82c95079a19519a048c8c63ae6ebc",38),
        "pandapower_v5": ("35a0dfbcbb2bd2d251c03f34a176bf9c3f5654a4cf9cab1970646dea10985652",44),
    }
    newer_tracked = {}
    for label,path in newer_paths.items():
        digest=hash_file(path)
        contents=json.loads(path.read_text(encoding="utf-8"))
        exp_digest,exp_count=expected[label]
        assert digest==exp_digest and len(contents["cells"])==exp_count
        newer_tracked[label]={"path":str(path.relative_to(ROOT)),
                              "sha256":digest,"cells":len(contents["cells"]),
                              "identical_to_uploaded_original":True}
    assert older_pypsa["cells"]==34 and "v17" in older_pypsa["heading"]
    assert older_pp["cells"]==37
    pp_cells=json.loads((ORIGINAL/"SanRafael_pandapower_Grid_Check.ipynb").read_text(encoding="utf-8"))["cells"]
    pp_text="\n".join("".join(c["source"]) for c in pp_cells)
    assert "LV_ROUTE_M = 324.5" in pp_text
    result={
        "audit_type":"historical source consistency; NOT field-confirmed network",
        "asset_94022":{"identifier":asset["asset"],"node":asset["node"],
             "circuit":asset["circuit"],"kva":float(asset["rating_kva"]),
             "lat":float(asset["latitude"]),"lon":float(asset["longitude"]),
             "source":"archived EPM extract"},
        "houses":{"image_ids":len(houses),"georeferenced_lat_lon":latlon_count,
                  "actual_transformer_allocation_verified":False},
        "line_traces_m":{"lv":lv,"mv":mv,"lv_geometry_register_m":lv_register,
                         "mv_geometry_register_m":mv_register,
                         "lv_difference_register_vs_trace_m":lv_register-lv["derived_length_m"]},
        "groupings":groups,
        "gitlab_original_notebooks":{"pypsa":older_pypsa,"pandapower":older_pp},
        "newer_already_tracked_notebooks":newer_tracked,
        "source_sha256":{
           str(x.relative_to(ROOT)):hash_file(x) for x in (
             PACKAGE/"04_grid_data/san_rafael_epm_asset_94022.csv",
             PACKAGE/"05_spatial_grouping/san_rafael_house_image_coordinates.csv",
             PACKAGE/"05_spatial_grouping/secondary_trace_points_94022.csv",
             PACKAGE/"05_spatial_grouping/scale_calibration.csv"
           )},
        "limitations":["House coordinates are only pixels",
                       "Candidate transformer sites are not existing EPM assets",
                       "328.8m versus 324.452m LV discrepancy remains",
                       "No new transformer or feeder route has been approved or modelled"]
    }
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=None)
    args=ap.parse_args()
    r=audit()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("AUDIT_SUMMARY_JSON="+json.dumps({"asset":r["asset_94022"],
       "houses":r["houses"],"lines":r["line_traces_m"],
       "groupings":r["groupings"],"original_notebooks":r["gitlab_original_notebooks"]}))
