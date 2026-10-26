#!/usr/bin/env python3
"""Rebuild completely offline dual-view map from committed project sources."""
import argparse
import json
from pathlib import Path
import base64

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PHOTO=REPO/"Energy Community - San Rafael"/"SanRafael_Reproducible_Model_Package_v2"/"01_raw_site"/"community_satellite_houses_1_35.jpg"

def render():
    template=(HERE/"map_offline_template.html").read_text(encoding="utf-8")
    satellite=base64.b64encode(PHOTO.read_bytes()).decode("ascii")
    geo=json.loads((HERE/"house_points_provisional.geojson").read_text(encoding="utf-8"))
    controls=json.loads((HERE/"control_points_supplied.geojson").read_text(encoding="utf-8"))
    assert len(geo["features"])==35, "Historical mapping must retain all 35 properties"
    return template.replace("__SATELLITE_BASE64__",satellite).replace("__GEOJSON__",json.dumps(geo,separators=(",",":"))).replace("__CONTROLS__",json.dumps(controls,separators=(",",":")))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=HERE/"map.html")
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(render(),encoding="utf-8")
    print("Offline map written:",args.output)
