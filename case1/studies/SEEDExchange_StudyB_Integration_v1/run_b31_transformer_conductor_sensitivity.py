"""Matched B3.1 transformer/conductor sensitivity; archived B3 is the baseline.
No annual AC, DER dispatch, equipment pricing or new siting claim.
"""
from pathlib import Path
import argparse,base64,hashlib,json,math,zipfile
import numpy as np
import pandas as pd
import pandapower as pp
from run_b3_load_only_pilot import HERE,ENGINE,ROOT_FACTOR,BASE,verify,tables,graph_of,build_net,solve,conductor_params

ARCHIVE=HERE/"outputs/b3_qualified_2026-11-27/B3_SIGNED_NUMERICAL_TABLES.zip"
ARCHIVE_HASH="96f2df6e1c73215f8701fd9822e0f4e65761de98026c4dd1a89cd80ae3bffa2c"
LAYOUTS=("UNIFORM_AAC4","UNIFORM_AAC2","UNIFORM_AAC10","SHARED_AAC10_LEAF_AAC4")
RATINGS=(5.,10.)
CONDS=(("REFERENCE",.98,1.),("SEVERE",.95,1.6))
KEY=["case_id","condition","layout","transformer_kva","hour_index"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,msg):
    if not ok:raise ValueError(msg)
def read_archive():
    check(sha(ARCHIVE)==ARCHIVE_HASH,"archive hash")
    r=json.loads((HERE/"B3_COMPLETE_3124340971_RECEIPT.json").read_text(encoding="utf-8"))["report"]
    q=json.loads((HERE/"B3_PAIRED_3124486343_RECEIPT.json").read_text(encoding="utf-8"))["report"]
    from io import BytesIO
    out={}
    with zipfile.ZipFile(ARCHIVE) as zz:
        for folder,expected in [("b3",r),("qualified",q)]:
            check(json.loads(zz.read(folder+"/manifest.json"))==expected,"archive manifest "+folder)
            for name,digest in expected["output_hashes"].items():
                raw=zz.read(folder+"/"+name)
                check(hashlib.sha256(raw).hexdigest()==digest,"archive table "+name)
                out[folder+"/"+name]=pd.read_csv(BytesIO(raw))
    check(pp.__version__==r["pandapower"],"pandapower version changed")
    for name,digest in r["engine_hashes"].items():check(sha(ENGINE/name)==digest,"engine hash "+name)
    return r,out
def make_territory(nodes,edges,factor,layout,rating):
    calibre={"UNIFORM_AAC4":"4","UNIFORM_AAC2":"2","UNIFORM_AAC10":"1/0","SHARED_AAC10_LEAF_AAC4":"4"}[layout]
    territory=graph_of(nodes,edges,factor,calibre)
    territory.trafo["kva"]=rating
    shared={str(e.branch_id) for e in edges.itertuples() if len(str(e.downstream_house_ids).split(";"))>=2}
    for _,_,d in territory.graph.edges(data=True):
        if layout=="SHARED_AAC10_LEAF_AAC4" and d["source_fid"] in shared:d["calibre"]="1/0"
        check(conductor_params("AAC",d["calibre"])[3],"unrecognized conductor")
    lengths={c:sum(float(d["length_m"]) for _,_,d in territory.graph.edges(data=True) if d["calibre"]==c) for c in ("4","2","1/0")}
    check(abs(sum(lengths.values())-float(edges.base_length_m.sum())*factor)<1e-6,"route length mismatch")
    return territory,lengths,shared
def normalize(r):
    return {k:(None if pd.isna(v) else v.item() if isinstance(v,np.generic) else v) for k,v in r.items()}
def failure_flags(z):
    c=z.converged
    z=z.copy()
    z["voltage_violation"]=c&((z.min_voltage_pu<.95-1e-8)|(z.max_voltage_pu>1.05+1e-8))
    z["thermal_violation"]=c&((z.trafo_loading_pct>100+1e-6)|(z.line_loading_pct>100+1e-6))
    z["failure_class"]=np.select([~c,z.screen_pass,z.voltage_violation&z.thermal_violation,z.voltage_violation,z.thermal_violation],["NONCONVERGED","PASS","BOTH","VOLTAGE_ONLY","THERMAL_ONLY"],default="INVALID")
    check(not z.failure_class.eq("INVALID").any(),"failure classification")
    return z
