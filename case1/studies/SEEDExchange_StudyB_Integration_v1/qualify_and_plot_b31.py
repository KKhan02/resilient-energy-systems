"""Independent B31 archive qualification and Python figures. No power-flow or LP calls."""
from pathlib import Path
import argparse,base64,hashlib,json,zipfile,io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
LAYOUTS=["UNIFORM_AAC4","UNIFORM_AAC2","SHARED_AAC10_LEAF_AAC4","UNIFORM_AAC10"]
LABELS=["AAC 4","AAC 2","Mixed","AAC 1/0"]
FACTORS=["topology","condition","layout","transformer_kva"]
KEY=["site_id","hour_index"]+FACTORS
def require(x,msg):
    if not x: raise ValueError(msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def load(path,digest,receipt,prefix="",exclude=()):
    require(sha(path.read_bytes())==digest,"archive hash "+path.name)
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,"archive CRC")
        require(json.loads(z.read(prefix+"manifest.json"))==receipt,"manifest parity")
        tables={}
        for n,h in receipt["output_hashes"].items():
            if n in exclude: continue
            b=z.read(prefix+n);require(sha(b)==h,"table hash "+n)
            tables[n]=pd.read_csv(io.BytesIO(b))
    return tables
def eq(a,b,keys,cols):
    m=a.merge(b,on=keys,validate="one_to_one",suffixes=("_a","_b"))
    require(len(m)==len(a)==len(b),"coverage "+str(keys))
    for c in cols:
        x,y=m[c+"_a"],m[c+"_b"]
        if pd.api.types.is_numeric_dtype(x) and not pd.api.types.is_bool_dtype(x):
            require(np.allclose(x,y,rtol=1e-10,atol=1e-9,equal_nan=True),"numeric parity "+c)
        else: require((x.fillna("").astype(str)==y.fillna("").astype(str)).all(),"identity "+c)
def metrics(z,keys):
    out=[]
    for k,t in z.groupby(keys,sort=True):
        if not isinstance(k,tuple):k=(k,)
        c=t[t.converged];s=t.groupby("site_id").screen_pass.all()
        item=dict(zip(keys,k))
        item.update(points=len(t),converged=int(t.converged.sum()),passed=int(t.screen_pass.sum()),sites=len(s),all_sampled_pass_sites=int(s.sum()))
        for name,col in [("min_voltage_pu","min_voltage_pu"),("max_transformer_pct","trafo_loading_pct"),("max_line_pct","line_loading_pct"),("max_loss_kw","loss_kw")]:
            item[name]=None if c.empty else float(c[col].min() if name.startswith("min") else c[col].max())
        for name in ["NONCONVERGED","VOLTAGE_ONLY","THERMAL_ONLY","BOTH"]:item[name.lower()]=int(t.failure_class.eq(name).sum())
        out.append(item)
    return pd.DataFrame(out)
def contrast(z,axis):
    other=[k for k in KEY if k!=axis]
    dims=[k for k in FACTORS if k!=axis]
    pairs=[(5.,10.)] if axis=="transformer_kva" else [("UNIFORM_AAC4",x) for x in LAYOUTS[1:]]
    out=[]
    for a,b in pairs:
        m=z[z[axis].eq(a)].merge(z[z[axis].eq(b)],on=other,validate="one_to_one",suffixes=("_a","_b"))
        require(len(m)==len(z[z[axis].eq(a)])==len(z[z[axis].eq(b)]),"contrast count")
        for k,t in m.groupby(dims):
            both=t.converged_a&t.converged_b
            row=dict(zip(dims,k));row.update(axis=axis,base=str(a),alternative=str(b),points=len(t),both_converged=int(both.sum()),rescued=int((~t.screen_pass_a&t.screen_pass_b).sum()),lost=int((t.screen_pass_a&~t.screen_pass_b).sum()),both_pass=int((t.screen_pass_a&t.screen_pass_b).sum()),neither_pass=int((~t.screen_pass_a&~t.screen_pass_b).sum()))
            for c in ["min_voltage_pu","trafo_loading_pct","loss_kw"]:row["median_delta_"+c]=float((t.loc[both,c+"_b"]-t.loc[both,c+"_a"]).median())
            out.append(row)
    return pd.DataFrame(out)
