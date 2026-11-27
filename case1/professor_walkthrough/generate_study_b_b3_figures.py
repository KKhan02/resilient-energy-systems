"""Render B3 figures and export signed source archive, without new solves."""
import argparse,base64,hashlib,json,zipfile
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent/"studies"/"SEEDExchange_StudyB_Integration_v1"
PLAN=json.loads((HERE/"STUDY_B_B3_FIGURE_PLAN_2026-11-27.json").read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,msg):
    if not ok:raise ValueError(msg)
def read(folder,hashes):
    data={}
    for name,digest in hashes.items():
        check(sha(folder/name)==digest,"hash mismatch "+name)
        data[name[:-4]]=pd.read_csv(folder/name)
    return data
def setup(title,subtitle,rows,cols,size):
    f,a=plt.subplots(rows,cols,figsize=size,squeeze=False)
    f.suptitle(title,fontsize=15,fontweight="bold",y=.975)
    f.text(.5,.925,subtitle,ha="center",fontsize=9)
    f.subplots_adjust(left=.085,right=.96,top=.84,bottom=.15,wspace=.31,hspace=.39)
    return f,a.ravel()
def style(a,x,y):
    a.set_xlabel(x);a.set_ylabel(y);a.grid(alpha=.22);a.set_axisbelow(True)
