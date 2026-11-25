#!/usr/bin/env python3
"""Figure 40: four matched physical options; sampled only, numerical CSVs."""
import argparse,hashlib,io,json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path("StudyA_94022_Matched_Physical_Options_v1")
SOURCES={
"OPTION_AC_SUMMARY.csv":"0d7176e7b4a59436cae0a90f348e66c8e615bfaf1df44dd12bc6496f35666289",
"SIGNED_HEAD_COMPARISON.csv":"b3629854b1421533850e2b602a91192440552dc896af8dd51a167811ebd87dde"}
def sha(b):return hashlib.sha256(b).hexdigest()
def load(path,h):
    b=path.read_bytes();lf=b.replace(b"\r\n",b"\n")
    if b"\r" in lf or (b"\r" in b and b"\n" in b.replace(b"\r\n",b"")) or h not in (sha(b),sha(lf),sha(lf.replace(b"\n",b"\r\n"))):
        raise ValueError("Source checksum mismatch "+str(path))
    return pd.read_csv(io.BytesIO(b)),sha(b)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."));ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    data={};receipts={}
    for name,h in SOURCES.items():
        data[name],actual=load(a.repo_root/ROOT/name,h);receipts[name]={"path":str(ROOT/name),"signed_sha256":h,"local_sha256":actual}
    x=data["OPTION_AC_SUMMARY.csv"];head=data["SIGNED_HEAD_COMPARISON.csv"].copy()
    if len(x)!=81 or x.duplicated(["option","case","pf","length_factor"]).any() or not x.sampled_hours.eq(67).all() or not x.converged.eq(67).all() or len(head)!=1809 or head.duplicated(["case","pf","length_factor","timestamp_lst"]).any():raise ValueError("Sample population changed")
    head["failed"]=~head.ac_feasible
    head["night_failed"]=head.failed&head.night_reactive_disabled
    head["daylight_failed"]=head.failed&~head.night_reactive_disabled
    g=head.groupby(["case","pf","length_factor"],as_index=False).agg(infeasible=("failed","sum"),night_failed=("night_failed","sum"),daylight_failed=("daylight_failed","sum"),min_v_pu=("min_v_pu","min"),max_v_pu=("max_v_pu","max"))
    g["option"]="head";x=pd.concat([x,g],ignore_index=True)
    names=["head","middle","end","head_hypothetical_R050"]
    labels=["Original head","Middle","End","Head, hypothetical R×0.5"]
    agg=x.groupby("option").agg(infeasible=("infeasible","sum"),night=("night_failed","sum"),day=("daylight_failed","sum"),vmin=("min_v_pu","min"),vmax=("max_v_pu","max")).reindex(names)
    if list(agg.infeasible)!=[342,165,780,0]:raise ValueError("Failure totals changed")
    factors=[(pf,l) for pf in (.95,.98,1.) for l in (1.,1.3,1.6)]
    fig,ax=plt.subplots(2,2,figsize=(14,9),layout="constrained")
    for i,opt in enumerate(names):
        q=x[x.option.eq(opt)].groupby(["pf","length_factor"]).infeasible.sum()
        values=np.array([[q.loc[(pf,l)] for pf,l in factors[j:j+3]] for j in (0,3,6)])
        a0=ax.flat[i];im=a0.imshow(values,cmap="Reds",vmin=0,vmax=3*67,aspect="auto")
        a0.set_xticks(range(3),["1.0","1.3","1.6"]);a0.set_yticks(range(3),["0.95","0.98","1.00"])
        a0.set(xlabel="Service length multiplier",ylabel="Load PF",title=f"{labels[i]} | {int(agg.loc[opt,'infeasible'])}/1809 failed")
        for row in range(3):
            for col in range(3):a0.text(col,row,str(values[row,col]),ha="center",va="center")
        fig.colorbar(im,ax=a0,shrink=.75,label="Failed case-hours / 201")
    fig.suptitle("94022 | Same three equipment designs and frozen dispatch; 67 common hours per factor\n4 options × 27 factors × 67 hours = 7,236 matched AC case-hours; sampled, not annual")
    a.out.mkdir(parents=True)
    for ext in ("png","svg"):fig.savefig(a.out/("40_matched_physical_option_robustness."+ext),dpi=180,bbox_inches="tight")
    plt.close(fig)
    m=dict(sources=receipts,script_sha256=sha(Path(__file__).read_bytes()),matplotlib=matplotlib.__version__,pandas=pd.__version__,sample_only=True,field_verified=False,output_sha256={f.name:sha(f.read_bytes()) for f in a.out.iterdir()})
    (a.out/"FIGURE_MANIFEST.json").write_text(json.dumps(m,indent=2)+"\n",encoding="utf-8");print(json.dumps(m,indent=2))
if __name__=="__main__":main()
