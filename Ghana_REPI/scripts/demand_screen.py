#!/usr/bin/env python3
"""Indicative household appliance-energy screen. Not an hourly demand model."""
import argparse
import csv
import json
import math
from pathlib import Path

REQUIRED={"household_id","community","appliance","quantity","rated_watts","hours_per_day","days_per_week"}

def calculate(path,community):
    with path.open(newline="",encoding="utf-8-sig") as f:
        rd=csv.DictReader(f)
        missing=REQUIRED-set(rd.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {sorted(missing)}")
        records=[r for r in rd if r["community"].strip().casefold()==community.casefold()]
    if not records:
        raise ValueError(f"No appliance records for {community!r}")
    totals={}
    for r in records:
        key=r["household_id"].strip()
        if not key:
            raise ValueError("Blank household_id")
        qty,watts,hours,days=(float(r[col]) for col in ("quantity","rated_watts","hours_per_day","days_per_week"))
        if not all(math.isfinite(x) for x in (qty,watts,hours,days)):
            raise ValueError("Invalid NaN/infinite demand field")
        if qty<0 or not qty.is_integer() or watts<0 or not 0<=hours<=24 or not 0<=days<=7:
            raise ValueError(f"Invalid appliance data for {key}")
        totals[key]=totals.get(key,0)+qty*watts*hours*days/7000
    result=[{"household_id":k,"average_kwh_per_day":round(v,6),
             "indicative_kwh_per_year":round(365*v,3)} for k,v in sorted(totals.items())]
    summary={"community":community,"households_with_appliance_records":len(result),
             "average_total_kwh_per_day":round(sum(totals.values()),6),
             "indicative_total_kwh_per_year":round(365*sum(totals.values()),3),
             "calculation":"quantity*watts*hours_per_day*days_per_week/(7*1000); annual=365*average_day",
             "limits":"No hourly load profile, peak simultaneity, seasons, growth, survey expansion or electric cooking inferred. Not sufficient for sizing."}
    return result,summary

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--appliances",type=Path,required=True)
    p.add_argument("--community",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    rows,summary=calculate(a.appliances,a.community.strip())
    a.output.mkdir(parents=True,exist_ok=True)
    with (a.output/"demand_by_household.csv").open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=["household_id","average_kwh_per_day","indicative_kwh_per_year"])
        wr.writeheader()
        wr.writerows(rows)
    (a.output/"demand_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
