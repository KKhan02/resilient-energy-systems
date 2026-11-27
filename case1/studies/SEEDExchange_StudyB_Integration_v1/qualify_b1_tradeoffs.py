"""B1 evidence qualification and matched geometric tradeoffs; no AC solves."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(ok, msg):
    if not ok:
        raise ValueError(msg)

def stats(s):
    return {k:float(v) for k,v in zip(("min","p25","median","p75","max"),np.quantile(s,[0,.25,.5,.75,1]))}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    prior=json.loads(Path(__file__).with_name("B1_RUN_3124217129_RECEIPT.json").read_text(encoding="utf-8"))["report"]
    actual=json.loads((a.input/"manifest.json").read_text(encoding="utf-8"))
    for k in ("source_hashes_expected","source_hashes_actual","topology_sha256","script_sha256","output_hashes","groups","partitions","sites","cases","screen_rows","branch_rows"):
        check(actual[k]==prior[k],f"replay mismatch: {k}")
    for name,digest in prior["output_hashes"].items():
        check(sha(a.input/name)==digest,f"table hash mismatch: {name}")
    t={name[:-4]:pd.read_csv(a.input/name) for name in prior["output_hashes"]}
    c=t["network_cases"]; g=t["group_roster"]; s=t["gross_screen"]; parts=t["partition_membership"]
    check(len(c)==3146 and c.case_id.is_unique,"case count")
    check(len(g.groupby("group_id"))==454 and not g.duplicated(["group_id","house_id"]).any(),"roster")
    check(len(s)==28314 and not s.duplicated(["case_id","pf","route_factor"]).any(),"screen count")
    check(set(s.ac_status)=={"NOT_RUN"},"AC claim")
    members=g.groupby("group_id").house_id.agg(set).to_dict()
    for pid,r in parts.groupby("partition_id"):
        h=[i for gid in r.group_id for i in members[gid]]
        expected={f"H{i:02}" for i in range(1,36)}
        if r.population.iloc[0]=="MATCHED34":expected.remove("H08")
        check(set(h)==expected and len(h)==len(expected),"partition integrity "+pid)
    w=c.pivot(index=["group_id","site_id","house_count"],columns="topology",values=["total_base_m","longest_base_path_m","peak_branch_kw"])
    d=pd.DataFrame(index=w.index).reset_index()
    for metric in ("total_base_m","longest_base_path_m","peak_branch_kw"):
        for topo in ("STAR","MST"):
            d[metric+"_"+topo]=w[(metric,topo)].to_numpy()
    d["cable_saving_pct"]=100*(1-d.total_base_m_MST/d.total_base_m_STAR)
    d["path_change_pct"]=100*(d.longest_base_path_m_MST/d.longest_base_path_m_STAR-1)
    d["branch_peak_change_kw"]=d.peak_branch_kw_MST-d.peak_branch_kw_STAR
    check(len(d)==1573 and (d.cable_saving_pct>=-1e-7).all(),"paired MST length")
    # Unique group per PF; route factor/site/topology cannot alter gross kVA.
    u=s.merge(c[["case_id","group_id","house_count"]],on="case_id",validate="many_to_one")
    metrics=["gross_peak_kva","gross_5kva_exceed_hours","annual_demand_kwh"]
    check((u.groupby(["group_id","pf"])[metrics].nunique()==1).all().all(),"gross invariance")
    u=u[["group_id","house_count","pf"]+metrics].drop_duplicates()
    out=[]
    for (n,pf),r in u.groupby(["house_count","pf"]):
        out.append({"house_count":int(n),"pf":float(pf),"groups":len(r),"groups_above_5kva":int((r.gross_5kva_exceed_hours>0).sum()),"peak_kva":stats(r.gross_peak_kva),"exceed_hours":stats(r.gross_5kva_exceed_hours)})
    # Nondominance only within identical group, three geometry/gross proxies, not AC or economics.
    front=[]
    cols=["total_base_m","longest_base_path_m","peak_branch_kw"]
    for gid,r in c.groupby("group_id"):
        x=r[cols].to_numpy(float)
        dominates=(x[:,None,:]<=x[None,:,:]+1e-9).all(axis=2)&(x[:,None,:]<x[None,:,:]-1e-9).any(axis=2)
        front.extend(r.loc[~dominates.any(axis=0),"case_id"].tolist())
    a.out.mkdir(parents=True,exist_ok=False)
    d.to_csv(a.out/"paired_topology_tradeoffs.csv",index=False)
    u.to_csv(a.out/"unique_group_gross.csv",index=False)
    c.assign(geometry_nondominated=c.case_id.isin(front)).to_csv(a.out/"candidate_geometry_front.csv",index=False)
    result={"status":"PASS_REPLAY_AND_GEOMETRY_TRADEOFFS_ONLY","verified_tables":7,"partition_count":len(parts.partition_id.unique()),"paired_sites":len(d),"geometry_nondominated_cases":len(front),"cable_savings_pct":stats(d.cable_saving_pct),"longest_path_change_pct":stats(d.path_change_pct),"branch_peak_change_kw":stats(d.branch_peak_change_kw),"by_N":[{"n":int(n),"sites":len(r),"cable_savings_pct":stats(r.cable_saving_pct),"path_change_pct":stats(r.path_change_pct),"branch_peak_change_kw":stats(r.branch_peak_change_kw)} for n,r in d.groupby("house_count")],"gross_by_N_PF":out,"AC_solves":0,"LP_solves":0}
    result["output_hashes"]={f.name:sha(f) for f in a.out.glob("*.csv")}
    (a.out/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("B1_TRADEOFF_REPORT_JSON "+json.dumps(result))
if __name__=="__main__":
    main()
