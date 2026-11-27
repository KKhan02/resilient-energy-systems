#!/usr/bin/env python3
"""Study A walkthrough figures 41-49. Read-only Matplotlib, signed CSV inputs."""
from pathlib import Path
import argparse,base64,hashlib,json,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE=Path(__file__).resolve().parent
PLAN=json.loads((HERE/"STUDY_A_FIGURE_PLAN_2026-11-27.json").read_text(encoding="utf-8"))
COLORS={"MIDDLE_NO_R_CHANGE":"#4e79a7","R050_CONDITIONAL":"#59a14f","OLDER_CONDITIONAL_FIVE_EDGE":"#b07aa1","MAPPED_HEAD":"#007f83"}
NAMES={"MIDDLE_NO_R_CHANGE":"A0 middle","R050_CONDITIONAL":"A0 R050","OLDER_CONDITIONAL_FIVE_EDGE":"A0 five-edge","MAPPED_HEAD":"A1 mapped"}
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10.5,"axes.spines.top":False,"axes.spines.right":False,"axes.titleweight":"bold","axes.grid":True,"grid.alpha":.18,"axes.axisbelow":True,"figure.facecolor":"white","savefig.facecolor":"white","svg.fonttype":"none","svg.hashsalt":"seedexchange-study-a-2026-11-27"})

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(root):
    data={};receipts={}
    for key,item in PLAN["inputs"].items():
        raw=(root/item["path"]).read_bytes()
        alternatives=[raw,raw.replace(b"\r\n",b"\n")] if b"\r" in raw else [raw,raw.replace(b"\n",b"\r\n")]
        if not any(sha(a)==item["sha256"] for a in alternatives):raise ValueError("Source signature "+key)
        data[key]=pd.read_csv(root/item["path"])
        receipts[key]=dict(path=item["path"],expected_sha256=item["sha256"],actual_sha256=sha(raw))
    counts={"candidates":53,"pareto":307,"headroom":24,"matched":8,"middle":6,"head":9,"a0":9,"a1":4,"gap":4}
    for key,n in counts.items():
        if len(data[key])!=n:raise ValueError("Row count "+key)
    c=data["candidates"];p=data["pareto"];h=data["headroom"]
    if not (p.households.eq(34)&p.demand_kwh.eq(64532)).all() or p.portfolio_id.duplicated().any():raise ValueError("Portfolio identities")
    if c[["reference_loss_kwh","stress_loss_kwh","stress_min_v","stress_peak_trafo_pct","discharge_dc_kwh"]].isna().any().any() or c.stress_min_v.min()<.95 or c.stress_peak_trafo_pct.max()>100:raise ValueError("Candidate evidence")
    if h.loc[h.min_voltage_screen.eq(.95)&h.max_trafo_screen.eq(100),"eligible"].sum()!=3312 or h.loc[~(h.min_voltage_screen.eq(.95)&h.max_trafo_screen.eq(100)),"eligible"].sum()!=0:raise ValueError("Headroom screen")
    if data["gap"].strict_failures.sum()!=1 or data["gap"].converged.sum()!=35040:raise ValueError("Reciprocal evidence")
    if data["head"].annual_pass_groups.sum()!=18:raise ValueError("94022 pass groups")
    if data["matched"].reference_composed_model_pass.sum()!=6 or data["matched"].stress_composed_model_pass.sum()!=3:raise ValueError("Matched accounting")
    return data,receipts

def canvas(title,note,cols=2,size=(12,5)):
    f,axs=plt.subplots(1,cols,figsize=size,squeeze=False)
    f.suptitle(title,fontsize=17,fontweight="bold",y=.97,x=.06,ha="left")
    f.text(.06,.018,note,fontsize=8,color="#4b5563",ha="left")
    f.subplots_adjust(left=.09,right=.96,top=.80,bottom=.20,wspace=.35)
    return f,axs[0]
def bar(ax,x,y,color,label=None,width=.24):
    ax.bar(x,y,width=width,color=color,label=label)
def fig41(d):
    z=d["middle"].query("pf == .95 and length_factor == 1.6").sort_values("modules")
    f,a=canvas("94022 | Chronological battery support changes annual feasibility","Ten-house A0; PF 0.95, length ×1.6. R050 is conditional modeled resistance reduction; not installed infrastructure.")
    x=np.arange(len(z))
    for i,(name,key,col) in enumerate([("Original middle","old_middle","#d97706"),("Reserve-corrected middle","new_middle","#007f83"),("Conditional R050","R050","#4e79a7")]):
        bar(a[0],x+(i-1)*.25,z[key+"_violations"],col,name)
        bar(a[1],x+(i-1)*.25,z[key+"_vmin_pu"],col,name)
    a[0].set_ylabel("Annual violating hours");a[1].set_ylabel("Minimum voltage (pu)");a[1].set_ylim(.935,.965);a[1].axhline(.95,color="#a62b2b",ls="--",lw=1)
    for ax in a:ax.set_xticks(x,[f"{n} modules" for n in z.modules]);ax.legend(fontsize=8,loc="best")
    return f
