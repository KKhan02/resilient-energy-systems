#!/usr/bin/env python3
"""Source-verified A1 106039 MC_REF Stage2 evening BESS reserve correction.

Shift DC battery discharge from 17:00 to the evening overload hour on
13 October and 27 November 2025. Revalidate four hours under pandapower;
reuse EXACT existing annual MC_REF AC rows and signed Stage2 delta AC rows
for unchanged hours only. Historical data are read-only. 5 kVA is assumed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback

import numpy as np
import pandas as pd

ETA_INV=.95
ETA_BAT=math.sqrt(.95)
SOC_MIN=8*.229
SOC_MAX=8*4.325
SHIFT_PLAN=(
    ('2025-10-13 17:00:00','2025-10-13 20:00:00',.60),
    ('2025-11-27 17:00:00','2025-11-27 20:00:00',.80),
)
V2_ROOT=Path('StudyA_A1_106039_PV_TieBreak_Local_v2')
DELTA_ROOT=Path('StudyA_A1_106039_PV_TieBreak_AC_Delta_Full_v1')
HIST_ROOT=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01/annual_ac_replays_v1')
AC_METRICS=('status','ac_feasible','min_v_pu','max_v_pu','max_trafo_pct',
            'max_line_pct','loss_kw','pcc_kva','q_selected_kvar','error')
PF_GRID_SCREEN=.98
GRID_KVA=5.0

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):
            h.update(block)
    return h.hexdigest()

def update_shift(frame, donor, target, dc):
    """Move one DC kWh of discharge, preserving annual import and cycle-end SOC."""
    a=frame.copy(deep=True)
    src=pd.Timestamp(donor);dst=pd.Timestamp(target)
    if src not in a.index or dst not in a.index or src>=dst or dc<=0:
        raise ValueError('Invalid ordered shift hours or DC amount')
    if (a.loc[src,'battery_discharge_dc_kw'] < dc-1e-8 or
        a.loc[dst,'battery_discharge_dc_kw']+dc > 12.+1e-8):
        raise ValueError('Source discharge unavailable or target battery power violated')
    moved=ETA_INV*dc
    if (a.loc[src,'inverter_ac_kw'] < moved-1e-8 or
        a.loc[dst,'inverter_ac_kw']+moved > 12.+1e-8 or
        a.loc[dst,'grid_import_kw'] < moved-1e-8):
        raise ValueError('Transfer would violate inverter availability/power or import nonnegativity')
    a.loc[src,'battery_discharge_dc_kw']-=dc
    a.loc[dst,'battery_discharge_dc_kw']+=dc
    a.loc[src,'inverter_ac_kw']-=moved
    a.loc[dst,'inverter_ac_kw']+=moved
    a.loc[src,'grid_import_kw']+=moved
    a.loc[dst,'grid_import_kw']-=moved
    a.loc[src:dst-pd.Timedelta(hours=1),'battery_soc_usable_kwh']+=dc/ETA_BAT
    for t in (src,dst):
        a.loc[t,'pcc_p_kw']=a.loc[t,'grid_import_kw']
        a.loc[t,'pcc_kva_proxy']=math.hypot(a.loc[t,'grid_import_kw'],a.loc[t,'pcc_q_kvar_proxy'])
    if (a.battery_soc_usable_kwh.min() < SOC_MIN-1e-6 or
        a.battery_soc_usable_kwh.max() > SOC_MAX+1e-6 or
        (a.pcc_kva_proxy > GRID_KVA+1e-4).any()):
        raise ValueError('Result violates manufacturer SOC or 5 kVA PF=.98 proxy')
    return a

def assert_dispatch(original, candidate):
    req=('demand_kw','pv_dc_generated_kw','pv_dc_available_kw',
         'battery_charge_dc_kw','battery_discharge_dc_kw','inverter_ac_kw',
         'battery_soc_usable_kwh','grid_import_kw','grid_export_kw',
         'unserved_kw','curtailed_pv_dc_kw')
    if len(candidate)!=8760 or not original.index.equals(candidate.index):
        raise ValueError('Original and candidate full-year chronology differ')
    if not np.isfinite(candidate[list(req)].to_numpy(float)).all():
        raise ValueError('Nonfinite candidate values')
    for field in ('demand_kw','pv_dc_generated_kw','pv_dc_available_kw',
                  'battery_charge_dc_kw','curtailed_pv_dc_kw'):
        if np.max(np.abs(candidate[field]-original[field])) > 1e-7:
            raise ValueError(field+' must not change')
    if (candidate.grid_export_kw.abs().max()>1e-5 or
        candidate.unserved_kw.abs().max()>1e-5):
        raise ValueError('No export/ENS allowed')
    if (candidate.battery_soc_usable_kwh.min()<SOC_MIN-1e-6 or
        candidate.battery_soc_usable_kwh.max()>SOC_MAX+1e-6):
        raise ValueError('Manufacturer physical SOC violation')
    if np.max(np.abs(candidate.demand_kw-candidate.grid_import_kw-candidate.inverter_ac_kw))>1e-5:
        raise ValueError('AC bus balance')
    if np.max(np.abs(candidate.pv_dc_generated_kw+candidate.battery_discharge_dc_kw-
                     candidate.battery_charge_dc_kw-candidate.inverter_ac_kw/ETA_INV))>1e-5:
        raise ValueError('DC bus balance')
    a=candidate.battery_soc_usable_kwh.to_numpy(float)
    ch=candidate.battery_charge_dc_kw.to_numpy(float)
    dis=candidate.battery_discharge_dc_kw.to_numpy(float)
    if np.max(np.abs(a-np.roll(a,1)-ETA_BAT*ch+dis/ETA_BAT))>2e-5:
        raise ValueError('Battery cyclic hourly SOC recurrence')
    if ((ch>1e-5)&(dis>1e-5)).any():
        raise ValueError('Simultaneous charge/discharge')
    if np.max(np.abs(candidate.pcc_kva_proxy-np.hypot(candidate.grid_import_kw,
                                                      candidate.pcc_q_kvar_proxy)))>1e-5:
        raise ValueError('PCC proxy mismatch')
    if (candidate.pcc_kva_proxy>5.+1e-5).any():
        raise ValueError('Assumed transformer proxy breached')
    for field in ('grid_import_kw','battery_discharge_dc_kw'):
        if abs(float(original[field].sum())-float(candidate[field].sum()))>1e-5:
            raise ValueError('Annual '+field+' was changed')
    if abs(original.battery_soc_usable_kwh.iat[-1]-candidate.battery_soc_usable_kwh.iat[-1])>1e-5:
        raise ValueError('Annual battery terminal SOC changed')

def load_inputs(repo):
    repo=Path(repo).resolve()
    sys.path.insert(0,str(repo/'case1/studies/SEEDExchange_StudyA_PV_TieBreak_AC_Delta_2026-11-19'))
    import ac_delta_replay as delta
    v6,trace,houses,outputs,plan,prov=delta.prepare(repo)
    s1,s2=outputs['MC_REF']
    candidate=s2.copy(deep=True)
    for donor,target,dc in SHIFT_PLAN:
        candidate=update_shift(candidate,donor,target,dc)
    assert_dispatch(s2,candidate)
    indexes=np.flatnonzero(np.abs(s2.inverter_ac_kw.to_numpy()-
                                  candidate.inverter_ac_kw.to_numpy())>1e-7).tolist()
    expected=[s2.index.get_loc(pd.Timestamp(x)) for a,b,_ in SHIFT_PLAN for x in (a,b)]
    if sorted(indexes)!=sorted(expected) or set(indexes)&set(plan['MC_REF']['changed_indexes']):
        raise ValueError('Unexpected or overlapping candidate changed-hour set')
    manifest=json.loads((repo/DELTA_ROOT/'RUN_MANIFEST.json').read_text(encoding='utf-8'))
    if (manifest['status']!='COMPLETE_MATCHED_DELTA_AC_WITHOUT_ANNUAL_CERTIFICATION'
        or manifest['errors'] or len(manifest['scenarios'])!=18 or
        manifest['source']['energy_run_manifest_sha256']!=sha(repo/V2_ROOT/'RUN_MANIFEST.json')):
        raise ValueError('Previous Stage2 AC delta manifest not fully signed')
    return v6,trace,houses,s1,s2,candidate,plan,manifest,indexes,prov

def summary(df):
    converged=df.status.eq('CONVERGED')
    feas=df.ac_feasible.fillna(False).astype(bool) & converged
    return {'hours':len(df),'converged':int(converged.sum()),
            'ac_infeasible_or_unconverged_hours':int((~feas).sum()),
            'min_v_pu':float(df.min_v_pu.min()),
            'max_v_pu':float(df.max_v_pu.max()),
            'max_trafo_pct':float(df.max_trafo_pct.max()),
            'max_line_pct':float(df.max_line_pct.max()),
            'yearly_ac_losses_kwh':float(df.loss_kw.sum()),
            'failed_timestamps':df.index[~feas].strftime('%Y-%m-%d %H:%M:%S').tolist()}

def metrics_equal(archive, delta_row, prefix, atol=1e-5):
    for col in ('min_v_pu','max_v_pu','max_trafo_pct','max_line_pct',
                'loss_kw','pcc_kva','q_selected_kvar'):
        if abs(float(archive[col])-float(delta_row[prefix+col]))>atol:
            raise ValueError('Historical AC mismatch at '+col)
    if str(archive['status'])!=str(delta_row[prefix+'status']) or (
       bool(archive['ac_feasible'])!=bool(delta_row[prefix+'ac_feasible'])):
        raise ValueError('Historical status/feasibility does not match paired AC')

def patch_ac(frame, time, record, prefix):
    for field in AC_METRICS:
        if prefix+field in record:
            frame.at[time,field]=record[prefix+field]

def ac_one_factor(repo,v6,trace,houses,s1,s2,candidate,manifest,indexes,pf,lf,qratio=.25):
    repo=Path(repo).resolve()
    tag=f'MC_REF_PF{round(pf*100):03d}_LEN{round(lf*10):02d}'
    annual_name=f'A1_106039_min_cost_ref_mapped_optimized_pf{round(pf*100):03d}_length{round(lf*10)}_annual8760'
    old_dir=repo/HIST_ROOT/annual_name
    record=json.loads((old_dir/'ac_summary.json').read_text(encoding='utf-8'))
    old_file=old_dir/'ac_hourly.csv'
    if (record['ac_hourly_sha256']!=sha(old_file) or
        record['energy_manifest_sha256']!=sha(repo/'case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01/energy_A1_106039_min_cost_ref/energy_manifest.json')
        or record['input_manifest_sha256']!=manifest['source']['input_manifest_sha256']
        or record['scenario']!='A1' or record['transformer']!='106039'
        or record['dispatch']!='optimized' or abs(record['pf']-pf)>1e-10
        or abs(record['length_factor']-lf)>1e-10 or record['hours']!=8760):
        raise ValueError('Historical full-year AC evidence mismatch: '+tag)
    original=pd.read_csv(old_file,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    if len(original)!=8760 or not original.index.equals(s1.index):
        raise ValueError('Historical timestamps mismatch')
    if (np.max(np.abs(original.inverter_ac_kw-s1.inverter_ac_kw))>1e-7 or
        np.max(np.abs(original.gross_demand_kw-s1.demand_kw))>1e-7):
        raise ValueError('Historical AC replay does not use same Stage 1 8760h power')
    staged=original.copy(deep=True)
    case_item=next((x for x in manifest['scenarios'] if x['tag']==tag),None)
    if case_item is None or case_item['changed_hours']!=68:
        raise ValueError('Missing signed Stage2 changed-hour scenario '+tag)
    changed_file=repo/DELTA_ROOT/case_item['output_csv']
    if sha(changed_file)!=case_item['output_sha256']:
        raise ValueError('Changed-hour AC file hash mismatch')
    change=pd.read_csv(changed_file,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    if len(change)!=68 or not change.index.is_unique:
        raise ValueError('Changed AC hour count/time uniqueness')
    if set(change.original_hour_index.astype(int))!=set(manifest['plan']['MC_REF']['changed_indexes']):
        raise ValueError('Changed AC hour set is not the saved exact energy difference')
    for t,row in change.iterrows():
        metrics_equal(original.loc[t],row,'stage1_')
        patch_ac(staged,t,row,'stage2_')
    import pandapower as pp
    v6.repo_modules(repo)
    from run_epm_validation import build_net
    territory=v6.new_territory(repo,'A1','106039',houses,lf)
    net,meta=build_net(territory,'head')
    if set(meta['loads'])!=set(houses):
        raise ValueError('Original household GIS topology mismatch')
    corrected=staged.copy(deep=True)
    changed=[]
    for index in indexes:
        t=trace.index[index]
        oldr=v6.solve_ac_hour(net,meta,territory,t,trace.iloc[index],pf,
                    float(s2.inverter_ac_kw.iat[index]),12.,
                    float(s2.pv_dc_available_kw.iat[index]),qratio,9,'pvbess',pp)
        if oldr['status']!='CONVERGED':
            raise RuntimeError('Stage2 original AC failed to converge at '+str(t))
        metrics_equal(staged.loc[t],pd.Series({'base_'+k:oldr.get(k) for k in AC_METRICS}),'base_')
        newr=v6.solve_ac_hour(net,meta,territory,t,trace.iloc[index],pf,
                    float(candidate.inverter_ac_kw.iat[index]),12.,
                    float(candidate.pv_dc_available_kw.iat[index]),qratio,9,'pvbess',pp)
        if newr['status']!='CONVERGED':
            raise RuntimeError('Candidate AC failed to converge at '+str(t))
        for key in AC_METRICS:
            corrected.at[t,key]=newr.get(key)
        changed.append({'timestamp_lst':str(t),'pf':pf,'length_factor':lf,
                        'inverter_stage2_kw':float(s2.inverter_ac_kw.iat[index]),
                        'inverter_corrected_kw':float(candidate.inverter_ac_kw.iat[index]),
                        'stage2_ac_feasible':oldr['ac_feasible'],
                        'corrected_ac_feasible':newr['ac_feasible'],
                        'stage2_trafo_pct':oldr['max_trafo_pct'],
                        'corrected_trafo_pct':newr['max_trafo_pct'],
                        'stage2_min_voltage_pu':oldr['min_v_pu'],
                        'corrected_min_voltage_pu':newr['min_v_pu'],
                        'stage2_loss_kw':oldr['loss_kw'],
                        'corrected_loss_kw':newr['loss_kw']})
    a,b,c=summary(original),summary(staged),summary(corrected)
    if a['ac_infeasible_or_unconverged_hours']!=record['AC_infeasible_hours']:
        raise ValueError('Original source AC annual failure count mismatch')
    for x in (a,b,c):
        if x['hours']!=8760 or x['converged']!=8760:
            raise ValueError('Full year lacks converged provenance')
    return {'tag':tag,'pf':pf,'length_factor':lf,'historical':a,'stage2':b,'reserve_candidate':c,
            'source_annual_ac_sha256':sha(old_file),
            'stage2_delta_csv_sha256':sha(changed_file),
            'changed_earlier_stage2_ac_hours':68,'new_reserve_corrected_hours':len(indexes),
            'interpretation':'SOURCE_STITCHED_COMPLETE_2025_AC_BALANCED_PROVISIONAL_GIS_NOT_A_NEW_8760H_SOLVE'},changed

def run(repo,out=None,preflight=False,scope='stress'):
    repo=Path(repo).resolve()
    v6,trace,houses,s1,s2,candidate,plan,manifest,indexes,provenance=load_inputs(repo)
    checks={'status':'SIGNED_SOURCE_GRID_RESERVE_PREFLIGHT',
            'source_v2_sha256':sha(repo/V2_ROOT/'RUN_MANIFEST.json'),
            'source_delta_sha256':sha(repo/DELTA_ROOT/'RUN_MANIFEST.json'),
            'source_annual_inverter_identity':'TO_BE_VALIDATED_PER_FACTOR',
            'shift_plan':SHIFT_PLAN,'replayed_grid_injection_hours':len(indexes),
            'stage2_grid_import_kwh':float(s2.grid_import_kw.sum()),
            'candidate_grid_import_kwh':float(candidate.grid_import_kw.sum()),
            'stage2_end_soc_kwh':float(s2.battery_soc_usable_kwh.iat[-1]),
            'candidate_end_soc_kwh':float(candidate.battery_soc_usable_kwh.iat[-1])}
    if preflight:return checks
    if out is None:raise ValueError('Provide a fresh --out directory')
    out=Path(out).resolve()
    if out.exists():raise FileExistsError('No overwrites: '+str(out))
    out.mkdir(parents=True)
    hourly_path=out/'MC_REF_STAGE2_GRID_RESERVE_CANDIDATE_8760.csv'
    candidate.to_csv(hourly_path,index_label='timestamp_lst',float_format='%.10f')
    cases=[(.95,1.6)] if scope=='stress' else [(pf,lf) for pf in (.95,.98,1.) for lf in (1.,1.3,1.6)]
    report={'status':'INCOMPLETE_OR_FAILED_SOURCE_STITCHED_AC','scope':scope,
            'preflight':checks,'candidate_sha256':sha(hourly_path),'cases':[],
            'errors':{},'assumed_transformer_kva':5.,
            'ac_provenance':'SIGNED_ANNUAL_STAGE1_PLUS_VERIFIED_STAGE2_CHANGED_HOURS_PLUS_4_NEW_AC_HOURS',
            'not_a_new_full_8760_solve':True,'not_field_certification':True}
    for pf,lf in cases:
        tag=f'PF{round(pf*100):03d}_LEN{round(lf*10):02d}'
        try:
            r,rows=ac_one_factor(repo,v6,trace,houses,s1,s2,candidate,manifest,indexes,pf,lf)
            csv=out/(tag+'_FOUR_CORRECTION_HOURS.csv')
            pd.DataFrame(rows).to_csv(csv,index=False,float_format='%.10f')
            r['replayed_four_hour_csv']=csv.name
            r['replayed_four_hour_sha256']=sha(csv)
            report['cases'].append(r)
        except Exception as exc:
            report['errors'][tag]={'type':type(exc).__name__,'message':str(exc),
                                   'traceback':traceback.format_exc()}
        (out/'RUN_MANIFEST.json').write_text(json.dumps(report,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8')
    if not report['errors']:
        report['status']='COMPLETE_SOURCE_STITCHED_2025_AC' if all(
           r['reserve_candidate']['ac_infeasible_or_unconverged_hours']==0 for r in report['cases']
        ) else 'COMPLETE_WITH_EXPLICIT_AC_FAILURES'
        (out/'RUN_MANIFEST.json').write_text(json.dumps(report,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8')
    return report

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path.cwd())
    ap.add_argument('--preflight-only',action='store_true')
    ap.add_argument('--scope',choices=['stress','full'],default='stress')
    ap.add_argument('--out',type=Path)
    args=ap.parse_args(argv)
    result=run(args.repo_root,args.out,args.preflight_only,args.scope)
    print(json.dumps(result if args.preflight_only else {
        'status':result['status'],'scope':result['scope'],
        'cases':[{k:v for k,v in r.items() if k in ('tag','stage2','reserve_candidate')} for r in result['cases']],
        'errors':result['errors']},indent=2,allow_nan=False,default=str))
    if not args.preflight_only and result['errors']:
        raise SystemExit(2)

if __name__=='__main__':
    main()
