#!/usr/bin/env python3
"""Read-only, checkpointed annual pandapower validation of research R*0.5 bundles.

Uses the A0 94022 sequenced battery candidates and the archived 432-case source.
No capacity optimization, no signed-source modifications and no physical cable certification.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import os
import sys
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TARGET_ZIP = HERE/'inputs'/'StudyA_A0_94022_AllNine_Bundle_v1_Results.zip'
TARGET_SHA = 'd94c960eb657ac866f8ea70849adc1633a52ccd5c16d656653733ef24126cc2d'
ALLNINE = Path('case1/studies/SEEDExchange_StudyA_94022_AllNine_Bundle_v1/studya_94022_allnine_targeted.py')
TRIAL_DEFAULT = Path('StudyA_A0_94022_Sequenced_Trial_v1')
WINDOWS = Path('case1/studies/SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1/StudyA_Mapped_SOC_Windows_for_Redispatch.zip')
BUNDLES = {'four':[7,4,14,11], 'five':[7,4,14,11,16], 'six':[7,4,14,11,16,18]}
OPTION_NAMES = {'four':'svc007_004_gis014_011_R050',
                'five':'svc007_004_gis014_011_016_R050',
                'six':'svc007_004_gis014_011_016_018_R050'}
FACTOR_GRIDS = {'pilot':[(.95,1.6)], 'reference':[(.98,1.0)],
                'all-nine':[(p,l) for p in (.95,.98,1.) for l in (1.,1.3,1.6)]}
RESULT_FIELDS = ['min_v_pu','max_v_pu','max_trafo_pct','max_line_pct','line_losses_kw','trafo_losses_kw']


def sha(path):
    h=hashlib.sha256()
    with open(xp(path),'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def xp(path):
    s=str(Path(path).resolve())
    if os.name=='nt' and not s.startswith('\\\\?\\'):
        s=('\\\\?\\UNC\\'+s[2:]) if s.startswith('\\\\') else ('\\\\?\\'+s)
    return s


def ensure_dir(path):
    os.makedirs(xp(path),exist_ok=True)


def import_mod(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if not spec or not spec.loader:raise FileNotFoundError(path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def load_target(src=TARGET_ZIP):
    if sha(src)!=TARGET_SHA:
        raise ValueError('All-nine selected-hour source ZIP SHA mismatch')
    with zipfile.ZipFile(xp(src)) as z:
        if z.testzip():raise ValueError('Source archive CRC failed')
        data=pd.read_csv(io.BytesIO(z.read('ALL_NINE_SELECTED_AC_ROWS.csv')))
        summary=pd.read_csv(io.BytesIO(z.read('ALL_NINE_OPTION_SUMMARY.csv')))
        manifest=json.loads(z.read('ALL_NINE_SOURCE_AND_SCOPE.json'))
    if len(data)!=1620 or len(summary)!=5 or data.duplicated(['case','dispatch','pf','length_factor','timestamp_lst','option']).any():
        raise ValueError('Uploaded all-nine source dimensions or identities inconsistent')
    if manifest.get('status')!='TARGETED_A0_94022_ALL_NINE_NOT_ANNUAL' or manifest.get('annual_8760_ac_validated') is not False:
        raise ValueError('All-nine source research-scope metadata inconsistent')
    expected = (data.status.eq('CONVERGED') & data.minimum_voltage_pu.ge(.95) &
                data.maximum_voltage_pu.le(1.05) & data.transformer_loading_pct.le(100) &
                data.line_loading_pct.le(100))
    if not expected.equals(data.ac_feasible):
        raise ValueError('Source feasibility flags differ from electrical outputs')
    for name,opt in OPTION_NAMES.items():
        x=data[data.option.eq(opt)]
        if len(x)!=324 or x.ac_feasible.sum()!=324:
            raise ValueError('Source bundle does not reproduce 324/324: '+name)
    return data,manifest


def select_checks(target,case,dispatch,pf,length,option):
    r=target[(target.case==case)&(target.dispatch==dispatch)&
             np.isclose(target.pf,pf)&np.isclose(target.length_factor,length)&
             target.option.eq(option)]
    if len(r)!=9 or r.timestamp_lst.nunique()!=9:
        raise ValueError('Expected nine unique prevalidated hours in source')
    return r.set_index('timestamp_lst')


def physical_feasible(frame):
    return (frame.status.eq('CONVERGED') & frame.min_v_pu.ge(.95) &
            frame.max_v_pu.le(1.05) & frame.max_trafo_pct.le(100) &
            frame.max_line_pct.le(100))


def verify_completed(folder,provenance):
    csv=folder/'annual_network_ac_hourly.csv'
    j=folder/'annual_network_ac_summary.json'
    if not os.path.isfile(xp(csv)) and not os.path.isfile(xp(j)):return None
    if not os.path.isfile(xp(csv)) or not os.path.isfile(xp(j)):
        raise ValueError('Incomplete existing output, preserving for manual audit: '+str(folder))
    with open(xp(j),encoding='utf-8') as f: meta=json.load(f)
    for key,val in provenance.items():
        if meta.get(key)!=val:raise ValueError('Existing result provenance differs: '+str((key,folder)))
    if sha(csv)!=meta.get('hourly_sha256'):
        raise ValueError('Existing annual file hash mismatch: '+str(csv))
    frame=pd.read_csv(xp(csv))
    if len(frame)!=8760 or frame.timestamp_lst.nunique()!=8760 or frame.status.ne('CONVERGED').any():
        raise ValueError('Existing annual file is incomplete: '+str(folder))
    if not pd.to_datetime(frame.timestamp_lst).equals(pd.Series(pd.date_range('2025-01-01',periods=8760,freq='h'))):
        raise ValueError('Existing annual time grid mismatch: '+str(folder))
    if frame[RESULT_FIELDS].isna().any().any():raise ValueError('Existing annual metrics not finite')
    if not physical_feasible(frame).equals(frame.ac_feasible):
        raise ValueError('Existing feasibility mismatch')
    if int((~frame.ac_feasible).sum())!=meta['AC_infeasible_hours']:
        raise ValueError('Existing annual failure count mismatch')
    return meta


def make_plan(trial,mode,bundle):
    if bundle not in BUNDLES or mode not in FACTOR_GRIDS:raise ValueError('Unsupported bundle/mode')
    candidate_list = trial.get('candidate_files',[])
    if len(candidate_list)!=4 or len(set((x['case'],x['dispatch']) for x in candidate_list))!=4:
        raise ValueError('Four expected source schedule identities not found')
    return [(x,p,l) for x in candidate_list for p,l in FACTOR_GRIDS[mode]]


def record_ac(rec,net,conn,pp,ts,case,dispatch,pf,length,source):
    r={
        'timestamp_lst':str(ts), 'case':case, 'dispatch':dispatch,
        'pf':pf,'length_factor':length,'status':rec['status'],
        'min_v_pu':float(rec['min_v_pu']),'max_v_pu':float(rec['max_v_pu']),
        'max_trafo_pct':float(rec['max_trafo_pct']),
        'max_line_pct':float(net.res_line.loc[conn['line_ids'],'loading_percent'].max()),
        'line_losses_kw':float(net.res_line.pl_mw.sum())*1000/source,
        'trafo_losses_kw':float(net.res_trafo.pl_mw.sum())*1000/source,
    }
    vals=[r[k] for k in RESULT_FIELDS]
    if not np.isfinite(vals).all():raise ValueError('Nonfinite AC result')
    r['ac_feasible']=bool(r['status']=='CONVERGED' and
        r['min_v_pu']>=.95 and r['max_v_pu']<=1.05 and
        r['max_trafo_pct']<=100 and r['max_line_pct']<=100)
    r['inverter_ac_kw']=float(rec.get('inverter_ac_kw',0.0)) if 'inverter_ac_kw' in rec else np.nan
    return r


def assert_control(frame,controls):
    x=frame.set_index('timestamp_lst')
    errors={}
    cols={'min_v_pu':'minimum_voltage_pu','max_v_pu':'maximum_voltage_pu',
          'max_trafo_pct':'transformer_loading_pct','max_line_pct':'line_loading_pct'}
    for ours,old in cols.items():
        err=float(np.max(np.abs(x.loc[controls.index,ours].to_numpy(float)-controls[old].to_numpy(float))))
        errors[ours]=err
    if max(errors.values())>2e-4:
        raise ValueError('Full-year AC differs from 9-hour source controls: '+str(errors))
    if not x.loc[controls.index,'ac_feasible'].astype(bool).equals(controls.ac_feasible.astype(bool)):
        raise ValueError('Selected-hour source feasibility does not match annual replay')
    return errors


def run_job(repo,trial_dir,outroot,item,pf,length,bundle,target,source_manifest,ctx,a0,mod,mp,signatures,reg,pp):
    case=item['case'];dispatch=item['dispatch'];opt=OPTION_NAMES[bundle]
    folder=outroot/f'{bundle}_{case}_{dispatch}_pf{int(round(pf*100)):03d}_l{int(round(length*10)):02d}'
    ensure_dir(folder)
    cand_path=trial_dir/item['candidate_file']
    if a0.sha(cand_path)!=item['sha256']:
        raise ValueError('A0 corrected annual candidate SHA mismatch: '+str(cand_path))
    original,emeta,trace,ids,energy_sha,origsha=a0.signed_source(repo,case,dispatch,
        signatures[(case,dispatch)],mod,ctx,mp)
    if origsha!=item['input_energy_sha256']:
        raise ValueError('Original energy source differs from the accepted shift trial')
    cand=pd.read_csv(a0.xp(cand_path),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    hw=emeta['hardware']
    a0.energy_checks(cand,int(hw['battery_modules']),
        float(hw['battery_power_dc_kw']),float(hw['inverter_kva']),original)
    screens=a0.load_ac_screens(repo,case,dispatch,energy_sha,a0.sha(mp),trace.index,original)
    source_ac,summary=screens[(pf,length)]
    sc=(repo/a0.BASE/'annual_ac_replays_v1'/f'{case}_mapped_{dispatch}_pf{int(round(pf*100)):03d}_length{int(round(length*10)):02d}_annual8760'/'ac_summary.json')
    provenance={
        'case':case,'dispatch':dispatch,'pf':pf,'length_factor':length,'bundle':bundle,
        'branch_indices':BUNDLES[bundle], 'r_multiplier':0.5,
        'input_candidate_sha256':item['sha256'],
        'input_annual_manifest_sha256':energy_sha,
        'original_AC_summary_sha256':a0.sha(sc),
        'original_AC_hourly_sha256':summary['ac_hourly_sha256'],
        'source_target_zip_sha256':TARGET_SHA,
        'source_A0_trial_manifest_sha256':a0.sha(trial_dir/'TRIAL_MANIFEST.json'),
        'annual_8760_AC_validated':True,'physical_cable_selection_validated':False
    }
    prev=verify_completed(folder,provenance)
    if prev is not None:
        print('REUSED VERIFIED',folder.name, 'violations',prev['AC_infeasible_hours'],flush=True)
        return prev
    terr=ctx[1].new_territory(repo,'A0','94022',ids,length)
    from run_epm_validation import build_net
    net,conn=build_net(terr,'head')
    names=net.line.loc[BUNDLES[bundle],'name'].astype(str).tolist()
    expected=reg.set_index('line_index').loc[BUNDLES[bundle],'line_name'].astype(str).tolist()
    if names!=expected:raise ValueError('Network branch index/identity differs from uploaded model')
    net.line.loc[BUNDLES[bundle],'r_ohm_per_km']*=.5
    control=select_checks(target,case,dispatch,pf,length,opt)
    records=[]
    # Source helper normalizes model loading/resistance consistently.
    from run_epm_validation import ROOT_FACTOR
    for idx,t in enumerate(trace.index):
        rec=ctx[1].solve_ac_hour(net,conn,terr,t,trace.loc[t],pf,
            float(cand.at[t,'inverter_ac_kw']),float(hw['inverter_kva']),
            float(cand.at[t,'pv_dc_available_kw']),
            float(summary.get('q_ratio_daylight',.25)),9,'pvbess',pp)
        if rec['status']!='CONVERGED':raise ValueError('Nonconverged annual AC '+str((case,dispatch,pf,length,t)))
        entry=record_ac(rec,net,conn,pp,t,case,dispatch,pf,length,ROOT_FACTOR)
        entry['inverter_ac_kw']=float(cand.at[t,'inverter_ac_kw'])
        records.append(entry)
        if (idx+1)%1000==0:print('  AC',folder.name,idx+1,'/8760',flush=True)
    frame=pd.DataFrame(records)
    if len(frame)!=8760 or frame.status.ne('CONVERGED').any():raise ValueError('Annual AC incomplete')
    check=assert_control(frame,control)
    assert not frame.duplicated('timestamp_lst').any()
    assert frame.timestamp_lst.eq(trace.index.astype(str)).all()
    # Only report AC violations. Do not silently optimize hardware or source dispatch.
    metadata={**provenance,'status':'ANNUAL_AC_RESEARCH_NETWORK_R050',
        'scope':'Full-year 2025 AC power-flow with unchanged A0 94022 battery dispatch and hypothetical 50% R branch reduction',
        'hours':8760,'converged_hours':8760,
        'AC_infeasible_hours':int((~frame.ac_feasible).sum()),
        'min_v_pu':float(frame.min_v_pu.min()),'max_v_pu':float(frame.max_v_pu.max()),
        'max_transformer_pct':float(frame.max_trafo_pct.max()),
        'max_line_pct':float(frame.max_line_pct.max()),
        'annual_line_loss_kwh':float(frame.line_losses_kw.sum()),
        'annual_transformer_loss_kwh':float(frame.trafo_losses_kw.sum()),
        'selected_hour_numerical_reproduction':check,
        'number_of_selected_hour_controls':len(control),
        'assumptions':'R*0.5 on selected model edges only; X/ampacity/transformer unchanged; household services and GIS taps provisional; balanced AC proxy.'}
    b=frame.to_csv(index=False).encode('utf-8')
    metadata['hourly_sha256']=hashlib.sha256(b).hexdigest()
    # Ensure no unsigned partial output is accepted or overwritten.
    csv=folder/'annual_network_ac_hourly.csv';j=folder/'annual_network_ac_summary.json'
    if os.path.exists(xp(csv)) or os.path.exists(xp(j)):
        raise FileExistsError('Signed output appeared while running: '+str(folder))
    with open(xp(csv),'xb') as f:f.write(b)
    with open(xp(j),'x',encoding='utf-8') as f:json.dump(metadata,f,indent=2)
    print('FINISHED',folder.name,'AC violations',metadata['AC_infeasible_hours'],flush=True)
    return metadata


def create_zip(results,root,out):
    if os.path.exists(xp(out)):raise FileExistsError('Refusing to overwrite ZIP '+str(out))
    with zipfile.ZipFile(xp(out),'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for meta in results:
            folder=root/f"{meta['bundle']}_{meta['case']}_{meta['dispatch']}_pf{int(round(meta['pf']*100)):03d}_l{int(round(meta['length_factor']*10)):02d}"
            for name in ('annual_network_ac_hourly.csv','annual_network_ac_summary.json'):
                z.write(xp(folder/name),arcname=folder.name+'/'+name)
        z.writestr('ANNUAL_RUN_SUMMARY.json',json.dumps({
            'status':'ANNUAL_NETWORK_SENSITIVITY_WITH_EXPLICIT_FAILURES',
            'jobs':len(results),'passing_jobs':sum(x['AC_infeasible_hours']==0 for x in results),
            'failing_jobs':sum(x['AC_infeasible_hours']>0 for x in results),
            'source_target_zip_sha256':TARGET_SHA,
            'results':[{k:m[k] for k in ('case','dispatch','pf','length_factor','bundle','AC_infeasible_hours','min_v_pu','max_v_pu','max_transformer_pct','annual_line_loss_kwh')} for m in results],
            'results_are_field_certification':False,'signed_originals_modified':False},indent=2)+'\n')
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--trial-dir',type=Path,default=TRIAL_DEFAULT)
    p.add_argument('--out-dir',type=Path,default=Path('StudyA_A0_94022_Annual_Bundle_Results_v1'))
    p.add_argument('--zip-out',type=Path,default=None)
    p.add_argument('--bundle',choices=sorted(BUNDLES),default='five')
    p.add_argument('--mode',choices=sorted(FACTOR_GRIDS),default='pilot')
    p.add_argument('--preflight',action='store_true')
    x=p.parse_args(argv)
    repo=x.repo_root.resolve(); trial_dir=x.trial_dir.resolve();outroot=x.out_dir.resolve()
    target,source_manifest=load_target()
    modall=import_mod(repo/ALLNINE,'studyA94022_annual_parent')
    original,reg,_,_=None,None,None,None
    ref,_,reg,_=modall.read_reference()
    oldprobe=modall.import_old(repo)
    a0=oldprobe.load_a0(repo)
    j,unresolved,changed,times=oldprobe.load_trial(trial_dir)
    plan=make_plan(j,x.mode,x.bundle)
    if x.preflight:
        print(json.dumps({'status':'PREFLIGHT_PASSED_WITHOUT_SOLVER','input_cases':len(j['candidate_files']),
             'job_count':len(plan),'annual_AC_hours_planned':8760*len(plan),
             'bundle':x.bundle,'mode':x.mode,'selected_source_controls_per_job':9,
             'target_zip_sha256':TARGET_SHA,'trial_manifest_sha256':a0.sha(trial_dir/'TRIAL_MANIFEST.json')},indent=2))
        return
    win=repo/WINDOWS
    if a0.sha(win)!=a0.EXPECTED_WINDOWS_SHA:raise ValueError('Signed SOC-window file changed')
    _,_,_,signatures=a0.load_windows(win)
    energymod=a0.load_module(repo/a0.MOD)
    mp=repo/energymod.MANIFEST_REL
    ctx=energymod.secure_context(repo,mp)
    ctx[1].repo_modules(repo)
    import pandapower as pp
    ensure_dir(outroot)
    results=[]
    for item,pf,length in plan:
        results.append(run_job(repo,trial_dir,outroot,item,pf,length,x.bundle,target,source_manifest,ctx,a0,energymod,mp,signatures,reg,pp))
    out=x.zip_out or Path(f'StudyA_A0_94022_Annual_{x.bundle}_{x.mode}_Results_v1.zip')
    out=out.resolve()
    create_zip(results,outroot,out)
    print(json.dumps({'status':'ANNUAL_RESEARCH_AC_COMPLETE','run_count':len(results),
       'passing_jobs':sum(r['AC_infeasible_hours']==0 for r in results),
       'failing_jobs':sum(r['AC_infeasible_hours']>0 for r in results),
       'archive':str(out)},indent=2))

if __name__=='__main__':main()
