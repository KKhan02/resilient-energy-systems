"""Render actual hash-qualified Study B B1 tables. No simulation or inferred series."""
import argparse, base64, hashlib, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
PLAN=json.loads((HERE/"STUDY_B_FIGURE_PLAN_2026-11-27.json").read_text(encoding="utf-8"))
STUDY=HERE.parent/"studies"/"SEEDExchange_StudyB_Integration_v1"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,msg):
    if not ok:raise ValueError(msg)
def read_tables(folder,receipt):
    d={}
    for name,digest in receipt["report"]["output_hashes"].items():
        check(sha(folder/name)==digest,"hash mismatch "+name)
        d[name[:-4]]=pd.read_csv(folder/name)
    return d
def header(fig,title,subtitle):
    fig.suptitle(title,fontsize=15,fontweight="bold")
    fig.text(.5,.925,subtitle,ha="center",fontsize=9)
def style(ax,x,y):
    ax.set_xlabel(x);ax.set_ylabel(y);ax.grid(alpha=.22);ax.set_axisbelow(True)
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--b1",type=Path,required=True);a.add_argument("--qualification",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True);a.add_argument("--emit-figure-bytes",action="store_true")
    x=a.parse_args()
    b1=json.loads((STUDY/"B1_RUN_3124217129_RECEIPT.json").read_text(encoding="utf-8"))
    q1=json.loads((STUDY/"B1_QUALIFICATION_3124248027_RECEIPT.json").read_text(encoding="utf-8"))
    t=read_tables(x.b1,b1);q=read_tables(x.qualification,q1)
    c=t["network_cases"];d=q["paired_topology_tradeoffs"];u=q["unique_group_gross"];front=q["candidate_geometry_front"]
    check(len(c)==3146 and len(d)==1573 and len(u)==454*3 and int(front.geometry_nondominated.sum())==2202,"count gate")
    plt.rcParams.update({"font.size":10,"figure.dpi":125,"axes.spines.top":False,"axes.spines.right":False})
    colors={"STAR":"#356aa0","MST":"#008779"}
    ns=np.arange(5,16); figs={}
    f,ax=plt.subplots(1,2,figsize=(11,4.7),layout="constrained")
    header(f,"Study B | Candidate population","Deduplicated groups and geometric supply sites; 36 disjoint community partitions separately verified")
    group=c.drop_duplicates("group_id").groupby("house_count").size().reindex(ns)
    sites=c.drop_duplicates("site_id").groupby("house_count").size().reindex(ns)
    for a,v,title in zip(ax,[group,sites],["Unique household groups","Unique supply sites"]):
        a.bar(ns,v);a.set_xticks(ns);style(a,"Households per group",title)
    figs[50]=f
    f,ax=plt.subplots(2,2,figsize=(10,8),layout="constrained")
    header(f,"Study B | Paired candidate networks","Same household group and supply site in each row; geometric chords, not installed or surveyed routes")
    for row,n in enumerate((10,15)):
        z=d[d.house_count.eq(n)].copy();z["distance"]=(z.cable_saving_pct-z.cable_saving_pct.median()).abs()
        r=z.sort_values(["distance","site_id"]).iloc[0]
        allnodes=t["network_nodes"];alledges=t["network_branches"]
        for col,typ in enumerate(("STAR","MST")):
            a=ax[row,col];case=c[c.site_id.eq(r.site_id)&c.topology.eq(typ)].iloc[0]
            nodes=allnodes[allnodes.case_id.eq(case.case_id)].set_index("node_id");edges=alledges[alledges.case_id.eq(case.case_id)]
            origin=nodes.loc["SUPPLY"];dx=(nodes.longitude-origin.longitude)*111195*np.cos(np.deg2rad(origin.latitude));dy=(nodes.latitude-origin.latitude)*111195
            for edge in edges.itertuples():a.plot([dx[edge.from_node],dx[edge.to_node]],[dy[edge.from_node],dy[edge.to_node]],color=colors[typ],lw=1.2,alpha=.85)
            a.scatter(dx,dy,c="#30363d",s=20);a.scatter([0],[0],marker="s",c="#d97706",s=68,zorder=4)
            a.set_aspect("equal",adjustable="box");a.set_title(f"{n} homes | {typ} | {case.total_base_m:.0f} m cable",fontsize=11)
            style(a,"East of supply (m)","North of supply (m)")
            a.text(.02,.98,str(r.site_id),transform=a.transAxes,va="top",fontsize=8)
    figs[51]=f
    f,ax=plt.subplots(1,3,figsize=(13,4.8),layout="constrained")
    header(f,"Study B | Geometry has an electrical trade-off","1,573 matched STAR/MST supply-site pairs; boxes show observed distribution by household count")
    for a,key,y in zip(ax,["cable_saving_pct","path_change_pct","branch_peak_change_kw"],["Cable length saved (%)","Longest path increase (%)","Peak branch increase (kW)"]):
        a.boxplot([d.loc[d.house_count.eq(n),key] for n in ns],positions=ns,showfliers=True,flierprops={"markersize":2,"alpha":.3})
        a.set_xticks(ns);style(a,"Households per group",y)
    figs[52]=f
    f,ax=plt.subplots(1,2,figsize=(12,4.9),layout="constrained")
    header(f,"Study B | Gross transformer demand boundary","454 distinct groups, 8,760 hourly synthetic profiles; ignores AC losses and PV/BESS")
    for pf,color in zip((.95,.98,1.),("#d97706","#356aa0","#008779")):
        v=u[np.isclose(u.pf,pf)].groupby("house_count")
        med=v.gross_peak_kva.median().reindex(ns);lo=v.gross_peak_kva.min().reindex(ns);hi=v.gross_peak_kva.max().reindex(ns)
        ax[0].plot(ns,med,"o-",label=f"PF {pf:.2f}",color=color);ax[0].fill_between(ns,lo.to_numpy(),hi.to_numpy(),alpha=.12,color=color)
        hours=v.gross_5kva_exceed_hours.median().reindex(ns)
        ax[1].plot(ns,hours,"o-",label=f"PF {pf:.2f}",color=color)
    ax[0].axhline(5,ls="--",color="#a62b2b",label="5 kVA hypothesis")
    for a,y in zip(ax,["Coincident gross peak (kVA)","Median hours above 5 kVA"]):
        a.set_xticks(ns);style(a,"Households per group",y);a.legend(fontsize=8)
    figs[53]=f
    f,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    header(f,"Study B | Within-group geometry frontier","2,202 nondominated cases in separate identical-membership groups; no cross-group or cost dominance")
    for a,key,y in zip(ax,["longest_base_path_m","peak_branch_kw"],["Longest supply path (m)","Coincident peak branch demand (kW)"]):
        for typ,color in colors.items():
            z=front[front.topology.eq(typ)];nd=z[z.geometry_nondominated]
            a.scatter(z.total_base_m,z[key],s=7,c="#c2c7ce",alpha=.22)
            a.scatter(nd.total_base_m,nd[key],s=10,c=color,alpha=.6,label=typ+" nondominated")
        style(a,"Total geometric cable length (m)",y);a.legend(fontsize=8)
    figs[54]=f
    x.out.mkdir(parents=True,exist_ok=False);files=[]
    for spec in PLAN["figures"]:
        f=figs[spec["number"]]
        for ext in ("png","svg"):
            path=x.out/(spec["stem"]+"."+ext);f.savefig(path,dpi=150,metadata={"Date":None} if ext=="svg" else {"Software":"Matplotlib"})
            raw=path.read_bytes();check(raw.startswith(b"\x89PNG\r\n\x1a\n") if ext=="png" else b"<svg" in raw,"header")
            files.append(dict(name=path.name,stage=spec["stage"],size=len(raw),sha256=sha(path)))
        plt.close(f)
    result=dict(status="COMPLETE_STUDY_B_B1_FIGURES",source_pipeline=PLAN["source_pipeline"],source_execution_commit=PLAN["source_execution_commit"],sources={**b1["report"]["output_hashes"],**q1["report"]["output_hashes"]},generator_sha256=sha(Path(__file__)),files=files,figures=len(figs),matplotlib=matplotlib.__version__,new_solves=0)
    (x.out/"FIGURE_MANIFEST.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("B1_FIGURE_REPORT_JSON "+json.dumps(result,separators=(",",":")),flush=True)
    if x.emit_figure_bytes:
        for item in files:
            payload=base64.b64encode((x.out/item["name"]).read_bytes()).decode("ascii");chunks=[payload[i:i+4000] for i in range(0,len(payload),4000)]
            for i,chunk in enumerate(chunks):print("B1_FIGURE_BYTES|"+item["name"]+"|"+str(i)+"|"+str(len(chunks))+"|"+chunk,flush=True)
if __name__=="__main__":main()
