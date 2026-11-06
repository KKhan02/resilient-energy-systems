#!/usr/bin/env python3
"""Case 12/106039 manufacturer-baseline AC sensitivity, without new SOC optimization.

Reuses the existing GIS network, coordinated Q control and saved 8,760-hour
manufacturer-DoD-constrained dispatch. All outputs are conditional engineering
screens, not measured EPM customer compliance. Never modifies source files.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import pandas as pd
from corridors import q_ratio_at_hour
from fixed_hardware import Hardware
from run_pilot import imported, filter_territory, CASE_HOUSE_IDS, CASE_FOLDERS
from validate_annual_ac import validate_trajectory, sha256
from validate_annual_ac_target import validate_manifest_against_hardware


def chosen_indices(ac: pd.DataFrame, hourly: pd.DataFrame, cutoff: float = .965,
                   top_n: int = 15) -> list[int]:
    """Select known weak/reference hours, not claimed to cover new-condition extremes."""
    if len(ac) != 8760 or len(hourly) != 8760:
        raise ValueError('Expected complete 8760-hour reference')
    if not (0 < cutoff < 1) or top_n < 1:
        raise ValueError('Invalid selection threshold or top_n')
    if not np.array_equal(pd.to_numeric(ac.hour_index,errors='raise').to_numpy(),np.arange(8760)):
        raise ValueError('Reference AC hours are not sequential')
    selection=set(ac.index[ac.min_v_pu <= cutoff].tolist())
    for col,ascending in [('min_v_pu',True),('max_v_pu',False),
                          ('max_trafo_pct',False),('max_line_pct',False)]:
        selection.update(ac.sort_values(col,ascending=ascending,kind='stable').index[:top_n].tolist())
    for col in ('demand_kw','inverter_ac_kw','grid_import_kw'):
        selection.update(hourly.sort_values(col,ascending=False,kind='stable').index[:top_n].tolist())
    ts=pd.to_datetime(hourly.timestamp_lst)
    for month in range(1,13):
        subset=ac.loc[ts.dt.month==month]
        if len(subset): selection.add(int(subset.min_v_pu.idxmin()))
    selection.update((0,8759))
    return sorted(selection)


def classify_records(records: pd.DataFrame, vmin:float=.95, vmax:float=1.05,
                     trafo_limit:float=100., line_limit:float=100.) -> dict:
    """Use actual converged AC magnitudes and thermal checks, not a prior label."""
    if not 0 < vmin < 1 < vmax or min(trafo_limit,line_limit)<=0:
        raise ValueError('Invalid limits')
    if records.empty: raise ValueError('No AC records')
    conv=records.status.eq('CONVERGED')
    ok=conv & records.min_v_pu.ge(vmin-1e-6) & records.max_v_pu.le(vmax+1e-6) & \
       records.max_trafo_pct.le(trafo_limit+1e-4) & records.max_line_pct.le(line_limit+1e-4)
    result={'hours':int(len(records)),'converged_hours':int(conv.sum()),
       'feasible_hours':int(ok.sum()),'failure_hours':int((~ok).sum()),
       'all_tested_hours_feasible':bool(ok.all()),
       'below_095_count':int((records.min_v_pu < .95-1e-6).sum()),
       'below_097_count':int((records.min_v_pu < .97-1e-6).sum()),
       'transformer_over_100_count':int((records.max_trafo_pct>100+1e-4).sum()),
       'line_over_100_count':int((records.max_line_pct>100+1e-4).sum())}
    if conv.any():
        c=records[conv]
        result.update(min_v_pu=float(c.min_v_pu.min()),max_v_pu=float(c.max_v_pu.max()),
           max_trafo_pct=float(c.max_trafo_pct.max()),max_line_pct=float(c.max_line_pct.max()))
    return result


def check_sources(manifest:dict, ref:dict, annual:pd.DataFrame,
                  trajectory:pd.DataFrame, mf:Path, trajectory_path:Path) -> None:
    if manifest.get('scenario') != 'twelve' or manifest.get('transformer')!='106039':
        raise ValueError('Only 12-house transformer 106039 manufacturer baseline accepted')
    if not manifest.get('full_year_pypsa_energy_and_soc_reoptimized'):
        raise ValueError('Manifest does not assert a new manufacturer SOC PyPSA solve')
    if manifest.get('nighttime_q_policy')!='off' or ref.get('nighttime_q')!='off':
        raise ValueError('Night-Q-off evidence required')
    if ref.get('scenario')!='twelve' or ref.get('transformer')!='106039' or ref.get('trajectory')!='manufacturer_baseline':
        raise ValueError('AC reference belongs to a different trajectory')
    if not(ref.get('all_8760_evaluated') and ref.get('ac_feasible_full_year')):
        raise ValueError('Reference annual AC study was incomplete or did not pass 0.95pu screen')
    if ref.get('source_pilot_manifest_sha256') != sha256(mf):
        raise ValueError('AC reference pilot manifest hash mismatch')
    if ref.get('source_trajectory_sha256') != sha256(trajectory_path):
        raise ValueError('AC reference trajectory hash mismatch')
    if manifest.get('source_trajectory_sha256') != sha256(trajectory_path):
        raise ValueError('Manufacturer source trajectory hash mismatch')
    if len(annual)!=8760 or len(trajectory)!=8760:
        raise ValueError('Full 8760 hours required')
    if not annual.status.eq('CONVERGED').all():
        raise ValueError('Reference AC table has unconverged hours')
    if not np.array_equal(pd.to_datetime(annual.timestamp).to_numpy(),
                          pd.to_datetime(trajectory.timestamp_lst).to_numpy()):
        raise ValueError('Timestamp misalignment')
    if abs(float(ref['voltage_screen']['min_v_pu'])-.95)>1e-8 or abs(float(ref['voltage_screen']['max_v_pu'])-1.05)>1e-8:
        raise ValueError('Expected previously established 0.95 to 1.05 engineering baseline')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--pilot-dir',type=Path,required=True,help='twelve_manufacturer_01')
    ap.add_argument('--annual-dir',type=Path,required=True,help='twelve_ac_full_02')
    ap.add_argument('--outdir',type=Path,required=True)
    ap.add_argument('--mode',choices=('critical','full'),default='critical')
    ap.add_argument('--power-factors',type=float,nargs='+',default=[.98,.95,.90])
    ap.add_argument('--service-factors',type=float,nargs='+',default=[1.,1.3,1.6])
    ap.add_argument('--vmin',type=float,default=.95)
    ap.add_argument('--vmax',type=float,default=1.05)
    ap.add_argument('--critical-voltage-cutoff',type=float,default=.965)
    ap.add_argument('--top-n',type=int,default=15)
    ap.add_argument('--q-grid-points',type=int,default=9)
    ap.add_argument('--q-refine',type=int,default=0)
    ap.add_argument('--reproduction-tolerance-pu',type=float,default=5e-5)
    args=ap.parse_args()
    if not(0<args.vmin<1<args.vmax) or not args.power_factors or any(not 0<x<=1 for x in args.power_factors):
        ap.error('Bad voltage limits or power factors')
    if not args.service_factors or any(x<1 for x in args.service_factors):ap.error('Service factors must be >=1')
    if args.q_grid_points<5 or not 0<=args.q_refine<=6 or args.top_n<1:ap.error('Invalid search settings')
    if args.reproduction_tolerance_pu<=0:ap.error('Invalid reproduction tolerance')
    repo=args.repo_root.resolve();pilot=args.pilot_dir.resolve();annual_dir=args.annual_dir.resolve();out=args.outdir.resolve()
    if not (repo/'.git').exists():ap.error('Use complete local GitLab checkout')
    if out.exists():ap.error('Output directory exists; choose a new one')
    mf=pilot/'pilot_manifest.json';tp=pilot/'fixed_hardware_manufacturer_soc_baseline.csv'
    apath=annual_dir/'annual_ac_hours.csv';sp=annual_dir/'annual_ac_summary.json'
    for p in (mf,tp,apath,sp):
        if not p.is_file():ap.error('Missing required source '+str(p))
    manifest=json.loads(mf.read_text(encoding='utf-8'))
    ref=json.loads(sp.read_text(encoding='utf-8'))
    ac=pd.read_csv(apath);hourly=pd.read_csv(tp)
    check_sources(manifest,ref,ac,hourly,mf,tp)
    saved=repo/'case1/studies/pypsa_joint_optimization_v1/outputs/full_study/shortlisted_hourly'/CASE_FOLDERS['twelve'][1]
    hw=Hardware.from_manifest(json.loads((saved/'model_manifest.json').read_text(encoding='utf-8')))
    validate_manifest_against_hardware(manifest,hw)
    (read_data,infer_assignments,build_territory,Territory,build_net,_,run_hour,load_source)=imported(repo)
    demand,_,_,_=load_source(repo,'twelve')
    validate_trajectory(hourly,demand,hw,float(manifest['manufacturer_min_soc_fraction']),tp.name)
    indices=chosen_indices(ac,hourly,args.critical_voltage_cutoff,args.top_n) if args.mode=='critical' else list(range(8760))
    from coordinated_q_control import ACLimits
    limits=ACLimits(args.vmin,args.vmax,100.,100.)
    houses,trafos,lv=read_data();assignments=infer_assignments(houses,trafos,lv,'base')
    out.mkdir(parents=True,exist_ok=False)
    pd.DataFrame({'hour_index':indices,'timestamp':hourly.timestamp_lst.iloc[indices].tolist()}).to_csv(out/'selected_hours.csv',index=False)
    summaries=[];start=time.monotonic()
    with (out/'sensitivity_ac_hours.csv').open('w',newline='',encoding='utf-8') as f:
        writer=None
        for factor in sorted(set(args.service_factors)):
            territory=build_territory('106039',houses,trafos,lv,assignments,factor)
            if territory is None:raise ValueError('No connected EPM GIS territory for 106039')
            territory=Territory(trafo={**territory.trafo,'kva':float(manifest['assumed_nameplate_kva'])},
                graph=territory.graph,attachments=territory.attachments,
                label=territory.label,root=territory.root,line_count=territory.line_count)
            territory,excluded=filter_territory('twelve',territory,Territory)
            if excluded or len(territory.attachments)!=12:raise ValueError('Unexpected candidate house associations')
            net,netmeta=build_net(territory,'head')
            for pf in sorted(set(args.power_factors),reverse=True):
                print(f'12 homes PF={pf} service x{factor}: {len(indices)} AC hours',flush=True)
                chunk=[]
                for ix in indices:
                    r=hourly.iloc[ix]
                    qratio=q_ratio_at_hour(float(r.pv_dc_available_kw),
                                          float(manifest['daylight_q_ratio']),night_q_allowed=False)
                    obs=run_hour(net,netmeta,territory,r,pf,'equal','head',qratio,'coordinated',
                        limits,hw.inverter_kva,hw.inverter_kva,args.q_grid_points,args.q_refine)
                    obs.update(hour_index=ix,service_factor=factor,
                        pv_dc_available_kw=float(r.pv_dc_available_kw),nighttime_q_disabled=(qratio==0))
                    if writer is None:
                        writer=csv.DictWriter(f,fieldnames=list(obs),extrasaction='ignore');writer.writeheader()
                    writer.writerow(obs);chunk.append(obs)
                    if abs(factor-1.)<1e-9 and abs(pf-float(hw.load_pf))<1e-9:
                        if obs['status']!='CONVERGED' or abs(float(obs['min_v_pu'])-float(ac.iloc[ix].min_v_pu))>args.reproduction_tolerance_pu:
                            raise RuntimeError('Baseline AC reproduction mismatch at hour '+str(ix))
                f.flush()
                summary=classify_records(pd.DataFrame(chunk),args.vmin,args.vmax)
                summary.update(load_pf=pf,service_factor=factor,scenario='twelve',transformer='106039',
                    mode=args.mode,full_year_evidence=bool(args.mode=='full' and len(indices)==8760))
                summaries.append(summary)
    pd.DataFrame(summaries).to_csv(out/'sensitivity_scenarios.csv',index=False)
    result={'status':'CONDITIONAL_GIS_AC_SENSITIVITY','scenario':'twelve','transformer':'106039',
       'mode':args.mode,'hours_per_scenario':len(indices),'scenarios':len(summaries),
       'voltage_target':{'min':args.vmin,'max':args.vmax},
       'reference_annual_summary_sha256':sha256(sp),'reference_annual_csv_sha256':sha256(apath),
       'source_manufacturer_trajectory_sha256':sha256(tp),'source_manifest_sha256':sha256(mf),
       'original_hourly_P_and_SOC_unchanged':True,'reoptimized_for_PF_or_service_length':False,
       'nighttime_Q_off':True,'reactive_P_and_Q_coupling_evaluated_in_pandapower':True,
       'feeder': 'balanced EPM GIS proxy, household service drops/phase and conductor impedance assumed',
       'runtime_seconds':round(time.monotonic()-start,2),
       'git_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=repo,text=True,capture_output=True).stdout.strip(),
       'conclusion_scope':'Full-year only in --mode full; critical mode is preliminary, not a pass proof'}
    (out/'robustness_manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(pd.DataFrame(summaries).to_string(index=False))
    print('Saved',out)


if __name__=='__main__':main()