def summaries(z,keys):
    out=[]
    for k,t in z.groupby(keys,sort=True):
        if not isinstance(k,tuple):k=(k,)
        c=t[t.converged]
        sites=t.groupby("site_id").screen_pass.all()
        item={name:(v.item() if isinstance(v,np.generic) else v) for name,v in zip(keys,k)}
        item.update(points=len(t),converged=int(t.converged.sum()),passed=int(t.screen_pass.sum()),sites=len(sites),all_sampled_pass_sites=int(sites.sum()),min_voltage_pu=None if c.empty else float(c.min_voltage_pu.min()),max_transformer_pct=None if c.empty else float(c.trafo_loading_pct.max()),max_line_pct=None if c.empty else float(c.line_loading_pct.max()),max_loss_kw=None if c.empty else float(c.loss_kw.max()))
        item.update({name.lower():int(t.failure_class.eq(name).sum()) for name in ("NONCONVERGED","BOTH","VOLTAGE_ONLY","THERMAL_ONLY")})
        out.append(item)
    return out
def compare(z,axis):
    keys=["site_id","case_id","house_count","topology","condition","hour_index","layout","transformer_kva"]
    other=[k for k in keys if k!=axis]
    cols=["screen_pass","converged","min_voltage_pu","trafo_loading_pct","loss_kw"]
    if axis=="transformer_kva":
        pairs=[(5.,10.)]
    else:
        pairs=[("UNIFORM_AAC4",x) for x in LAYOUTS if x!="UNIFORM_AAC4"]
    out=[]
    for a,b in pairs:
        left=z[z[axis].eq(a)][other+cols]
        right=z[z[axis].eq(b)][other+cols]
        m=left.merge(right,on=other,suffixes=("_base","_new"),validate="one_to_one")
        check(len(m)==len(left)==len(right),"contrast coverage")
        dims=["topology","condition","layout"] if axis=="transformer_kva" else ["topology","condition","transformer_kva"]
        for k,t in m.groupby(dims):
            ppair=t.converged_base&t.converged_new
            same=t[ppair]
            d={name:(v.item() if isinstance(v,np.generic) else v) for name,v in zip(dims,k)}
            d.update(axis=axis,base=str(a),alternative=str(b),points=len(t),both_converged=int(ppair.sum()),rescued=int((~t.screen_pass_base&t.screen_pass_new).sum()),lost=int((t.screen_pass_base&~t.screen_pass_new).sum()),both_pass=int((t.screen_pass_base&t.screen_pass_new).sum()),neither_pass=int((~t.screen_pass_base&~t.screen_pass_new).sum()))
            for field in ("min_voltage_pu","trafo_loading_pct","loss_kw"):
                d["median_delta_"+field]=None if same.empty else float((same[field+"_new"]-same[field+"_base"]).median())
            out.append(d)
    return out
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--repo-root",type=Path,default=Path("."));a.add_argument("--b1",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True);a.add_argument("--preflight-only",action="store_true")
    x=a.parse_args();root=x.repo_root.resolve();verify(root)
    receipt,archive=read_archive()
    r1=json.loads((HERE/"B1_RUN_3124217129_RECEIPT.json").read_text(encoding="utf-8"))
    g=tables(x.b1,r1)
    sites=archive["b3/selected_sites.csv"];hours=archive["b3/matched_critical_hours.csv"];baseline=archive["b3/sampled_ac.csv"].copy()
    check(len(sites)==43 and len(hours)==741 and len(baseline)==5928,"B3 coverage")
    baseline["layout"]=baseline.conductor.map({"AAC 4":"UNIFORM_AAC4","AAC 1/0":"UNIFORM_AAC10"})
    check(baseline.layout.notna().all(),"baseline conductor")
    baseline["origin"]="ARCHIVED_B3"
    raw=pd.read_csv(root/(BASE+"household_profiles_2025_excel_35.csv"))
    m=pd.read_csv(root/(BASE+"fixed_house_to_profile_map.csv"))
    profiles=pd.DataFrame({r.house:raw[r.profile_column] for r in m.itertuples()})
    check(profiles.shape==(8760,35) and np.allclose(profiles.sum(),1898,atol=1e-7,rtol=0),"frozen profiles")
    check(conductor_params("AAC","4")== (3.3,.16,.095,True) and conductor_params("AAC","2")== (2.1,.16,.125,True) and conductor_params("AAC","1/0")== (1.312,.16,.18,True),"conductor registry changed")
    case_table=g["network_cases"];roster=g["group_roster"];nodes=g["network_nodes"];edges=g["network_branches"]
    records=[];length_rows=[];smokes=0;aliases=[]
    for item in sites.itertuples():
        cases=case_table[case_table.site_id.eq(item.site_id)].sort_values("topology")
        check(len(cases)==2 and set(cases.topology)=={"STAR","MST"},"matched pair")
        h=sorted(roster.loc[roster.group_id.eq(item.group_id),"house_id"])
        hs=hours[hours.site_id.eq(item.site_id)]
        check(len(h)==item.house_count and len(hs)>0,"site cohort/hours")
        check((hs.timestamp==raw.timestamp.iloc[hs.hour_index.to_numpy()].to_numpy()).all(),"hour identity")
        for case in cases.itertuples():
            no=nodes[nodes.case_id.eq(case.case_id)];en=edges[edges.case_id.eq(case.case_id)]
            for cond,pf,factor in CONDS:
                for rating in RATINGS:
                    for layout in LAYOUTS:
                        territory,lengths,shared=make_territory(no,en,factor,layout,rating)
                        check({a["house"] for a in territory.attachments}==set(h),"house mapping")
                        length_rows.append(dict(site_id=item.site_id,case_id=case.case_id,house_count=int(item.house_count),topology=case.topology,condition=cond,layout=layout,transformer_kva=rating,aac4_m=lengths["4"],aac2_m=lengths["2"],aac10_m=lengths["1/0"]))
                        if x.preflight_only and not (cond=="REFERENCE" and layout in ("UNIFORM_AAC4","UNIFORM_AAC2","SHARED_AAC10_LEAF_AAC4")):continue
                        if not x.preflight_only and rating==5 and layout in ("UNIFORM_AAC4","UNIFORM_AAC10"):continue
                        if not x.preflight_only and layout=="SHARED_AAC10_LEAF_AAC4" and case.topology=="STAR":
                            check(not shared,"STAR shared branch unexpected")
                            aliases.append((case.case_id,cond,rating))
                            continue
                        net,meta=build_net(territory,"head")
                        check(not meta["fallback_conductors"] and len(meta["loads"])==len(h),"net mapping")
                        check(abs(float(net.trafo.loc[meta["trafo"],"sn_mva"])-rating*ROOT_FACTOR/1000)<1e-12,"transformer rating")
                        chosen=hs if not x.preflight_only else hs.loc[hs.hour_index.eq(int(profiles[h].sum(axis=1).idxmax()))]
                        check(len(chosen)>0,"peak sample absent")
                        for row in chosen.itertuples():
                            i=int(row.hour_index);v=profiles.iloc[i];gross=float(v[h].sum())
                            original=baseline[(baseline.case_id==case.case_id)&(baseline.condition==cond)&(baseline.hour_index==i)]
                            check(len(original)==2 and np.allclose(original.gross_kw,gross,rtol=0,atol=1e-9),"baseline gross parity")
                            ans=solve(net,meta,v,pf)
                            if x.preflight_only and rating==5 and layout=="UNIFORM_AAC4":
                                old=original[original.layout.eq(layout)].iloc[0]
                                check(bool(old.converged)==ans["converged"] and bool(old.screen_pass)==ans["screen_pass"],"baseline regression")
                                if ans["converged"]:
                                    for k in ("min_voltage_pu","max_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw","balance_residual_kw"):check(abs(float(old[k])-ans[k])<1e-8,"baseline regression "+k)
                                smokes+=1
                            records.append(dict(site_id=item.site_id,group_id=item.group_id,case_id=case.case_id,house_count=int(item.house_count),topology=case.topology,condition=cond,pf=pf,route_factor=factor,layout=layout,transformer_kva=rating,hour_index=i,timestamp=str(row.timestamp),gross_kw=gross,origin="NEW_AC",**ans))
        if x.preflight_only:break
    new=pd.DataFrame(records)
    if x.preflight_only:
        check(smokes==2 and len(new)==12 and new.converged.all(),"paired preflight")
        print("B31_PREFLIGHT_JSON "+json.dumps(dict(status="PASS",baseline_regressions=smokes,diagnostic_solves=len(new)),allow_nan=False),flush=True);return
    check(len(new)==14820 and not new.duplicated(KEY).any(),"new solve count")
    z=pd.concat([baseline.drop(columns=["conductor"]),new],ignore_index=True)
    alias=[]
    for cid,cond,rating in aliases:
        t=z[(z.case_id==cid)&(z.condition==cond)&(z.transformer_kva==rating)&(z.layout=="UNIFORM_AAC4")].copy()
        check(len(t)>0,"alias source")
        t["layout"]="SHARED_AAC10_LEAF_AAC4";t["origin"]="EXACT_STAR_LAYOUT_ALIAS";alias.append(t)
    z=pd.concat([z,*alias],ignore_index=True)
    check(len(z)==23712 and not z.duplicated(KEY).any() and len(z[z.origin.eq("EXACT_STAR_LAYOUT_ALIAS")])==2964,"complete design matrix")
    check((z.groupby(["site_id","hour_index"]).size()==32).all(),"full site/hour factorial")
    z=failure_flags(z)
    check(float(z.loc[z.converged,"balance_residual_kw"].abs().max())<.002,"balance")
    factor=summaries(z,["topology","condition","layout","transformer_kva"])
    by_n=summaries(z,["house_count","topology","condition","layout","transformer_kva"])
    by_site=summaries(z,["site_id","house_count","topology","condition","layout","transformer_kva"])
    contrasts=compare(z,"transformer_kva")+compare(z,"layout")
    x.out.mkdir(parents=True,exist_ok=False)
    for name,t in [("new_ac.csv",new),("factor_summary.csv",pd.DataFrame(factor)),("house_count_summary.csv",pd.DataFrame(by_n)),("site_summary.csv",pd.DataFrame(by_site)),("paired_contrasts.csv",pd.DataFrame(contrasts)),("conductor_lengths.csv",pd.DataFrame(length_rows)),("logical_screen.csv",z)]:
        t.to_csv(x.out/name,index=False)
    manifest=dict(status="COMPLETE_B31_MATCHED_SENSITIVITY",source_archive_sha256=ARCHIVE_HASH,source_b3_hashes=receipt["output_hashes"],source_b1_hashes=r1["report"]["output_hashes"],engine_hashes=receipt["engine_hashes"],script_sha256=sha(Path(__file__)),pandapower=pp.__version__,new_ac_solves=len(new),archived_baseline_points=len(baseline),exact_alias_points=2964,logical_points=len(z),annual_AC_solves=0,LP_solves=0,factor_summary=factor,paired_contrasts=contrasts,output_hashes={p.name:sha(p) for p in x.out.glob("*.csv")})
    (x.out/"manifest.json").write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("B31_REPORT_JSON "+json.dumps(manifest,separators=(",",":"),allow_nan=False),flush=True)
    # Only export compact original new AC records + summaries. Logical matrix is reproducible with pinned baseline and exact aliases.
    bundle=x.out/"B31_NUMERICAL_TABLES.zip"
    with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zz:
        for f in sorted(x.out.glob("*.csv")):
            if f.name!="logical_screen.csv":zz.write(f,f.name)
        zz.write(x.out/"manifest.json","manifest.json")
    info=dict(name=bundle.name,size=bundle.stat().st_size,sha256=sha(bundle))
    print("B31_ARCHIVE_JSON "+json.dumps(info),flush=True)
    if info["size"]<=2200000:
        data=base64.b64encode(bundle.read_bytes()).decode("ascii");n=(len(data)+3999)//4000
        for i in range(n):print(f"B31_SOURCE_BYTES|{bundle.name}|{i}|{n}|"+data[4000*i:4000*(i+1)],flush=True)
    else:print("B31_ARCHIVE_TRACE_EXPORT_SKIPPED_SIZE; complete archive retained as CI artifact",flush=True)
if __name__=="__main__":main()
