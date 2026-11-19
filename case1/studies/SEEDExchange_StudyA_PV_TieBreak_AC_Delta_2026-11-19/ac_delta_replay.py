#!/usr/bin/env python3
"""Paired AC replays only for altered PCC-injection hours of signed PV tie-break.

Uses the *existing* A1 106039 v6 GIS/pandapower AC solver and prepared profiles.
This is a matched difference study, NOT a full-year network certification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace

import numpy as np
import pandas as pd

CASES = ('MC_REF', 'MC_P33')
REQUIRED_STATUS = 'COMPLETE_TWO_STAGE_ENERGY_ONLY_NOT_AC_VALIDATED'
SRC_FOLDER = 'StudyA_A1_106039_PV_TieBreak_Local_v2'
V6_FOLDER = 'case1/studies/SEEDExchange_StudyA_v6_LocalRunner'
INPUT_MANIFEST = V6_FOLDER + '/outputs/run_01/input_manifest_v6_2.json'
DIFFERENCE_TOL_KW = 1e-5
AC_FIELDS = ('ac_feasible','status','min_v_pu','max_v_pu','max_trafo_pct',
             'max_line_pct','loss_kw','pcc_kva','q_selected_kvar','error')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def changed_inverter_hours(ref, alt, tol=DIFFERENCE_TOL_KW):
    a = np.asarray(ref, dtype=float)
    b = np.asarray(alt, dtype=float)
    if len(a) != 8760 or a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Expected two finite 8760-hour inverter series')
    return np.flatnonzero(np.abs(a-b) > tol)


def verified_hourly(repo, folder=SRC_FOLDER):
    base = repo / folder
    manifest_path = base / 'RUN_MANIFEST.json'
    man = json.loads(manifest_path.read_text(encoding='utf-8'))
    if man.get('status') != REQUIRED_STATUS or man.get('errors') or set(man.get('cases',{})) != set(CASES):
        raise ValueError('Two-stage source did not pass BOTH annual energy cases')
    outputs={}
    for case in CASES:
        frames=[]
        for stage in ('STAGE1','STAGE2'):
            path = base / f'{case}_{stage}_8760.csv'
            expected = man['cases'][case][stage+'_csv_sha256']
            if sha(path) != expected:
                raise ValueError('CSV SHA256 mismatch: '+str(path))
            df = pd.read_csv(path, parse_dates=['timestamp_lst']).set_index('timestamp_lst')
            if (len(df) != 8760 or not df.index.is_unique or df.index.hasnans or
                    not (df.index == pd.date_range('2025-01-01',periods=8760,freq='h')).all()):
                raise ValueError(f'{case} {stage}: year/timebase mismatch')
            vals = df.select_dtypes(include=['number']).to_numpy(float)
            if not np.isfinite(vals).all():
                raise ValueError(f'{case} {stage}: non-finite numeric data')
            if df[['grid_export_kw','unserved_kw']].abs().to_numpy().max() > 1e-5:
                raise ValueError(f'{case} {stage}: export/ENS')
            if (df.grid_import_kw < -1e-5).any() or (df.inverter_ac_kw < -1e-5).any():
                raise ValueError(f'{case} {stage}: negative grid import/inverter injection')
            if abs(float(df.grid_import_kw.sum())-
                   man['cases'][case]['stage'+stage[-1]+('_reproduced_economic' if stage=='STAGE1' else '_tiebreak')]['annual_grid_import_ac_kwh']) > 1e-4:
                raise ValueError(f'{case} {stage}: import data/manifest mismatch')
            if np.max(np.abs(df.demand_kw.to_numpy(float) - (
                    df.inverter_ac_kw.to_numpy(float)+df.grid_import_kw.to_numpy(float)))) > 2e-4:
                raise ValueError(f'{case} {stage}: AC bus energy mismatch')
            frames.append(df)
        if np.max(np.abs(frames[0].demand_kw.to_numpy()-frames[1].demand_kw.to_numpy())) > 1e-7:
            raise ValueError(f'{case}: Stage 1/2 household demand changed')
        if np.max(np.abs(frames[0].pv_dc_available_kw.to_numpy()-
                         frames[1].pv_dc_available_kw.to_numpy())) > 1e-7:
            raise ValueError(f'{case}: Stage 1/2 irradiance changed')
        h=man['source_checks'][case]['hardware']
        if (h['pv_panels'] != (41 if case=='MC_REF' else 33) or
            h['battery_modules']!=8 or abs(h['inverter_kva']-12)>1e-9 or
            abs(h['transformer_kva_assumed_or_evidenced']-5)>1e-9):
            raise ValueError(f'{case}: unexpected fixed-hardware source')
        outputs[case]=tuple(frames)
    return man, outputs, manifest_path


def prepare(repo):
    repo=Path(repo).resolve()
    if not (repo/'.git').exists():
        raise ValueError('Run from original full GitLab checkout')
    man, outputs, source_manifest_path=verified_hourly(repo)
    sys.path.insert(0,str(repo/V6_FOLDER))
    import seed_study_a_v6 as v6
    args=SimpleNamespace(manifest=repo/INPUT_MANIFEST,
                         assignment='A1',transformer='106039')
    checked_repo, input_man, house_ids, trace=v6.data_for_case(args)
    if checked_repo.resolve()!=repo or len(house_ids)!=11 or len(trace)!=8760:
        raise ValueError('A1 106039/source checkout mismatch')
    plan={}
    for case,(r,a) in outputs.items():
        if not r.index.equals(trace.index) or not a.index.equals(trace.index):
            raise ValueError(f'{case}: timestamps differ from 35-house source profiles')
        if np.max(np.abs(r.demand_kw.to_numpy()-trace.sum(axis=1).to_numpy())) > 1e-5:
            raise ValueError(f'{case}: household-specific demand does not close')
        # Paired AC outcomes can only differ if inverter injection, load, solar
        # availability or policy differ; the latter three are held identical.
        hours=changed_inverter_hours(r.inverter_ac_kw,a.inverter_ac_kw)
        if np.max(np.abs((a.grid_import_kw-r.grid_import_kw).to_numpy()+
                         (a.inverter_ac_kw-r.inverter_ac_kw).to_numpy())) > 1e-5:
            raise ValueError(f'{case}: mismatch in changed PCC injection')
        plan[case]={'changed_inverter_hours':int(len(hours)),
                    'changed_indexes':hours.tolist(),
                    'max_inverter_delta_kw':float(np.abs(a.inverter_ac_kw-r.inverter_ac_kw).max()),
                    'source_stage1_csv_sha256':man['cases'][case]['STAGE1_csv_sha256'],
                    'source_stage2_csv_sha256':man['cases'][case]['STAGE2_csv_sha256']}
    provenance={'energy_run_manifest_sha256':sha(source_manifest_path),
                'input_manifest_sha256':sha(repo/INPUT_MANIFEST),
                'original_v6_runner_sha256':sha(repo/V6_FOLDER/'seed_study_a_v6.py'),
                'assignment':'A1','transformer':'106039','n_houses':11,
                'site':'inverter_HEAD_PROVISIONAL',
                'nighttime_Q':'OFF','source_cases':list(CASES)}
    return v6, trace, house_ids, outputs, plan, provenance


def matched_run(repo, out, scope='baseline', q_ratio=.25, q_points=9):
    v6, trace, houses, outputs, plan, provenance=prepare(repo)
    if scope not in ('baseline','full'):
        raise ValueError('scope must be baseline or full')
    if not 0<=q_ratio<=1 or q_points<3:
        raise ValueError('Bad Q capability/control settings')
    factors=[(.98,1.0)] if scope=='baseline' else [(pf,l) for pf in (.95,.98,1.0) for l in (1.0,1.3,1.6)]
    out=Path(out).resolve()
    if out.exists():
        raise FileExistsError('Will not overwrite '+str(out))
    out.mkdir(parents=True)
    record={'status':'INCOMPLETE_DELTA_AC_NOT_ANNUAL_AC', 'scope':scope,
            'source':provenance,'plan':plan,'q_ratio_daylight':q_ratio,
            'q_grid_points':q_points,'scenarios':[],
            'errors':{},'research_status':'PROVISIONAL_GIS_BALANCED_3PH_NO_ANNUAL_CERTIFICATION'}
    import pandapower as pp
    v6.repo_modules(Path(repo).resolve())
    from run_epm_validation import build_net
    for case in CASES:
        s1,s2=outputs[case]
        hours=plan[case]['changed_indexes']
        for pf,lf in factors:
            tag=f'{case}_PF{int(pf*100):03d}_LEN{int(lf*10):02d}'
            try:
                territory=v6.new_territory(Path(repo).resolve(),'A1','106039',houses,lf)
                net,meta=build_net(territory,'head')
                if set(meta['loads'])!=set(houses):
                    raise ValueError('Reconstructed LV GIS network house membership differs')
                rows=[]
                for i in hours:
                    row={'case':case,'timestamp_lst':str(trace.index[i]),
                         'original_hour_index':i,'pf':pf,'length_factor':lf,
                         'inverter_stage1_kw':float(s1.inverter_ac_kw.iat[i]),
                         'inverter_stage2_kw':float(s2.inverter_ac_kw.iat[i]),
                         'grid_stage1_kw':float(s1.grid_import_kw.iat[i]),
                         'grid_stage2_kw':float(s2.grid_import_kw.iat[i])}
                    for name,source in [('stage1',s1),('stage2',s2)]:
                        r=v6.solve_ac_hour(net,meta,territory,trace.index[i],
                                trace.iloc[i],pf,float(source.inverter_ac_kw.iat[i]),
                                12.,float(source.pv_dc_available_kw.iat[i]),
                                q_ratio,q_points,'pvbess',pp)
                        for k in AC_FIELDS:
                            row[name+'_'+k]=r.get(k)
                    if row['stage1_status']=='CONVERGED' and row['stage2_status']=='CONVERGED':
                        row['delta_loss_kw']=row['stage2_loss_kw']-row['stage1_loss_kw']
                        row['delta_trafo_pct']=row['stage2_max_trafo_pct']-row['stage1_max_trafo_pct']
                        row['delta_min_voltage_pu']=row['stage2_min_v_pu']-row['stage1_min_v_pu']
                    rows.append(row)
                frame=pd.DataFrame(rows)
                if len(frame)!=len(hours):
                    raise AssertionError('Changed-hour replay count mismatch')
                bad1=int((frame['stage1_status']!='CONVERGED').sum()) if len(frame) else 0
                bad2=int((frame['stage2_status']!='CONVERGED').sum()) if len(frame) else 0
                fail1=int((~frame['stage1_ac_feasible']).sum()) if len(frame) else 0
                fail2=int((~frame['stage2_ac_feasible']).sum()) if len(frame) else 0
                newfails=int(((frame.stage1_ac_feasible==True)&(frame.stage2_ac_feasible==False)).sum()) if len(frame) else 0
                fixedfails=int(((frame.stage1_ac_feasible==False)&(frame.stage2_ac_feasible==True)).sum()) if len(frame) else 0
                file=out/(tag+'_matched_changed_hours.csv')
                frame.to_csv(file,index=False,float_format='%.10f')
                record['scenarios'].append({'tag':tag,'case':case,'pf':pf,'length_factor':lf,
                    'changed_hours':len(hours),'stage1_nonconverged':bad1,'stage2_nonconverged':bad2,
                    'stage1_infeasible_or_nonconverged_hours':fail1,
                    'stage2_infeasible_or_nonconverged_hours':fail2,
                    'new_ac_failures':newfails,'resolved_ac_failures':fixedfails,
                    'delta_losses_kwh_on_changed_hours':float(frame.delta_loss_kw.sum()) if bad1==0 and bad2==0 and len(frame) else None,
                    'max_stage1_trafo_pct':float(frame.stage1_max_trafo_pct.max()) if len(frame) and bad1==0 else None,
                    'max_stage2_trafo_pct':float(frame.stage2_max_trafo_pct.max()) if len(frame) and bad2==0 else None,
                    'output_csv':file.name,'output_sha256':sha(file)})
            except Exception as exc:
                record['errors'][tag]={'type':type(exc).__name__,'message':str(exc),
                                      'traceback':traceback.format_exc()}
            (out/'RUN_MANIFEST.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if not record['errors']:
        record['status']='COMPLETE_MATCHED_DELTA_AC_WITHOUT_ANNUAL_CERTIFICATION'
        (out/'RUN_MANIFEST.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return record


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path.cwd())
    ap.add_argument('--preflight-only',action='store_true')
    ap.add_argument('--scope',choices=['baseline','full'],default='baseline')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--q-ratio',type=float,default=.25)
    ap.add_argument('--q-grid-points',type=int,default=9)
    args=ap.parse_args(argv)
    if args.preflight_only:
        _,_,_,_,plan,prov=prepare(args.repo_root)
        print(json.dumps({'status':'SOURCE_VERIFIED_AC_DELTA_PREFLIGHT',
                          'plan':{x:{k:v for k,v in y.items() if k!='changed_indexes'}
                                  for x,y in plan.items()},'source':prov},indent=2))
        return
    if args.out is None:
        ap.error('--out is required for AC numerical replay')
    r=matched_run(args.repo_root,args.out,args.scope,args.q_ratio,args.q_grid_points)
    print(json.dumps({'status':r['status'],'scenarios':r['scenarios'],
                       'errors':r['errors']},indent=2))
    if r['errors']:
        raise SystemExit(2)


if __name__=='__main__':
    main()
