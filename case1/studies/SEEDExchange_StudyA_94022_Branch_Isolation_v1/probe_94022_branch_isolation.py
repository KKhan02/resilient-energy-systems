#!/usr/bin/env python3
"""Isolate LV line resistance contribution to nine A0 94022 residual timestamps.

The output is a targeted, read-only electrical sensitivity, NOT an equipment
selection, costed cable upgrade, or 8760-hour annual AC feasibility finding.
The runner imports the original read-only A0 candidate and GIS AC model. It
never edits the signed simulations or the reference 94022 probe.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, os, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

PREVIOUS = Path('case1/studies/SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16/probe_94022_network_options.py')
TRIAL_DEFAULT = Path('StudyA_A0_94022_Sequenced_Trial_v1')
PROBE_DEFAULT = Path(__file__).resolve().parent/'inputs'/'StudyA_A0_94022_Network_Probe_v1.zip'
FACTORS=[(0.98,1.0),(0.95,1.6)]

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def import_previous(repo):
    path=repo/PREVIOUS
    if not path.is_file():raise FileNotFoundError(f'Missing earlier network-probe code: {path}')
    spec=importlib.util.spec_from_file_location('studyA_94022_original_probe',path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def read_prior_probe(path):
    with zipfile.ZipFile(path) as z:
        if z.testzip():raise ValueError('Source probe ZIP CRC mismatch')
        manifest=json.loads(z.read('PROBE_MANIFEST.json'))
        rows=pd.read_csv(io.BytesIO(z.read('A0_94022_NETWORK_OPTION_PROBES.csv')))
        times=pd.read_csv(io.BytesIO(z.read('A0_94022_NINE_RESIDUAL_TIMESTAMPS.csv')))
    if manifest.get('status')!='TARGETED_NETWORK_OPTION_SENSITIVITY_ONLY':raise ValueError('Incorrect source probe status')
    if manifest.get('rows')!=360 or len(rows)!=360 or len(times)!=9:raise ValueError('Incorrect source probe dimensions')
    if sorted(tuple(x) for x in manifest['factors'])!=sorted(FACTORS):raise ValueError('Unexpected source probe factor set')
    if rows.status.ne('CONVERGED').any():raise ValueError('Nonconverged source probe row')
    keys=['case','dispatch','pf','length_factor','timestamp_lst','option']
    if rows.duplicated(keys).any():raise ValueError('Duplicate source probe case')
    if not set(times.timestamp_lst).issubset(set(rows.timestamp_lst)):raise ValueError('Probe timestamps inconsistent')
    return manifest,rows,times

def line_metadata(net,meta):
    result=[]
    for i in meta['line_ids']:
        row=net.line.loc[i]
        nm=str(row['name'])
        kind='EPM_GIS_LV' if nm.startswith('gis_lv_') else 'ASSUMED_SERVICE' if nm.startswith('assumed_service_') else 'OTHER'
        if kind=='OTHER':raise ValueError('Unrecognized line kind '+nm)
        result.append(dict(line_index=int(i),line_name=nm,kind=kind,
            length_m=float(row.length_km)*1000,r_ohm_per_km=float(row.r_ohm_per_km),
            x_ohm_per_km=float(row.x_ohm_per_km),max_i_ka=float(row.max_i_ka)))
    if not result:raise ValueError('No model LV line indices')
    return pd.DataFrame(result)

def options(lines):
    groups={'head_reference':[],
            'all_LV_R050':lines.line_index.tolist(),
            'GIS_only_R050':lines.loc[lines.kind.eq('EPM_GIS_LV'),'line_index'].tolist(),
            'service_only_R050':lines.loc[lines.kind.eq('ASSUMED_SERVICE'),'line_index'].tolist()}
    if len(groups['GIS_only_R050'])==0 or len(groups['service_only_R050'])==0:
        raise ValueError('Missing EPM GIS or assumed-service edges')
    for idx in lines.line_index:
        groups[f'line_{int(idx):03d}_R050']=[int(idx)]
    return groups

def consistent_catalog(reference,current):
    ref=reference.sort_values('line_index').reset_index(drop=True)
    now=current.sort_values('line_index').reset_index(drop=True)
    if len(ref)!=len(now) or not ref[['line_index','line_name','kind']].equals(now[['line_index','line_name','kind']]):
        raise ValueError('Network line index/catalog changed between scenarios')
    if not np.allclose(ref[['length_m','r_ohm_per_km','x_ohm_per_km','max_i_ka']],
                       now[['length_m','r_ohm_per_km','x_ohm_per_km','max_i_ka']],rtol=1e-9,atol=1e-9):
        raise ValueError('Line electrical data changed between scenarios')

def check_probe_head(ac,baseline,tolerance=2e-4):
    if ac['status']!='CONVERGED':raise ValueError('Baseline head AC nonconvergent')
    for name,old in [('min_v_pu','minimum_voltage_pu'),('max_v_pu','maximum_voltage_pu'),
                     ('max_trafo_pct','transformer_loading_pct')]:
        if abs(float(ac[name])-float(baseline[old]))>tolerance:
            raise ValueError('Source probe mismatch '+name+': '+str((ac[name],baseline[old])))

def check_feasible(row):
    if row['status']!='CONVERGED':return False
    return bool(row['minimum_voltage_pu']>=0.95-1e-7 and row['maximum_voltage_pu']<=1.05+1e-7 and
        row['transformer_loading_pct']<=100+1e-6 and row['line_loading_pct']<=100+1e-6)

def run(repo,trial_dir,probe_zip,out_zip):
    if out_zip.exists():raise FileExistsError('Refusing to overwrite '+str(out_zip))
    prior=import_previous(repo)
    a0=prior.load_a0(repo)
    trial,unresolved,changed,times=prior.load_trial(trial_dir)
    prior_manifest,source,source_times=read_prior_probe(probe_zip)
    if prior.digest_file(trial_dir/'TRIAL_MANIFEST.json')!=prior_manifest['source_trial_manifest_sha256']:
        raise ValueError('Source trial manifest is not the signed version used in probe')
    win=repo/'case1/studies/SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1/StudyA_Mapped_SOC_Windows_for_Redispatch.zip'
    if a0.sha(win)!=prior_manifest['source_window_archive_sha256']:
        raise ValueError('Mapped SOC source ZIP checksum changed')
    _,_,_,signatures=a0.load_windows(win)
    mod=a0.load_module(repo/a0.MOD)
    mp=repo/mod.MANIFEST_REL
    ctx=mod.secure_context(repo,mp)
    ctx[1].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    outputs=[]
    catalog=None
    for item in trial['candidate_files']:
        case=item['case'];dispatch=item['dispatch'];key=(case,dispatch)
        path=trial_dir/item['candidate_file']
        if a0.sha(path)!=item['sha256']:raise ValueError('Candidate file SHA mismatch: '+str(path))
        original,meta,trace,ids,energy_sha,originalsha=a0.signed_source(
            repo,case,dispatch,signatures[key],mod,ctx,mp)
        if originalsha!=item['input_energy_sha256']:raise ValueError('Signed energy file mismatch')
        candidate=pd.read_csv(a0.xp(path),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
        hw=meta['hardware']
        a0.energy_checks(candidate,int(hw['battery_modules']),float(hw['battery_power_dc_kw']),float(hw['inverter_kva']),original)
        screens=a0.load_ac_screens(repo,case,dispatch,energy_sha,a0.sha(mp),trace.index,original)
        for pf,length in FACTORS:
            signed_ac,summary=screens[(pf,length)]
            terr=ctx[1].new_territory(repo,'A0','94022',ids,length)
            n0,conn0=build_net(terr,'head')
            raw_catalog=line_metadata(n0,conn0)
            # line length can change with the service length factor; compare indices/types,
            # and make the registered catalog report specifically the reference length=1.0.
            if length==1.0:
                if catalog is None:catalog=raw_catalog
                else:consistent_catalog(catalog,raw_catalog)
            opt_map=options(raw_catalog)
            models={}
            for label,indices in opt_map.items():
                net,connection=build_net(terr,'head')
                if indices:
                    net.line.loc[indices,'r_ohm_per_km'] *= .5
                models[label]=(net,connection)
            for stamp in times:
                prev=source[(source.case==case)&(source.dispatch==dispatch)&
                            np.isclose(source.pf,pf)&np.isclose(source.length_factor,length)&
                            source.timestamp_lst.eq(str(stamp))&source.option.eq('head_reference')]
                if len(prev)!=1:raise ValueError('Prior head source row missing or duplicated')
                for label,(net,connection) in models.items():
                    rec=ctx[1].solve_ac_hour(net,connection,terr,stamp,trace.loc[stamp],pf,
                        float(candidate.at[stamp,'inverter_ac_kw']),float(hw['inverter_kva']),
                        float(candidate.at[stamp,'pv_dc_available_kw']),
                        float(summary.get('q_ratio_daylight',.25)),9,'pvbess',pp)
                    if label=='head_reference':check_probe_head(rec,prev.iloc[0])
                    if rec['status']!='CONVERGED':
                        raise ValueError(f'Nonconvergent branch probe: {label}, {case}, {stamp}, {pf}, {length}')
                    voltages={house:float(net.res_bus.at[connection['buses']['HOUSE_'+house],'vm_pu'])
                              for house in sorted(connection['loads'])}
                    limiting=min(voltages,key=voltages.get)
                    row={'case':case,'dispatch':dispatch,'pf':pf,'length_factor':length,
                        'timestamp_lst':str(stamp),'option':label,'changed_line_count':len(opt_map[label]),
                        'status':rec['status'],'minimum_voltage_pu':float(rec['min_v_pu']),
                        'maximum_voltage_pu':float(rec['max_v_pu']),
                        'transformer_loading_pct':float(rec['max_trafo_pct']),
                        'line_loading_pct':float(net.res_line.loc[connection['line_ids'],'loading_percent'].max()),
                        'limiting_house':limiting,'inverter_ac_kw':float(candidate.at[stamp,'inverter_ac_kw']),
                        'original_event_key':bool((unresolved.case.eq(case)&unresolved.dispatch.eq(dispatch)&
                                                 unresolved.event_timestamp.eq(str(stamp))).any())}
                    row['ac_feasible']=check_feasible(row)
                    if label=='head_reference' and row['ac_feasible']!=bool(prev.iloc[0]['ac_feasible']):
                        raise ValueError('Head AC feasible result differs from supplied probe')
                    outputs.append(row)
            print(f'BRANCH SCREEN {case} {dispatch} PF={pf} factor={length}',flush=True)
    result=pd.DataFrame(outputs)
    if catalog is None:raise ValueError('Missing reference line catalog')
    groups=options(catalog)
    expected=4*len(FACTORS)*9*len(groups)
    if len(result)!=expected:raise ValueError(f'Unexpected count {len(result)} versus {expected}')
    by_option=result.groupby('option',as_index=False).agg(n=('ac_feasible','size'),passing=('ac_feasible','sum'),
        min_voltage_pu=('minimum_voltage_pu','min'),max_voltage_pu=('maximum_voltage_pu','max'),
        peak_transformer_pct=('transformer_loading_pct','max'),peak_line_pct=('line_loading_pct','max'))
    by_option['scope']='nine_residual_timestamps_two_factor_screen_only'
    manifest={'status':'BRANCH_ISOLATION_TARGETED_ONLY','source_probe_sha256':digest(probe_zip),
        'source_trial_manifest_sha256':prior_manifest['source_trial_manifest_sha256'],
        'factors':FACTORS,'timestamps':9,'dispatch_design_groups':4,
        'line_count':len(catalog),'options_count':len(groups),'rows':len(result),
        'note':'Every R=0.5 sensitivity changes resistance only, not reactance, ampacity, routing, installation cost, or nameplate. GIS and house connections remain provisional.',
        'annual_AC_8760_verified':False,'source_files_modified':False}
    with zipfile.ZipFile(out_zip,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('BRANCH_SCREEN_AC_HOURLY.csv',result.to_csv(index=False))
        z.writestr('BRANCH_SCREEN_OPTION_SUMMARY.csv',by_option.to_csv(index=False))
        z.writestr('94022_LV_BRANCH_REGISTER.csv',catalog.to_csv(index=False))
        z.writestr('BRANCH_SCREEN_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--trial-dir',type=Path,default=TRIAL_DEFAULT)
    p.add_argument('--prior-probe',type=Path,default=PROBE_DEFAULT)
    p.add_argument('--out',type=Path,default=Path('StudyA_94022_Branch_Isolation_v1.zip'))
    p.add_argument('--preflight',action='store_true')
    x=p.parse_args();repo=x.repo_root.resolve()
    trial=x.trial_dir.resolve();probe=x.prior_probe.resolve()
    for f in [repo/PREVIOUS,repo/'case1/studies/SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1/a0_sequenced_trial.py',
              trial/'TRIAL_MANIFEST.json',probe]:
        if not f.is_file():raise FileNotFoundError('Required source missing: '+str(f))
    if x.preflight:
        m,r,t=read_prior_probe(probe)
        print(json.dumps({'status':'BRANCH_SCREEN_PREFLIGHT_OK','source_rows':len(r),
            'source_timestamps':len(t),'factors':m['factors'],
            'source_trial_sha_match':digest(trial/'TRIAL_MANIFEST.json')==m['source_trial_manifest_sha256']},indent=2))
        if digest(trial/'TRIAL_MANIFEST.json')!=m['source_trial_manifest_sha256']:
            raise ValueError('Source trial checksum mismatch')
        return
    print(json.dumps(run(repo,trial,probe,x.out.resolve()),indent=2))

if __name__=='__main__':main()
