#!/usr/bin/env python3
"""Independent year-long AC screening of manufacturer-SOC dispatch, with voltage bands.

Reads a completed manufacturer-baseline or redispatch folder. Controls/reactive
power evaluated with the existing GIS pandapower coordinated-Q implementation.
No new PyPSA energy solve; AC losses remain outside the optimization.
"""
from __future__ import annotations
import argparse
import csv
import json
import subprocess
from pathlib import Path
import pandas as pd
from corridors import q_ratio_at_hour
from fixed_hardware import Hardware
from run_pilot import imported, filter_territory, CASE_HOUSE_IDS, CASE_FOLDERS
from validate_annual_ac import validate_trajectory, summarize_ac, sha256
from voltage_band_protocol import validate_limits, reclassify_ac_hours


def validate_manifest_against_hardware(meta:dict, hw:Hardware):
    case=str(meta.get('scenario'))
    if case not in CASE_FOLDERS:
        raise ValueError('Unrecognized research reference case')
    expected_trafo,_=CASE_FOLDERS[case]
    if meta.get('transformer')!=expected_trafo or meta.get('selected_candidate_houses')!=list(CASE_HOUSE_IDS[case]):
        raise ValueError('Scenario/transformer/GIS candidate membership mismatch')
    if meta.get('nighttime_q_policy')!='off':
        raise ValueError('Only night-Q-off conservative model is supported')
    h=meta.get('hardware',{})
    for k in ['panels','battery_modules','battery_power_dc_kw','inverter_kva','transformer_kva']:
        if abs(float(h[k])-float(getattr(hw,k)))>1e-5:
            raise ValueError('Changed saved hardware '+k)
    if abs(float(meta['assumed_nameplate_kva'])-hw.transformer_kva)>1e-6:
        raise ValueError('Inconsistent assumed transformer rating')
    return case,expected_trafo