def fig42(d):
    f,a=canvas("Territory sizing | More storage does not define a universal optimum","All points pass reference and severe annual model limits. Marker area = annual DC curtailment; 85398 cohorts differ.",3,(14,5.2))
    for ax,key,title,col in zip(a,["head","a0","a1"],["94022 • A1 (8 homes)","85398 • A0 (4 homes)","85398 • A1 (5 homes)"],["#007f83","#4e79a7","#b07aa1"]):
        z=d[key];ax.scatter(z.annual_import_kwh/1000,z.reference_loss_cost_usd,s=28+z.annual_curtail_dc_kwh/22,c=col,alpha=.72,edgecolor="white",linewidth=.7)
        for label,idx in [("min cost",z.reference_loss_cost_usd.idxmin()),("min spill",z.annual_curtail_dc_kwh.idxmin()),("min imports",z.annual_import_kwh.idxmin())]:
            r=z.loc[idx];ax.annotate(label,(r.annual_import_kwh/1000,r.reference_loss_cost_usd),xytext=(5,7 if label!="min spill" else -14),textcoords="offset points",fontsize=8)
        ax.set_title(title);ax.set_xlabel("Grid imports (MWh/a)");ax.set_ylabel("Annual reference cost (USD)")
    return f
def fig43(d):
    z=d["gap"];f,a=canvas("113699 | Final reciprocal annual verification","Same signed hardware and profiles within each case; one severe nighttime failure retained (30 March 2025, 19:00).")
    labels=["6 homes • A0 → A1","4 homes • A1 → A0"];x=np.arange(2)
    for i,(pf,l,col,lab) in enumerate([(.98,1.,"#4e79a7","Reference"),(.95,1.6,"#d97706","Severe stress")]):
        q=z[(z.pf==pf)&(z.length_factor==l)].set_index("case").loc[["A0_113699_ss90_to_A1","A1_113699_min_cost_to_A0"]]
        bar(a[0],x+(i-.5)*.33,q.minimum_voltage_pu,col,lab,.3);bar(a[1],x+(i-.5)*.33,q.peak_transformer_pct,col,lab,.3)
        for k,r in enumerate(q.itertuples()):a[0].text(x[k]+(i-.5)*.33,r.minimum_voltage_pu+.0006,f"{r.strict_failures} fail",ha="center",fontsize=8)
    a[0].set_ylim(.942,.980);a[0].axhline(.95,color="#a62b2b",ls="--");a[0].set_ylabel("Minimum voltage (pu)");a[1].axhline(100,color="#a62b2b",ls="--");a[1].set_ylabel("Peak transformer loading (%)")
    for ax in a:ax.set_xticks(x,labels);ax.legend(fontsize=9)
    return f
def fig44(d):
    z=d["matched"];f,a=canvas("Controlled assignment comparison | Annual evidence by portfolio","Five modeled territories per portfolio; common hypothetical 92395 STAR. Pass counts include source overlays; not field certification.",2,(13,6.2))
    labs=[f"{r.hardware_origin} → {r.load_assignment} / {'MC' if r.tier=='min_cost' else 'SS90'}" for r in z.itertuples()]
    for ax,k,title in zip(a,["reference","stress"],["Reference PF .98, ×1","Severe PF .95, ×1.6"]):
        left=np.zeros(len(z))
        for sub,col,lab in [("passing","#007f83","Pass"),("failing","#c04b43","Fail"),("unresolved","#aab4bf","Unresolved")]:
            val=z[f"{k}_{sub}_territories"];ax.barh(labs,val,left=left,color=col,label=lab);left+=val
        ax.set_xlim(0,5);ax.set_xticks(range(6));ax.set_xlabel("Territories");ax.set_title(title);ax.invert_yaxis();ax.legend(loc="lower center",bbox_to_anchor=(.5,-.27),ncol=3,fontsize=8)
    f.subplots_adjust(bottom=.24,top=.82,left=.16)
    return f
