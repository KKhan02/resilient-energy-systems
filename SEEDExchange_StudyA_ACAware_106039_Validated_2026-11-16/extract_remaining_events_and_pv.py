#!/usr/bin/env python3
"""Read-only Study A PV/BESS AC-failure and solar-curtailment diagnostics.

Requires original locally signed annual outputs. Uses the distinct scenario, hardware
family, topology, dispatch, power factor and length factor of every AC case.
All output is written to a new ZIP; no source simulations are edited or rerun.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, zipfile
from pathlib import Path
import pandas as pd
import numpy as np

BASE=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')

def xp(path):
    path=Path(path).resolve()
    s=str(path)
    return '\\\\?\\'+s if os.name=='nt' and not s.startswith('\\\\?\\') else s

def jread(p):
    with open(xp(p),'r',encoding='utf-8') as f:return json.load(f)

def valid_hash(path,hash_value):
    h=hashlib.sha256()
    with open(xp(path),'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    if h.hexdigest()!=hash_value:raise ValueError('SHA-256 mismatch '+str(path))

def load_hourly(path):
    d=pd.read_csv(xp(path),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    t=pd.date_range('2025-01-01',periods=8760,freq='h')
    if len(d)!=8760 or not d.index.equals(t):raise ValueError('Non-8760 2025 chronology '+str(path))
    return d

def dispatch_and_hardware(base,r,cache):
    family='four' if r.hardware_family=='four_house_new' else 'ref'
    parent=f'{r.scenario}_{r.transformer}_{r.tier}_{family}'
    key=(parent,r.dispatch)
    if key in cache:return cache[key]
    ef=base/f'energy_{parent}'
    e=jread(ef/'energy_manifest.json')
    valid_hash(ef/'energy_hourly_2025.csv',e['energy_csv_sha256'])
    if r.dispatch=='optimized':
        dispatch=load_hourly(ef/'energy_hourly_2025.csv')
    else:
        cf=base/f'causal_{parent}';meta=jread(cf/'causal_summary.json')
        valid_hash(cf/'causal_pv_first_2025.csv',meta['output_sha256'])
        dispatch=load_hourly(cf/'causal_pv_first_2025.csv')
    cache[key]=(dispatch,e['hardware'])
    return cache[key]

def collect(repo,register):
    repo=Path(repo).resolve();base=repo/BASE
    ac_rows=[];issues=[];cache={};validated=0
    cases=register.loc[register.effective_infeasible_hours.gt(0)].copy()
    for n,r in enumerate(cases.itertuples(index=False),1):
        try:
            case_dir=base/'annual_ac_replays_v1'/r.case
            summary=jread(case_dir/'ac_summary.json')
            if int(summary.get('hours',0))!=8760 or int(summary.get('converged_hours',0))!=8760:
                raise ValueError('Incomplete yearly AC summary')
            for key,val in [('scenario',r.scenario),('transformer',str(r.transformer)),('topology',r.topology),('dispatch',r.dispatch)]:
                if str(summary.get(key))!=str(val):raise ValueError('AC case identity mismatch '+key)
            if abs(float(summary['pf'])-float(r.pf))>1e-9 or abs(float(summary['length_factor'])-float(r.length_factor))>1e-9:
                raise ValueError('AC PF or length mismatch')
            valid_hash(case_dir/'ac_hourly.csv',summary['ac_hourly_sha256'])
            ac=load_hourly(case_dir/'ac_hourly.csv')
            if not (ac.status=='CONVERGED').all():raise ValueError('AC hours not all converged')
            is_bad=(ac.ac_feasible.astype(str).str.lower()!='true')
            if int(is_bad.sum())!=int(r.infeasible_hours):raise ValueError(f'Failure hours mismatch: {is_bad.sum()} vs {r.infeasible_hours}')
            dis,hw=dispatch_and_hardware(base,r,cache)
            if (dis.demand_kw-ac.gross_demand_kw).abs().max()>1e-4:
                raise ValueError('Energy/AC gross demand mismatch')
            if (dis.inverter_ac_kw-ac.inverter_ac_kw).abs().max()>1e-4:
                raise ValueError('Energy/AC inverter dispatch mismatch')
            for time,row in ac.loc[is_bad].iterrows():
                dr=dis.loc[time]
                item={'case':r.case,'scenario':r.scenario,'transformer':r.transformer,'tier':r.tier,'hardware_family':r.hardware_family,
                    'topology':r.topology,'dispatch':r.dispatch,'pf':r.pf,'length_factor':r.length_factor,
                    'timestamp_lst':str(time),'max_trafo_pct':float(row.max_trafo_pct),'min_v_pu':float(row.min_v_pu),
                    'max_line_pct':float(row.max_line_pct),'voltage_under_095':bool(float(row.min_v_pu)<0.95),
                    'trafo_over_100':bool(float(row.max_trafo_pct)>100),
                    'inverter_ac_kw':float(dr.inverter_ac_kw),'grid_import_kw':float(dr.grid_import_kw),
                    'demand_kw':float(dr.demand_kw),'pv_dc_available_kw':float(dr.pv_dc_available_kw),
                    'curtailed_pv_dc_kw':float(dr.curtailed_pv_dc_kw),
                    'battery_soc_after_kwh':float(dr.battery_soc_usable_kwh),
                    'battery_charge_dc_kw':float(dr.battery_charge_dc_kw),
                    'battery_discharge_dc_kw':float(dr.battery_discharge_dc_kw),
                    'battery_power_limit_dc_kw':float(hw['battery_power_dc_kw']),
                    'battery_modules':int(hw['battery_modules'])}
                if 'pcc_kva' in ac: item['pcc_kva']=float(row.pcc_kva)
                ac_rows.append(item)
            validated+=1
        except Exception as ex:
            issues.append({'case':r.case,'issue':type(ex).__name__+': '+str(ex)})
        if n%25==0:print('Checked remaining AC cases',n,'/',len(cases),flush=True)
    events=pd.DataFrame(ac_rows)
    if len(events):
        keys=['scenario','transformer','tier','hardware_family','topology','dispatch','timestamp_lst']
        unique=events.groupby(keys,as_index=False).agg(
            failing_pf_length_combinations=('case','count'),
            peak_trafo_pct=('max_trafo_pct','max'),lowest_v_pu=('min_v_pu','min'),
            any_trafo_overload=('trafo_over_100','max'),any_low_voltage=('voltage_under_095','max'),
            inverter_ac_kw=('inverter_ac_kw','first'),
            battery_soc_after_kwh=('battery_soc_after_kwh','first'),
            battery_discharge_dc_kw=('battery_discharge_dc_kw','first'),
            pv_curtailed_dc_kw=('curtailed_pv_dc_kw','first'))
    else:unique=pd.DataFrame()
    pv=[]
    for r in register[['scenario','transformer','tier','hardware_family','topology','dispatch']].drop_duplicates().itertuples(index=False):
        key=(f'{r.scenario}_{r.transformer}_{r.tier}_{"four" if r.hardware_family=="four_house_new" else "ref"}',r.dispatch)
        try:
            dis,hw=dispatch_and_hardware(base,r,cache)
            curtailed=dis.curtailed_pv_dc_kw.clip(lower=0)
            mask=curtailed>1e-6
            pv.append({'case_family':key[0],'dispatch':r.dispatch,'annual_demand_kwh':float(dis.demand_kw.sum()),
                'annual_import_kwh':float(dis.grid_import_kw.sum()),
                'pv_available_dc_kwh':float(dis.pv_dc_available_kw.sum()),
                'pv_curtailed_dc_kwh':float(curtailed.sum()),
                'pv_curtailment_pct':100*float(curtailed.sum())/max(1e-9,float(dis.pv_dc_available_kw.sum())),
                'curtailment_hours':int(mask.sum()),
                'curtailment_at_near_full_end_soc_hours':int((mask & (dis.battery_soc_usable_kwh>=float(hw['battery_modules'])*4.325-1e-4)).sum()),
                'curtailment_at_near_charge_power_cap_hours':int((mask & (dis.battery_charge_dc_kw>=float(hw['battery_power_dc_kw'])-1e-4)).sum()),
                'curtailment_with_ac_inverter_near_nameplate_hours':int((mask & (dis.inverter_ac_kw>=float(hw['inverter_kva'])-1e-4)).sum()),
                'pv_panels':int(hw['pv_panels']),'battery_modules':int(hw['battery_modules']),
                'battery_power_dc_kw':float(hw['battery_power_dc_kw']),'inverter_kva':float(hw['inverter_kva'])})
        except Exception as ex:issues.append({'case':str(key),'issue':type(ex).__name__+': '+str(ex)})
    pv=pd.DataFrame(pv).drop_duplicates(['case_family','dispatch']) if pv else pd.DataFrame()
    return events,unique,pv,validated,issues

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--status-table',type=Path,default=Path(__file__).with_name('PORTFOLIO_432_STATUS_WITH_TRIAL_OVERLAY.csv'))
    ap.add_argument('--out',type=Path,default=Path('StudyA_Remaining_AC_And_PV_Diagnostics.zip'))
    args=ap.parse_args()
    reg=pd.read_csv(args.status_table,dtype={'transformer':str})
    if len(reg)!=432 or int(reg.corrected_by_trial.sum())!=18 or int(reg.effective_infeasible_hours.gt(0).sum())!=126:
        raise ValueError('Incorrect signed-reconciliation register, refuse to proceed')
    events,unique,pv,validated,issues=collect(args.repo_root,reg)
    info={'expected_remaining_failing_ac_cases':126,'verified_failing_ac_cases':validated,
        'violation_event_records':len(events),'distinct_design_timestamp_events':len(unique),
        'dispatch_family_summaries':len(pv),'issues':issues,
        'note':'Curtailed-PV coincidence flags overlap, they do not prove the cause of curtailment. No automatic intervention is performed.'}
    out=args.out.resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError('Output protected: '+str(out))
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for name,df in [('REMAINING_AC_VIOLATION_EVENTS.csv',events),('DEDUPLICATED_CONSTRAINT_EVENTS.csv',unique),('PV_CURTAILMENT_DIAGNOSTICS.csv',pv)]:
            z.writestr(name,df.to_csv(index=False))
        z.writestr('EXTRACTION_QA.json',json.dumps(info,indent=2)+'\n')
    print(json.dumps({'archive':str(out),'cases_verified':validated,'events':len(events),'issues':len(issues)},indent=2))

if __name__=='__main__':main()
