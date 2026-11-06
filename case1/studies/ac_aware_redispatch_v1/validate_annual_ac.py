#!/usr/bin/env python3
"""Independent 8,760-hour AC screening of an existing WP1 fixed-hardware trajectory.

Reads existing pilot outputs and EPM GIS models. Does not dispatch or modify SOC.
Conservative nighttime Q rule matches v1.1 of ac_aware_redispatch_v1.
The numerical results are conditional on the balanced GIS network and assumptions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from corridors import q_ratio_at_hour
from fixed_hardware import Hardware, physical_soc_floor_usable_kwh
from run_pilot import imported, filter_territory, CASE_HOUSE_IDS, CASE_FOLDERS


def validate_trajectory(data: pd.DataFrame, expected_demand, hardware: Hardware,
                        manufacturer_min_soc: float, source_name: str) -> None:
    """Reject mismatched or physically inconsistent trajectories before AC analysis."""
    required = {
        'timestamp_lst', 'demand_kw', 'pv_dc_available_kw', 'inverter_ac_kw',
        'battery_charge_dc_kw', 'battery_discharge_dc_kw', 'battery_soc_usable_kwh',
        'grid_import_kw', 'grid_export_kw', 'unserved_kw',
    }
    if not required.issubset(data.columns):
        raise ValueError(f'{source_name} missing columns: {sorted(required-set(data.columns))}')
    if len(data) != 8760:
        raise ValueError(f'{source_name}: expected all 8760 hours, got {len(data)}')
    ts = pd.to_datetime(data['timestamp_lst'], errors='coerce')
    year = pd.date_range('2025-01-01', periods=8760, freq='h')
    if ts.isna().any() or not ts.equals(pd.Series(year, name='timestamp_lst')):
        raise ValueError(f'{source_name}: timestamps do not cover ordered 2025 hourly series')
    numeric = data[list(required - {'timestamp_lst'})].apply(pd.to_numeric, errors='raise')
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f'{source_name}: non-finite numerical input')
    if not np.allclose(data.demand_kw.to_numpy(float), np.asarray(expected_demand,float), atol=1e-4, rtol=0):
        raise ValueError(f'{source_name}: demand differs from source data')
    if (data.unserved_kw > 1e-6).any():
        raise ValueError(f'{source_name}: nonzero ENS, cannot call zero-ENS reference')
    if hardware.export_policy == 'zero' and (data.grid_export_kw.abs() > 1e-6).any():
        raise ValueError(f'{source_name}: grid export conflicts with saved zero-export policy')
    if (data.inverter_ac_kw < -1e-6).any() or (data.inverter_ac_kw > hardware.inverter_kva+1e-5).any():
        raise ValueError(f'{source_name}: inverter P outside rating')
    ac_balance = data.inverter_ac_kw+data.grid_import_kw+data.unserved_kw-data.grid_export_kw-data.demand_kw
    if ac_balance.abs().max() > 1e-3:
        raise ValueError(f'{source_name}: energy-balance residual exceeds 1e-3 kW')
    floor = physical_soc_floor_usable_kwh(hardware.battery_modules, manufacturer_min_soc)
    if data.battery_soc_usable_kwh.min() < floor-1e-5:
        raise ValueError(f'{source_name}: battery violates manufacturer SOC floor')
    if data.battery_soc_usable_kwh.max() > hardware.battery_modules*(17.3/4)+1e-5:
        raise ValueError(f'{source_name}: battery exceeds reference usable capacity')
    if (data.battery_charge_dc_kw > 1e-6).mul(data.battery_discharge_dc_kw > 1e-6).any():
        raise ValueError(f'{source_name}: simultaneous charge and discharge')
    eta = float(np.sqrt(.95))
    e = data.battery_soc_usable_kwh.to_numpy(float)
    residue = e-np.roll(e,1)-eta*data.battery_charge_dc_kw.to_numpy(float)+data.battery_discharge_dc_kw.to_numpy(float)/eta
    if np.abs(residue).max() > 1e-3:
        raise ValueError(f'{source_name}: hourly cyclic SOC energy balance violated')


def summarize_ac(df: pd.DataFrame, hours: int) -> dict:
    ok = df['status'].astype(str).eq('CONVERGED')
    passed = df['ac_feasible'].astype(str).str.lower().eq('true') & ok
    converged = df.loc[ok]
    def extremum(name, which):
        if name not in converged or len(converged)==0:return None
        y=pd.to_numeric(converged[name],errors='coerce')
        return float(getattr(y,which)()) if y.notna().any() else None
    return {
        'hours_checked':len(df),
        'hours_requested':hours,
        'all_8760_evaluated':bool(len(df)==8760 and hours==8760),
        'converged_hours':int(ok.sum()),
        'ac_feasible_hours':int(passed.sum()),
        'ac_violation_or_failure_hours':int((~passed).sum()),
        'ac_feasible_full_year':bool(len(df)==hours==8760 and passed.all()),
        'min_voltage_pu':extremum('min_v_pu','min'),
        'max_voltage_pu':extremum('max_v_pu','max'),
        'max_trafo_loading_pct':extremum('max_trafo_pct','max'),
        'max_line_loading_pct':extremum('max_line_pct','max'),
        'sum_modelled_ac_losses_kwh':float(pd.to_numeric(converged.get('loss_kw',pd.Series(dtype=float)), errors='coerce').sum()),
    }


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--pilot-dir',type=Path,required=True,
                   help='Existing completed v1.1 pilot output directory (read-only)')
    p.add_argument('--outdir',type=Path,required=True,help='New non-existing output directory')
    p.add_argument('--trajectory',choices=('manufacturer_baseline','redispatched'),default='manufacturer_baseline')
    p.add_argument('--max-hours',type=int,default=0,help='0 means all 8760 (default); other values are diagnostic only')
    p.add_argument('--q-grid-points',type=int,default=9)
    p.add_argument('--q-refine',type=int,default=0)
    args=p.parse_args()
    if args.max_hours<0 or args.max_hours>8760 or args.q_grid_points<5 or not 0<=args.q_refine<=6:
        p.error('Invalid hour count or Q search settings')
    repo=args.repo_root.resolve();pilot=args.pilot_dir.resolve();out=args.outdir.resolve()
    if not (repo/'.git').exists():p.error('Repository root must contain .git')
    if out.exists():p.error('Output path exists; choose a fresh folder to preserve previous results')
    manifest_file=pilot/'pilot_manifest.json'
    if not manifest_file.exists():p.error('Missing v1.1 pilot manifest: '+str(manifest_file))
    m=json.loads(manifest_file.read_text(encoding='utf8'))
    case=str(m['scenario'])
    if case not in CASE_FOLDERS:p.error('Pilot case not recognized')
    trafo,folder=CASE_FOLDERS[case]
    if m.get('transformer')!=trafo:p.error('Pilot transformer mismatches selected case')
    if m.get('nighttime_q_policy')!='off':
        p.error('This annual-validation patch is for the agreed conservative night-Q-off pilot only')
    if m.get('selected_candidate_houses')!=list(CASE_HOUSE_IDS[case]):
        p.error('Pilot membership differs from the versioned case definition')
    ref_manifest_file=repo/'case1/studies/pypsa_joint_optimization_v1/outputs/full_study/shortlisted_hourly'/folder/'model_manifest.json'
    h=Hardware.from_manifest(json.loads(ref_manifest_file.read_text(encoding='utf8')))
    if abs(h.inverter_kva-float(m['hardware']['inverter_kva']))>1e-6:
        p.error('Hardware mismatch between source reference and pilot')
    filename='fixed_hardware_manufacturer_soc_baseline.csv' if args.trajectory=='manufacturer_baseline' else 'redispatched_hourly.csv'
    src=pilot/filename
    if not src.exists():p.error('Missing trajectory: '+str(src))
    df=pd.read_csv(src)
    (read_data,infer_assignments,build_territory,Territory,build_net,
     critical_indices,run_hour,load_source)=imported(repo)
    demand, pv_pu, ghi, rawpath=load_source(repo,case)
    floor=float(m['manufacturer_min_soc_fraction'])
    validate_trajectory(df,demand,h,floor,filename)
    houses,trafos,lv=read_data()
    ass=infer_assignments(houses,trafos,lv,'base')
    territory=build_territory(trafo,houses,trafos,lv,ass,float(m.get('service_factor',1.0)))
    if territory is None:raise ValueError('Missing valid EPM GIS topology')
    territory=Territory(trafo={**territory.trafo,'kva':float(m['assumed_nameplate_kva'])},
                        graph=territory.graph,attachments=territory.attachments,
                        label=territory.label,root=territory.root,line_count=territory.line_count)
    territory,excluded=filter_territory(case,territory,Territory)
    if len(territory.attachments)!=len(CASE_HOUSE_IDS[case]):
        raise ValueError('GIS membership mismatch')
    # Version 1.1 used 'head' and 'equal' as its defaults. Fail if pilot ever
    # specifies different assumptions instead of silently changing topology.
    if m.get('siting','head')!='head' or m.get('load_allocation','equal')!='equal':
        p.error('Only head/equal pilot assumptions are supported by this patch')
    net,meta=build_net(territory,'head')
    from coordinated_q_control import ACLimits
    limits=ACLimits()
    n=8760 if args.max_hours==0 else args.max_hours
    out.mkdir(parents=True)
    dest=out/'annual_ac_hours.csv'
    with dest.open('w',newline='',encoding='utf8') as f:
        writer=None
        for i in range(n):
            row=df.iloc[i]
            pv=float(row.pv_dc_available_kw)
            ratio=q_ratio_at_hour(pv,float(m['daylight_q_ratio']),False)
            obs=run_hour(net,meta,territory,row,float(h.load_pf),'equal','head',ratio,
                 'coordinated',limits,float(h.inverter_kva),float(h.inverter_kva),
                 args.q_grid_points,args.q_refine)
            obs['hour_index']=i
            obs['pv_dc_available_kw']=pv
            obs['nighttime_q_disabled']=bool(ratio==0.)
            if writer is None:
                writer=csv.DictWriter(f,fieldnames=list(obs.keys()),extrasaction='ignore')
                writer.writeheader()
            writer.writerow(obs)
            if (i+1)%500==0:
                f.flush()
                print(f'Checked {i+1}/{n} hours; partial results saved',flush=True)
    ac=pd.read_csv(dest)
    summary=summarize_ac(ac,n)
    summary.update({
        'scenario':case, 'transformer':trafo, 'trajectory':args.trajectory,
        'manufacturer_soc_floor':floor, 'nighttime_q':'off',
        'daylight_q_ratio':m['daylight_q_ratio'], 'inverter_kva':h.inverter_kva,
        'assumed_trafo_kva':m['assumed_nameplate_kva'],
        'GIS_HOUSE_ASSIGNMENTS':'PROVISIONAL',
        'AC_LIMITS':'0.97..1.03pu, <=100% transformer/line loading: study limits only',
        'source_pilot_manifest_sha256':sha256(manifest_file),
        'source_trajectory_sha256':sha256(src),
        'source_git_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=repo,
                 capture_output=True,text=True).stdout.strip(),
        'full_year_pypsa_energy_and_soc_reoptimized':False,
        'results_are_field_certified':False,
        'interpretation':'Conditional AC feasibility only. Losses in AC replay are not integrated into PyPSA dispatch/cost.',
    })
    (out/'annual_ac_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    bad=ac.loc[~(ac.status.astype(str).eq('CONVERGED') & ac.ac_feasible.astype(str).str.lower().eq('true'))].copy()
    bad.to_csv(out/'annual_ac_violating_hours.csv',index=False)
    smallest=ac.sort_values('min_v_pu',ascending=True,na_position='last').head(30)
    smallest.to_csv(out/'annual_ac_worst_voltage_hours.csv',index=False)
    print(json.dumps(summary,indent=2))
    print('Results:',out)

if __name__=='__main__':main()