def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--repo-root',type=Path,default=Path('.'))
    pa.add_argument('--pilot-dir',type=Path,required=True,
                    help='Manufacturer-SOC baseline or feedback output, containing pilot_manifest.json')
    pa.add_argument('--trajectory',choices=['manufacturer_baseline','redispatched'],default='manufacturer_baseline')
    pa.add_argument('--outdir',type=Path,required=True)
    pa.add_argument('--vmin',type=float,default=.95,help='Research engineering reference; not legal supply tolerance')
    pa.add_argument('--vmax',type=float,default=1.05,help='Research engineering reference; not legal supply tolerance')
    pa.add_argument('--max-hours',type=int,default=0,help='0: full 8760; positive: preliminary smoke test only')
    pa.add_argument('--q-grid-points',type=int,default=9)
    pa.add_argument('--q-refine',type=int,default=0)
    args=pa.parse_args()
    try:validate_limits(args.vmin,args.vmax)
    except ValueError as exc:pa.error(str(exc))
    if not 0<=args.max_hours<=8760 or args.q_grid_points<5 or not 0<=args.q_refine<=6:
        pa.error('Invalid sampling settings')
    repo=args.repo_root.resolve();pilot=args.pilot_dir.resolve();out=args.outdir.resolve()
    if not (repo/'.git').exists():pa.error('Full local GitLab checkout required')
    if out.exists():pa.error('Output directory already exists; preserve original results')
    meta_file=pilot/'pilot_manifest.json'
    meta=json.loads(meta_file.read_text(encoding='utf8'))
    case=str(meta['scenario']);trafo,folder=CASE_FOLDERS[case]
    reference_manifest_path=repo/'case1/studies/pypsa_joint_optimization_v1/outputs/full_study/shortlisted_hourly'/folder/'model_manifest.json'
    hw=Hardware.from_manifest(json.loads(reference_manifest_path.read_text(encoding='utf8')))
    case,trafo=validate_manifest_against_hardware(meta,hw)
    src=pilot/('fixed_hardware_manufacturer_soc_baseline.csv' if args.trajectory=='manufacturer_baseline' else 'redispatched_hourly.csv')
    trajectory=pd.read_csv(src)
    (read_data,infer_assignments,build_territory,Territory,build_net,
      critical_indices,run_hour,load_source)=imported(repo)
    demand,pv_pu,ghi,source_input=load_source(repo,case)
    floor=float(meta['manufacturer_min_soc_fraction'])
    validate_trajectory(trajectory,demand,hw,floor,src.name)
    if meta.get('source_trajectory_sha256') and args.trajectory=='manufacturer_baseline':
        if sha256(src)!=meta['source_trajectory_sha256']:
            raise ValueError('Baseline trajectory source hash does not match its manifest')
    houses,trafos,lv=read_data()
    assignments=infer_assignments(houses,trafos,lv,'base')
    terr=build_territory(trafo,houses,trafos,lv,assignments,float(meta.get('service_factor',1.0)))
    if terr is None:raise ValueError('Missing mapped LV territory')
    terr=Territory(trafo={**terr.trafo,'kva':float(meta['assumed_nameplate_kva'])},
        graph=terr.graph,attachments=terr.attachments,label=terr.label,root=terr.root,line_count=terr.line_count)
    terr,excluded=filter_territory(case,terr,Territory)
    if len(terr.attachments)!=len(CASE_HOUSE_IDS[case]):
        raise ValueError('GIS customer membership differs from saved scenario')
    siting=meta.get('siting','head');allocation=meta.get('load_allocation','equal')
    if siting not in ('head','middle','end') or allocation not in ('equal','far_end_heavy'):
        raise ValueError('Unknown inverter siting or load allocation')
    net,acmeta=build_net(terr,siting)
    from coordinated_q_control import ACLimits
    limits=ACLimits(min_v=args.vmin,max_v=args.vmax,max_trafo_pct=100,max_line_pct=100)
    n=8760 if args.max_hours==0 else args.max_hours
    out.mkdir(parents=True,exist_ok=False)
    path=out/'annual_ac_hours.csv'
    writer=None
    with path.open('w',newline='',encoding='utf8') as f:
        for ix in range(n):
            r=trajectory.iloc[ix]
            qratio=q_ratio_at_hour(float(r.pv_dc_available_kw),
                  float(meta['daylight_q_ratio']),night_q_allowed=False)
            obs=run_hour(net,acmeta,terr,r,float(hw.load_pf),allocation,siting,
                  qratio,'coordinated',limits,hw.inverter_kva,hw.inverter_kva,
                  args.q_grid_points,args.q_refine)
            obs.update(hour_index=ix,pv_dc_available_kw=float(r.pv_dc_available_kw),
                       nighttime_q_disabled=(qratio==0.))
            if writer is None:
                writer=csv.DictWriter(f,fieldnames=list(obs),extrasaction='ignore')
                writer.writeheader()
            writer.writerow(obs)
            if (ix+1)%500==0:
                f.flush()
                print(f'AC screening: {ix+1}/{n} hours',flush=True)
    ac=pd.read_csv(path)
    summary=summarize_ac(ac,n)
    bands=reclassify_ac_hours(ac)
    bands.to_csv(out/'voltage_band_comparison.csv',index=False)
    passed=(ac.status.astype(str).eq('CONVERGED') & ac.ac_feasible.astype(str).str.lower().eq('true'))
    ac.loc[~passed].to_csv(out/'annual_ac_violating_hours.csv',index=False)
    ac.sort_values('min_v_pu',ascending=True,na_position='last').head(30).to_csv(out/'annual_ac_worst_voltage_hours.csv',index=False)
    summary.update({'scenario':case,'transformer':trafo,'trajectory':args.trajectory,
      'manufacturer_soc_floor':floor,'nighttime_q':'off',
      'daylight_q_ratio':float(meta['daylight_q_ratio']),'inverter_kva':hw.inverter_kva,
      'assumed_trafo_kva':hw.transformer_kva,
      'voltage_screen':{'min_v_pu':args.vmin,'max_v_pu':args.vmax,'thermal_limit_pct':100},
      'source_pilot_manifest_sha256':sha256(meta_file),
      'source_trajectory_sha256':sha256(src),
      'source_git_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=repo,
          capture_output=True,text=True).stdout.strip(),
      'full_year_pypsa_energy_and_soc_reoptimized_by_this_script':False,
      'source_trajectory_claims_full_year_reoptimization':bool(meta.get('full_year_pypsa_energy_and_soc_reoptimized',False)),
      'AC_losses_included_in_optimization':False,
      'GIS_HOUSE_ASSIGNMENTS':'PROVISIONAL',
      'results_are_field_certified':False,
      'source_is_full_year':n==8760,
      'interpretation':'Hourly AC magnitude screen on balanced GIS model; not compliance to duration-based regulation',
      'alternative_voltage_bands_are_postprocessing_only':True})
    (out/'annual_ac_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    print(json.dumps(summary,indent=2))
    print('Annual screen saved to',out)


if __name__=='__main__':main()