def fig45(d):
    z=d["pareto"];f,a=canvas("34-house portfolio frontier | Separate physical alternatives","307 nondominated points within four geometry classes. Costs include modeled reference losses at $0.29/kWh; no infrastructure CAPEX.",2,(13,5.5))
    for key,q in z.groupby("geometry_family",sort=False):
        for ax,x,label in [(a[0],q.self_sufficiency_pct,"Self-sufficiency (%)"),(a[1],q.curtailment_dc_kwh/1000,"DC curtailment (MWh/a)")]:
            ax.scatter(x,q.reference_loss_purchase_cost_usd/1000,s=21,alpha=.75,c=COLORS[key],label=NAMES[key],edgecolor="none");ax.set_xlabel(label);ax.set_ylabel("Annual cost (thousand USD)")
    for ax in a:ax.legend(fontsize=8,loc="best")
    return f
def fig46(d):
    z=d["reps"];order=["MIN_REFERENCE_LOSS_COST","MIN_DC_CURTAILMENT","MAX_VOLTAGE_HEADROOM","MIN_REFERENCE_LOSS_COST_SS90","MIN_IMPORTS"]
    q=z[z.geometry_family.eq("MAPPED_HEAD")].set_index("selection").loc[order]
    f,ax=plt.subplots(2,2,figsize=(12,8));f.suptitle("A1 | Five decision-relevant investment strategies",x=.06,ha="left",fontsize=18,fontweight="bold")
    labels=["Min cost","Min spill","Headroom","≥90% SS","Min imports"];x=np.arange(5)
    for a,key,title,scale,col in zip(ax.ravel(),["reference_loss_purchase_cost_usd","imports_kwh","curtailment_dc_kwh","efc_physical_window"],["Annual cost (thousand USD)","Grid imports (MWh/a)","DC curtailment (MWh/a)","Equivalent battery cycles"],[1000,1000,1000,1],["#4e79a7","#007f83","#d97706","#b07aa1"]):
        v=q[key]/scale;a.bar(x,v,color=col,width=.65);a.set_xticks(x,labels,rotation=12,ha="right");a.set_title(title)
        for j,y in enumerate(v):a.text(j,y+max(v)*.018,f"{y:.1f}" if scale==1000 else f"{y:.0f}",ha="center",fontsize=9)
        a.set_ylim(0,max(v)*1.15)
    f.text(.06,.025,"Same 34 households; EFC is capacity-weighted physical-window throughput, not a degradation prediction. Infrastructure CAPEX excluded.",fontsize=8,color="#4b5563")
    f.subplots_adjust(left=.09,right=.96,top=.88,bottom=.13,wspace=.26,hspace=.48)
    return f
def fig47(d):
    z=d["candidates"];f,a=canvas("Electrical vulnerability | Territory bottlenecks remain after sizing","53 stress-qualified model candidates. Margins above 0.95 pu / below 100% loading; values are not probability or field measurements.",2,(12,5.7))
    territories=sorted(z.territory.unique())
    for ass,col,offset in [("A0","#4e79a7",-.12),("A1","#007f83",.12)]:
        q=z[z.assignment.eq(ass)]
        for idx,t in enumerate(territories):
            r=q[q.territory.eq(t)]
            for ax,key in [(a[0],"stress_voltage_margin_pu"),(a[1],"stress_transformer_margin_pct_points")]:
                ax.scatter(np.full(len(r),idx+offset),r[key],s=35,alpha=.68,color=col,label=ass if idx==0 else None)
    a[0].set_yscale("log");a[0].set_ylabel("Voltage margin (pu, log scale)");a[1].set_ylabel("Transformer loading margin (percentage points)")
    for ax in a:ax.set_xticks(range(len(territories)),[str(t) for t in territories]);ax.legend()
    return f
def fig48(d):
    r=d["reps"];h=d["headroom"];f,a=canvas("Adaptive capacity | Existing alternatives have limited headroom","Illustrative post-processing screens only, not new grid-code requirements. No outage or load-growth simulation.",2,(13,5.7))
    keys=list(NAMES);labs=[NAMES[k] for k in keys];q=r[r.selection.eq("MAX_VOLTAGE_HEADROOM")].set_index("geometry_family").loc[keys]
    vals=q.stress_voltage_margin_pu*1000
    a[0].barh(labs,vals,color=[COLORS[k] for k in keys]);a[0].axvline(1,color="#a62b2b",ls="--",label="0.951 pu screen");a[0].set_xlabel("Best voltage margin (millipu)");a[0].set_xlim(0,1.12);a[0].invert_yaxis();a[0].legend(fontsize=8)
    for i,v in enumerate(vals):a[0].text(max(v,.002)+.025,i,f"{v:.6f}",va="center",fontsize=8)
    tests=[(.95,100),(.951,100),(.95,99),(.951,99)];count=[int(h.loc[h.min_voltage_screen.eq(v)&h.max_trafo_screen.eq(t),"eligible"].sum()) for v,t in tests]
    a[1].barh(["Main limits","V ≥ .951","Loading ≤ 99%","Both tighter"],count,color=["#007f83","#aab4bf","#aab4bf","#aab4bf"]);a[1].invert_yaxis();a[1].set_xlabel("Eligible portfolios");a[1].set_xlim(0,3650)
    for i,v in enumerate(count):a[1].text(v+65,i,str(v),va="center")
    return f