def main():
    a=argparse.ArgumentParser();a.add_argument("--out",type=Path,required=True);a.add_argument("--emit",action="store_true");x=a.parse_args()
    rec=json.loads((HERE/"B31_RUN_3127147250_RECEIPT.json").read_text(encoding="utf-8"));r=rec["report"]
    require(r["new_ac_solves"]==14820 and r["logical_points"]==23712 and r["annual_AC_solves"]==r["LP_solves"]==0,"scope")
    b31=load(HERE/"outputs/b31_2026-11-28/B31_NUMERICAL_TABLES.zip",rec["archive"]["sha256"],r,exclude=("logical_screen.csv",))
    r3=json.loads((HERE/"B3_COMPLETE_3124340971_RECEIPT.json").read_text(encoding="utf-8"))["report"]
    require(r3["output_hashes"]==r["source_b3_hashes"] and r3["engine_hashes"]==r["engine_hashes"],"source identity")
    b3=load(HERE/"outputs/b3_qualified_2026-11-27/B3_SIGNED_NUMERICAL_TABLES.zip",r["source_archive_sha256"],r3,"b3/")
    old=b3["sampled_ac.csv"].copy();old["layout"]=old.conductor.map({"AAC 4":"UNIFORM_AAC4","AAC 1/0":"UNIFORM_AAC10"});old["origin"]="ARCHIVED_B3";old=old.drop(columns="conductor")
    new=b31["new_ac.csv"];require(len(new)==14820 and new.origin.eq("NEW_AC").all(),"new count")
    q=pd.concat([old,new],ignore_index=True);alias=q[q.topology.eq("STAR")&q.layout.eq("UNIFORM_AAC4")].copy();alias["layout"]="SHARED_AAC10_LEAF_AAC4";alias["origin"]="EXACT_STAR_LAYOUT_ALIAS"
    z=pd.concat([q,alias],ignore_index=True);require(len(old)==5928 and len(alias)==2964 and len(z)==23712 and not z.duplicated(KEY).any(),"matrix identity")
    require(set(z.topology)=={"STAR","MST"} and set(z.condition)=={"REFERENCE","SEVERE"} and set(z.layout)==set(LAYOUTS) and set(z.transformer_kva)=={5.,10.},"factor identity")
    h=b3["matched_critical_hours.csv"];require(len(h)==741 and z.site_id.nunique()==43 and (z.groupby(["site_id","hour_index"]).size()==32).all(),"full matrix")
    require(set(map(tuple,z[["site_id","hour_index"]].drop_duplicates().to_numpy()))==set(map(tuple,h[["site_id","hour_index"]].to_numpy())),"hour coverage")
    g=z.groupby(["site_id","hour_index"]);require(g.timestamp.nunique().eq(1).all() and (g.gross_kw.max()-g.gross_kw.min()).abs().max()<1e-9,"matched inputs")
    require(z.loc[z.condition.eq("REFERENCE"),"pf"].eq(.98).all() and z.loc[z.condition.eq("SEVERE"),"pf"].eq(.95).all() and z.loc[z.condition.eq("REFERENCE"),"route_factor"].eq(1).all() and z.loc[z.condition.eq("SEVERE"),"route_factor"].eq(1.6).all(),"conditions")
    c=z.converged;v=c&((z.min_voltage_pu<.95-1e-8)|(z.max_voltage_pu>1.05+1e-8));th=c&((z.trafo_loading_pct>100+1e-6)|(z.line_loading_pct>100+1e-6))
    require((z.screen_pass==(c&~v&~th)).all(),"limit parity")
    require(np.isfinite(z.loc[c,["min_voltage_pu","max_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw","balance_residual_kw"]]).all().all(),"finite outputs")
    residual=float(z.loc[c,"balance_residual_kw"].abs().max());require(residual<.002,"balance")
    z["failure_class"]=np.select([~c,v&th,v,th],["NONCONVERGED","BOTH","VOLTAGE_ONLY","THERMAL_ONLY"],default="PASS")
    factor=metrics(z,FACTORS);by_n=metrics(z,["house_count"]+FACTORS);by_site=metrics(z,["site_id","house_count"]+FACTORS)
    for name,t,keys in [("factor_summary.csv",factor,FACTORS),("house_count_summary.csv",by_n,["house_count"]+FACTORS),("site_summary.csv",by_site,["site_id","house_count"]+FACTORS)]:
        eq(t,b31[name],keys,[col for col in t if col not in keys])
    pair=pd.concat([contrast(z,"transformer_kva"),contrast(z,"layout")],ignore_index=True)
    for axis in ["transformer_kva","layout"]:
        keys=["axis","base","alternative"]+[k for k in FACTORS if k!=axis];aa=pair[pair.axis.eq(axis)].drop(columns=("transformer_kva" if axis=="transformer_kva" else "layout"));bb=b31["paired_contrasts.csv"];bb=bb[bb.axis.eq(axis)].drop(columns=("transformer_kva" if axis=="transformer_kva" else "layout"))
        eq(aa,bb,keys,[col for col in aa if col not in keys])
    lengths=b31["conductor_lengths.csv"];require(len(lengths)==43*32 and not lengths.duplicated(["site_id"]+FACTORS).any(),"length coverage")
    require((lengths[["aac4_m","aac2_m","aac10_m"]]>=0).all().all(),"negative length")
    lengths["total_m"]=lengths[["aac4_m","aac2_m","aac10_m"]].sum(axis=1)
    gg=lengths.groupby(["site_id","topology","condition"]);require((gg.total_m.max()-gg.total_m.min()).abs().max()<1e-6,"geometry changed")
    for layout,col in [("UNIFORM_AAC4","aac4_m"),("UNIFORM_AAC2","aac2_m"),("UNIFORM_AAC10","aac10_m")]:
        t=lengths[lengths.layout.eq(layout)];require(np.allclose(t[col],t.total_m,atol=1e-6,rtol=0),"uniform composition")
    t=lengths[lengths.layout.eq("SHARED_AAC10_LEAF_AAC4")];require(t.aac2_m.eq(0).all() and t[t.topology.eq("STAR")].aac10_m.eq(0).all(),"mixed composition")
    # Independent paired topology outcome, with logical aliases explicit.
    keys=["site_id","hour_index","condition","layout","transformer_kva"]
    m=z[z.topology.eq("STAR")].merge(z[z.topology.eq("MST")],on=keys,validate="one_to_one",suffixes=("_star","_mst"))
    require(len(m)==11856,"topology coverage");m["outcome"]=np.select([m.screen_pass_star&m.screen_pass_mst,m.screen_pass_star&~m.screen_pass_mst,~m.screen_pass_star&m.screen_pass_mst],["BOTH_PASS","STAR_ONLY","MST_ONLY"],default="NEITHER")
    topo=m.groupby(["condition","layout","transformer_kva","outcome"]).size().unstack(fill_value=0).reset_index()
    x.out.mkdir(parents=True,exist_ok=False)
    for n,t in [("qualified_factor",factor),("qualified_by_house_count",by_n),("qualified_site",by_site),("qualified_contrasts",pair),("qualified_topology",topo),("qualified_lengths",lengths)]:t.to_csv(x.out/(n+".csv"),index=False)
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"svg.hashsalt":"B31"})
    files=[]
    def save(fig,name):
        for ext in ["png","svg"]:
            f=x.out/(name+"."+ext);fig.savefig(f,dpi=160,bbox_inches="tight",metadata={"Date":None} if ext=="svg" else None);files.append(dict(name=f.name,size=f.stat().st_size,sha256=sha(f.read_bytes())))
        plt.close(fig)
    # 59: rating sensitivity, fixed layout and topology.
    fig,axs=plt.subplots(2,2,figsize=(11,7),layout="constrained",sharey=True)
    for ax,(tp,cond) in zip(axs.flat,[(t,c) for t in ["STAR","MST"] for c in ["REFERENCE","SEVERE"]]):
        sub=factor[(factor.topology==tp)&(factor.condition==cond)];xx=np.arange(4)
        for i,kva in enumerate([5.,10.]):
            t=sub[sub.transformer_kva.eq(kva)].set_index("layout").loc[LAYOUTS];ax.bar(xx+(i-.5)*.34,t.passed,width=.34,label=f"{kva:g} kVA")
        ax.set(xticks=xx,xticklabels=LABELS,title=f"{tp} | {cond.title()}",ylabel="Passing points (of 741)",ylim=(0,790));ax.legend()
    fig.suptitle("Study B3.1 | Transformer rating at fixed conductor and geometry\n43 sites; selected critical hours only; STAR mixed is AAC 4",fontsize=14);save(fig,"59_transformer_rating_sensitivity")
    # 60: exclusive failures at 10 kVA.
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout="constrained",sharey=True)
    for ax,cond in zip(axs,["REFERENCE","SEVERE"]):
        t=factor[(factor.transformer_kva==10)&(factor.condition==cond)].set_index(["topology","layout"]).loc[[(tp,l) for tp in ["STAR","MST"] for l in LAYOUTS]];bot=np.zeros(8)
        for col,label in [("passed","Pass"),("voltage_only","Voltage only"),("thermal_only","Thermal only"),("both","Both"),("nonconverged","Nonconvergence")]:
            ax.bar(range(8),t[col],bottom=bot,label=label);bot+=t[col].to_numpy()
        ax.set(xticks=range(8),xticklabels=[f"{tp}\n{l}" for tp in ["STAR","MST"] for l in LABELS],title=cond.title(),ylabel="Points (of 741)");ax.tick_params(axis="x",labelrotation=35)
    axs[1].legend(loc="upper left",bbox_to_anchor=(1,1));fig.suptitle("Study B3.1 | Remaining constraints at 10 kVA");save(fig,"60_conductor_and_failure_modes")
    # 61: same-site conductor composition; reference route and 5 kVA, no costs.
    t=lengths[(lengths.condition=="REFERENCE")&(lengths.transformer_kva==5)&(lengths.layout=="SHARED_AAC10_LEAF_AAC4")];fig,ax=plt.subplots(figsize=(12,5),layout="constrained")
    order=t[t.topology.eq("STAR")].sort_values("total_m").site_id.tolist();xx=np.arange(len(order))
    for i,tp in enumerate(["STAR","MST"]):
        tt=t[t.topology.eq(tp)].set_index("site_id").loc[order];off=xx+(i-.5)*.38;ax.bar(off,tt.aac4_m,.38,label=f"{tp} AAC 4");ax.bar(off,tt.aac10_m,.38,bottom=tt.aac4_m,label=f"{tp} AAC 1/0")
    ax.set(xlabel="Matched supply sites, sorted by STAR total length",ylabel="Hypothetical conductor route length (m)",title="Study B3.1 | Mixed conductor allocation by matched site");ax.legend(ncol=2);save(fig,"61_mixed_conductor_lengths")
    # 62: site-level coverage by group size at 10 kVA, denominator retained.
    fig,axs=plt.subplots(2,2,figsize=(11,7),layout="constrained",sharey=True)
    for ax,(tp,cond) in zip(axs.flat,[(t,c) for t in ["STAR","MST"] for c in ["REFERENCE","SEVERE"]]):
        t=by_n[(by_n.topology==tp)&(by_n.condition==cond)&(by_n.transformer_kva==10)]
        for l,label in zip(LAYOUTS,LABELS):
            u=t[t.layout.eq(l)].sort_values("house_count");ax.plot(u.house_count,u.all_sampled_pass_sites/u.sites*100,marker="o",label=label)
        ax.set(title=f"{tp} | {cond.title()}",xlabel="Households",ylabel="Sites passing every sampled hour (%)",xticks=range(5,16),ylim=(-3,103));ax.legend(fontsize=8)
    fig.suptitle("Study B3.1 | Site coverage at 10 kVA (diagnostic sites, not annual probability)");save(fig,"62_site_coverage_by_house_count")
    # 63: length vs paired pass counts, no fabricated cost.
    fig,axs=plt.subplots(1,2,figsize=(11,5),layout="constrained",sharey=True)
    for ax,cond in zip(axs,["REFERENCE","SEVERE"]):
        t=by_site[(by_site.condition==cond)&(by_site.transformer_kva==10)].merge(lengths,on=["site_id","house_count"]+FACTORS,validate="one_to_one")
        for tp,mark in [("STAR","o"),("MST","^")]:
            for l,label in [("UNIFORM_AAC4","AAC 4"),("SHARED_AAC10_LEAF_AAC4","Mixed"),("UNIFORM_AAC10","AAC 1/0")]:
                if tp=="STAR" and label=="Mixed":continue
                u=t[(t.topology==tp)&(t.layout==l)];ax.scatter(u.total_m,u.passed/u.points*100,marker=mark,s=20,alpha=.65,label=f"{tp} {label}")
        ax.set(title=cond.title(),xlabel="Total route length (m)",ylabel="Sampled points passing (%)");ax.legend(fontsize=7)
    fig.suptitle("Study B3.1 | Physical route and electrical trade-offs at 10 kVA");save(fig,"63_route_feasibility_tradeoffs")
    report=dict(status="QUALIFIED_B31",logical_points=len(z),new_AC_solves=0,new_LP_solves=0,source_archive_sha256=rec["archive"]["sha256"],source_b3_sha256=r["source_archive_sha256"],max_balance_residual_kw=residual,converged=int(c.sum()),passed=int(z.screen_pass.sum()),failure_counts={str(k):int(v) for k,v in z.failure_class.value_counts().items()},topology_outcomes={str(k):int(v) for k,v in m.outcome.value_counts().items()},output_hashes={f.name:sha(f.read_bytes()) for f in x.out.glob("*.csv")},files=files,matplotlib=matplotlib.__version__)
    (x.out/"manifest.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8");print("B31_QUAL_REPORT_JSON "+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    if x.emit:
        for f in files:
            b=base64.b64encode((x.out/f["name"]).read_bytes()).decode();n=(len(b)+3999)//4000
            for i in range(n):print(f"B31_FIG_BYTES|{f['name']}|{i}|{n}|"+b[i*4000:(i+1)*4000],flush=True)
if __name__=="__main__":main()
