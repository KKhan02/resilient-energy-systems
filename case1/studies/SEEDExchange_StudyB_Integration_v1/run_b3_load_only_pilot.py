"""B3 pilot: load-only sampled AC using the original EPM balanced-equivalent builder."""
from pathlib import Path
from types import SimpleNamespace
import argparse,hashlib,json,math,sys
import numpy as np
import pandas as pd
import networkx as nx
import pandapower as pp
from pandapower.auxiliary import LoadflowNotConverged

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/"epm_gis_pandapower_v1"
sys.path.insert(0,str(ENGINE))
from run_epm_validation import build_net,ROOT_FACTOR,MV_V_KV,LV_V_KV
from epm_topology import conductor_params
from build_independent_b1 import SOURCES,BASE,verify

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,msg):
    if not ok:raise ValueError(msg)
def tables(path,receipt):
    d={}
    for name,digest in receipt["report"]["output_hashes"].items():
        check(sha(path/name)==digest,"hash mismatch "+name)
        d[name[:-4]]=pd.read_csv(path/name)
    return d

def select(d,u):
    picked={}
    peak=u[np.isclose(u.pf,.98)][["group_id","gross_peak_kva"]]
    d=d.merge(peak,on="group_id",validate="many_to_one")
    for n,z in d.groupby("house_count"):
        z=z.copy();z["median_distance"]=(z.cable_saving_pct-z.cable_saving_pct.median()).abs()
        choices=[
            ("MEDIAN_CABLE_SAVING",z.sort_values(["median_distance","site_id"]).iloc[0]),
            ("MAX_PATH_INCREASE",z.sort_values(["path_change_pct","site_id"],ascending=[False,True]).iloc[0]),
            ("MIN_MST_ABSOLUTE_PATH",z.sort_values(["longest_base_path_m_MST","site_id"]).iloc[0]),
            ("MAX_GROSS_PEAK",z.sort_values(["gross_peak_kva","total_base_m_MST","site_id"],ascending=[False,True,True]).iloc[0])]
        for reason,r in choices:
            item=picked.setdefault(r.site_id,dict(site_id=r.site_id,group_id=r.group_id,house_count=int(n),reasons=[]))
            item["reasons"].append(reason)
    return pd.DataFrame([{**v,"reasons":";".join(v["reasons"])} for v in picked.values()]).sort_values(["house_count","site_id"])

def graph_of(nodes,edges,factor,calibre):
    g=nx.Graph();names={};attach=[]
    for r in nodes.itertuples():
        h=None if pd.isna(r.house_id) or not str(r.house_id) else str(r.house_id)
        name="HOUSE_"+h if h else "SUPPLY"
        names[r.node_id]=name;g.add_node(name)
        if h:attach.append({"house":h})
    for e in edges.itertuples():
        a,b=names[e.from_node],names[e.to_node]
        check(a!=b and not g.has_edge(a,b) and e.base_length_m>0,"invalid edge")
        g.add_edge(a,b,length_m=float(e.base_length_m)*factor,kind="proposed_branch",source_fid=str(e.branch_id),material="AAC",calibre=calibre)
    check(nx.is_tree(g) and len(attach)==len({r["house"] for r in attach}),"invalid tree")
    return SimpleNamespace(graph=g,root=names["SUPPLY"],attachments=attach,trafo={"identifier":"B3_PROXY","kva":5.})

def select_hours(ng,edges_by_case,nodes_by_case,profiles):
    # Shared sample across both topologies, derived only from load and geometry.
    h=sorted(ng);X=profiles[h].to_numpy(float);ix={v:i for i,v in enumerate(h)}
    reasons={}
    def add(i,why):reasons.setdefault(int(i),set()).add(why)
    agg=X.sum(axis=1)
    for i in np.argsort(agg,kind="stable")[-3:]:add(i,"GROSS_TOP3")
    add(np.argmin(agg),"GROSS_MIN")
    for j,k in enumerate(h):add(np.argmax(X[:,j]),"HOUSE_PEAK_"+k)
    for cid,edges in edges_by_case.items():
        g=nx.DiGraph()
        for e in edges.itertuples():
            sub=str(e.downstream_house_ids).split(";")
            flow=X[:,[ix[k] for k in sub]].sum(axis=1)
            add(np.argmax(flow),"BRANCH_PEAK_"+cid)
            g.add_edge(e.from_node,e.to_node,weight=flow*float(e.base_length_m))
        check(nx.is_arborescence(g) and "SUPPLY" in g,"rooted geometry")
        check(set(g)==set(nodes_by_case[cid].node_id),"node mismatch")
        # First-order path weighted load proxy, not solved voltage.
        for node in g.nodes:
            if node=="SUPPLY":continue
            path=nx.shortest_path(g,"SUPPLY",node)
            z=sum((g[a][b]["weight"] for a,b in zip(path[:-1],path[1:])),start=np.zeros(len(X)))
            add(np.argmax(z),"PATH_STRESS_"+cid)
    return [(i,";".join(sorted(r))) for i,r in sorted(reasons.items())]

