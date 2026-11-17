#!/usr/bin/env python3
"""Source-checked nine-factor, selected-hour A0 94022 branch-bundle AC screen.

Do not confuse this selected-hour screen with an annual AC replay, a physical
conductor selection, or an installation cost estimate. No signed source changes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'inputs'/'StudyA_94022_DualService_Trial_v1_Results.zip'
SOURCE_SHA='c0985268efa29d621273812ccefca23f24a3b57ad619359d476fc6d6bf670879'
PRIOR=Path('case1/studies/SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16/probe_94022_network_options.py')
TRIAL_DEFAULT=Path('StudyA_A0_94022_Sequenced_Trial_v1')
FACTOR_GRID=[(pf,length) for pf in (0.95,0.98,1.00) for length in (1.0,1.3,1.6)]
BUNDLES={
    'head_reference':[],
    'svc007_004_gis014_011_R050':[7,4,14,11],
    'svc007_004_gis014_011_016_R050':[7,4,14,11,16],
    'svc007_004_gis014_011_016_018_R050':[7,4,14,11,16,18],
    'all_LV_R050':list(range(26)),
}
FIELDS=['minimum_voltage_pu','maximum_voltage_pu','transformer_loading_pct','line_loading_pct']
KEYS=['case','dispatch','pf','length_factor','timestamp_lst','option']


def digest(path:Path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def feasible(r):
    return (r.minimum_voltage_pu.ge(.95) & r.maximum_voltage_pu.le(1.05) &
            r.transformer_loading_pct.le(100) & r.line_loading_pct.le(100) &
            r.status.eq('CONVERGED'))


def read_reference(path:Path=SOURCE):
    if not path.is_file() or digest(path)!=SOURCE_SHA:
        raise ValueError('Prior uploaded dual-service source ZIP missing or hash mismatch')
    with zipfile.ZipFile(path) as z:
        if z.testzip():raise ValueError('Previous ZIP CRC mismatch')
        data=pd.read_csv(io.BytesIO(z.read('DUAL_SERVICE_AC_72_CASES_EACH.csv')))
        summ=pd.read_csv(io.BytesIO(z.read('DUAL_SERVICE_OPTIONS_RANKED.csv')))
        reg=pd.read_csv(io.BytesIO(z.read('DUAL_SERVICE_MODEL_BRANCH_ENDPOINTS.csv')))
        mani=json.loads(z.read('DUAL_SERVICE_MANIFEST.json'))
    if len(data)!=1152 or len(summ)!=16 or len(reg)!=26 or data.duplicated(KEYS).any():
        raise ValueError('Prior dual-service dimensions/identities invalid')
    if mani['status']!='TARGETED_DUAL_SERVICE_SENSITIVITY_NOT_ANNUAL' or mani['annual_8760_AC_verified'] is not False:
        raise ValueError('Previous scope/provenance inconsistent')
    if data.status.ne('CONVERGED').any() or not data[FIELDS].apply(np.isfinite).all().all():
        raise ValueError('Previous source AC invalid')
    if not feasible(data).equals(data.ac_feasible):
        raise ValueError('Previous source feasibility flags inconsistent')
    if len(reg.line_index.unique())!=26 or set(reg.line_index)!=set(range(26)):
        raise ValueError('Original line index register changed')
    if not (reg.set_index('line_index').at[7,'to_model_bus']=='HOUSE_H01' and
            reg.set_index('line_index').at[4,'to_model_bus']=='HOUSE_H06'):
        raise ValueError('H01/H06 branch-to-bus provenance changed')
    if any(not set(k).issubset(set(reg.line_index)) for k in BUNDLES.values()):
        raise ValueError('Invalid branch index')
    return data,summ,reg,mani


def import_old(repo:Path):
    path=repo/PRIOR
    if not path.is_file():raise FileNotFoundError('Missing prior A0 probe code: '+str(path))
    spec=importlib.util.spec_from_file_location('studyA94022allnine_parent',path)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    return mod


def compare_overlaps(new:pd.DataFrame,old:pd.DataFrame):
    overlap=old[old.option.isin(BUNDLES)].copy()
    current=new.merge(overlap[KEYS+FIELDS+['ac_feasible']],on=KEYS,how='inner',suffixes=('','_prior'),validate='one_to_one')
    expected=len(overlap)
    if len(current)!=expected or expected!=72*len(BUNDLES):
        raise ValueError('Historical control overlaps missing')
    diffs={s:float(np.max(np.abs(current[s]-current[s+'_prior']))) for s in FIELDS}
    if max(diffs.values())>2e-4 or not current.ac_feasible.equals(current.ac_feasible_prior):
        raise ValueError('Matched 2-factor source powerflows differ from previous trial: '+str(diffs))
    return expected,diffs


def validate_rows(results:pd.DataFrame,old:pd.DataFrame):
    expected=4*9*9*len(BUNDLES)
    if len(results)!=expected or results.duplicated(KEYS).any():
        raise ValueError(f'Unexpected new rows or duplicates: {len(results)} versus {expected}')
    if results.status.ne('CONVERGED').any() or not results[FIELDS].apply(np.isfinite).all().all():
        raise ValueError('Nonconvergent or nonfinite AC calculations')
    if not feasible(results).equals(results.ac_feasible):
        raise ValueError('Recomputed feasibility disagree with recorded results')
    factors=set(zip(results.pf,results.length_factor))
    if factors!=set(FACTOR_GRID):raise ValueError('Nine-factor coverage incomplete')
    for opt,g in results.groupby('option'):
        if opt not in BUNDLES or len(g)!=324 or g.timestamp_lst.nunique()!=9:
            raise ValueError('Unexpected option/chronology: '+opt)
        if len(g[['case','dispatch']].drop_duplicates())!=4:
            raise ValueError('Case/dispatch coverage incomplete')
    return compare_overlaps(results,old)


def main_run(repo:Path,trial_dir:Path,out:Path):
    if out.exists():raise FileExistsError('Refusing to overwrite existing ZIP: '+str(out))
    old_data,_,reg,old_manifest=read_reference()
    prior=import_old(repo)
    a0=prior.load_a0(repo)
    trial,unresolved,changed,times=prior.load_trial(trial_dir)
    win=repo/'case1/studies/SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1/StudyA_Mapped_SOC_Windows_for_Redispatch.zip'
    if a0.sha(win)!=a0.EXPECTED_WINDOWS_SHA:raise ValueError('Signed SOC-window source mismatch')
    _,_,_,signatures=a0.load_windows(win)
    energy_module=a0.load_module(repo/a0.MOD)
    mp=repo/energy_module.MANIFEST_REL
    ctx=energy_module.secure_context(repo,mp)
    ctx[1].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    row_list=[]
    for item in trial['candidate_files']:
        case=item['case'];dispatch=item['dispatch'];key=(case,dispatch)
        cand_path=trial_dir/item['candidate_file']
        if a0.sha(cand_path)!=item['sha256']:
            raise ValueError('Candidate signature mismatch: '+str(cand_path))
        original,meta,trace,ids,energy_sha,origsha=a0.signed_source(repo,case,dispatch,
            signatures[key],energy_module,ctx,mp)
        if origsha!=item['input_energy_sha256']:
            raise ValueError('Original annual signed energy input mismatch')
        candidate=pd.read_csv(a0.xp(cand_path),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
        hardware=meta['hardware']
        a0.energy_checks(candidate,int(hardware['battery_modules']),
            float(hardware['battery_power_dc_kw']),float(hardware['inverter_kva']),original)
        screens=a0.load_ac_screens(repo,case,dispatch,energy_sha,a0.sha(mp),trace.index,original)
        for pf,length in FACTOR_GRID:
            signed_ac,summary=screens[(pf,length)]
            terr=ctx[1].new_territory(repo,'A0','94022',ids,length)
            nets={}
            for name,lines in BUNDLES.items():
                n,conn=build_net(terr,'head')
                names=n.line.loc[lines,'name'].astype(str) if lines else pd.Series(dtype='str')
                expected_names=reg.set_index('line_index').loc[lines,'line_name'].astype(str) if lines else pd.Series(dtype='str')
                if lines and names.tolist()!=expected_names.tolist():
                    raise ValueError('Model line indices/name changed: '+name)
                if lines:
                    n.line.loc[lines,'r_ohm_per_km'] *= .5
                nets[name]=(n,conn)
            for time in times:
                if time not in candidate.index:raise ValueError('Selected time missing from annual candidate')
                changed_here=changed[(changed.case==case)&changed.dispatch.eq(dispatch)&
                    np.isclose(changed.pf,pf)&np.isclose(changed.length_factor,length)&
                    changed.timestamp_lst.eq(str(time))]
                if len(changed_here)>1:raise ValueError('Duplicate changed-hour signed AC evidence')
                benchmark=changed_here.iloc[0] if len(changed_here) else signed_ac.loc[time]
                if not len(changed_here) and abs(float(candidate.at[time,'inverter_ac_kw'])-
                                                float(original.at[time,'inverter_ac_kw']))>2e-5:
                    raise ValueError('Unaccounted difference in unchanged source AC hour')
                for opt,(n,conn) in nets.items():
                    rec=ctx[1].solve_ac_hour(n,conn,terr,time,trace.loc[time],pf,
                        float(candidate.at[time,'inverter_ac_kw']),float(hardware['inverter_kva']),
                        float(candidate.at[time,'pv_dc_available_kw']),
                        float(summary.get('q_ratio_daylight',.25)),9,'pvbess',pp)
                    if rec['status']!='CONVERGED':raise ValueError('Nonconverged AC '+opt+' '+str(time))
                    if opt=='head_reference':
                        for col,rcol in (('min_v_pu','min_v_pu'),('max_trafo_pct','max_trafo_pct')):
                            if abs(float(rec[col])-float(benchmark[rcol]))>2e-4:
                                raise ValueError('Signed source head AC mismatch '+str((case,dispatch,pf,length,time,col)))
                    house_volts={h:float(n.res_bus.at[conn['buses']['HOUSE_'+h],'vm_pu']) for h in conn['loads']}
                    limiting=min(house_volts,key=house_volts.get)
                    row=dict(case=case,dispatch=dispatch,pf=pf,length_factor=length,
                             timestamp_lst=str(time),option=opt,changed_line_count=len(BUNDLES[opt]),
                             status=rec['status'],minimum_voltage_pu=float(rec['min_v_pu']),
                             maximum_voltage_pu=float(rec['max_v_pu']),
                             transformer_loading_pct=float(rec['max_trafo_pct']),
                             line_loading_pct=float(n.res_line.loc[conn['line_ids'],'loading_percent'].max()),
                             limiting_house=limiting,
                             inverter_ac_kw=float(candidate.at[time,'inverter_ac_kw']),
                             source_event_key=bool((unresolved.case.eq(case)&unresolved.dispatch.eq(dispatch)&
                                unresolved.event_timestamp.eq(str(time))).any()))
                    row['ac_feasible']=bool(rec['ac_feasible'])
                    row_list.append(row)
            print(f'ALL-NINE {case} {dispatch}: pf={pf}, length={length}',flush=True)
    data=pd.DataFrame(row_list)
    controls,errors=validate_rows(data,old_data)
    summary=data.groupby('option',as_index=False).agg(
        n=('ac_feasible','size'),passing=('ac_feasible','sum'),
        minimum_voltage_pu=('minimum_voltage_pu','min'),maximum_voltage_pu=('maximum_voltage_pu','max'),
        peak_transformer_pct=('transformer_loading_pct','max'),peak_line_pct=('line_loading_pct','max'))
    summary['failing']=summary.n-summary.passing
    summary['reference_length_m']=summary.option.map(lambda n:float(reg.set_index('line_index').loc[BUNDLES[n],'length_m'].sum()) if BUNDLES[n] else 0.)
    # Explicit margin display; pass/fail computed from actual measurements, not rounded text.
    summary['voltage_margin_min_pu']=summary.minimum_voltage_pu-.95
    source={
        'status':'TARGETED_A0_94022_ALL_NINE_NOT_ANNUAL',
        'source_dual_service_sha256':SOURCE_SHA,
        'prior_trial_manifest_sha256':digest(trial_dir/'TRIAL_MANIFEST.json'),
        'source_dual_service_manifest_sha256':hashlib.sha256(json.dumps(old_manifest,sort_keys=True).encode()).hexdigest(),
        'source_control_rows_rechecked':controls,'source_control_max_abs_errors':errors,
        'case_dispatch_groups':4,'selected_timestamps':9,
        'pf_length_pairs':[[float(p),float(l)] for p,l in FACTOR_GRID],
        'bundle_options':{k:v for k,v in BUNDLES.items()},
        'ac_rows':len(data),'annual_8760_ac_validated':False,'source_files_modified':False,
        'interpretation':'Assumed service drops and EPM LV graph edges are not verified construction assets; R*0.5 only, ampacity and reactance unchanged. 9 selected hours are not full-year proof.'
    }
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('ALL_NINE_SELECTED_AC_ROWS.csv',data.to_csv(index=False))
        z.writestr('ALL_NINE_OPTION_SUMMARY.csv',summary.to_csv(index=False))
        z.writestr('ALL_NINE_SOURCE_AND_SCOPE.json',json.dumps(source,indent=2)+'\n')
    print(json.dumps({'status':source['status'],'rows':len(data),'source_controls':controls,
                     'passing':summary[['option','passing','n']].to_dict('records'),'out':str(out)},indent=2))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--trial-dir',type=Path,default=TRIAL_DEFAULT)
    ap.add_argument('--out',type=Path,default=Path('StudyA_A0_94022_AllNine_Bundle_v1_Results.zip'))
    ap.add_argument('--preflight',action='store_true')
    args=ap.parse_args()
    old,_,reg,mani=read_reference()
    if args.preflight:
        prior=import_old(args.repo_root.resolve())
        trial,unresolved,changed,times=prior.load_trial(args.trial_dir.resolve())
        print(json.dumps({'status':'ALL_NINE_PREFLIGHT_PASS','prior_uploaded_rows':len(old),
                          'test_bundles':len(BUNDLES),'factor_pairs':len(FACTOR_GRID),
                          'source_timestamps':len(times),'new_ac_rows':4*9*9*len(BUNDLES),
                          'trial_manifest_sha256':digest(args.trial_dir.resolve()/'TRIAL_MANIFEST.json')},indent=2))
        return
    main_run(args.repo_root.resolve(),args.trial_dir.resolve(),args.out.resolve())

if __name__=='__main__':main()