def fig49(d):
    z=d["pareto"]
    f,a=canvas("Techno-economic Pareto trade-offs | Cost, imports, spill and battery use","Nondominated within each physical class; color = DC spill (left) or capacity-weighted equivalent cycles (right). CAPEX for network works excluded.",2,(13,5.8))
    markers={"MIDDLE_NO_R_CHANGE":"o","R050_CONDITIONAL":"s","OLDER_CONDITIONAL_FIVE_EDGE":"^","MAPPED_HEAD":"D"}
    for ax,key,label,cmap in [(a[0],"curtailment_dc_kwh","DC curtailment (MWh/a)","viridis"),(a[1],"efc_physical_window","Equivalent battery cycles","plasma")]:
        v=z[key]/(1000 if key=="curtailment_dc_kwh" else 1)
        norm=matplotlib.colors.Normalize(vmin=v.min(),vmax=v.max())
        for g,q in z.groupby("geometry_family",sort=False):
            ax.scatter(q.imports_kwh/1000,q.reference_loss_purchase_cost_usd/1000,c=q[key]/(1000 if key=="curtailment_dc_kwh" else 1),norm=norm,cmap=cmap,marker=markers[g],s=28,alpha=.8,label=NAMES[g],edgecolors="none")
        f.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap),ax=ax,label=label,pad=.02)
        ax.set_xlabel("Grid imports (MWh/a)");ax.set_ylabel("Annual reference cost (thousand USD)")
        ax.legend(fontsize=7,loc="best")
    return f
FUN={41:fig41,42:fig42,43:fig43,44:fig44,45:fig45,46:fig46,47:fig47,48:fig48,49:fig49}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path("."));ap.add_argument("--out",type=Path,required=True);ap.add_argument("--preflight-only",action="store_true");ap.add_argument("--emit-figure-bytes",action="store_true");args=ap.parse_args()
    d,receipts=load(args.repo_root.resolve())
    if args.preflight_only:
        print("WALKTHROUGH_PREFLIGHT="+json.dumps({"status":"PASS","sources":receipts,"figures":len(PLAN["figures"])},separators=(",",":")),flush=True);return
    args.out.mkdir(parents=True,exist_ok=False);outputs=[]
    for spec in PLAN["figures"]:
        fig=FUN[spec["number"]](d)
        for ext in ("png","svg"):
            path=args.out/(spec["stem"]+"."+ext);fig.savefig(path,dpi=160,metadata={"Date":None} if ext=="svg" else {"Software":"Matplotlib"});raw=path.read_bytes()
            if ext=="png" and not raw.startswith(b"\x89PNG\r\n\x1a\n"):raise ValueError("PNG header")
            if ext=="svg" and b"<svg" not in raw:raise ValueError("SVG header")
            outputs.append(dict(name=path.name,stage=spec["stage"],size=len(raw),sha256=sha(raw)))
        plt.close(fig)
    report={"status":"COMPLETE_STUDY_A_WALKTHROUGH_FIGURES","source_commit":PLAN["source_commit"],"sources":receipts,"figures":len(PLAN["figures"]),"files":outputs,"matplotlib":matplotlib.__version__,"new_solves":0}
    (args.out/"FIGURE_MANIFEST.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("WALKTHROUGH_REPORT="+json.dumps(report,separators=(",",":")),flush=True)
    if args.emit_figure_bytes:
        # Public research plot bytes only, no runner or environment secrets.
        for item in outputs:
            raw=(args.out/item["name"]).read_bytes();payload=base64.b64encode(raw).decode("ascii");chunks=[payload[i:i+4000] for i in range(0,len(payload),4000)]
            for i,chunk in enumerate(chunks):print("WALKTHROUGH_BYTES|"+item["name"]+"|"+str(i)+"|"+str(len(chunks))+"|"+chunk,flush=True)
if __name__=="__main__":main()