def emit(tag,name,path):
    b=base64.b64encode(path.read_bytes()).decode("ascii");n=(len(b)+3999)//4000
    for i in range(n):print(f"{tag}|{name}|{i}|{n}|"+b[4000*i:4000*(i+1)],flush=True)
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--b3",type=Path,required=True);a.add_argument("--qualified",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True);a.add_argument("--emit",action="store_true");x=a.parse_args()
    receipt=STUDY/"B3_COMPLETE_3124340971_RECEIPT.json"
    r=json.loads(receipt.read_text(encoding="utf-8"))["report"]
    m=json.loads((x.b3/"manifest.json").read_text(encoding="utf-8"));check(m==r,"B3 manifest vs receipt")
    q=json.loads((x.qualified/"manifest.json").read_text(encoding="utf-8"))
    check(q["source_hashes"]==r["output_hashes"] and q["source_receipt"]==sha(receipt) and q["status"]=="QUALIFIED_B3_PAIRED_SAMPLED_ANALYSIS","qualified provenance")
    raw=read(x.b3,r["output_hashes"]);d=read(x.qualified,q["output_hashes"])
    z=d["point_failure_flags"];pair=d["paired_topology"];c=d["paired_conductor"];s=d["failure_summary"];site=d["site_summary"]
    check(len(z)==5928 and len(pair)==len(c)==2964 and len(site)==344 and len(s)==88,"coverage")
    check(int(z.screen_pass.sum())==2645 and int(z.converged.sum())==5767,"result count")
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"svg.hashsalt":"study-b-b3-v1"})
    ns=np.arange(5,16);labels=["STAR • AAC 1/0","STAR • AAC 4","MST • AAC 1/0","MST • AAC 4"]
    combinations=[("STAR","AAC 1/0"),("STAR","AAC 4"),("MST","AAC 1/0"),("MST","AAC 4")]
    conditions=("REFERENCE","SEVERE");cols=["#356aa0","#008779"];figs={}
    f,ax=setup("Study B | Load-only electrical feasibility","5,928 diagnostic AC points; 43 sites, 741 matched site-hours; no annual interpretation",2,2,(12,7.8))
    for j,cond in enumerate(conditions):
        a=ax[j];arr=np.array([s[(s.topology==top)&(s.conductor==con)&(s.condition==cond)].set_index("house_count").reindex(ns).pass_fraction_sampled.to_numpy()*100 for top,con in combinations])
        im=a.imshow(arr,aspect="auto",vmin=0,vmax=100,cmap="YlGnBu")
        a.set_xticks(range(len(ns)),ns);a.set_yticks(range(4),labels);a.set_title(cond.title()+" | sampled pass (%)")
        for i in range(4):
            for k,v in enumerate(arr[i]):a.text(k,i,f"{v:.0f}",ha="center",va="center",fontsize=7.6,color="white" if v>60 else "#111827")
        f.colorbar(im,ax=a,pad=.02,fraction=.04)
        a=ax[j+2]
        for (top,con),lab,col,ls in zip(combinations,labels,["#356aa0","#356aa0","#008779","#008779"],["-","--","-","--"]):
            t=raw["sampled_summary"];v=t[(t.topology==top)&(t.conductor==con)&(t.condition==cond)].set_index("house_count").reindex(ns)
            a.plot(ns,v.min_voltage_pu,marker="o",ms=3,ls=ls,color=col,label=lab)
        a.axhline(.95,color="#a62b2b",ls=":");a.set_xticks(ns);style(a,"Households per group","Minimum converged voltage (pu)");a.set_title(cond.title()+" | voltage minima");a.legend(fontsize=7)
    figs[55]=f
    f,ax=setup("Study B | Matched STAR versus MST differences","MST minus STAR; numerical differences only when both cases converge. Nonconvergent pairs remain in outcome counts.",2,2,(12,8))
    order=[(cond,con) for cond in conditions for con in ("AAC 1/0","AAC 4")];labs=["Ref.\n1/0","Ref.\n4","Severe\n1/0","Severe\n4"]
    for a,key,y in zip(ax[:3],["min_voltage_pu","trafo_loading_pct","loss_kw"],["Δ minimum voltage (pu)","Δ transformer loading (percentage points)","Δ network loss (kW)"]):
        v=[pair.loc[(pair.condition==cond)&(pair.conductor==con)&pair.both_converged,"delta_"+key+"_MST_minus_STAR"].dropna() for cond,con in order]
        a.boxplot(v,positions=range(4),showfliers=True,flierprops={"markersize":2,"alpha":.3});a.axhline(0,color="#626b73",ls=":");a.set_xticks(range(4),labs);style(a,"Condition / conductor",y)
    a=ax[3];bottom=np.zeros(4)
    for outcome,col in [("BOTH_PASS","#008779"),("STAR_ONLY","#356aa0"),("MST_ONLY","#d97706"),("NEITHER_PASS","#b4bbc3")]:
        v=np.array([int(((pair.condition==cond)&(pair.conductor==con)&(pair.pair_outcome==outcome)).sum()) for cond,con in order])
        a.bar(range(4),v,bottom=bottom,color=col,label=outcome.replace("_"," ").title());bottom+=v
    a.set_xticks(range(4),labs);style(a,"Condition / conductor","Matched pairs");a.legend(fontsize=8);figs[56]=f
    f,ax=setup("Study B | Conductor sensitivity","Uniform AAC 4 to AAC 1/0, same topology, site, load and condition; no conductor cost assigned.",1,2,(12,5.5))
    order2=[(top,cond) for top in ("STAR","MST") for cond in conditions];l2=["STAR\nRef.","STAR\nSevere","MST\nRef.","MST\nSevere"]
    a=ax[0];bottom=np.zeros(4)
    for name,col in [("both_pass","#008779"),("rescued","#356aa0"),("lost","#d97706"),("neither","#b4bbc3")]:
        vals=[]
        for top,cond in order2:
            t=c[(c.topology==top)&(c.condition==cond)];a4=t.screen_pass_AAC4;a10=t.screen_pass_AAC10
            m={"both_pass":a4&a10,"rescued":~a4&a10,"lost":a4&~a10,"neither":~a4&~a10}[name];vals.append(int(m.sum()))
        vals=np.asarray(vals);a.bar(range(4),vals,bottom=bottom,label=name.replace("_"," ").title(),color=col);bottom+=vals
    a.set_xticks(range(4),l2);style(a,"Matched case","Paired operating points");a.legend(fontsize=8)
    a=ax[1];vals=[c.loc[(c.topology==top)&(c.condition==cond)&c.both_converged,"delta_min_voltage_pu_AAC10_minus_AAC4"].dropna() for top,cond in order2]
    a.boxplot(vals,positions=range(4),showfliers=True,flierprops={"markersize":2,"alpha":.3});a.set_xticks(range(4),l2);a.axhline(0,color="#626b73",ls=":");style(a,"Matched case","Voltage improvement (pu)");figs[57]=f
    f,ax=setup("Study B | Site-level constraints and point failures","Site passes require every selected hour to pass. Point failures are mutually exclusive categories; not an annual probability.",1,2,(13,5.7))
    order3=[(top,cond,con) for top,con in combinations for cond in conditions]
    labs3=[f"{top} {con.split()[-1]}\n{cond.title()[:3]}" for top,cond,con in order3]
    a=ax[0];v=[int(site[(site.topology==top)&(site.condition==cond)&(site.conductor==con)].all_sampled_pass.sum()) for top,cond,con in order3]
    a.bar(range(8),v,color=["#356aa0"]*4+["#008779"]*4);a.set_ylim(0,43);a.set_xticks(range(8),labs3,rotation=35,ha="right");style(a,"Topology / conductor / condition","Sites passing all sampled hours (of 43)")
    for i,k in enumerate(v):a.text(i,k+.5,str(k),ha="center",fontsize=8)
    a=ax[1];bottom=np.zeros(8)
    for key,label,col in [("screen_pass","Pass","#008779"),("voltage_only","Voltage only","#e5a84b"),("thermal_only","Thermal only","#b66b59"),("both_voltage_and_thermal","Both limits","#8b648d"),("nonconverged","Nonconvergence","#646b73")]:
        v=[]
        for top,cond,con in order3:
            t=z[(z.topology==top)&(z.condition==cond)&(z.conductor==con)]
            v.append(int((~t.converged).sum()) if key=="nonconverged" else int(t[key].sum()))
        v=np.asarray(v);a.bar(range(8),v,bottom=bottom,color=col,label=label);bottom+=v
    check((bottom==741).all(),"mutually exclusive failure accounting")
    a.set_xticks(range(8),labs3,rotation=35,ha="right");style(a,"Topology / conductor / condition","Sampled points (of 741)");a.legend(fontsize=7);figs[58]=f
    x.out.mkdir(parents=True,exist_ok=False);files=[]
    for spec in PLAN["figures"]:
        f=figs[spec["number"]]
        for ext in ("png","svg"):
            path=x.out/(spec["stem"]+"."+ext);f.savefig(path,dpi=150,metadata={"Date":None} if ext=="svg" else {"Software":"Matplotlib"})
            rawbytes=path.read_bytes();check(rawbytes.startswith(b"\x89PNG\r\n\x1a\n") if ext=="png" else b"<svg" in rawbytes,"header")
            files.append(dict(name=path.name,stage=spec["stage"],size=len(rawbytes),sha256=sha(path)))
        plt.close(f)
    # Store immutable exact source bytes for future work without another runner replay.
    archive=x.out/"B3_SIGNED_NUMERICAL_TABLES.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zz:
        for name in sorted(r["output_hashes"]):zz.write(x.b3/name,"b3/"+name)
        zz.write(x.b3/"manifest.json","b3/manifest.json")
        for name in sorted(q["output_hashes"]):zz.write(x.qualified/name,"qualified/"+name)
        zz.write(x.qualified/"manifest.json","qualified/manifest.json")
    archiveinfo=dict(name=archive.name,size=archive.stat().st_size,sha256=sha(archive))
    result=dict(status="COMPLETE_B3_WALKTHROUGH_FIGURES",source_pipeline=PLAN["source_pipeline"],source_execution_commit=PLAN["source_execution_commit"],source_hashes=r["output_hashes"],qualified_hashes=q["output_hashes"],generator_sha256=sha(Path(__file__)),files=files,archive=archiveinfo,matplotlib=matplotlib.__version__,new_solves=0)
    (x.out/"FIGURE_MANIFEST.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("B3_FIGURE_REPORT_JSON "+json.dumps(result,separators=(",",":"),allow_nan=False),flush=True)
    if x.emit:
        for f in files:emit("B3_FIGURE_BYTES",f["name"],x.out/f["name"])
        emit("B3_SOURCE_BYTES",archive.name,archive)
if __name__=="__main__":main()
