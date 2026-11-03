#!/usr/bin/env python3
"""Validate canonical hourly dispatch with CONDITIONAL pandapower AC snapshots.

Seven/nine-house 94022 reuse original reference conditional_powerflow.make_network;
12-house unknown transformer uses EXPLICIT representative radial length scenarios.
No surveyed LV routing, split-phase/neutral check, utility approvals or new transformers.
"""
from __future__ import annotations
import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from run_integrated_dispatch import locate_repo,SOURCE_REL,HOUSES_REL


def selected_timestamps(h):
    """Deterministic, deduplicated critical AC snapshot selection."""
    if len(h)==0 or 'timestamp_lst' not in h.columns:
        raise ValueError('Expected canonical annual_dispatch_8760.csv')
    timestamps=pd.to_datetime(h.timestamp_lst)
    indices={0,len(h)-1}
    for col,which in [('demand_requested_kw','max'),('demand_requested_kw','min'),
                      ('pv_ac_kw','max'),('grid_import_kw','max'),('grid_export_kw','max'),
                      ('pcc_s_kva','max'),('soc_usable_kwh','min'),('soc_usable_kwh','max')]:
        if col in h:
            indices.add(int(h[col].idxmax() if which=='max' else h[col].idxmin()))
    for month in (1,4,7,10):
        for hour in (12,19):
            mask=(timestamps.dt.month==month)&(timestamps.dt.hour==hour)
            if mask.any():indices.add(int(np.flatnonzero(mask)[len(np.flatnonzero(mask))//2]))
    return sorted(indices)


def import_reference_network(repo):
    try:
        import pandapower as pp
    except ImportError as e:
        raise RuntimeError('pandapower is absent: install the pinned case1 legacy environment') from e
    path=Path(repo)/'case1/studies/conditional_94022_pv_bess/conditional_powerflow.py'
    spec=importlib.util.spec_from_file_location('_seed_existing_conditional_pp',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return pp,module


def make_parametric_12house(pp,houses,route_m):
    """The actual location is UNKNOWN: assume each independent radial LV route length.

    Uses archived 5kVA equivalent transformer and reference conductor parameters.
    This is a parametric electrical test, NOT an inferred 106039 transformer site.
    """
    n=pp.create_empty_network(f_hz=60,sn_mva=1)
    hvsrc=pp.create_bus(n,vn_kv=math.sqrt(3)*7.621)
    hv=pp.create_bus(n,vn_kv=math.sqrt(3)*7.621)
    lv=pp.create_bus(n,vn_kv=math.sqrt(3)*.240)
    pp.create_ext_grid(n,bus=hvsrc,vm_pu=1)
    pp.create_line_from_parameters(n,from_bus=hvsrc,to_bus=hv,length_km=.3542,
        r_ohm_per_km=.832,x_ohm_per_km=.4,c_nf_per_km=0,max_i_ka=.184)
    pp.create_transformer_from_parameters(n,hv_bus=hv,lv_bus=lv,sn_mva=.015,
        vn_hv_kv=math.sqrt(3)*7.621,vn_lv_kv=math.sqrt(3)*.240,
        vk_percent=3,vkr_percent=1.8,pfe_kw=.09,i0_percent=2.5,shift_degree=0)
    buses={};loads={};lines={}
    for h in houses:
        b=pp.create_bus(n,vn_kv=math.sqrt(3)*.240)
        l=pp.create_line_from_parameters(n,from_bus=lv,to_bus=b,length_km=route_m/1000,
            r_ohm_per_km=1.312,x_ohm_per_km=.16,c_nf_per_km=0,max_i_ka=.15)
        loads[h]=pp.create_load(n,bus=b,p_mw=0,q_mvar=0)
        buses[h]=b;lines[h]=l
    sgen=pp.create_sgen(n,bus=lv,p_mw=0,q_mvar=0)
    return n,buses,loads,lines,[sgen]


def ac_run(repo,hourly_csv,outdir,mode='critical',routes=('euclidean','rectilinear'),
           assumed_lengths=(75.,150.,325.),pf=.98):
    pp,ref=import_reference_network(repo)
    df=pd.read_csv(hourly_csv,parse_dates=['timestamp_lst'])
    if len(df)!=8760 or df.timestamp_lst.duplicated().any() or not df.timestamp_lst.is_monotonic_increasing:
        raise ValueError('Expected exactly 8760 unique sorted annual timestamps')
    if df.network_validation_status.ne('NOT_SIMULATED').any():
        raise ValueError('Source must contain pre-validation hourly records')
    node=str(df.transformer_node.iloc[0]);houses=df.house_ids.iloc[0].split('|')
    if node=='931076':
        source_points={r['house_id']:(float(r['latitude']),float(r['longitude'])) for r in csv.DictReader(open(Path(repo)/HOUSES_REL,newline='',encoding='utf-8'))}
        variants=[(mode2,'known_94022_coordinate_with_hypothetical_radials',
                    lambda m=mode2:ref.make_network({h:source_points[h] for h in houses},m,'central')) for mode2 in routes]
    elif node=='923494':
        variants=[(f'{r:g}m','unknown_106039_location_parametric_equal_service_lengths',
                  lambda length=r:make_parametric_12house(pp,houses,length)) for r in assumed_lengths]
    else:raise ValueError('Initial AC runner only supports node 931076 or conditional 923494')
    meta_file=Path(hourly_csv).parent/'manifest.json'
    if not meta_file.is_file():
        raise FileNotFoundError('Canonical hourly manifest.json required beside annual_dispatch_8760.csv')
    meta=json.loads(meta_file.read_text(encoding='utf-8'))
    if meta['territory_node']!=node or meta['houses']!=houses:
        raise ValueError('Scenario metadata mismatch; refusing conditional AC run')
    eta_inv=float(meta['inverter_efficiency'])
    if not 0<eta_inv<=1.:raise ValueError('Invalid inverter conversion efficiency')
    src=pd.read_csv(Path(repo)/SOURCE_REL,parse_dates=['timestamp']).set_index('timestamp')
    if mode=='full':indices=list(range(len(df)))
    elif mode=='critical':indices=selected_timestamps(df)
    else:raise ValueError('mode critical or full')
    base=Path(outdir);base.mkdir(parents=True,exist_ok=True)
    results=[]
    qfac=math.sqrt(1/pf**2-1)
    for route,evidence,create in variants:
        net,buses,loads,lines,sg=create()
        for ii in indices:
            record=df.iloc[ii];stamp=record.timestamp_lst
            requested=np.array([float(src.at[stamp,f'house_{j}_kw']) for j in range(1,len(houses)+1)])
            if requested.sum()<1e-12 and record.demand_served_kw>1e-8:
                raise ValueError('Inconsistent source and served demand')
            ratio=float(record.demand_served_kw)/max(float(requested.sum()),1e-12)
            for h,req in zip(houses,requested):
                served=float(req)*ratio
                net.load.at[loads[h],'p_mw']=3*served/1000
                net.load.at[loads[h],'q_mvar']=3*served*qfac/1000
            ac_local=float(record.pv_ac_kw)+float(record.battery_discharge_dc_kw)*eta_inv
            net.sgen.at[sg[0],'p_mw']=3*ac_local/1000
            net.sgen.at[sg[0],'q_mvar']=0.
            try:
                pp.runpp(net,algorithm='bfsw',init='flat',
                         max_iteration=100,tolerance_mva=1e-9)
                minv=min(float(net.res_bus.vm_pu.at[b]) for b in buses.values())
                maxv=max(float(net.res_bus.vm_pu.at[b]) for b in buses.values())
                traf=float(net.res_trafo.loading_percent.iloc[0])
                line=max(float(net.res_line.loading_percent.at[z]) for z in lines.values())
                losses=float(sum(net.res_line.pl_mw.at[z] for z in lines.values()))*1000/3
                screen=bool(minv>=.97 and maxv<=1.03 and traf<=100 and line<=100 and record.ens_kw<=1e-6)
                entry=dict(timestamp_lst=str(stamp),node=node,houses=len(houses),route=route,
                    evidence=evidence,min_lv_pu=minv,max_lv_pu=maxv,transformer_loading_pct=traf,
                    max_lv_line_loading_pct=line,lv_line_losses_kw=losses,
                    model_pcc_kva=float(record.pcc_s_kva),ens_kw=float(record.ens_kw),
                    screen_pass=screen,converged=True)
            except pp.LoadflowNotConverged:
                entry=dict(timestamp_lst=str(stamp),node=node,houses=len(houses),route=route,
                    evidence=evidence,min_lv_pu=np.nan,max_lv_pu=np.nan,transformer_loading_pct=np.nan,
                    max_lv_line_loading_pct=np.nan,lv_line_losses_kw=np.nan,
                    model_pcc_kva=float(record.pcc_s_kva),ens_kw=float(record.ens_kw),
                    screen_pass=False,converged=False)
            results.append(entry)
    result=pd.DataFrame(results)
    result.to_csv(base/'ac_validation.csv',index=False,float_format='%.7f')
    manifest={'status':'CONDITIONAL_PANDAPOWER_AC_SNAPSHOT_VALIDATION',
              'mode':mode,'hours_simulated':len(indices),'variants':len(variants),'rows':len(result),
              'passes':int(result.screen_pass.sum()),'failures':int((~result.screen_pass).sum()),
              'topology':'unverified radial service lines, matched v5 parameters, balanced threefold equivalent',
              'transformer_106039_nameplate':'hypothetical 5kVA only, not EPM certified' if node=='923494' else None,
              'actual_LV_circuits':'UNKNOWN', 'phase_neutral':'NOT_VALIDATED',
              'standards_screen':'chosen 0.97..1.03 pu, line/trafo <=100%; not regulatory certification'}
    (base/'ac_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return result,manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path)
    p.add_argument('--hourly',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--mode',choices=['critical','full'],default='critical')
    a=p.parse_args()
    _,m=ac_run(locate_repo(a.repo_root),a.hourly,a.outdir,mode=a.mode)
    print(json.dumps(m,indent=2))
