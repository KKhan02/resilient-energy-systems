"""Reconstruct B3 report from retained failed-job CSVs. No power-flow calls."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from run_b3_load_only_pilot import select,select_hours,tables,verify,BASE,ENGINE,HERE

def check(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--root",type=Path,default=Path("."));a.add_argument("--archive-root",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    args=a.parse_args();root=args.root.resolve();verify(root)
    b1=json.loads((HERE/"B1_RUN_3124217129_RECEIPT.json").read_text(encoding="utf-8"))
    q1=json.loads((HERE/"B1_QUALIFICATION_3124248027_RECEIPT.json").read_text(encoding="utf-8"))
    t=tables(args.archive_root/"study-b-b1",b1);q=tables(args.archive_root/"study-b-b1-qualification",q1)
    src=args.archive_root/"study-b-b3";names=["selected_sites.csv","matched_critical_hours.csv","sampled_ac.csv","sampled_summary.csv"]
    d={n:pd.read_csv(src/n) for n in names}
    selected=select(q["paired_topology_tradeoffs"],q["unique_group_gross"])
    pd.testing.assert_frame_equal(d[names[0]].reset_index(drop=True),selected.reset_index(drop=True),check_dtype=False)
    raw=pd.read_csv(root/(BASE+"household_profiles_2025_excel_35.csv"))
    m=pd.read_csv(root/(BASE+"fixed_house_to_profile_map.csv"))
    profiles=pd.DataFrame({h:raw[col] for h,col in zip(m.house,m.profile_column)})
    c=t["network_cases"];roster=t["group_roster"];alln=t["network_nodes"];alle=t["network_branches"]
    hourrows=[];expected=[]
    for item in selected.itertuples():
        cases=c[c.site_id.eq(item.site_id)].sort_values("topology")
        h=sorted(roster.loc[roster.group_id.eq(item.group_id),"house_id"])
        en={cid:alle[alle.case_id.eq(cid)] for cid in cases.case_id};no={cid:alln[alln.case_id.eq(cid)] for cid in cases.case_id}
        for i,reason in select_hours(h,en,no,profiles):
            hourrows.append(dict(site_id=item.site_id,hour_index=i,timestamp=raw.timestamp.iloc[i],selection_reason=reason))
            for case in cases.itertuples():
                for cond,pf,factor in [("REFERENCE",.98,1.),("SEVERE",.95,1.6)]:
                    for conductor in ("AAC 4","AAC 1/0"):
                        expected.append(dict(site_id=item.site_id,group_id=item.group_id,case_id=case.case_id,house_count=int(item.house_count),topology=case.topology,condition=cond,pf=pf,route_factor=factor,conductor=conductor,transformer_kva=5.,hour_index=i,timestamp=raw.timestamp.iloc[i],gross_kw=float(profiles.iloc[i][h].sum())))
    pd.testing.assert_frame_equal(d[names[1]].reset_index(drop=True),pd.DataFrame(hourrows),check_dtype=False)
    z=d[names[2]];e=pd.DataFrame(expected);keys=["case_id","condition","conductor","hour_index"]
    check(not z.duplicated(keys).any() and len(z)==len(e),"case coverage")
    pd.testing.assert_frame_equal(z[e.columns].sort_values(keys).reset_index(drop=True),e.sort_values(keys).reset_index(drop=True),check_dtype=False,rtol=0,atol=1e-9)
    v=z[z.converged];check(len(v)>0 and v.balance_residual_kw.abs().max()<.002,"balance")
    check(np.isfinite(v[["min_voltage_pu","max_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw"]].to_numpy()).all(),"finite converged")
    passed=v.min_voltage_pu.ge(.95-1e-8)&v.max_voltage_pu.le(1.05+1e-8)&v.trafo_loading_pct.le(100+1e-6)&v.line_loading_pct.le(100+1e-6)
    check((passed==v.screen_pass).all() and not z.loc[~z.converged,"screen_pass"].any(),"screen parity")
    summary=[]
    for keys,r in z.groupby(["house_count","topology","condition","conductor"]):
        ok=r[r.converged]
        summary.append(dict(zip(["house_count","topology","condition","conductor"],(int(keys[0]),str(keys[1]),str(keys[2]),str(keys[3]))))|dict(sampled_points=len(r),converged_points=len(ok),pass_points=int(r.screen_pass.sum()),min_voltage_pu=None if ok.empty else float(ok.min_voltage_pu.min()),peak_transformer_pct=None if ok.empty else float(ok.trafo_loading_pct.max()),peak_line_pct=None if ok.empty else float(ok.line_loading_pct.max()),max_sample_loss_kw=None if ok.empty else float(ok.loss_kw.max())))
    pd.testing.assert_frame_equal(d[names[3]].reset_index(drop=True),pd.DataFrame(summary),check_dtype=False,rtol=1e-10,atol=1e-10)
    # Original smoke point must be present and match its authenticated receipt.
    smoke=json.loads((HERE/"B3_PREFLIGHT_3124290063_RECEIPT.json").read_text(encoding="utf-8"))["report"]["smoke"]
    for row in smoke:
        hit=z[(z.case_id==row["case_id"])&(z.condition==row["condition"])&(z.conductor==row["conductor"])&(z.hour_index==row["hour_index"])]
        check(len(hit)==1,"smoke missing")
        for key in ["min_voltage_pu","max_voltage_pu","trafo_loading_pct","line_loading_pct","loss_kw","balance_residual_kw"]:
            check(abs(float(hit.iloc[0][key])-row[key])<1e-8,"smoke mismatch "+key)
    args.out.mkdir(parents=True,exist_ok=False)
    for name in names:(args.out/name).write_bytes((src/name).read_bytes())
    result=dict(status="COMPLETE_SAMPLED_LOAD_ONLY_AC",sites=len(selected),sampled_ac_solves=len(z),converged=int(z.converged.sum()),passed=int(z.screen_pass.sum()),failed=int((~z.screen_pass).sum()),LP_solves=0,annual_AC_solves=0,source_hashes={**b1["report"]["output_hashes"],**q1["report"]["output_hashes"]},recovered_from_job=18436937794,original_execution_commit="edc4a4dda1a81527fa7f3e7d3121f7d4bbcbb33f",recovery_script_sha256=sha(Path(__file__)),new_AC_solves=0,summary=summary,output_hashes={n:sha(args.out/n) for n in names})
    (args.out/"manifest.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("B3_PILOT_REPORT_JSON "+json.dumps(result,separators=(",",":"),allow_nan=False),flush=True)
if __name__=="__main__":main()