def solve(net,meta,values,pf):
    h=sorted(meta["loads"])
    for k in h:
        i=meta["loads"][k];p=float(values[k])*ROOT_FACTOR/1000
        net.load.at[i,"p_mw"]=p;net.load.at[i,"q_mvar"]=p*math.tan(math.acos(pf))
    check(float(net.sgen.p_mw.sum())==0 and float(net.sgen.q_mvar.sum())==0,"DER must remain off")
    try:
        pp.runpp(net,algorithm="bfsw",init="flat",calculate_voltage_angles=False,max_iteration=75,tolerance_mva=1e-8)
    except LoadflowNotConverged:
        return dict(converged=False,screen_pass=False,reason="NONCONVERGED")
    check(net.converged,"convergence flag")
    v=net.res_bus.loc[[meta["buses"]["HOUSE_"+k] for k in h],"vm_pu"].astype(float)
    tr=float(net.res_trafo.at[meta["trafo"],"loading_percent"])
    line=float(net.res_line.loc[meta["line_ids"],"loading_percent"].max())
    pext=float(net.res_ext_grid.p_mw.sum())*1000/ROOT_FACTOR
    qext=float(net.res_ext_grid.q_mvar.sum())*1000/ROOT_FACTOR
    losses=float(net.res_line.pl_mw.sum()+net.res_trafo.pl_mw.sum())*1000/ROOT_FACTOR
    p=float(sum(values[k] for k in h));resid=pext-p-losses
    check(np.isfinite([*v,tr,line,pext,qext,losses,resid]).all() and abs(resid)<.002,"AC balance/finite gate")
    low=float(v.min());high=float(v.max())
    passed=low>=.95-1e-8 and high<=1.05+1e-8 and tr<=100+1e-6 and line<=100+1e-6
    return dict(converged=True,screen_pass=passed,reason="PASS" if passed else "LIMIT_VIOLATION",
                min_voltage_pu=low,max_voltage_pu=high,trafo_loading_pct=tr,line_loading_pct=line,
                pcc_p_kw=pext,pcc_q_kvar=qext,loss_kw=losses,balance_residual_kw=resid,
                min_voltage_house=h[int(np.argmin(v.to_numpy()))])

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--repo-root",type=Path,default=Path("."));a.add_argument("--b1",type=Path,required=True)
    a.add_argument("--qualification",type=Path,required=True);a.add_argument("--out",type=Path,required=True)
    a.add_argument("--preflight-only",action="store_true");args=a.parse_args()
    root=args.repo_root.resolve();verify(root)
    b1=json.loads((HERE/"B1_RUN_3124217129_RECEIPT.json").read_text(encoding="utf-8"))
    q1=json.loads((HERE/"B1_QUALIFICATION_3124248027_RECEIPT.json").read_text(encoding="utf-8"))
    t=tables(args.b1,b1);q=tables(args.qualification,q1)
    check(ROOT_FACTOR==3 and abs(LV_V_KV/math.sqrt(3)-.24)<1e-12 and abs(MV_V_KV/math.sqrt(3)-7.621)<1e-12,"equivalent scale")
    check(conductor_params("AAC","4")== (3.3,.16,.095,True) and conductor_params("AAC","1/0")== (1.312,.16,.18,True),"registry changed")
    raw=pd.read_csv(root/(BASE+"household_profiles_2025_excel_35.csv"))
    m=pd.read_csv(root/(BASE+"fixed_house_to_profile_map.csv"))
    mapping=dict(zip(m.house,m.profile_column));profiles=pd.DataFrame({h:raw[col] for h,col in mapping.items()})
    check(profiles.shape==(8760,35) and np.allclose(profiles.sum(),1898,atol=1e-7,rtol=0),"frozen profiles")
    selected=select(q["paired_topology_tradeoffs"],q["unique_group_gross"])
    check(set(selected.house_count)==set(range(5,16)) and len(selected)<=44,"selection gate")
    c=t["network_cases"];roster=t["group_roster"];alln=t["network_nodes"];alle=t["network_branches"]
    conditions=[("REFERENCE",.98,1.),("SEVERE",.95,1.6)]
    records=[];hourrows=[]
    for item in selected.itertuples():
        cases=c[c.site_id.eq(item.site_id)].sort_values("topology")
        check(len(cases)==2 and set(cases.topology)=={"STAR","MST"},"matched pair")
        h=sorted(roster.loc[roster.group_id.eq(item.group_id),"house_id"])
        en={cid:alle[alle.case_id.eq(cid)] for cid in cases.case_id};no={cid:alln[alln.case_id.eq(cid)] for cid in cases.case_id}
        hours=select_hours(h,en,no,profiles)
        if args.preflight_only:hours=[(int(profiles[h].sum(axis=1).idxmax()),"SMOKE_GROSS_PEAK")]
        for i,reason in hours:hourrows.append(dict(site_id=item.site_id,hour_index=i,timestamp=raw.timestamp.iloc[i],selection_reason=reason))
        for case in cases.itertuples():
            for cond,pf,factor in (conditions[:1] if args.preflight_only else conditions):
                for calibre in (("4",) if args.preflight_only else ("4","1/0")):
                    territory=graph_of(no[case.case_id],en[case.case_id],factor,calibre)
                    check({a["house"] for a in territory.attachments}==set(h),"house mapping")
                    net,meta=build_net(territory,"head")
                    check(len(meta["loads"])==len(h) and len(meta["line_ids"])==len(en[case.case_id]),"builder counts")
                    for i,reason in hours:
                        vals=profiles.iloc[i]
                        r=solve(net,meta,vals,pf)
                        records.append(dict(site_id=item.site_id,group_id=item.group_id,case_id=case.case_id,
                            house_count=item.house_count,topology=case.topology,condition=cond,pf=pf,route_factor=factor,
                            conductor="AAC "+calibre,transformer_kva=5.,hour_index=i,timestamp=raw.timestamp.iloc[i],
                            gross_kw=float(vals[h].sum()),**r))
        if args.preflight_only:break
    check(len(records)>0,"no solves")
    if args.preflight_only:
        check(len(records)==2 and all(r["converged"] for r in records),"smoke convergence")
        print("B3_PREFLIGHT_JSON "+json.dumps(dict(status="PASS",selected_sites=len(selected),smoke=records)),flush=True);return
    z=pd.DataFrame(records);hr=pd.DataFrame(hourrows)
    check(len(z)==len(hr)*8 and not z.duplicated(["case_id","condition","conductor","hour_index"]).any(),"sample coverage")
    summary=[]
    for keys,r in z.groupby(["house_count","topology","condition","conductor"]):
        ok=r[r.converged]
        summary.append(dict(zip(["house_count","topology","condition","conductor"],keys))|dict(
            sampled_points=len(r),converged_points=len(ok),pass_points=int(r.screen_pass.sum()),
            min_voltage_pu=None if ok.empty else float(ok.min_voltage_pu.min()),
            peak_transformer_pct=None if ok.empty else float(ok.trafo_loading_pct.max()),
            peak_line_pct=None if ok.empty else float(ok.line_loading_pct.max()),
            max_sample_loss_kw=None if ok.empty else float(ok.loss_kw.max())))
    args.out.mkdir(parents=True,exist_ok=False)
    for name,d in [("selected_sites.csv",selected),("matched_critical_hours.csv",hr),("sampled_ac.csv",z),("sampled_summary.csv",pd.DataFrame(summary))]:d.to_csv(args.out/name,index=False)
    result=dict(status="COMPLETE_SAMPLED_LOAD_ONLY_AC",sites=len(selected),sampled_ac_solves=len(z),converged=int(z.converged.sum()),
                passed=int(z.screen_pass.sum()),failed=int((~z.screen_pass).sum()),LP_solves=0,annual_AC_solves=0,
                source_hashes={**b1["report"]["output_hashes"],**q1["report"]["output_hashes"]},
                engine_hashes={name:sha(ENGINE/name) for name in ("run_epm_validation.py","epm_topology.py","hil_voltvar.py","transformer_q_guard.py")},
                script_sha256=sha(Path(__file__)),pandapower=pp.__version__,summary=summary,
                output_hashes={f.name:sha(f) for f in args.out.glob("*.csv")})
    (args.out/"manifest.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("B3_PILOT_REPORT_JSON "+json.dumps(result,separators=(",",":")),flush=True)
if __name__=="__main__":main()
