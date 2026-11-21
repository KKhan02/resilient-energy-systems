#!/usr/bin/env python3
"""Geometry-only household screening. No routed LV feasibility assessment."""
import argparse
import csv
import json
import math
from pathlib import Path

EARTH_RADIUS_M = 6371008.8
REQUIRED = ("household_id", "community", "latitude", "longitude")

def distance_m(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2-lat1, lon2-lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*EARTH_RADIUS_M*math.asin(min(1.0, math.sqrt(h)))

def load_households(path, community):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        missing = set(REQUIRED)-set(rd.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {sorted(missing)}")
        selected = [r for r in rd if r["community"].strip().casefold()==community.casefold()]
    if not selected:
        raise ValueError(f"No household coordinate rows for {community!r}")
    rows, ids = [], set()
    for r in selected:
        identifier = r["household_id"].strip()
        if not identifier or identifier in ids:
            raise ValueError("Household IDs must be nonempty and unique in the selected community")
        ids.add(identifier)
        lat, lon = float(r["latitude"]), float(r["longitude"])
        if not (math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):
            raise ValueError(f"Invalid coordinates for {identifier}")
        rows.append({"household_id":identifier,"latitude":lat,"longitude":lon})
    return sorted(rows, key=lambda r:r["household_id"])

def build_screen(rows):
    n = len(rows)
    if not n:
        raise ValueError("At least one house is needed")
    pts = [(r["latitude"],r["longitude"]) for r in rows]
    d = [[distance_m(pts[i],pts[j]) for j in range(n)] for i in range(n)]
    medoid = min(range(n), key=lambda i:(sum(d[i]),rows[i]["household_id"]))
    near_vals, details = [], []
    for i,r in enumerate(rows):
        near = min((j for j in range(n) if j!=i),
                   key=lambda j:(d[i][j],rows[j]["household_id"]),default=None)
        dist = None if near is None else d[i][near]
        if dist is not None:
            near_vals.append(dist)
        details.append({"household_id":r["household_id"],
                        "nearest_household_id":"" if near is None else rows[near]["household_id"],
                        "nearest_distance_m":None if dist is None else round(dist,3),
                        "distance_to_medoid_m":round(d[i][medoid],3)})
    visited, edges = {medoid}, []
    while len(visited)<n:
        length,i,j = min((d[i][j],i,j) for i in visited for j in range(n) if j not in visited)
        edges.append({"from_household_id":rows[i]["household_id"],
                      "to_household_id":rows[j]["household_id"],
                      "straight_line_distance_m":round(length,3)})
        visited.add(j)
    pairs=[d[i][j] for i in range(n) for j in range(i+1,n)]
    def quantile(xs,p):
        if not xs: return None
        pos=p*(len(xs)-1)
        lo,hi=math.floor(pos),math.ceil(pos)
        return xs[lo] if lo==hi else xs[lo]*(hi-pos)+xs[hi]*(pos-lo)
    summary={
      "households_with_coordinates":n,
      "status":"geometry_screen_only" if n>=2 else "insufficient_households_for_network_screen",
      "medoid_household_id":rows[medoid]["household_id"],
      "medoid_latitude":rows[medoid]["latitude"],"medoid_longitude":rows[medoid]["longitude"],
      "straight_line_star_length_m":round(sum(d[medoid]),3),
      "straight_line_mst_length_m":round(sum(e["straight_line_distance_m"] for e in edges),3),
      "longest_mst_edge_m":round(max((e["straight_line_distance_m"] for e in edges),default=0),3),
      "max_pairwise_distance_m":round(max(pairs,default=0),3),
      "median_nearest_neighbor_m":round(quantile(sorted(near_vals),.5),3) if near_vals else None,
      "p90_nearest_neighbor_m":round(quantile(sorted(near_vals),.9),3) if near_vals else None,
      "duplicate_coordinate_pairs":sum(1 for p in pairs if p<.001),
      "limitations":"Straight-line lower bounds only; no shoreline, access routes, terrain, voltage, thermal limits, protection, grid access or costs. No conclusion on mini-grid versus SHS. Medoid is a house location, not an approved plant site."
    }
    return summary,details,edges

def write_csv(path,records,cols):
    with path.open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=cols)
        wr.writeheader()
        wr.writerows(records)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--households",type=Path,required=True)
    p.add_argument("--community",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    rows=load_households(a.households,a.community.strip())
    summary,details,edges=build_screen(rows)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/"summary.json").write_text(json.dumps({"community":a.community,**summary},indent=2)+"\n",encoding="utf-8")
    write_csv(a.output/"household_distances.csv",details,
              ["household_id","nearest_household_id","nearest_distance_m","distance_to_medoid_m"])
    write_csv(a.output/"mst_edges.csv",edges,["from_household_id","to_household_id","straight_line_distance_m"])
    print(json.dumps({"community":a.community,**summary},indent=2))

if __name__=="__main__":
    main()
