#!/usr/bin/env python3
"""Figure 37: eight-design nine-factor sampled results; no simulations."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SOURCE=Path("StudyA_Sizing_NineFactor_Sample_v1/FACTOR_AC_SUMMARY.csv")
EXPECTED="a641606147653e1626eff0a632654215e99731c46ac69ef9374744a029fbf95b"
CASES=["113699_P20_B4","113699_B4","113699_P18","113699_P20","113699_P22","A1_94022_min_cost_to_A0","94022_B6","94022_B7"]
FACTORS=[(pf,l) for pf in (.95,.98,1.) for l in (1.,1.3,1.6)]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    raw=(a.repo_root/SOURCE).read_bytes()
    lf=raw.replace(b"\r\n",b"\n")
    if b"\r" in lf or (b"\r" in raw and b"\n" in lf and b"\n" in raw.replace(b"\r\n",b"")) or EXPECTED not in (sha(raw),sha(lf),sha(lf.replace(b"\n",b"\r\n"))):
        raise ValueError("Source signature mismatch")
    x=pd.read_csv(io.BytesIO(raw))
    if len(x)!=72 or x.duplicated(["case","pf","length_factor"]).any() or x.sampled_hours.sum()!=5409 or x.infeasible.sum()!=342 or not x.converged.eq(x.sampled_hours).all():
        raise ValueError("Sample population changed")
    x=x.set_index(["case","pf","length_factor"])
    fail=np.array([[x.loc[(c,pf,l),"infeasible"] for pf,l in FACTORS] for c in CASES])
    v=np.array([[x.loc[(c,pf,l),"min_v_pu"] for pf,l in FACTORS] for c in CASES])
    labels=["113699 P20_B4","113699 B4","113699 P18","113699 P20","113699 P22","94022 5B","94022 6B","94022 7B"]
    fig,axes=plt.subplots(2,1,figsize=(13,9),layout="constrained")
    for ax,z,title,cmap,fmt in zip(axes,[fail,v],["Failed sampled hours","Minimum sampled voltage (pu)"],["Reds","RdYlGn"],["d",".4f"]):
        im=ax.imshow(z,aspect="auto",cmap=cmap,vmin=0 if fmt=="d" else .935,vmax=24 if fmt=="d" else 1.)
        ax.set_xticks(range(9),[f"{pf:.2f} / {l:.1f}" for pf,l in FACTORS])
        ax.set_yticks(range(8),labels);ax.set_title(title);ax.set_xlabel("Load PF / service length multiplier")
        ax.axhline(4.5,color="black",linewidth=1.2)
        for i in range(8):
            for j in range(9):
                ax.text(j,i,format(int(z[i,j]),fmt) if fmt=="d" else format(z[i,j],fmt),ha="center",va="center",fontsize=9)
        fig.colorbar(im,ax=ax,shrink=.75)
    fig.suptitle("Study A | 72 fixed-schedule factor combinations, 2025 sampled AC only\n113699: 80 common hours; 94022: 67 common hours. Reference band 0.95–1.05 pu.")
    a.out.mkdir(parents=True)
    for ext in ("png","svg"):
        fig.savefig(a.out/("37_eight_design_nine_factor_sample."+ext),dpi=180,bbox_inches="tight")
    plt.close(fig)
    manifest=dict(source_path=str(SOURCE),source_sha256=sha(raw),signed_expected_sha256=EXPECTED,script_sha256=sha(Path(__file__).read_bytes()),
        sample_only=True,field_verified=False,matplotlib=matplotlib.__version__,pandas=pd.__version__,
        output_sha256={f.name:sha(f.read_bytes()) for f in a.out.iterdir()})
    (a.out/"FIGURE_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))
if __name__=="__main__":main()
