#!/usr/bin/env python3
"""Figure 39: numerical physical-option probes and worst-house voltage drops."""
import argparse,hashlib,io,json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path("StudyA_94022_Physical_Options_v1")
HASHES={"PHYSICAL_OPTION_PROBES.csv":"1986a8f373430fdf87ab75d125e6974a8bc1204e01f72ab383372c77410bcb4e",
"WORST_HOUSE_PATH_DROPS.csv":"50d86ad20c7de48ddaf17cd1883f135431dfde4fe0803f09e5fbb62c28853d78"}
def sha(b):return hashlib.sha256(b).hexdigest()
def load(path,h):
    b=path.read_bytes();lf=b.replace(b"\r\n",b"\n")
    if b"\r" in lf or (b"\r" in b and b"\n" in b.replace(b"\r\n",b"")) or h not in (sha(b),sha(lf),sha(lf.replace(b"\n",b"\r\n"))):
        raise ValueError("Source checksum "+str(path))
    return pd.read_csv(io.BytesIO(b)),sha(b)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."));ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    frames={};receipts={}
    for name,h in HASHES.items():
        frames[name],actual=load(a.repo_root/ROOT/name,h);receipts[name]={"path":str(ROOT/name),"signed_sha256":h,"local_sha256":actual}
    p=frames["PHYSICAL_OPTION_PROBES.csv"];d=frames["WORST_HOUSE_PATH_DROPS.csv"]
    if len(p)!=756 or len(d)!=833 or p.duplicated(["option","pf","length_factor","timestamp_lst","probe_index"]).any():raise ValueError("Population changed")
    ts="2025-09-24 20:00:00"
    z=p[p.timestamp_lst.eq(ts)&p.pf.eq(.95)&p.length_factor.eq(1.6)]
    q=d[d.timestamp_lst.eq(ts)&d.pf.eq(.95)&d.length_factor.eq(1.6)&d.option.eq("head")&d.probe_index.eq(20)].sort_values("edge_order")
    if len(z)!=84 or len(q)!=14 or q.iloc[-1].to_node!="HOUSE_H01":raise ValueError("Event identity changed")
    fig,ax=plt.subplots(2,2,figsize=(13,9),layout="constrained")
    names={"head":"Head","middle":"Middle","end":"End","head_hypothetical_R050":"Head, hypothetical R×0.5"}
    for opt,group in z.groupby("option",sort=False):
        group=group.sort_values("probe_p_kw")
        ax[0,0].plot(group.probe_p_kw,group.min_v_pu,label=names[opt],marker=".",ms=3)
        ax[0,1].plot(group.probe_p_kw,group.max_v_pu,label=names[opt],marker=".",ms=3)
    for a0,limit,title in [(ax[0,0],.95,"Minimum household voltage"),(ax[0,1],1.05,"Maximum household voltage")]:
        a0.axhline(limit,color="firebrick",ls="--");a0.set(xlabel="Inverter active power (kW)",ylabel="Voltage (pu)",title=title);a0.legend(fontsize=8)
    pos=np.r_[0,q.length_m.cumsum().to_numpy()];v=np.r_[q.iloc[0].from_v_pu,q.to_v_pu.to_numpy()]
    ax[1,0].plot(pos,v,marker=".",label="Head at power ceiling");ax[1,0].axhline(.95,ls="--",color="firebrick");ax[1,0].set(xlabel="Cumulative modeled root-to-H01 path (m)",ylabel="Voltage (pu)",title="Original head: LV path to H01");ax[1,0].legend(fontsize=8)
    root=float(q.iloc[0].from_v_pu);tap=float(q.iloc[-1].from_v_pu);house=float(q.iloc[-1].to_v_pu)
    ax[1,1].bar(["Source to LV root","Shared LV path","H01 service"],[1-root,root-tap,tap-house]);ax[1,1].set(ylabel="Voltage drop (pu)",title="Voltage-drop decomposition");ax[1,1].tick_params(axis="x",labelrotation=12)
    fig.suptitle("94022 | 24 Sep 2025 20:00, PF 0.95, service length ×1.6 | instantaneous, not annual\nSame load and equipment power limits; night Q off; hypothetical GIS proxy")
    a.out.mkdir(parents=True)
    for ext in ("png","svg"):fig.savefig(a.out/("39_physical_option_voltage_diagnostics."+ext),dpi=180,bbox_inches="tight")
    plt.close(fig)
    m=dict(sources=receipts,script_sha256=sha(Path(__file__).read_bytes()),matplotlib=matplotlib.__version__,pandas=pd.__version__,field_verified=False,output_sha256={f.name:sha(f.read_bytes()) for f in a.out.iterdir()})
    (a.out/"FIGURE_MANIFEST.json").write_text(json.dumps(m,indent=2)+"\n",encoding="utf-8");print(json.dumps(m,indent=2))
if __name__=="__main__":main()
