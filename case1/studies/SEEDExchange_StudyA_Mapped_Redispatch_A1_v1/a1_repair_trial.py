#!/usr/bin/env python3
"""Study A A1 mapped-feeder, signed-source, SOC-neutral repair trial.

Requires local original 2025 annual energy and AC files, and the independently
checked 175-event SOC-window ZIP. NEVER overwrites original source results.
Only A1 94022/113699 and the still-uncorrected A1 106039 causal schedules.
Exploratory fixed-hardware shift heuristic, not new optimization or final engineering.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, math, os, re, sys, zipfile
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

BASE=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
MOD=Path('case1/studies/SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py')
ETA_INV=.95
ETA_BAT=math.sqrt(.95)
FLOOR_PER_MODULE=4.325-.8*5.12
PFS=(.95,.98,1.0)
LENGTHS=(1.,1.3,1.6)
MOVES=(.15,.25,.35,.5,.65,.8,1.,1.25,1.5,1.8,2.1,2.5)
TARGETS={'A1_94022_min_cost_ref','A1_94022_ss90_ref',
         'A1_113699_min_cost_ref','A1_106039_min_cost_ref','A1_106039_ss90_ref'}

def xp(path):
    p=Path(path).resolve();s=str(p)
    if os.name=='nt' and not s.startswith('\\\\?\\'):
        s='\\\\?\\UNC\\'+s[2:] if s.startswith('\\\\') else '\\\\?\\'+s
    return s

def sha(path):
    h=hashlib.sha256()
    with open(xp(path),'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def jread(path):
    with open(xp(path),encoding='utf-8') as f:return json.load(f)

def load_module(path):
    s=importlib.util.spec_from_file_location('studya_pvbess_signed_source',path)
    if s is None or s.loader is None:raise FileNotFoundError(path)
    obj=importlib.util.module_from_spec(s);sys.modules[s.name]=obj;s.loader.exec_module(obj)
    return obj

def load_windows(path):
    with zipfile.ZipFile(path) as z:
        r=json.loads(z.read('SOURCE_VERIFICATION.json'))
        e=pd.read_csv(io.BytesIO(z.read('MAPPED_EVENT_SELECTION.csv')),dtype={'transformer':str},parse_dates=['timestamp_lst'])
        w=pd.read_csv(io.BytesIO(z.read('MAPPED_EVENT_SOC_WINDOWS.csv')),dtype={'transformer':str},parse_dates=['event_timestamp','hour_timestamp'])
    if r.get('status')!='READ_ONLY_ANNUAL_WINDOWS_VERIFIED' or (r['event_count'],r['dispatch_source_count'],r['window_hour_rows'])!=(175,16,5075):
        raise ValueError('Wrong mapped windows provenance or dimensions')
    if len(e)!=175 or len(w)!=5075 or len(r['source_files_sha256'])!=16:raise ValueError('Bad mapped evidence dimensions')
    ekey=['scenario','transformer','tier','hardware_family','dispatch','timestamp_lst']
    if e.duplicated(ekey).any():raise ValueError('Duplicate event identities')
    we=['case_family','dispatch','event_timestamp']
    if len(w.groupby(we))!=175 or not (w.groupby(we).size()==29).all():raise ValueError('Missing 29-hour windows')
    if not all(tuple(g.hours_from_event)==tuple(range(-24,5)) for _,g in w.groupby(we,sort=False)):
        raise ValueError('Non-contiguous or reordered window offsets')
    if not (w.hour_timestamp==w.event_timestamp+pd.to_timedelta(w.hours_from_event,unit='h')).all():
        raise ValueError('Window timestamps do not match event offsets')
    if w[['demand_kw','inverter_ac_kw','battery_charge_dc_kw','battery_discharge_dc_kw','battery_soc_usable_kwh']].isna().any().any():
        raise ValueError('Invalid energy values')
    signatures={(x['case_family'],x['dispatch']):x for x in r['source_files_sha256']}
    if len(signatures)!=16:raise ValueError('Duplicate annual source signature')
    return e,w,r,signatures

def selected_a1(e):
    r=e[(e.scenario=='A1') & (e.topology=='mapped') &
        (e.hardware_family=='archived_reference')].copy()
    if len(r)!=19 or len(r.groupby(['scenario','transformer','tier','dispatch']))!=8:
        raise ValueError(f'A1 scope changed, events={len(r)} schedules={r.groupby(["scenario","transformer","tier","dispatch"]).ngroups}')
    if any(f'A1_{x.transformer}_{x.tier}_ref' not in TARGETS for x in r.itertuples()):
        raise ValueError('Unexpected A1 hardware target')
    if len(r[(r.transformer=='106039') & (r.dispatch!='causal')]):
        raise ValueError('106039 optimized already corrected; do not redo')
    return r

def case_parts(case):
    match=re.fullmatch(r'(A[01])_(\d+)_(min_cost|ss90)_(ref|four)',case)
    if match is None:raise ValueError('Unknown Study A case identity: '+case)
    return match.groups()

def signed_source(repo,case,dispatch,expected,mod,m,mp):
    variant,tid,tier,family=case_parts(case)
    if variant!='A1' or family!='ref':raise ValueError('Only A1 archived references')
    ids,trace=mod.source_trace(m[0],m[2],m[3],variant,tid)
    base=repo/BASE
    ef=base/f'energy_{case}'
    optimized,meta=mod.validated_energy_directory(ef,m[0],mp,variant,tid,ids,trace)
    if dispatch=='optimized':
        path=ef/'energy_hourly_2025.csv';d=optimized
    else:
        cf=base/f'causal_{case}'; cm=jread(cf/'causal_summary.json')
        path=cf/'causal_pv_first_2025.csv'
        if cm.get('output_sha256')!=sha(path):raise ValueError('Causal CSV hash mismatch')
        if sha(ef/'energy_manifest.json') not in (cm.get('source_energy_manifest_sha256'),cm.get('reference_energy_manifest_sha256')):
            raise ValueError('Causal energy source mismatch')
        d=pd.read_csv(xp(path),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
        if len(d)!=8760 or not d.index.equals(trace.index):raise ValueError('Bad causal 2025 chronology')
    if sha(path)!=expected['annual_file_sha256']:raise ValueError('SOC-window source SHA differs from signed local file')
    if (int(meta['hardware']['battery_modules']),round(float(meta['hardware']['battery_power_dc_kw']),6),int(meta['hardware']['pv_panels'])) != \
       (int(expected['battery_modules']),round(float(expected['battery_power_dc_kw']),6),int(expected['pv_panels'])):
        raise ValueError('Hardware mismatch to uploaded evidence')
    if abs(float(meta['hardware']['inverter_kva'])-float(expected['inverter_kva']))>1e-6:
        raise ValueError('Inverter rating mismatches uploaded source evidence')
    if np.max(abs(d.demand_kw.to_numpy(float)-trace.sum(axis=1).to_numpy(float)))>1e-4:
        raise ValueError('Demand changed between signed sources')
    return d,meta,trace,ids,sha(ef/'energy_manifest.json'),sha(path)

def energy_checks(frame,modules,dc_kw,inverter_kva,orig=None):
    needed=['demand_kw','battery_discharge_dc_kw','battery_charge_dc_kw','inverter_ac_kw','battery_soc_usable_kwh','pv_dc_available_kw','curtailed_pv_dc_kw','grid_import_kw','grid_export_kw','unserved_kw']
    if not set(needed).issubset(frame.columns):raise ValueError('Missing energy columns '+str(set(needed)-set(frame.columns)))
    if len(frame)!=8760 or not frame.index.equals(pd.date_range('2025-01-01',periods=8760,freq='h')):raise ValueError('Bad annual time')
    x=frame[needed].to_numpy(dtype=float)
    if not np.isfinite(x).all():raise ValueError('Nonfinite energy')
    def mx(expr):return float(np.max(np.abs(expr)))
    ac=frame.inverter_ac_kw.to_numpy(float);imp=frame.grid_import_kw.to_numpy(float)
    discharge=frame.battery_discharge_dc_kw.to_numpy(float);charge=frame.battery_charge_dc_kw.to_numpy(float)
    soc=frame.battery_soc_usable_kwh.to_numpy(float)
    if mx(ac+imp+frame.unserved_kw.to_numpy(float)-frame.grid_export_kw.to_numpy(float)-frame.demand_kw.to_numpy(float))>7e-5:raise ValueError('AC energy balance')
    generated=frame.pv_dc_available_kw.to_numpy(float)-frame.curtailed_pv_dc_kw.to_numpy(float)
    if generated.min()<-7e-5:raise ValueError('PV curtailment exceeds available PV')
    if 'pv_dc_generated_kw' in frame and mx(frame.pv_dc_generated_kw.to_numpy(float)-generated)>7e-5:raise ValueError('PV energy balance')
    if mx(generated+discharge-charge-ac/ETA_INV)>7e-5:raise ValueError('DC energy balance')
    if mx(soc[1:]-soc[:-1]-(ETA_BAT*charge-discharge/ETA_BAT)[1:])>7e-5:raise ValueError('SOC chronology')
    if soc.min()<FLOOR_PER_MODULE*modules-7e-5 or soc.max()>4.325*modules+7e-5:raise ValueError('Battery SOC outside available range')
    if charge.min()<-7e-5 or discharge.min()<-7e-5 or max(charge.max(),discharge.max())>dc_kw+7e-5:raise ValueError('Battery power outside limits')
    if (np.minimum(charge,discharge)>7e-5).any():raise ValueError('Simultaneous charge and discharge')
    if ac.min()<-7e-5 or ac.max()>inverter_kva+7e-5:raise ValueError('Inverter AC power outside rating')
    if imp.min()<-7e-5 or frame.grid_export_kw.abs().max()>7e-5 or frame.unserved_kw.abs().max()>7e-5:raise ValueError('Import/export/ENS policy')
    if orig is not None:
        for k in ('demand_kw','grid_export_kw','unserved_kw','pv_dc_available_kw','curtailed_pv_dc_kw','battery_charge_dc_kw'):
            if mx(frame[k].to_numpy(float)-orig[k].to_numpy(float))>1e-6:raise ValueError('Source quantity changed: '+k)
        for k in ('grid_import_kw','battery_discharge_dc_kw'):
            if abs(float(frame[k].sum()-orig[k].sum()))>1e-4:raise ValueError('Annual sum not preserved: '+k)
        if abs(float(frame.battery_soc_usable_kwh.iloc[-1]-orig.battery_soc_usable_kwh.iloc[-1]))>1e-5:
            raise ValueError('Year-end SOC changed')
    return {'annual_import_kwh':float(imp.sum()),'annual_pv_curtailment_dc_kwh':float(frame.curtailed_pv_dc_kw.sum()),
            'min_soc_kwh':float(soc.min()),'max_soc_kwh':float(soc.max()),'end_soc_kwh':float(soc[-1])}

def shift_one(d,src,dst,move,dc_kw,inverter_kva,modules):
    """Conservatively transfer a fixed DC kWh from earlier same-day discharge."""
    src=pd.Timestamp(src);dst=pd.Timestamp(dst);move=float(move)
    if not (src<dst and src.date()==dst.date() and move>0):raise ValueError('Not a forward, same-day battery shift')
    if src not in d.index or dst not in d.index:raise ValueError('Shift index missing')
    if d.loc[src,'battery_discharge_dc_kw']<move+1e-6:raise ValueError('Insufficient donor discharge')
    if d.loc[dst,'battery_charge_dc_kw']>1e-6:raise ValueError('Target is charging')
    if d.loc[dst,'battery_discharge_dc_kw']+move>dc_kw+1e-6:raise ValueError('Target DC power limit')
    if d.loc[dst,'inverter_ac_kw']+move*ETA_INV>inverter_kva+1e-6:raise ValueError('Target inverter AC power limit')
    if d.loc[dst,'grid_import_kw']<move*ETA_INV-1e-6:raise ValueError('Shift would create export')
    ix=(d.index>=src)&(d.index<dst)
    if float(d.loc[ix,'battery_soc_usable_kwh'].max())+move/ETA_BAT>modules*4.325+1e-6:
        raise ValueError('Intermediate SOC exceeds usable maximum')
    out=d.copy(deep=True)
    for stamp,s in ((src,-1.),(dst,1.)):
        out.loc[stamp,'battery_discharge_dc_kw']+=s*move
        out.loc[stamp,'inverter_ac_kw']+=s*move*ETA_INV
        out.loc[stamp,'grid_import_kw']-=s*move*ETA_INV
        if 'pcc_p_kw' in out:out.loc[stamp,'pcc_p_kw']=out.loc[stamp,'grid_import_kw']-out.loc[stamp,'grid_export_kw']
        if {'pcc_p_kw','pcc_q_kvar_proxy','pcc_kva_proxy'}.issubset(out.columns):
            out.loc[stamp,'pcc_kva_proxy']=math.hypot(float(out.loc[stamp,'pcc_p_kw']),float(out.loc[stamp,'pcc_q_kvar_proxy']))
    out.loc[ix,'battery_soc_usable_kwh']+=move/ETA_BAT
    return out

def load_ac_screens(repo,case,dispatch,energy_sha,mp_sha,index,original):
    screens={}
    for pf in PFS:
        for length in LENGTHS:
            suffix=f'{case}_mapped_{dispatch}_pf{int(round(pf*100)):03d}_length{int(round(length*10)):02d}_annual8760'
            base=repo/BASE/'annual_ac_replays_v1'/suffix
            summary=jread(base/'ac_summary.json')
            if int(summary['hours'])!=8760 or int(summary['converged_hours'])!=8760:
                raise ValueError('AC incomplete '+suffix)
            if summary['energy_manifest_sha256']!=energy_sha or summary['input_manifest_sha256']!=mp_sha:
                raise ValueError('AC source mismatch '+suffix)
            if str(summary['scenario'])!='A1' or str(summary['transformer'])!=case_parts(case)[1] or summary['dispatch']!=dispatch or summary['topology']!='mapped':
                raise ValueError('AC identity mismatch '+suffix)
            if abs(float(summary['pf'])-pf)>1e-9 or abs(float(summary['length_factor'])-length)>1e-9:raise ValueError('AC sensitivity identity')
            if sha(base/'ac_hourly.csv')!=summary['ac_hourly_sha256']:raise ValueError('AC hash mismatch '+suffix)
            ac=pd.read_csv(xp(base/'ac_hourly.csv'),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
            if len(ac)!=8760 or not ac.index.equals(index):raise ValueError('AC annual chronology wrong '+suffix)
            if not (ac.status=='CONVERGED').all():raise ValueError('Signed AC nonconvergence')
            if float(np.max(abs(ac.inverter_ac_kw.to_numpy(float)-original.inverter_ac_kw.to_numpy(float))))>5e-5:
                raise ValueError('AC/energy inverter dispatch mismatch '+suffix)
            if float(np.max(abs(ac.gross_demand_kw.to_numpy(float)-original.demand_kw.to_numpy(float))))>5e-5:
                raise ValueError('AC/energy demand mismatch '+suffix)
            if int((~ac.ac_feasible.astype(bool)).sum())!=int(summary['AC_infeasible_hours']):raise ValueError('AC violation count mismatch')
            screens[(pf,length)]=(ac,summary)
    return screens

def ac_replay(v6,pp,net,node,terr,trace,frame,t,pf,inverter_kva,q_ratio=.25):
    return v6.solve_ac_hour(net,node,terr,t,trace.loc[t],pf,float(frame.loc[t,'inverter_ac_kw']),
        inverter_kva,float(frame.loc[t,'pv_dc_available_kw']),q_ratio,9,'pvbess',pp)

def ac_good(r):return r['status']=='CONVERGED' and bool(r['ac_feasible'])

def inspect_pair(frame,src,dst,nets,screens,trace,v6,pp,kva,check_baseline=False):
    results=[]
    # First run worst of the approved sensitivity grid, then independently all 9
    order=[(.95,1.6)]+[q for q in sorted(screens) if q!=(.95,1.6)]
    for pf,length in order:
        net,node,terr=nets[(pf,length)]
        ac,summary=screens[(pf,length)]
        for t in (src,dst):
            rec=ac_replay(v6,pp,net,node,terr,trace,frame,t,pf,kva,float(summary.get('q_ratio_daylight',.25)))
            results.append({'timestamp_lst':str(t),'pf':pf,'length_factor':length,
                'status':rec['status'],'ac_feasible':bool(rec.get('ac_feasible',False)),
                'max_trafo_pct':float(rec['max_trafo_pct']) if rec['status']=='CONVERGED' else None,
                'min_v_pu':float(rec['min_v_pu']) if rec['status']=='CONVERGED' else None})
            if check_baseline:
                prev=ac.loc[t]
                if rec['status']!='CONVERGED' or any(abs(float(prev[k])-float(rec[k]))>2e-4 for k in ('max_trafo_pct','min_v_pu','max_v_pu','pcc_kva')):
                    raise ValueError(f'Cannot reproduce signed source AC at {t} for {pf}, {length}')
            elif not ac_good(rec):return False,results
    return True,results

def donor_hours(window_rows,dst):
    # 12:00 onward, same calendar date, up to 8 hours before target.
    sub=window_rows[(window_rows.hour_timestamp.dt.date==dst.date()) &
        (window_rows.hour_timestamp>=dst-pd.Timedelta(hours=8)) &
        (window_rows.hour_timestamp<dst) &
        (window_rows.hour_timestamp.dt.hour>=12) &
        (window_rows.battery_discharge_dc_kw>=.15)]
    return list(sub.sort_values('hour_timestamp',ascending=False).hour_timestamp)

def simulate_a1_group(repo,events,windows,signature,mod,ctx,mp,case,dispatch):
    original,meta,trace,ids,energy_sha,source_sha=signed_source(repo,case,dispatch,signature,mod,ctx,mp)
    hw=meta['hardware'];kva=float(hw['inverter_kva']);dc_kw=float(hw['battery_power_dc_kw']);modules=int(hw['battery_modules'])
    before=energy_checks(original,modules,dc_kw,kva)
    screens=load_ac_screens(repo,case,dispatch,energy_sha,sha(mp),trace.index,original)
    ctx[1].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    nets={}
    for pf,length in sorted(screens):
        terr=ctx[1].new_territory(repo,'A1',case_parts(case)[1],ids,length)
        net,node=build_net(terr,'head')
        if set(node['loads'])!=set(ids):raise ValueError('Network cohort changed')
        nets[(pf,length)]=(net,node,terr)
    use=original.copy(deep=True)
    adopted=[];rejected=[];baseline_checked=set()
    g=events[(events.transformer==case_parts(case)[1]) & (events.tier==case_parts(case)[2]) & (events.dispatch==dispatch)]
    for r in g.sort_values('timestamp_lst').itertuples(index=False):
        dest=pd.Timestamp(r.timestamp_lst)
        w=windows[(windows.case_family==case)&(windows.dispatch==dispatch)&(windows.event_timestamp==dest)]
        if len(w)!=29:raise ValueError('Incomplete same-source event window')
        orig_row=w.loc[w.hours_from_event==0].iloc[0]
        for k in ('inverter_ac_kw','battery_soc_usable_kwh','grid_import_kw','battery_discharge_dc_kw'):
            if abs(float(orig_row[k])-float(original.loc[dest,k]))>2e-4:
                raise ValueError('Window data differs from signed local source at '+str(dest))
        attempts=Counter();chosen=None
        for src in donor_hours(w,dest):
            for move in MOVES:
                try:tmp=shift_one(use,src,dest,move,dc_kw,kva,modules)
                except ValueError as exc:attempts['physical_'+str(exc)[:45]]+=1;continue
                try:energy_checks(tmp,modules,dc_kw,kva,original)
                except ValueError as exc:attempts['annual_'+str(exc)[:45]]+=1;continue
                if (src,dest) not in baseline_checked:
                    inspect_pair(original,src,dest,nets,screens,trace,ctx[1],pp,kva,check_baseline=True)
                    baseline_checked.add((src,dest))
                okay,checks=inspect_pair(tmp,src,dest,nets,screens,trace,ctx[1],pp,kva)
                attempts['ac_ok' if okay else 'ac_rejected']+=1
                if okay:
                    use=tmp
                    chosen={'source_hour':str(src),'target_hour':str(dest),'moved_dc_kw':move,
                       'added_target_ac_kw':ETA_INV*move,'replayed_checks':len(checks)}
                    break
            if chosen:break
        if chosen:
            adopted.append({'case':case,'dispatch':dispatch,**chosen})
            print('AC-PASS',case,dispatch,chosen,flush=True)
        else:
            rejected.append({'case':case,'dispatch':dispatch,'event_timestamp':str(dest),
                'peak_trafo_pct':r.peak_trafo_pct,'lowest_v_pu':r.lowest_v_pu,
                'tested_attempts':dict(attempts)})
            print('UNRESOLVED',case,dispatch,str(dest),dict(attempts),flush=True)
    after=energy_checks(use,modules,dc_kw,kva,original)
    checks_final=[];new_summary=[]
    if adopted:
        changed=sorted({pd.Timestamp(x[k]) for x in adopted for k in ('source_hour','target_hour')})
    else:changed=[]
    for (pf,length),(ac,summary) in screens.items():
        # All unmodified hourly AC rows remain signed and unchanged.
        mask=~ac.ac_feasible.astype(bool)
        baseline_bad=int(mask.sum())
        for t in changed:
            net,node,terr=nets[(pf,length)]
            rec=ac_replay(ctx[1],pp,net,node,terr,trace,use,t,pf,kva,float(summary.get('q_ratio_daylight',.25)))
            if rec['status']!='CONVERGED':raise ValueError('Final AC did not converge '+str(t))
            checks_final.append({'case':case,'dispatch':dispatch,'pf':pf,'length_factor':length,
                  'timestamp_lst':str(t),'ac_feasible':bool(rec['ac_feasible']),
                  'max_trafo_pct':float(rec['max_trafo_pct']),'min_v_pu':float(rec['min_v_pu'])})
            mask.loc[t]=not bool(rec['ac_feasible'])
        new_summary.append({'case':case,'dispatch':dispatch,'pf':pf,'length_factor':length,
            'original_bad_hours':baseline_bad,'trial_bad_hours':int(mask.sum()),
            'annual_hours_accounted_for':len(ac),'shift_count':len(adopted),
            'source_ac_sha256':summary['ac_hourly_sha256']})
    return {'case':case,'dispatch':dispatch,'input_energy_sha256':source_sha,
        'input_energy_manifest_sha256':energy_sha,'hardware':hw,'source_checks':before,'candidate_checks':after,
        'shifts':adopted,'unresolved':rejected,'annual_screens':new_summary,
        'changed_ac_checks':checks_final,'candidate':use if adopted else None}

def execute(repo,windows_zip,out,only_case=None,only_dispatch=None):
    if out.exists():raise FileExistsError('Protected output exists: '+str(out))
    e,w,receipt,signatures=load_windows(windows_zip)
    a1=selected_a1(e)
    if only_case:a1=a1[a1.apply(lambda x:f'A1_{x.transformer}_{x.tier}_ref'==only_case,axis=1)]
    if only_dispatch:a1=a1[a1.dispatch==only_dispatch]
    groups=list(a1.groupby(['transformer','tier','dispatch']))
    if not groups:raise ValueError('No selected A1 cases')
    mod=load_module(repo/MOD)
    mp=repo/mod.MANIFEST_REL
    ctx=mod.secure_context(repo,mp)
    result=[]
    for (tid,tier,dispatch),g in groups:
        case=f'A1_{tid}_{tier}_ref'
        print('START',case,dispatch,'events=',len(g),flush=True)
        result.append(simulate_a1_group(repo,a1,w,signatures[(case,dispatch)],mod,ctx,mp,case,dispatch))
    out.mkdir(parents=True,exist_ok=False)
    decisions=[];unresolved=[];screens=[];checks=[];files=[]
    for r in result:
        decisions+=r['shifts'];unresolved+=r['unresolved'];screens+=r['annual_screens'];checks+=r['changed_ac_checks']
        if r['candidate'] is not None:
            name=f'{r["case"]}_{r["dispatch"]}_candidate_8760.csv'
            dest=out/name
            r['candidate'].to_csv(dest,float_format='%.10f')
            files.append({'case':r['case'],'dispatch':r['dispatch'],'candidate_file':name,'sha256':sha(dest),
                          'input_energy_sha256':r['input_energy_sha256'],'energy_original':r['source_checks'],
                          'energy_candidate':r['candidate_checks']})
    pd.DataFrame(decisions).to_csv(out/'ADOPTED_SHIFT_EVENTS.csv',index=False)
    pd.DataFrame(unresolved).to_csv(out/'UNRESOLVED_EVENTS.csv',index=False)
    pd.DataFrame(screens).to_csv(out/'NINE_FACTOR_ANNUAL_REUSE.csv',index=False)
    pd.DataFrame(checks).to_csv(out/'CHANGED_HOURS_FINAL_AC.csv',index=False)
    status='ALL_SELECTED_A1_PASSED' if not unresolved and all(x['trial_bad_hours']==0 for x in screens) else 'PARTIAL_OR_UNRESOLVED'
    manifest={'status':status,'mode':'A1_GREEDY_FIXED_HARDWARE_AC_AWARE_SHIFTS_NOT_PYPSA_OPTIMUM',
      'windows_zip_sha256':sha(windows_zip),'selected_event_count':len(a1),
      'source_group_count':len(groups),'adopted_shift_count':len(decisions),'unresolved_event_count':len(unresolved),
      'annual_factor_comparisons':len(screens),'changed_hour_replays':len(checks),
      'candidate_files':files,'note':['Signed original annual energy/AC files unmodified',
      'Changed hours newly solved; unchanged hours verified and reused',
      'No site field certification, battery dynamic control or full-year new PyPSA optimization',
      'Causal schedules retain their original noncyclic SOC boundary when applicable',
      'This stage addresses A1 only; A0 multi-hour events and proposed 92395 MST remain open']}
    (out/'TRIAL_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--windows-zip',type=Path,default=Path(__file__).with_name('StudyA_Mapped_SOC_Windows_for_Redispatch.zip'))
    ap.add_argument('--out',type=Path,default=Path('StudyA_A1_Mapped_Redispatch_Trial_v1'))
    ap.add_argument('--zip-out',type=Path,default=Path('StudyA_A1_Mapped_Redispatch_Trial_v1.zip'))
    ap.add_argument('--only-case',choices=sorted(TARGETS))
    ap.add_argument('--only-dispatch',choices=['optimized','causal'])
    ap.add_argument('--preflight',action='store_true',help='Audit uploaded windows without solver or local signed sources')
    args=ap.parse_args(argv)
    zip_path=args.windows_zip.resolve()
    e,w,receipt,sigs=load_windows(zip_path)
    a1=selected_a1(e)
    if args.preflight:
        print(json.dumps({'status':'WINDOW_SOURCE_PREFLIGHT_OK','zip_sha256':sha(zip_path),
            'all_175_events':len(e),'all_5075_window_rows':len(w),
            'source_signatures':len(sigs),'selected_a1_events':len(a1),
            'selected_a1_schedules':a1.groupby(['scenario','transformer','tier','dispatch']).ngroups},indent=2));return
    if args.zip_out.resolve().exists():raise FileExistsError('Protected ZIP exists: '+str(args.zip_out))
    result=execute(args.repo_root.resolve(),zip_path,args.out.resolve(),args.only_case,args.only_dispatch)
    output_dir=args.out.resolve()
    with zipfile.ZipFile(args.zip_out.resolve(),'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(output_dir.iterdir()):
            if file.is_file():z.write(file,file.name)
    print(json.dumps({**{k:v for k,v in result.items() if k!='candidate_files'},'result_zip':str(args.zip_out.resolve())},indent=2))

if __name__=='__main__':main()
