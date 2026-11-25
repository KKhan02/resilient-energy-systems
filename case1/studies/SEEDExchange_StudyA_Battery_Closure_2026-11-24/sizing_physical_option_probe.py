#!/usr/bin/env python3
"""Compare existing-model inverter siting and previously studied hypothetical R*0.5 bundle.
Nine unresolved sampled factor-events; matched fixed power, night Q=0, no LP or annual claim.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import sizing_stress_p_probe as prior
import sizing_nine_factor as nf
import sizing_ac_followup as follow
import reserve_full_night as rn
from audit_battery_coverage import signed,read_json

SOURCE=Path("StudyA_94022_Stress_P_Probe_v1")
HASHES={"STRESS_P_CORRIDORS.csv":"4fd86089d5a90a5a3949190cd44b51b226301a07763ba2717aa90398c5779860",
"STRESS_P_PROBES.csv":"d7689fe04470047de318ccb388ae725321effc6284bac3d12979d3e595c6a947"}
REGISTER=Path("case1/studies/SEEDExchange_StudyA_94022_AllNine_Bundle_v1/CANDIDATE_BRANCH_REGISTER.csv")
REGISTER_HASH="63d16776d6989cce95fdbfefc99a81d33d2b9ec1760c41b9a9c087555f1f8192"
BUNDLE="svc007_004_gis014_011_016_R050"
OPTIONS=("head","middle","end","head_hypothetical_R050")

def prepare(repo):
    m=read_json(repo/SOURCE/"RUN_MANIFEST.json")
    if m["status"]!="COMPLETE_TARGETED_STRESS_P_DIAGNOSTIC" or m["regressions"]!=342 or m["probes"]!=3687:
        raise ValueError("Unexpected diagnostic receipt")
    for name,h in HASHES.items():
        nf.check_receipt_hash(repo/SOURCE/name,h,m["output_sha256"][name]);signed(repo/SOURCE/name,h)
    c=pd.read_csv(repo/SOURCE/"STRESS_P_CORRIDORS.csv",parse_dates=["timestamp_lst"])
    a=pd.read_csv(repo/SOURCE/"STRESS_P_PROBES.csv",parse_dates=["timestamp_lst"],keep_default_na=False)
    keys=["pf","length_factor","timestamp_lst"]
    if len(c)!=115 or c.duplicated(keys).any() or len(a)!=3687:
        raise ValueError("Source population changed")
    events=c[c.status.eq("NO_TESTED_FEASIBLE_POINT")].copy()
    if len(events)!=9 or events.timestamp_lst.nunique()!=5:
        raise ValueError("Unresolved event identity changed")
    signed(repo/REGISTER,REGISTER_HASH)
    reg=pd.read_csv(repo/REGISTER);reg=reg[reg.option.eq(BUNDLE)]
    if set(reg.line_index)!={7,4,14,11,16} or len(reg)!=5:
        raise ValueError("Historical bundle changed")
    v6,annual,x,_=prior.prepare(repo)
    return v6,annual,x,events,a,reg

def apply_bundle(net,reg,l):
    # Verify all branch identities before changing anything.
    for row in reg.itertuples():
        i=int(row.line_index);line=net.line.loc[i]
        if str(line["name"])!=row.line_name or {str(net.bus.at[int(line.from_bus),"name"]),str(net.bus.at[int(line.to_bus),"name"])}!={row.from_model_bus,row.to_model_bus}:
            raise ValueError("Historical branch identity mismatch")
        expected=float(row.original_length_m)*(l if row.kind=="ASSUMED_SERVICE" else 1.)
        if abs(float(line.length_km)*1000-expected)>1e-6 or abs(float(line.r_ohm_per_km)-float(row.original_r_ohm_per_km))>1e-9:
            raise ValueError("Historical branch impedance/length mismatch")
    net.line.loc[reg.line_index.tolist(),"r_ohm_per_km"]*=.5

def run(out,prepared,doc):
    import pandapower as pp
    import networkx as nx
    from run_epm_validation import build_net
    v6,annual,x,events,archive,reg=prepared
    common=x["cases"][0];f=x["frames"][common]
    rows=[];houses=[];paths=[];summary=[];regressions=0
    for e in events.itertuples():
        t=e.timestamp_lst;pf=float(e.pf);l=float(e.length_factor)
        terr=x["territories"][l]
        old=archive[archive.pf.eq(pf)&archive.length_factor.eq(l)&archive.timestamp_lst.eq(t)]
        cap=follow.power_ceiling(float(f.at[t,"demand_kw"]),x["hardware"][common])
        if len(old)!=21 or abs(cap-float(e.ceiling_kw))>1e-9 or not np.allclose(old.probe_p_kw,np.linspace(0,cap,21),rtol=0,atol=1e-10):
            raise ValueError("Source grid changed")
        for opt in OPTIONS:
            net,meta=build_net(terr,"head" if opt.startswith("head") else opt)
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity changed")
            if opt=="head_hypothetical_R050":apply_bundle(net,reg,l)
            local=[]
            for i,p in enumerate(np.linspace(0,cap,21)):
                q=follow.evaluate(v6,pp,net,meta,terr,x,common,t,pf,p=float(p))
                if not q["night_reactive_disabled"] or q["status"]!="CONVERGED":
                    raise ValueError("Unexpected AC failure/night policy")
                if opt=="head":
                    annual.exact_ac_regression(q,old.iloc[i].to_dict(),opt+" "+str(t));regressions+=1
                ok=rn.strict_point(q)
                volts={h:float(net.res_bus.at[meta["buses"]["HOUSE_"+h],"vm_pu"]) for h in sorted(meta["loads"])}
                worst=min(volts,key=volts.get)
                root_v=float(net.res_bus.at[meta["buses"][terr.root],"vm_pu"])
                base=dict(option=opt,pf=pf,length_factor=l,probe_index=i,probe_p_kw=float(p),inverter_node=meta["node"])
                rec=dict(q,**base,strict_feasible=ok,min_house=worst,root_voltage_pu=root_v,root_minus_worst_pu=root_v-volts[worst])
                local.append(rec);rows.append(rec)
                if i in (0,20):
                    for house,voltage in volts.items():
                        houses.append(dict(base,timestamp_lst=str(t),house=house,voltage_pu=voltage))
                    nodes=nx.shortest_path(meta["graph"],terr.root,"HOUSE_"+worst)
                    for j,(a,b) in enumerate(zip(nodes[:-1],nodes[1:])):
                        va=float(net.res_bus.at[meta["buses"][a],"vm_pu"]);vb=float(net.res_bus.at[meta["buses"][b],"vm_pu"])
                        paths.append(dict(base,timestamp_lst=str(t),worst_house=worst,edge_order=j,from_node=a,to_node=b,
                                          length_m=meta["graph"][a][b]["length_m"],from_v_pu=va,to_v_pu=vb,drop_pu=va-vb))
            feasible=[z for z in local if z["strict_feasible"]]
            best=max(local,key=lambda z:z["min_v_pu"])
            summary.append(dict(option=opt,pf=pf,length_factor=l,timestamp_lst=str(t),inverter_node=meta["node"],
                 grid_pass_count=len(feasible),first_tested_pass_p_kw=feasible[0]["probe_p_kw"] if feasible else np.nan,
                 best_tested_voltage_pu=best["min_v_pu"],best_voltage_p_kw=best["probe_p_kw"],
                 ceiling_voltage_pu=local[-1]["min_v_pu"],ceiling_min_house=local[-1]["min_house"],
                 ceiling_root_voltage_pu=local[-1]["root_voltage_pu"],ceiling_strict_pass=local[-1]["strict_feasible"]))
        print(pf,l,t,"complete",flush=True)
    for name,z in (("PHYSICAL_OPTION_PROBES.csv",rows),("PHYSICAL_OPTION_SUMMARY.csv",summary),("HOUSE_VOLTAGE_ENDPOINTS.csv",houses),("WORST_HOUSE_PATH_DROPS.csv",paths)):
        pd.DataFrame(z).to_csv(out/name,index=False)
    doc.update(status="COMPLETE_PHYSICAL_OPTION_SCREEN",head_regressions=regressions,probe_rows=len(rows),option_event_rows=len(summary),
       output_sha256={p.name:follow.sample.sha(p) for p in out.iterdir() if p.is_file() and p.name!="RUN_MANIFEST.json"})

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--out",type=Path);ap.add_argument("--preflight-only",action="store_true");a=ap.parse_args()
    if not a.preflight_only and (a.out is None or a.out.exists()):ap.error("Choose fresh output")
    prepared=prepare(a.repo_root.resolve())
    doc=dict(status="SIGNED_PHYSICAL_OPTION_PREFLIGHT_NO_SOLVES",events=9,options=list(OPTIONS),planned_probe_rows=756,
             planned_head_regressions=189,field_verified=False,annual_verified=False,no_new_LP=True,
             caveat="Existing GIS proxy, hypothetical relocation and R*0.5 on five historical branches; no physical upgrade specification or cost.")
    print(doc,flush=True)
    if a.preflight_only:return
    a.out.mkdir(parents=False);doc["status"]="INCOMPLETE_PHYSICAL_OPTION_SCREEN";follow.jsonsave(a.out/"RUN_MANIFEST.json",doc)
    try:run(a.out,prepared,doc)
    except Exception as e:
        doc["error"]=repr(e);follow.jsonsave(a.out/"RUN_MANIFEST.json",doc);raise
    follow.jsonsave(a.out/"RUN_MANIFEST.json",doc);print(doc,flush=True)

if __name__=="__main__":main()
