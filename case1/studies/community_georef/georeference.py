#!/usr/bin/env python3
"""Rebuild research-only property estimates from original archived image pixels.

Zero assumed customer transformer assignments. Pure Python 3 standard library.
"""
import argparse
import csv
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SRC=REPO/"Energy Community - San Rafael"/"SanRafael_Reproducible_Model_Package_v2"/"05_spatial_grouping"
R=6378137.0
RAD=math.pi/180.0
LAT0,LON0=6.245,-75.007
FACTOR=math.cos(LAT0*RAD)
FITTED=(1,4,5,6,18)

def read_csv(path):
    with open(path,encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))

def to_xy(lon,lat):
    return (R*(lon-LON0)*RAD*FACTOR, R*(lat-LAT0)*RAD)

def solve(a,b):
    z=[list(a[i])+[b[i]] for i in range(3)]
    for k in range(3):
        pivot=max(range(k,3),key=lambda i:abs(z[i][k]))
        z[k],z[pivot]=z[pivot],z[k]
        if abs(z[k][k])<1e-7:
            raise ValueError("Landmark geometry is degenerate")
        div=z[k][k]
        for j in range(k,4):z[k][j]/=div
        for i in range(3):
            if i==k:continue
            s=z[i][k]
            for j in range(k,4):z[i][j]-=s*z[k][j]
    return [r[3] for r in z]

def transform(house,fit):
    q=[float(house["x_px"]),float(house["y_px"]),1]
    east=sum(fit[0][k]*q[k] for k in range(3))
    north=sum(fit[1][k]*q[k] for k in range(3))
    return (LON0+east/(R*RAD*FACTOR), LAT0+north/(R*RAD))

def fit_affine(houses,controls,ids):
    a=[[0]*3 for _ in range(3)]
    b,c=[0]*3,[0]*3
    for hid in ids:
        h=houses[hid];p=controls[hid]
        q=[float(h["x_px"]),float(h["y_px"]),1]
        e,n=to_xy(float(p["longitude"]),float(p["latitude"]))
        for i in range(3):
            b[i]+=q[i]*e;c[i]+=q[i]*n
            for j in range(3):a[i][j]+=q[i]*q[j]
    return (solve(a,b),solve(a,c))

def discrepancy(point,ref):
    a,b=to_xy(*point),to_xy(*ref)
    return math.hypot(a[0]-b[0],a[1]-b[1])

def generate():
    houses={int(h["house_id"]):h for h in read_csv(SRC/"san_rafael_house_image_coordinates.csv")}
    groups={int(h["house_id"]):h["group_id"] for h in read_csv(SRC/"san_rafael_case_8_houses_max_house_groups.csv")}
    controls={int(h["house_id"]):h for h in read_csv(HERE/"landmark_controls.csv")}
    if sorted(houses)!=list(range(1,36)) or set(groups)!=set(houses):
        raise ValueError("Archived 35-property inventory differs from expected")
    if sorted(controls)!=[1,4,5,6,18,25] or not controls[25]["role"].startswith("excluded"):
        raise ValueError("Controls unexpectedly changed")
    fit=fit_affine(houses,controls,FITTED)
    geo={"type":"FeatureCollection","features":[]}
    rows=[]
    for hid,h in sorted(houses.items()):
        lon,lat=transform(h,fit)
        x,y=int(h["x_px"]),int(h["y_px"])
        feature={"type":"Feature","geometry":{"type":"Point","coordinates":[round(lon,8),round(lat,8)]},
                 "properties":{"house_id":hid,"image_x":x,"image_y":y,
                               "proximity_group_max8":groups[hid],
                               "location_status":"provisional_affine_estimate",
                               "service_transformer":"unknown"}}
        geo["features"].append(feature)
        rows.append(dict(house_id=hid,image_x=x,image_y=y,longitude=round(lon,8),
                         latitude=round(lat,8),proximity_group_max8=groups[hid],
                         location_status="provisional_affine_estimate",service_transformer="unknown"))
    residual,loo=[],[]
    for hid in FITTED:
        p=controls[hid];reference=(float(p["longitude"]),float(p["latitude"]))
        err=discrepancy(transform(houses[hid],fit),reference)
        residual.append({"id":hid,"m":round(err,2)})
        restricted=fit_affine(houses,controls,[k for k in FITTED if k!=hid])
        loo.append({"id":hid,"m":round(discrepancy(transform(houses[hid],restricted),reference),2)})
    info={
      "method":"affine_image_pixel_to_local_east_north",
      "local_origin_lat":LAT0,"local_origin_lon":LON0,"R_m":R,
      "fit_ids":list(FITTED),"excluded_ids":[25],
      "east_coefficients":fit[0],"north_coefficients":fit[1],
      "calibration_residuals_m":residual,"leave_one_out_errors_m":loo,
      "max_held_out_error_m":max(v["m"] for v in loo),
      "h25_model_lonlat":transform(houses[25],fit),
      "h25_supplied_lonlat":[float(controls[25]["longitude"]),float(controls[25]["latitude"])],
      "notes":["All 35 are image-digitized properties, not verified 33 residence meters",
               "Large held-out errors; do not claim surveyed accuracy",
               "No transformer service allocations",
               "H25 user-supplied point is another nearby building and is excluded from fitting"]
    }
    return geo,rows,info

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",type=Path,default=HERE)
    args=ap.parse_args()
    args.outdir.mkdir(parents=True,exist_ok=True)
    geo,rows,diag=generate()
    (args.outdir/"house_points_provisional.geojson").write_text(json.dumps(geo,indent=2)+"\n",encoding="utf-8")
    (args.outdir/"georeferencing_diagnostics.json").write_text(json.dumps(diag,indent=2)+"\n",encoding="utf-8")
    with open(args.outdir/"house_points_provisional.csv","w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Rebuilt 35 unverified point estimates")

if __name__=="__main__":main()
