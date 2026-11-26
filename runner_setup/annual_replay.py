"""Infrastructure annual replay, not a current Study A result or sizing sweep."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runner-test" / "annual"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT/"case1"))
from wp1_v3 import model as m

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

src = ROOT/"case1"/"results"
options = pd.read_csv(src/"selected_community_options.csv")
manifest = json.loads((src/"RUN_MANIFEST.json").read_text())
# The archive stores demand/PV and dispatch at seven decimal places.
# Diagnostic tolerances, not engineering compliance thresholds.
power_tol = 1e-5
stored_tol = 1e-3
energy_tol = 1e-3
report = {"schema":1,"scope":"frozen-input archived Case 1 replay; not current Study A",
          "commit":os.environ["CI_COMMIT_SHA"],"job_id":os.environ["CI_JOB_ID"],
          "runner_id":os.environ["CI_RUNNER_ID"],"session_id":int(os.environ["RUNNER_VERIFIED_SESSION_ID"]),
          "python":sys.version.split()[0],"archive_solar_method":manifest["solar_method"],
          "reference_precision_decimals":7,"tolerance":{"hourly_power_kw_or_kva":power_tol,
          "stored_energy_kwh":stored_tol,"annual_energy_kwh":energy_tol},"cases":[]}
summaries = []
for hh in (4,8,12,15,17):
    start = time.perf_counter()
    selection = options.loc[options.households==hh]
    assert len(selection)==1
    cfg = selection.iloc[0]
    path=src/f"hourly_selected_{hh}house.csv"
    baseline=pd.read_csv(path,parse_dates=["timestamp"]).set_index("timestamp")
    expected_index=pd.date_range("2025-01-01",periods=8760,freq="h")
    assert baseline.index.equals(expected_index)
    demand=baseline.demand_kw
    pv=baseline.pv_dc_available_kw
    modules=int(cfg.bess_modules)
    result=m.dispatch(demand,pv,modules=modules,inverter_kva=float(cfg.inverter_kva),
                      cap_pu=float(cfg.transformer_allow_kva)/5,pf=float(cfg.load_pf),
                      initial_soc_pu=.55,policy="conventional",
                      charge_discharge_kw=float(cfg.battery_power_cap_kw))
    assert result.index.equals(baseline.index) and np.isfinite(result.to_numpy()).all()
    assert set(m.COLS).issubset(baseline.columns)
    deltas=(result[m.COLS]-baseline[m.COLS]).abs().max()
    tol={k:(stored_tol if k=="soc_usable_kwh" else power_tol) for k in m.COLS}
    mismatch=[k for k in m.COLS if deltas[k]>tol[k]]
    pv_error=float((result.pv_direct_ac/m.ETA_INV+result.pv_charge_dc+result.grid_export/m.ETA_INV+result.curtailed_dc-pv).abs().max())
    ac_error=float((result.pv_direct_ac+result.battery_discharge_dc*m.ETA_INV+result.grid_import-result.load_served).abs().max())
    demand_error=float((demand-result.load_served-result.ens).abs().max())
    initial=modules*m.USABLE_KWH_MODULE*(.55-.1)/.9
    previous=np.r_[initial,result.soc_usable_kwh.to_numpy()[:-1]]
    battery_error=float(np.max(np.abs(result.soc_usable_kwh.to_numpy()-previous-result.pv_charge_dc.to_numpy()*m.ETA_BAT+result.battery_discharge_dc.to_numpy()/m.ETA_BAT)))
    annual={}
    for key,col in (("import_kwh","grid_import"),("export_kwh","grid_export"),("ens_kwh","ens"),("served_kwh","load_served")):
        a=float(baseline[col].sum()); b=float(result[col].sum())
        annual[key]={"reference":a,"replay":b,"difference":b-a}
    physics_pass=bool(max(pv_error,ac_error,demand_error,battery_error)<1e-6 and
                 result.pcc_kva.max()<=float(cfg.transformer_allow_kva)+1e-6 and
                 result.soc_usable_kwh.min()>=-1e-6 and
                 result.soc_usable_kwh.max()<=modules*m.USABLE_KWH_MODULE+1e-6)
    parity=not mismatch and all(abs(x["difference"])<=energy_tol for x in annual.values())
    entry={"households":hh,"hours":len(result),"panels":int(cfg.panels),
           "battery_modules":modules,"inverter_kva":float(cfg.inverter_kva),
           "battery_power_cap_kw":float(cfg.battery_power_cap_kw),
           "archive_input_sha256":sha(path),"physics_pass":physics_pass,"archive_parity":parity,
           "max_column_abs_error":{k:float(v) for k,v in deltas.items()},"mismatch_columns":mismatch,
           "annual":annual,"max_pcc_kva":float(result.pcc_kva.max()),
           "energy_balance_max_residual":{"pv":pv_error,"ac":ac_error,"demand":demand_error,"battery":battery_error},
           "runtime_s":time.perf_counter()-start}
    report["cases"].append(entry)
    result.assign(demand_kw=demand,pv_dc_available_kw=pv).to_csv(OUT/f"replay_{hh}house.csv",index_label="timestamp",float_format="%.10g")
    summaries.append({"households":hh,"physics_pass":physics_pass,"archive_parity":parity,
                      **{k+"_difference":v["difference"] for k,v in annual.items()}})
    if hh==8:
        fig,ax=plt.subplots(2,1,figsize=(10,6),constrained_layout=True)
        ax[0].plot(baseline.index[:168],baseline.grid_import.iloc[:168],label="Archived import",lw=2)
        ax[0].plot(result.index[:168],result.grid_import.iloc[:168],label="Replay import",ls="--")
        ax[0].set_ylabel("Grid import (kW)")
        ax[0].legend()
        ax[1].plot(result.index,(result.grid_import-baseline.grid_import),lw=.6)
        ax[1].set_ylabel("Replay minus archive (kW)")
        ax[1].set_xlabel("2025")
        fig.suptitle("Frozen-input 8-household annual replay, diagnostic only")
        fig.savefig(OUT/"replay_comparison_8house.png",dpi=130)
        plt.close(fig)
pd.DataFrame(summaries).to_csv(OUT/"summary.csv",index=False)
report["physics_pass"]=all(x["physics_pass"] for x in report["cases"])
report["archive_parity"]=all(x["archive_parity"] for x in report["cases"])
report["status"]="PASS" if report["physics_pass"] and report["archive_parity"] else "REVIEW"
report["files"]=[{"name":f.name,"sha256":sha(f),"bytes":f.stat().st_size} for f in sorted(OUT.iterdir()) if f.is_file()]
payload=json.dumps(report,allow_nan=False,separators=(",",":"))
(OUT/"report.json").write_text(payload+"\n",encoding="utf-8")
assert len(payload.encode("utf-8"))<=16000
print("ANNUAL_REPLAY_V1 "+payload,flush=True)
sys.exit(0 if report["status"]=="PASS" else 1)
