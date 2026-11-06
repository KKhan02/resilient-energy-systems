#!/usr/bin/env python3
"""Conservative fixed-hardware / GIS AC-feedback redispatch research pilot.

Run FROM a complete local checkout of KKhan02/resilient-energy-systems, with
its PyPSA/pandapower environment installed. Existing results are read-only.

This is a pilot, NOT full-year AC verification. A sampled P interval is a
hypothesis: every redispatched P is revalidated with pandapower. Only tested
hours can be reported as verified and only under the assumed GIS network.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
import math
import numpy as np
import pandas as pd
from corridors import grid_points, choose_corridor, q_ratio_at_hour
from fixed_hardware import Hardware,solve_fixed
from scenario_membership import filter_territory, CASE_HOUSE_IDS, EXCLUDED_PROVISIONAL

CASE_FOLDERS={
    'seven': ('94022','seven_best_fixedPV_26panels'),
    'nine': ('94022','nine_best_fixedPV_34panels'),
    'twelve': ('106039','twelve_best_fixedPV_41panels'),
}


def json_write(path, obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False,default=str)+'\n',encoding='utf8')


def imported(repo):
    epm=repo/'case1/studies/epm_gis_pandapower_v1'
    pypsa=repo/'case1/studies/pypsa_joint_optimization_v1'
    if not (epm/'run_coordinated_q.py').is_file():
        raise FileNotFoundError('Missing existing EPM GIS controller in complete repository')
    if not (pypsa/'run.py').is_file():
        raise FileNotFoundError('Missing existing PyPSA model')
    sys.path.insert(0,str(epm));sys.path.insert(0,str(pypsa))
    from epm_topology import read_data,infer_assignments,build_territory,Territory
    from run_epm_validation import build_net,critical_indices
    from run_coordinated_q import run_hour
    from run import load_source
    return (read_data,infer_assignments,build_territory,Territory,build_net,
            critical_indices,run_hour,load_source)


def select_critical(df, func, top_n, max_hours):
    selected=func(df,top_n)
    if max_hours and max_hours<len(selected):
        # Stratified subset of the deterministic sorted critical-hour set.
        k=np.linspace(0,len(selected)-1,max_hours).round().astype(int)
        selected=sorted({selected[int(j)] for j in k})
    return selected


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--case',choices=list(CASE_FOLDERS),default='seven')
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--assumed-trafo-kva',type=float,default=5.)
    p.add_argument('--siting',choices=['head','middle','end'],default='head')
    p.add_argument('--load-allocation',choices=['equal','far_end_heavy'],default='equal')
    p.add_argument('--service-factor',type=float,default=1.)
    p.add_argument('--q-ratio',type=float,default=.25)
    p.add_argument('--night-q',choices=['off','idealized_on'],default='off')
    p.add_argument('--manufacturer-min-soc',type=float,default=0.20,
                   help='SE-G5.1 manufacturer-recommended physical minimum SOC (20%%).')
    p.add_argument('--p-grid-points',type=int,default=7)
    p.add_argument('--q-grid-points',type=int,default=9)
    p.add_argument('--q-refine',type=int,default=0)
    p.add_argument('--top-n',type=int,default=10)
    p.add_argument('--max-hours',type=int,default=12)
    args=p.parse_args()
    if not (0<args.assumed_trafo_kva and 0<=args.q_ratio<=1 and args.service_factor>=1
            and 0 <= args.manufacturer_min_soc < 1):
        p.error('Invalid rating, Q ratio or service factor')
    if args.p_grid_points<5 or args.q_grid_points<5 or args.max_hours<0 or args.top_n<1:
        p.error('Invalid number of sample points/hours')
    repo=args.repo_root.resolve()
    if not (repo/'.git').exists():
        p.error('Set --repo-root to the full local GitLab checkout')
    out=args.outdir.resolve()
    if out.exists():
        p.error('Output directory exists. Select a new directory to preserve prior results: '+str(out))
    read_data,infer_assignments,build_territory,Territory,build_net,critical_indices,run_hour,load_source=imported(repo)
    transformer,folder=CASE_FOLDERS[args.case]
    saved=repo/'case1/studies/pypsa_joint_optimization_v1/outputs/full_study/shortlisted_hourly'/folder
    m=json.loads((saved/'model_manifest.json').read_text(encoding='utf8'))
    hw=Hardware.from_manifest(m)
    if m['summary']['candidate_epm_node']!=('931076' if transformer=='94022' else '923494'):
        raise ValueError('Saved case node does not match selected transformer')
    if abs(hw.transformer_kva-args.assumed_trafo_kva)>1e-6:
        raise ValueError('Pilot fixes saved PyPSA nameplate. Run a separate explicit rating scenario instead of silently changing it.')
    if hw.export_policy!='zero':
        raise ValueError('This pilot supports the saved zero-export scenarios only')
    original=pd.read_csv(saved/'hourly_dispatch.csv',parse_dates=['timestamp_lst'])
    if len(original)!=8760 or original.timestamp_lst.isna().any():
        raise ValueError('Saved reference must be full-year with timestamps')
    demand,pv_pu,ghi,source=load_source(repo,args.case)
    if not np.allclose(original.demand_kw.to_numpy(float),demand.to_numpy(float),atol=1e-4):
        raise ValueError('Saved dispatch demand does not match the exact model input: do not continue')
    houses,trafos,lv=read_data()
    assignment=infer_assignments(houses,trafos,lv,'base')
    territory=build_territory(transformer,houses,trafos,lv,assignment,args.service_factor)
    if territory is None or not territory.attachments:
        raise ValueError('No mapped LV/houses for '+transformer)
    original_gis_kva=float(territory.trafo['kva'])
    territory=Territory(trafo={**territory.trafo,'kva':args.assumed_trafo_kva},
                        graph=territory.graph,attachments=territory.attachments,
                        label=territory.label,root=territory.root,line_count=territory.line_count)
    original_association_count=len(territory.attachments)
    territory,excluded_houses=filter_territory(args.case,territory,Territory)
    if len(territory.attachments)!=len(m['summary']['profile_indices']):
        raise ValueError('Saved synthetic profiles count differs from explicitly selected GIS scenario')
    if len(territory.attachments)!=len(CASE_HOUSE_IDS[args.case]):
        raise ValueError('Internal scenario membership size mismatch')
    net,meta=build_net(territory,args.siting)
    out.mkdir(parents=True)
    selected=select_critical(original,critical_indices,args.top_n,args.max_hours)
    (out/'selected_hours.csv').write_text('hour_index,timestamp_lst\n'+''.join(
        f'{i},{original.at[i,"timestamp_lst"]}\n' for i in selected),encoding='utf8')

    start=time.monotonic()
    raw=[];refs=[];band_rows=[];corridors={};unresolved=[]
    allow_night=args.night_q=='idealized_on'
    def evaluate(index, p_kw):
        row=original.iloc[index].copy()
        row['inverter_ac_kw']=float(p_kw)
        ratio=q_ratio_at_hour(float(row.pv_dc_available_kw),args.q_ratio,allow_night)
        r=run_hour(net,meta,territory,row,hw.load_pf,args.load_allocation,
                   args.siting,ratio,'coordinated',
                   __import__('coordinated_q_control').ACLimits(),
                   hw.inverter_kva,hw.inverter_kva,args.q_grid_points,args.q_refine)
        r.update(hour_index=index,pv_dc_available_kw=float(row.pv_dc_available_kw),
                 day_or_night_q_ratio=ratio,sampled_inverter_p_kw=float(p_kw))
        return r
    for ix in selected:
        row=original.iloc[ix]
        pref=float(row.inverter_ac_kw)
        base=evaluate(ix,pref)
        refs.append(base)
        if base['ac_feasible'] is True or str(base['ac_feasible'])=='True':
            # A reference P that already passes needs no new AC corridor for this hour.
            continue
        max_p=min(float(row.demand_kw),hw.inverter_kva)
        if pref>max_p+1e-5:
            raise ValueError('Saved zero-export reference P exceeds household demand or inverter rating')
        samples=[]
        for point in grid_points(max_p,pref,args.p_grid_points):
            obs=base if abs(point-pref)<1e-8 else evaluate(ix,point)
            raw.append(obs)
            samples.append((point,bool(obs['ac_feasible'])))
        selected_band=choose_corridor(samples,pref)
        if selected_band is None:
            unresolved.append(dict(hour_index=ix,timestamp_lst=str(row.timestamp_lst),
                                   reference_p_kw=pref,reason='NO_SAMPLED_AC_FEASIBLE_P_Q'))
        else:
            ts=pd.Timestamp(row.timestamp_lst)
            corridors[ts]=(selected_band.p_min_kw,selected_band.p_max_kw)
            band_rows.append(dict(hour_index=ix,timestamp_lst=str(ts),
                reference_p_kw=pref,lo_kw=selected_band.p_min_kw,
                hi_kw=selected_band.p_max_kw,feasible_samples=selected_band.sampled_feasible,
                extrapolated=False,continuous_interval_verified=False))
    pd.DataFrame(refs).to_csv(out/'ac_reference_hours.csv',index=False)
    pd.DataFrame(raw).to_csv(out/'ac_p_samples.csv',index=False)
    pd.DataFrame(band_rows).to_csv(out/'sampled_corridors.csv',index=False)
    pd.DataFrame(unresolved).to_csv(out/'unresolved_hours.csv',index=False)
    manifest={
        'label':'RESEARCH_PILOT_NOT_FIELD_VALIDATED',
        'reference_folder':str(saved.relative_to(repo)),
        'scenario':args.case,'transformer':transformer,
        'households':len(territory.attachments),'hardware':vars(hw),
        'gis_total_provisional_associations':original_association_count,
        'selected_candidate_houses':list(CASE_HOUSE_IDS[args.case]),
        'excluded_gis_candidate_houses':excluded_houses,
        'unresolved_alternative_houses':list(EXCLUDED_PROVISIONAL[args.case]),
        'household_specific_loads':'NOT_AVAILABLE; equal or far-end synthetic allocation',
        'manufacturer_battery_model':'Deye SE-G5.1 (HOMER XML)',
        'manufacturer_min_soc_fraction':args.manufacturer_min_soc,
        'battery_DOD_basis':'80pct recommended DoD, Deye SE-G5.1, not HOMER historical 10pct min SOC',
        'gis_recorded_nominal_field':original_gis_kva,
        'assumed_nameplate_kva':args.assumed_trafo_kva,
        'gis_balanced_three_phase_proxy':True,'service_assignments':'PROVISIONAL',
        'p_corridors_are_provisional':True,'ac_verified_full_year':False,
        'perfect_foresight':True,'bat_soc_model':'existing PyPSA Store e_cyclic; full-year 8760h',
        'nighttime_q_policy':args.night_q,'daylight_q_ratio':args.q_ratio,
        'reactive_device_losses_and_dc_link_drain':'NOT_MODELLED',
        'assumed_0_97_1_03_pu':'STUDY_LIMIT_NOT_OFFICIAL_EPM',
        'p_grid_points':args.p_grid_points,'q_grid_points':args.q_grid_points,
        'q_refine':args.q_refine,'selected_critical_hours':len(selected),
        'reference_failed_ac_hours':sum(not bool(r['ac_feasible']) for r in refs),
        'sampled_corridors':len(corridors), 'unresolved_hours':len(unresolved),
        'source_input':str(source.relative_to(repo)),
        'elapsed_ac_sampling_seconds':round(time.monotonic()-start,2),
        'limitation':'No actual LV phase/bus assignments, inverter-nighttime Q support, measured impedance, or full-year AC approval',
    }
    if unresolved:
        manifest['outcome']='HALTED_NO_AC_BANDS_FOR_SOME_HOURS'
        json_write(out/'pilot_manifest.json',manifest)
        raise SystemExit('Pilot found hours with no sampled feasible operating point. Results saved; no dispatch reoptimization claimed.')
    if not corridors:
        manifest['outcome']='NO_REDISPATCH_NEEDED_FOR_THE_SAMPLED_HOURS'
        json_write(out/'pilot_manifest.json',manifest)
        print('All sampled critical reference hours passed. No revised dispatch created.')
        return
    # Re-solve SAME fixed hardware without new corridors first. This separates
    # numerical/model reproducibility changes from the cost of AC constraints.
    # First reproduce original fixed-hardware dispatch without the newly enforced
    # manufacturer SOC floor. Do not silently compare different battery constraints.
    reference_recomputed,reference_summary=solve_fixed(repo,hw,demand,pv_pu,min_physical_soc=None)
    reference_recomputed.to_csv(out/'fixed_hardware_reference_soc_hourly.csv')
    manifest['reference_recomputed_annual_total_usd']=float(reference_summary['annual_total_usd'])
    manifest['reference_vs_saved_cost_difference_usd']=float(reference_summary['annual_total_usd']-hw.annual_total_usd)
    manifest['reference_versus_saved_needs_review']=abs(reference_summary['annual_total_usd']-hw.annual_total_usd)>1.0
    if manifest['reference_versus_saved_needs_review']:
        manifest['outcome']='HALTED_BASELINE_REPRODUCIBILITY_DIFF_GT_1USD'
        json_write(out/'pilot_manifest.json',manifest)
        raise SystemExit('Reference annual objective differs by >1 USD from saved reference; inspect before AC redispatch.')
    # Keep manufacturer SOC floor identical for the actual comparator scenarios.
    baseline,baseline_summary=solve_fixed(repo,hw,demand,pv_pu,min_physical_soc=args.manufacturer_min_soc)
    baseline.to_csv(out/'fixed_hardware_manufacturer_soc_baseline.csv')
    manifest['manufacturer_soc_baseline_annual_total_usd']=float(baseline_summary['annual_total_usd'])
    manifest['soc_floor_incremental_cost_usd_vs_historical_reference']=float(baseline_summary['annual_total_usd']-reference_summary['annual_total_usd'])
    revised,summary=solve_fixed(repo,hw,demand,pv_pu,corridors,min_physical_soc=args.manufacturer_min_soc)
    revised.to_csv(out/'redispatched_hourly.csv')
    checks=[]
    for ix in selected:
        # The evaluator pulls base demand from the exact saved reference row.
        new_row=original.iloc[ix].copy()
        new_row['inverter_ac_kw']=float(revised.iloc[ix].inverter_ac_kw)
        ratio=q_ratio_at_hour(float(new_row.pv_dc_available_kw),args.q_ratio,allow_night)
        obs=run_hour(net,meta,territory,new_row,hw.load_pf,args.load_allocation,
                     args.siting,ratio,'coordinated',__import__('coordinated_q_control').ACLimits(),
                     hw.inverter_kva,hw.inverter_kva,args.q_grid_points,args.q_refine)
        obs.update(hour_index=ix,redispatched_p_kw=float(new_row.inverter_ac_kw),
                   reference_p_kw=float(original.iloc[ix].inverter_ac_kw))
        checks.append(obs)
    pd.DataFrame(checks).to_csv(out/'redispatch_ac_validation_selected_hours.csv',index=False)
    nfail=sum(not bool(r['ac_feasible']) for r in checks)
    manifest['redispatch_annual_total_usd']=float(summary['annual_total_usd'])
    manifest['incremental_annual_total_usd_AC_only_vs_manufacturer_soc_baseline']=float(summary['annual_total_usd']-baseline_summary['annual_total_usd'])
    manifest['incremental_annual_total_usd_vs_saved_reference']=float(summary['annual_total_usd']-hw.annual_total_usd)
    manifest['redispatch_annual_grid_import_kwh']=float(summary['grid_import_kwh'])
    manifest['redispatch_self_sufficiency_pct']=float(summary['self_sufficiency_of_demand_pct'])
    manifest['redispatched_sampled_hours_failed_ac']=nfail
    manifest['outcome']='PILOT_SELECTED_HOURS_PASS' if nfail==0 else 'PILOT_SELECTED_HOURS_STILL_FAIL'
    manifest['next_gate']='Validate full 8760 AC hours and repeat with violations; study sample grid refinement and inverter device loss models'
    json_write(out/'pilot_manifest.json',manifest)
    print(manifest['outcome'],'saved to',out)


if __name__=='__main__':
    main()
