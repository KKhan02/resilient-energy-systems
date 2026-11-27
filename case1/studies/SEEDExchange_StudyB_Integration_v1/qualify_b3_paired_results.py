"""Post-process signed Study B B3 sampled AC results, without any new solves.
Run only against the completed B3 archive and its independently recovered trace receipt.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

def check(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--b3",type=Path,required=True)
    a.add_argument("--receipt",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    x=a.parse_args()
    receipt=json.loads(x.receipt.read_text(encoding="utf-8"))["report"]
    manifest=json.loads((x.b3/"manifest.json").read_text(encoding="utf-8"))
    check(manifest==receipt and manifest["status"]=="COMPLETE_SAMPLED_LOAD_ONLY_AC","manifest vs independent trace")
    check(manifest["annual_AC_solves"]==0 and manifest["LP_solves"]==0,"scope")
    tables={}
    for name,digest in manifest["output_hashes"].items():
        check(sha(x.b3/name)==digest,"hash mismatch "+name)
        tables[name[:-4]]=pd.read_csv(x.b3/name)
    z=tables["sampled_ac"]; h=tables["matched_critical_hours"];sites=tables["selected_sites"]
    check(len(sites)==43 and sites.site_id.is_unique and len(z)==8*len(h)==manifest["sampled_ac_solves"],"sample count")
    check(set(z.site_id)==set(sites.site_id) and not h.duplicated(["site_id","hour_index"]).any(),"sample sites")
    check(set(z.topology)=={"STAR","MST"} and set(z.condition)=={"REFERENCE","SEVERE"} and set(z.conductor)=={"AAC 4","AAC 1/0"},"factor coverage")
    keys=["site_id","hour_index","condition","conductor"]
    check(not z.duplicated(keys+["topology"]).any(),"duplicate paired result")
    check((z.groupby(["site_id","hour_index"]).size()==8).all(),"full per-hour factorial")
    check(set(map(tuple,z[["site_id","hour_index"]].drop_duplicates().to_numpy()))==set(map(tuple,h[["site_id","hour_index"]].to_numpy())),"hour list")
    check(int(z.converged.sum())==manifest["converged"] and int(z.screen_pass.sum())==manifest["passed"] and int((~z.screen_pass).sum())==manifest["failed"],"receipt counts")
    v=z[z.converged].copy()
    check(len(v)>0 and v.balance_residual_kw.abs().max()<.002,"power balance")
    check(np.isfinite(v[["min_voltage_pu","max_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw"]].to_numpy()).all(),"finite convergence")
    recalc=v.min_voltage_pu.ge(.95-1e-8)&v.max_voltage_pu.le(1.05+1e-8)&v.trafo_loading_pct.le(100+1e-6)&v.line_loading_pct.le(100+1e-6)
    check((recalc==v.screen_pass).all() and not z.loc[~z.converged,"screen_pass"].any(),"screen parity")
    smoke=json.loads(Path(__file__).with_name("B3_PREFLIGHT_3124290063_RECEIPT.json").read_text(encoding="utf-8"))["report"]["smoke"]
    for row in smoke:
        hit=z[(z.case_id==row["case_id"])&(z.condition==row["condition"])&(z.conductor==row["conductor"])&(z.hour_index==row["hour_index"])]
        check(len(hit)==1,"smoke missing")
        for key in ["min_voltage_pu","max_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw","balance_residual_kw"]:
            check(abs(float(hit.iloc[0][key])-row[key])<1e-8,"smoke mismatch "+key)
    # Keep simultaneous limit violations as separate Boolean flags; nonconvergence is distinct.
    z["undervoltage"]=z.converged & z.min_voltage_pu.lt(.95-1e-8)
    z["overvoltage"]=z.converged & z.max_voltage_pu.gt(1.05+1e-8)
    z["transformer_overload"]=z.converged & z.trafo_loading_pct.gt(100+1e-6)
    z["line_overload"]=z.converged & z.line_loading_pct.gt(100+1e-6)
    z["voltage_only"]=(z.undervoltage|z.overvoltage)&~z.transformer_overload&~z.line_overload
    z["thermal_only"]=(z.transformer_overload|z.line_overload)&~z.undervoltage&~z.overvoltage
    z["both_voltage_and_thermal"]=(z.undervoltage|z.overvoltage)&(z.transformer_overload|z.line_overload)
    dims=["site_id","group_id","house_count","hour_index","timestamp","condition","conductor","pf","route_factor"]
    metrics=["converged","screen_pass","gross_kw","min_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw"]
    l=z[z.topology.eq("STAR")][dims+metrics];r=z[z.topology.eq("MST")][dims+metrics]
    pair=l.merge(r,on=dims,suffixes=("_STAR","_MST"),validate="one_to_one")
    check(len(pair)*2==len(z) and np.allclose(pair.gross_kw_STAR,pair.gross_kw_MST,rtol=0,atol=1e-9),"paired common load")
    pair["both_converged"]=pair.converged_STAR&pair.converged_MST
    pair["pair_outcome"]=np.select([pair.screen_pass_STAR&pair.screen_pass_MST,pair.screen_pass_STAR&~pair.screen_pass_MST,~pair.screen_pass_STAR&pair.screen_pass_MST],["BOTH_PASS","STAR_ONLY","MST_ONLY"],default="NEITHER_PASS")
    for col in ["min_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw"]:
        pair["delta_"+col+"_MST_minus_STAR"]=(pair[col+"_MST"]-pair[col+"_STAR"]).where(pair.both_converged)
    # Conductor contrasts within a fixed topology/site/hour/condition.
    dims2=["site_id","group_id","house_count","hour_index","timestamp","condition","topology","pf","route_factor"]
    c=z[z.conductor.eq("AAC 4")][dims2+metrics].merge(z[z.conductor.eq("AAC 1/0")][dims2+metrics],on=dims2,validate="one_to_one",suffixes=("_AAC4","_AAC10"))
    check(len(c)*2==len(z) and np.allclose(c.gross_kw_AAC4,c.gross_kw_AAC10,atol=1e-9,rtol=0),"paired conductor load")
    c["both_converged"]=c.converged_AAC4&c.converged_AAC10
    c["rescued_by_lower_R"]=~c.screen_pass_AAC4&c.screen_pass_AAC10
    c["lost_pass"]=c.screen_pass_AAC4&~c.screen_pass_AAC10
    for col in ["min_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw"]:
        c["delta_"+col+"_AAC10_minus_AAC4"]=(c[col+"_AAC10"]-c[col+"_AAC4"]).where(c.both_converged)
    gkeys=["house_count","topology","condition","conductor"]
    summary=z.groupby(gkeys).agg(sampled_points=("screen_pass","size"),converged_points=("converged","sum"),pass_points=("screen_pass","sum"),
        undervoltage=("undervoltage","sum"),overvoltage=("overvoltage","sum"),transformer_overload=("transformer_overload","sum"),line_overload=("line_overload","sum"),
        voltage_only=("voltage_only","sum"),thermal_only=("thermal_only","sum"),both_voltage_and_thermal=("both_voltage_and_thermal","sum")).reset_index()
    summary["nonconverged"]=summary.sampled_points-summary.converged_points
    summary["pass_fraction_sampled"]=summary.pass_points/summary.sampled_points
    # Each site has different critical-hour counts. Report site-level pass as well as pooled point counts.
    site=z.groupby(gkeys+["site_id"]).agg(sampled_points=("screen_pass","size"),pass_points=("screen_pass","sum"),converged_points=("converged","sum"),min_voltage_pu=("min_voltage_pu","min"),peak_transformer_pct=("trafo_loading_pct","max"),max_sample_loss_kw=("loss_kw","max")).reset_index()
    site["all_sampled_pass"]=site.pass_points.eq(site.sampled_points)
    site["all_sampled_converged"]=site.converged_points.eq(site.sampled_points)
    check(int(z.screen_pass.sum()+z.voltage_only.sum()+z.thermal_only.sum()+z.both_voltage_and_thermal.sum()+(~z.converged).sum())==len(z),"exclusive failure accounting")
    x.out.mkdir(parents=True,exist_ok=False)
    for name,t in [("point_failure_flags",z),("paired_topology",pair),("paired_conductor",c),("failure_summary",summary),("site_summary",site)]:
        t.to_csv(x.out/(name+".csv"),index=False)
    report=dict(status="QUALIFIED_B3_PAIRED_SAMPLED_ANALYSIS",source_receipt=sha(x.receipt),source_hashes=manifest["output_hashes"],sampled_points=len(z),paired_points=len(pair),paired_conductor_points=len(c),paired_outcomes={str(k):int(v) for k,v in pair.pair_outcome.value_counts().items()},both_converged_topology=int(pair.both_converged.sum()),rescued_by_lower_R=int(c.rescued_by_lower_R.sum()),lost_pass=int(c.lost_pass.sum()),voltage_only=int(z.voltage_only.sum()),thermal_only=int(z.thermal_only.sum()),both_voltage_thermal=int(z.both_voltage_and_thermal.sum()),nonconverged=int((~z.converged).sum()),new_AC_solves=0,new_LP_solves=0,output_hashes={f.name:sha(f) for f in x.out.glob("*.csv")})
    report["max_balance_residual_kw"]=float(v.balance_residual_kw.abs().max())
    report["site_pass_counts"]=[dict(topology=str(k[0]),condition=str(k[1]),conductor=str(k[2]),sites=len(t),all_sampled_pass=int(t.all_sampled_pass.sum())) for k,t in site.groupby(["topology","condition","conductor"])]
    report["paired_by_factor"]=[dict(condition=str(k[0]),conductor=str(k[1]),pairs=len(t),both_converged=int(t.both_converged.sum()),outcomes={str(a):int(b) for a,b in t.pair_outcome.value_counts().items()}) for k,t in pair.groupby(["condition","conductor"])]
    report["conductor_by_factor"]=[dict(topology=str(k[0]),condition=str(k[1]),pairs=len(t),rescued=int(t.rescued_by_lower_R.sum()),lost=int(t.lost_pass.sum())) for k,t in c.groupby(["topology","condition"])]
    (x.out/"manifest.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("B3_PAIRED_REPORT_JSON "+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
if __name__=="__main__":main()
