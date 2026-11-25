#!/usr/bin/env python3
"""Figure 38 from completed annual stress and nighttime P diagnostics only."""
import argparse, hashlib, io, json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SOURCES={"annual":("StudyA_113699_Sizing_AnnualStress_v1/FACTOR_AC_SUMMARY.csv","09d2daa06ef68e66ce0228ca450df326765c76b534681f20216a1efa682d17b0"),
"corridors":("StudyA_94022_Stress_P_Probe_v1/STRESS_P_CORRIDORS.csv","4fd86089d5a90a5a3949190cd44b51b226301a07763ba2717aa90398c5779860")}
def sha(b):return hashlib.sha256(b).hexdigest()
def load(repo,path,expected):
    raw=(repo/path).read_bytes();lf=raw.replace(b"\r\n",b"\n")
    if b"\r" in lf or (b"\r" in raw and b"\n" in raw.replace(b"\r\n",b"")) or expected not in (sha(raw),sha(lf),sha(lf.replace(b"\n",b"\r\n"))):
        raise ValueError("Source checksum mismatch "+path)
    return pd.read_csv(io.BytesIO(raw)),{"path":path,"signed_sha256":expected,"local_sha256":sha(raw)}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."));ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    frames={};receipts={}
    for k,(path,h) in SOURCES.items():frames[k],receipts[k]=load(a.repo_root,path,h)
    x=frames["annual"];c=frames["corridors"]
    if len(x)!=5 or not x.case.is_unique or not x.case_hour_records.eq(8760).all() or not x.converged_hours.eq(8760).all() or not x.main_band_infeasible_hours.eq(0).all() or not x.pf.eq(.95).all() or not x.length_factor.eq(1.6).all():raise ValueError("Annual source changed")
    u=c[c.status.eq("NO_TESTED_FEASIBLE_POINT")].copy()
    if len(c)!=115 or c.duplicated(["pf","length_factor","timestamp_lst"]).any() or len(u)!=9 or c.status.eq("TESTED_TERMINAL_SEGMENT").sum()!=106:raise ValueError("Probe source changed")
    fig,ax=plt.subplots(1,2,figsize=(14,6),layout="constrained")
    y=np.arange(len(x));ax[0].scatter(x.minimum_voltage_pu,y,s=55);ax[0].set_yticks(y,x.case.str.replace("113699_","",regex=False));ax[0].axvline(.95,ls="--",color="firebrick",label="Main lower limit");ax[0].axvline(.97,ls=":",color="gray",label="Optional lower limit");ax[0].set_xlim(.945,.985);ax[0].invert_yaxis();ax[0].set_xlabel("Annual minimum voltage (pu)");ax[0].set_title("113699 | 5 × 8,760 h, PF 0.95 / length ×1.6");ax[0].legend(loc="lower right")
    u=u.sort_values(["pf","length_factor","timestamp_lst"]);y=np.arange(len(u))
    labels=[f"{t[5:16]} | {pf:.2f} / {l:.1f}" for t,pf,l in zip(u.timestamp_lst,u.pf,u.length_factor)]
    ax[1].scatter(u.best_tested_voltage_pu,y,color="firebrick",s=55);ax[1].axvline(.95,ls="--",color="black");ax[1].set_yticks(y,labels);ax[1].invert_yaxis();ax[1].set_xlim(.943,.951);ax[1].set_xlabel("Best tested minimum voltage (pu)");ax[1].set_title("94022 | 9 unresolved of 115 sampled events")
    fig.suptitle("Study A | Annual fixed-schedule stress versus instantaneous power-feasibility diagnostic\n94022: 106 events with tested terminal segments; no SOC feasibility or global infeasibility inference")
    a.out.mkdir(parents=True)
    for ext in ("png","svg"):fig.savefig(a.out/("38_annual_stress_and_unresolved_events."+ext),dpi=180,bbox_inches="tight")
    plt.close(fig)
    m=dict(sources=receipts,script_sha256=sha(Path(__file__).read_bytes()),matplotlib=matplotlib.__version__,pandas=pd.__version__,field_verified=False,output_sha256={p.name:sha(p.read_bytes()) for p in a.out.iterdir()})
    (a.out/"FIGURE_MANIFEST.json").write_text(json.dumps(m,indent=2)+"\n",encoding="utf-8");print(json.dumps(m,indent=2))
if __name__=="__main__":main()
