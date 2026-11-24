"""Read-only project validation and bounded publication; no production result claims."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runner-test" / "project"
OUT.mkdir(parents=True, exist_ok=True)
report = {"schema": 1, "scope": "archived Case 1 regression and synthetic 48-hour dispatch",
          "commit": os.environ["CI_COMMIT_SHA"], "job_id": os.environ["CI_JOB_ID"],
          "runner_id": os.environ["CI_RUNNER_ID"],
          "session_id": int(os.environ["RUNNER_VERIFIED_SESSION_ID"]),
          "python": sys.version.split()[0], "checks": {}}

def check(name, fn):
    try:
        report["checks"][name] = {"status":"PASS", "result": fn()}
    except Exception as exc:
        traceback.print_exc()
        report["checks"][name] = {"status":"FAIL", "error_type": type(exc).__name__}

def regression():
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_wp1_v3.py",
                             "-q", "--junitxml=" + str(OUT / "junit.xml")],
                            cwd=ROOT/"case1", timeout=240)
    suite = ET.parse(OUT/"junit.xml").getroot()
    rows = []
    for case in suite.iter("testcase"):
        status = next((s for s in ("failure", "error", "skipped") if case.find(s) is not None), "passed")
        rows.append({"name": case.attrib["name"], "status":status, "seconds":float(case.attrib.get("time",0))})
    import csv
    with (OUT/"regression.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name","status","seconds"])
        w.writeheader()
        w.writerows(rows)
    report["regression"] = {"exit_code":result.returncode,"tests":len(rows),
                            "passed":sum(r["status"]=="passed" for r in rows),
                            "cases":rows}
    assert result.returncode == 0 and len(rows) == 22 and all(r["status"]=="passed" for r in rows)
    return {"passed":len(rows)}

def dispatch():
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(ROOT/"case1"))
    from wp1_v3 import model as m
    index = pd.date_range("2025-01-01", periods=48, freq="h")
    load = pd.Series(1.5, index=index)
    pv = pd.Series(np.where((index.hour>=8)&(index.hour<=16),3.,0.),index=index)
    frame = m.dispatch(load,pv,modules=4,inverter_kva=5.,charge_discharge_kw=5.,pf=.98)
    pv_used=frame.pv_direct_ac/m.ETA_INV+frame.pv_charge_dc+frame.grid_export/m.ETA_INV+frame.curtailed_dc
    ac=frame.pv_direct_ac+frame.battery_discharge_dc*m.ETA_INV+frame.grid_import
    pv_error=float(np.max(np.abs(pv_used-pv)))
    ac_error=float(np.max(np.abs(ac-frame.load_served)))
    demand_error=float(np.max(np.abs(load-frame.load_served-frame.ens)))
    assert np.isfinite(frame.to_numpy()).all() and max(pv_error,ac_error,demand_error)<1e-6
    assert frame.pcc_kva.max()<=4.5+1e-6
    assert frame.soc_usable_kwh.min()>=-1e-6 and frame.soc_usable_kwh.max()<=4*m.USABLE_KWH_MODULE+1e-6
    frame.assign(demand_kw=load,pv_dc_kw=pv).to_csv(OUT/"dispatch_48h.csv",index_label="timestamp",float_format="%.10g")
    fig, ax = plt.subplots(figsize=(9,4))
    ax.plot(index, load, label="Demand (kW)")
    ax.plot(index, pv, label="PV DC (kW)")
    ax.plot(index, frame.grid_import, label="Grid import (kW)")
    ax.set(ylabel="Power (kW)",title="Synthetic 48-hour Case 1 dispatch; diagnostic only")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT/"dispatch_48h.png",dpi=120)
    plt.close(fig)
    return {"hours":len(frame),"demand_kwh":float(load.sum()),"pv_dc_kwh":float(pv.sum()),
            "grid_import_kwh":float(frame.grid_import.sum()),"grid_export_kwh":float(frame.grid_export.sum()),
            "ens_kwh":float(frame.ens.sum()),"max_pcc_kva":float(frame.pcc_kva.max()),
            "pv_balance_max_kw":pv_error,"ac_balance_max_kw":ac_error,"demand_balance_max_kw":demand_error,
            "initial_soc_pu":.55,"end_usable_soc_kwh":float(frame.soc_usable_kwh.iloc[-1])}

check("case1_regression",regression)
check("synthetic_dispatch",dispatch)
report["status"]="PASS" if all(c["status"]=="PASS" for c in report["checks"].values()) else "FAIL"
report["files"] = []
for name in ("junit.xml","regression.csv","dispatch_48h.csv","dispatch_48h.png"):
    f=OUT/name
    if f.is_file():
        report["files"].append({"name":name,"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()})
payload=json.dumps(report,ensure_ascii=True,allow_nan=False,separators=(",",":"))
(OUT/"report.json").write_text(payload+"\n",encoding="utf-8")
if len(payload.encode("utf-8"))>12000:
    raise RuntimeError("Approved inline report exceeds limit; use artifacts")
print("RUNNER_RESULT_V1 "+payload,flush=True)
sys.exit(report["status"]!="PASS")
