#!/usr/bin/env python3
"""Read-only targeted AC siting/line-resistance research screen for unresolved A0 94022 hours.

Uses exact candidate annual schedules from A0 94022 sequenced trial and the previously
signed local Study A energy and AC files. This is a research sensitivity, NOT a
validated cable upgrade, physical siting approval, or full-year AC validation.
No source files are written.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, os, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

REPO_A0 = Path('case1/studies/SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1/a0_sequenced_trial.py')
EXPECTED_ORIGINAL_A0_EVENTS = 112
OPTIONS = [
    ('head_reference','head',1.0),
    ('middle_siting_proxy','middle',1.0),
    ('end_siting_proxy','end',1.0),
    ('head_R_075_proxy','head',0.75),
    ('head_R_050_proxy','head',0.50),
]
STANDARD_FACTORS = [(0.98,1.0), (0.95,1.6)]

def digest_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def load_a0(repo):
    path=repo/REPO_A0
    if not path.is_file():raise FileNotFoundError('Previous immutable A0 trial runner not found: '+str(path))
    spec=importlib.util.spec_from_file_location('a0_source_verified_trial',path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def load_trial(trial_dir):
    j=json.loads((trial_dir/'TRIAL_MANIFEST.json').read_text(encoding='utf-8'))
    if (j['tested_transformer']!='94022' or j['selected_event_count']!=EXPECTED_ORIGINAL_A0_EVENTS or
        j['source_group_count']!=4 or j['adopted_shift_count']!=80 or j['unresolved_event_count']!=32 or
        j['status']!='PARTIAL_OR_UNRESOLVED'):
        raise ValueError('Unexpected 94022 trial provenance or trial status')
    unresolved=pd.read_csv(trial_dir/'UNRESOLVED_EVENTS.csv')
    changes=pd.read_csv(trial_dir/'CHANGED_HOURS_FINAL_AC.csv')
    if len(unresolved)!=32 or len(changes)!=1368:raise ValueError('Unexpected AC/event count')
    # Select nine distinct clock times. Do not pretend this is a full annual rerun.
    times=pd.DatetimeIndex(pd.to_datetime(unresolved.event_timestamp.unique())).sort_values()
    if len(times)!=9:raise ValueError('Expected nine distinct unresolved timestamps')
    return j,unresolved,changes,times

def scenario_options(broad=False):
    if broad:return [(pf, length) for pf in (0.95,0.98,1.0) for length in (1.0,1.3,1.6)]
    return STANDARD_FACTORS

def make_option(territory,build_net,option):
    name,siting,rscale=option
    net,meta=build_net(territory,siting)
    if rscale!=1.0:
        # Resistance-only proxy on the assumed GIS/service LV line models.
        # NOT a manufacturer conductor specification, transformer change,
        # site capacity change or approved engineering design.
        net.line.loc[meta['line_ids'],'r_ohm_per_km'] *= rscale
    return net,meta

def relative_equal(x,y,tol=2e-4):
    return abs(float(x)-float(y))<=tol

def run(repo,trial_dir,out_zip,all_nine=False):
    if out_zip.exists():raise FileExistsError('Refusing overwrite: '+str(out_zip))
    a0=load_a0(repo)
    trial,unresolved,changed,times=load_trial(trial_dir)
    window_path=repo/'case1/studies/SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1/StudyA_Mapped_SOC_Windows_for_Redispatch.zip'
    if a0.sha(window_path)!=a0.EXPECTED_WINDOWS_SHA:raise ValueError('SOC window source archive hash mismatch')
    _,_,_,signatures=a0.load_windows(window_path)
    mod=a0.load_module(repo/a0.MOD)
    mp=repo/mod.MANIFEST_REL
    ctx=mod.secure_context(repo,mp)
    ctx[1].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    rows=[]
    factors=scenario_options(all_nine)
    for item in trial['candidate_files']:
        case=item['case'];dispatch=item['dispatch']; key=(case,dispatch)
        cand_path=trial_dir/item['candidate_file']
        if a0.sha(cand_path)!=item['sha256']:raise ValueError('Candidate file SHA-256 mismatch: '+str(cand_path))
        original,meta,trace,ids,energy_sha,origsha=a0.signed_source(repo,case,dispatch,signatures[key],mod,ctx,mp)
        if origsha!=item['input_energy_sha256']:raise ValueError('Original signed dispatch changed')
        candidate=pd.read_csv(a0.xp(cand_path),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
        hw=meta['hardware']
        a0.energy_checks(candidate,int(hw['battery_modules']),float(hw['battery_power_dc_kw']),float(hw['inverter_kva']),original)
        screens=a0.load_ac_screens(repo,case,dispatch,energy_sha,a0.sha(mp),trace.index,original)
        for pf,length in factors:
            signed_ac,summary=screens[(pf,length)]
            territory=ctx[1].new_territory(repo,'A0','94022',ids,length)
            nets={o[0]:make_option(territory,build_net,o) for o in OPTIONS}
            for timestamp in times:
                if timestamp not in candidate.index:raise ValueError('Missing selected date')
                # Head case must reproduce previously verified local final trial
                # at modified hours, otherwise unmodified original signed AC.
                used_changed=changed[(changed.case==case)&(changed.dispatch==dispatch)&
                    np.isclose(changed.pf,pf)&np.isclose(changed.length_factor,length)&
                    (changed.timestamp_lst==str(timestamp))]
                if len(used_changed)>1:raise ValueError('Duplicate local changed hour evidence')
                benchmark=used_changed.iloc[0] if len(used_changed)==1 else signed_ac.loc[timestamp]
                if len(used_changed)==0 and abs(float(candidate.at[timestamp,'inverter_ac_kw'])-
                          float(original.at[timestamp,'inverter_ac_kw']))>2e-5:
                    raise ValueError('Unaccounted input change in supposedly unchanged source AC hour')
                for label,net_siting,rscale in OPTIONS:
                    net,connection=nets[label]
                    rec=ctx[1].solve_ac_hour(net,connection,territory,timestamp,trace.loc[timestamp],pf,
                        float(candidate.at[timestamp,'inverter_ac_kw']),float(hw['inverter_kva']),
                        float(candidate.at[timestamp,'pv_dc_available_kw']),
                        float(summary.get('q_ratio_daylight',.25)),9,'pvbess',pp)
                    if rec['status']!='CONVERGED':
                        rows.append({'case':case,'dispatch':dispatch,'pf':pf,'length_factor':length,
                            'timestamp_lst':str(timestamp),'option':label,'status':rec['status'],
                            'ac_feasible':False,'residual_hour':bool((unresolved.case.eq(case)&
                               unresolved.dispatch.eq(dispatch)&unresolved.event_timestamp.eq(str(timestamp))).any())})
                        if label=='head_reference':raise ValueError('Original head-source model now nonconvergent')
                        continue
                    house_voltages={house:float(net.res_bus.at[connection['buses']['HOUSE_'+house],'vm_pu'])
                        for house in sorted(connection['loads'])}
                    min_house=min(house_voltages,key=house_voltages.get)
                    if label=='head_reference':
                        if (not relative_equal(rec['max_trafo_pct'],benchmark['max_trafo_pct']) or
                            not relative_equal(rec['min_v_pu'],benchmark['min_v_pu'])):
                            raise ValueError('Source AC head-model cannot reproduce '+str((case,dispatch,pf,length,timestamp)))
                    rows.append({'case':case,'dispatch':dispatch,'pf':pf,'length_factor':length,
                        'timestamp_lst':str(timestamp),'option':label,'status':rec['status'],
                        'ac_feasible':bool(rec['ac_feasible']),'minimum_voltage_pu':float(rec['min_v_pu']),
                        'maximum_voltage_pu':float(rec['max_v_pu']),'transformer_loading_pct':float(rec['max_trafo_pct']),
                        'line_loading_pct':float(net.res_line.loc[connection['line_ids'],'loading_percent'].max()),
                        'limiting_house':min_house,'limiting_house_voltage_pu':house_voltages[min_house],
                        'inverter_ac_kw':float(candidate.at[timestamp,'inverter_ac_kw']),
                        'grid_import_kw':float(candidate.at[timestamp,'grid_import_kw']),
                        'pv_dc_available_kw':float(candidate.at[timestamp,'pv_dc_available_kw']),
                        'residual_hour':bool((unresolved.case.eq(case)&unresolved.dispatch.eq(dispatch)&
                           unresolved.event_timestamp.eq(str(timestamp))).any()),
                        'line_r_scale':rscale,'siting_assumption':net_siting})
            print('SCREEN',case,dispatch,'PF',pf,'factor',length,flush=True)
    output=pd.DataFrame(rows)
    expected=len(trial['candidate_files'])*len(factors)*len(times)*len(OPTIONS)
    if len(output)!=expected:raise ValueError(f'Expected {expected} rows, found {len(output)}')
    report={'status':'TARGETED_NETWORK_OPTION_SENSITIVITY_ONLY',
        'baseline_head_reproduces_trial_or_original_hourly_AC':True,
        'source_trial_manifest_sha256':digest_file(trial_dir/'TRIAL_MANIFEST.json'),
        'source_window_archive_sha256':a0.EXPECTED_WINDOWS_SHA,
        'options':[{'name':a,'siting':b,'resistance_multiplier':c} for a,b,c in OPTIONS],
        'factors':list(map(list,factors)),'unique_probe_hours':len(times),
        'annual_profiles_per_hour':len(trial['candidate_files']),
        'rows':len(output),'not_annual_feasibility':True,
        'loss_aware_reoptimization':False,'originals_modified':False,
        'scope':'Exploratory network/electrical siting sensitivity for proposed A0 94022; compare limiting house, not certified routing.'}
    if out_zip.exists():raise FileExistsError(str(out_zip))
    with zipfile.ZipFile(out_zip,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('A0_94022_NETWORK_OPTION_PROBES.csv',output.to_csv(index=False))
        z.writestr('A0_94022_NINE_RESIDUAL_TIMESTAMPS.csv',pd.DataFrame({'timestamp_lst':times.astype(str)}).to_csv(index=False))
        z.writestr('PROBE_MANIFEST.json',json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--trial-dir',type=Path,default=Path('StudyA_A0_94022_Sequenced_Trial_v1'))
    p.add_argument('--out-zip',type=Path,default=Path('StudyA_A0_94022_Network_Probe_v1.zip'))
    p.add_argument('--all-nine',action='store_true',help='Use full 9 PF/length conditions rather than reference+stress pair')
    p.add_argument('--preflight',action='store_true',help='Check trial files and counts, no model execution')
    x=p.parse_args()
    repo=x.repo_root.resolve();trial=x.trial_dir.resolve()
    j,u,c,times=load_trial(trial)
    if x.preflight:
        print(json.dumps({'status':'TRIAL_INPUT_PREFLIGHT_OK','trial':str(trial),
            'candidate_files':len(j['candidate_files']),'adopted_shifts':j['adopted_shift_count'],
            'unresolved_records':len(u),'distinct_residual_hours':len(times),
            'selected_PF_length_pairs':len(scenario_options(x.all_nine))},indent=2));return
    print(json.dumps(run(repo,trial,x.out_zip.resolve(),x.all_nine),indent=2))

if __name__=='__main__':main()
