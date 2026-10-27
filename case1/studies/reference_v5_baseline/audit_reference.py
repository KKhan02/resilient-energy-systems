#!/usr/bin/env python3
"""Audit the preserved v5 fixed-route headroom output. This does not rerun pandapower."""
import csv
import hashlib
import json
from pathlib import Path
import argparse

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/"Energy Community - San Rafael"/"pandapower_results_nasa"/"transformer_headroom_house_sweep.csv"

def calculate():
    with SOURCE.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    if [int(r["houses"]) for r in rows]!=list(range(1,21)):
        raise ValueError("Expected original v5 1-20 household sensitivity only")
    tab=[]
    for r in rows:
        n=int(r["houses"]);p=float(r["load_kw"])
        tr=float(r["transformer_loading_pct"])
        low=float(r["min_lv_vm_pu"]);high=float(r["max_lv_vm_pu"])
        ok_v=low>=.97 and high<=1.03
        ok_t=tr<=100
        if str(ok_v).lower()!=r["lv_drop_screen_ok"].lower() or str(ok_t).lower()!=r["transformer_nominal_ok"].lower():
            raise ValueError("Historical screening flags disagree with stored numbers")
        tab.append([n,f"{p:.6f}",f"{tr:.6f}",f"{low:.6f}",f"{high:.6f}",str(ok_v).lower(),str(ok_t).lower(),r["timestamp"]])
    a=next((r[0] for r in tab if r[5]=="false"),None)
    b=next((r[0] for r in tab if r[6]=="false"),None)
    result={"source":"Energy Community - San Rafael/pandapower_results_nasa/transformer_headroom_house_sweep.csv",
            "input_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "first_voltage_screen_failure_homes":a,
            "first_nominal_transformer_overload_homes":b,
            "screen_voltages_pu":[.97,1.03],
            "screen_transformer_loading_pct":100,
            "rows":len(tab),
            "status":"PREVIOUSLY SAVED pandapower v5 results. No new power flow or utility topology validation.",
            "assumptions":"Existing v5 5kVA, 324.5m representative fixed LV radial, two households per tap, balanced equivalent, max-load no-DER time for each N; 35 actual service connections unknown."}
    return tab,result

def run(directory):
    tab,result=calculate()
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/"v5_existing_reference_limits.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,lineterminator="\n")
        w.writerow(["houses","peak_load_kw","transformer_loading_pct","min_lv_vm_pu","max_lv_vm_pu","voltage_screen_ok","transformer_screen_ok","peak_timestamp"])
        w.writerows(tab)
    (directory/"audit_summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",type=Path,default=HERE)
    args=ap.parse_args()
    run(args.outdir)
