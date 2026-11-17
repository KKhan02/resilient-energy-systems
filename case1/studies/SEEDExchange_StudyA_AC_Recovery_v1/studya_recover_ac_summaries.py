#!/usr/bin/env python3
"""Guarded recovery of missing Study A PV+BESS annual AC summaries.

Inspects but does not alter existing results by default. With --repair, reconstructs
ONLY a missing ac_summary.json from an existing complete, individually validated
8760-row ac_hourly.csv. Never changes the hourly CSV, source models, or histories.

This is post-processing and source provenance restoration, NOT a new power flow.
An incomplete CSV, failed AC hour, mismatched dispatch, unexpected case identity,
nonfinite outputs, or nonreproducible flags are grounds to reject recovery.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import pandas as pd
import numpy as np

BASE = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
SRC = Path('case1/studies/SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1/run_annual_replays.py')
MANIFEST = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json')
NEEDED = {'timestamp_lst','gross_demand_kw','inverter_ac_kw','status','ac_feasible',
          'min_v_pu','max_v_pu','max_trafo_pct','max_line_pct','loss_kw',
          'voltage_below_095','voltage_above_105','trafo_over_100','line_over_100'}



def windows_extended_path(path):
    """Use Windows extended-length path syntax for filesystem I/O only.

    This changes neither the target directory nor its contents.  The prefix
    bypasses the legacy MAX_PATH boundary for standard Python file operations.
    Leave ordinary paths unchanged on non-Windows hosts.
    """
    path = Path(path)
    if sys.platform != 'win32':
        return path
    raw = str(path)
    if raw.startswith('\\\\?\\'):
        return path
    raw = str(path if path.is_absolute() else path.absolute())
    if raw.startswith('\\\\'):
        return Path('\\\\?\\UNC\\' + raw[2:])
    return Path('\\\\?\\' + raw)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda:fh.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def boolcol(df, key):
    values=df[key].astype(str).str.strip().str.lower()
    if not values.isin(['true','false','1','0']).all():
        raise ValueError(f'{key}: not a strict bool column')
    return values.isin(['true','1']).to_numpy(dtype=bool)


def check_and_reconstruct(job, manifest, input_sha):
    """Return a summary dict only if all chronological, source, and AC checks pass."""
    result=windows_extended_path(job['output'])/'ac_hourly.csv'
    if not result.is_file():raise ValueError('Missing AC hourly CSV')
    if (windows_extended_path(job['output'])/'ac_summary.json').exists():
        raise ValueError('AC summary already exists; no recovery')
    raw=pd.read_csv(result)
    if not NEEDED.issubset(raw.columns):
        raise ValueError('Missing AC CSV fields: '+str(sorted(NEEDED-set(raw.columns))))
    if len(raw)!=8760:raise ValueError(f'AC CSV contains {len(raw)} not 8760 rows')
    when=pd.to_datetime(raw['timestamp_lst'],errors='coerce')
    expected=pd.date_range('2025-01-01',periods=8760,freq='h')
    if when.isna().any() or not pd.DatetimeIndex(when).equals(expected):
        raise ValueError('Hourly AC timestamps not complete unique 2025 LST chronology')
    if not (raw['status'].astype(str)=='CONVERGED').all():
        counts=raw['status'].astype(str).value_counts().to_dict()
        raise ValueError('AC failure statuses in CSV: '+str(counts)+'; require original run diagnostics')
    numcols=['gross_demand_kw','inverter_ac_kw','min_v_pu','max_v_pu',
             'max_trafo_pct','max_line_pct','loss_kw']
    for name in numcols:
        data=pd.to_numeric(raw[name],errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(data).all():raise ValueError(f'{name}: null/non-finite values')
    if (raw['gross_demand_kw']<0).any() or (raw['inverter_ac_kw']<-1e-6).any():
        raise ValueError('Negative gross demand or inverter AC power')
    if (raw['max_trafo_pct']<0).any() or (raw['max_line_pct']<0).any() or (raw['loss_kw']<-1e-5).any():
        raise ValueError('Invalid transformer/line/loss data')
    if (raw['min_v_pu']>raw['max_v_pu']+1e-8).any():
        raise ValueError('Minimum voltage exceeds maximum voltage')
    if 'load_pf' in raw.columns:
        pf=pd.to_numeric(raw['load_pf'],errors='coerce').to_numpy(float)
        if not np.isfinite(pf).all() or np.max(np.abs(pf-job['pf']))>1e-9:
            raise ValueError('Recorded AC power factors mismatch this case')
    if 'ac_feasible' in raw.columns:
        flag=boolcol(raw,'ac_feasible')
        calc=(raw['min_v_pu'].to_numpy(float)>=.95-1e-6)&(raw['max_v_pu'].to_numpy(float)<=1.05+1e-6)&\
             (raw['max_trafo_pct'].to_numpy(float)<=100+1e-4)&(raw['max_line_pct'].to_numpy(float)<=100+1e-4)
        if not np.array_equal(flag,calc):
            raise ValueError(f'AC feasible flags differ from solved voltage/thermal values in {int((flag!=calc).sum())} hours')
    else:raise ValueError('AC feasibility flag missing')
    tests={
        'voltage_below_095':raw['min_v_pu'].to_numpy(float)<.95-1e-6,
        'voltage_above_105':raw['max_v_pu'].to_numpy(float)>1.05+1e-6,
        'trafo_over_100':raw['max_trafo_pct'].to_numpy(float)>100+1e-4,
        'line_over_100':raw['max_line_pct'].to_numpy(float)>100+1e-4}
    for name,expr in tests.items():
        flags=pd.to_numeric(raw[name],errors='coerce').to_numpy(float)
        if not np.isfinite(flags).all() or not np.isin(flags,[0,1]).all():
            raise ValueError(f'{name}: invalid binary flags')
        if not np.array_equal(flags.astype(bool),expr):
            raise ValueError(f'{name}: {int((flags.astype(bool)!=expr).sum())} mismatches')
    from_source=job['causal']/'causal_pv_first_2025.csv' if job['dispatch']=='causal' else job['energy']/'energy_hourly_2025.csv'
    if not from_source.exists():raise ValueError('Missing same-case signed dispatch CSV')
    source=pd.read_csv(from_source)
    if len(source)!=8760 or 'demand_kw' not in source or 'inverter_ac_kw' not in source:
        raise ValueError('Source dispatch lacks full year or required columns')
    if max(float(np.max(np.abs(raw['gross_demand_kw'].to_numpy(float)-source['demand_kw'].to_numpy(float)))),
           float(np.max(np.abs(raw['inverter_ac_kw'].to_numpy(float)-source['inverter_ac_kw'].to_numpy(float)))))>2e-5:
        raise ValueError('AC gross demand/inverter power differs from source dispatch')
    energy_meta=json.loads((job['energy']/'energy_manifest.json').read_text(encoding='utf-8'))
    if energy_meta.get('input_manifest_sha256')!=input_sha:
        raise ValueError('Input manifest signature differs from source energy')
    if energy_meta.get('selected_house_ids')!=manifest['groups'][job['variant']][job['transformer']]:
        raise ValueError('Household population does not match signed manifest')
    if energy_meta.get('hardware_selection_tier')!=job['tier']:
        raise ValueError('Equipment tier mismatch')
    if job['dispatch']=='causal':
        c=json.loads((job['causal']/'causal_summary.json').read_text(encoding='utf-8'))
        if c.get('output_sha256')!=digest(from_source):raise ValueError('Causal dispatch hash differs')
    else:
        if energy_meta.get('energy_csv_sha256')!=digest(from_source):raise ValueError('Energy dispatch hash differs')
    # Exact same aggregate keys as source Study A v1 implementation. The added
    # recovery_provenance field prevents confusion with a source-written summary.
    summary={'status':'ANNUAL_PVBESS_AC',
        'model':'fixed_active_power_replay_with_daylight_q_not_ac_constrained_energy_reoptimization',
        'scenario':job['variant'],'transformer':job['transformer'],
        'topology':job['topology'],'tier':energy_meta['hardware_selection_tier'],
        'dispatch':job['dispatch'],
        'selected_house_ids':manifest['groups'][job['variant']][job['transformer']],
        'hours':8760,'converged_hours':8760,'nonconverged_hours':0,
        'AC_infeasible_hours':int(np.sum(~calc)),
        'voltage_below_095_hours':int(np.sum(tests['voltage_below_095'])),
        'transformer_overload_hours':int(np.sum(tests['trafo_over_100'])),
        'min_voltage_pu':float(raw['min_v_pu'].min()),
        'max_transformer_loading_pct':float(raw['max_trafo_pct'].max()),
        'annual_or_sample_losses_kwh':float(raw['loss_kw'].sum()),
        'pf':job['pf'],'length_factor':job['length'],
        'q_ratio_daylight':.25,'night_q_disabled':True,
        'energy_manifest_sha256':digest(job['energy']/'energy_manifest.json'),
        'input_manifest_sha256':input_sha,'ac_hourly_sha256':digest(result),
        'evidence':'PROPOSED_GEOGRAPHIC_BALANCED_AC_ONLY',
        'recovery_provenance':{
           'method':'Reconstructed summary solely from preserved complete ac_hourly.csv, signed annual dispatch and case definition; no AC simulation rerun',
           'script':'studya_recover_ac_summaries.py',
           'csv_byte_identical_to_pre_recovery':True,
           'source_summary_was_missing':True}}
    json.dumps(summary,allow_nan=False)
    return summary


def execute(repo,repair,report_file,scope):
    source=repo/SRC
    if not source.is_file():raise FileNotFoundError('Missing original annual portfolio controller: '+str(source))
    import importlib.util
    spec=importlib.util.spec_from_file_location('seed_original_annual_replays',source)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    manifest_path=repo/MANIFEST
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    input_sha=digest(manifest_path)
    outbase=repo/BASE
    jobs=mod.build_jobs(repo,outbase,scope='baseline' if scope=='baseline' else 'full',dispatch='both',cases='all')
    status=[]
    for job in jobs:
        d=windows_extended_path(job['output']);name=job['output'].name
        try:
            mod.verify_source(job,input_sha,manifest)
            if mod.verify_completed(job,input_sha,manifest):
                status.append(dict(case=name,status='EXISTING_VERIFIED_COMPLETE'));continue
        except Exception as e:
            if (d/'ac_summary.json').is_file():
                status.append(dict(case=name,status='EXISTING_SIGNED_OUTPUT_INCONSISTENT',reason=str(e)));continue
        if not d.exists():
            status.append(dict(case=name,status='NOT_STARTED'));continue
        if (d/'ac_summary.json').is_file():
            status.append(dict(case=name,status='SUMMARY_PRESENT_UNVERIFIED'));continue
        try:
            mod.verify_source(job,input_sha,manifest)
            summary=check_and_reconstruct(job,manifest,input_sha)
            if not repair:
                status.append(dict(case=name,status='RECOVERABLE_CHECKED_NO_WRITE',
                                   convergence=summary['converged_hours'],
                                   ac_infeasible_hours=summary['AC_infeasible_hours'],
                                   csv_sha256=summary['ac_hourly_sha256']))
            else:
                target=d/'ac_summary.json'
                # Exclusive creation prevents overwriting any concurrent or original summary.
                with target.open('x',encoding='utf-8') as fh:
                    json.dump(summary,fh,indent=2,allow_nan=False)
                    fh.write('\n')
                try:
                    if not mod.verify_completed(job,input_sha,manifest):
                        raise RuntimeError('Official original portfolio verifier returned False')
                except Exception:
                    target.unlink()
                    raise
                status.append(dict(case=name,status='RECOVERED_SIGNED_FROM_8760_HOURLY',
                                   ac_infeasible_hours=summary['AC_infeasible_hours'],
                                   csv_sha256=summary['ac_hourly_sha256']))
        except Exception as e:
            status.append(dict(case=name,status='NOT_RECOVERABLE_NEEDS_INSPECTION',reason=str(e)))
    totals={k:sum(r['status']==k for r in status) for k in sorted({r['status'] for r in status})}
    report={'status':'RECOVERY_NOT_NUMERICAL_SIMULATION','repair_requested':repair,
            'scope':scope,'source_input_manifest_sha256':input_sha,'totals':totals,
            'cases':status,'historical_files_modified':False}
    if report_file.exists():raise FileExistsError('Report path already exists: '+str(report_file))
    report_file.parent.mkdir(parents=True,exist_ok=True)
    report_file.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(report_file),'totals':totals},indent=2))
    for r in status:
        if r['status'] not in ('EXISTING_VERIFIED_COMPLETE','NOT_STARTED'):
            print(r['status'],r['case'],r.get('reason',''))
    return 2 if any(r['status'] in ('NOT_RECOVERABLE_NEEDS_INSPECTION','EXISTING_SIGNED_OUTPUT_INCONSISTENT','SUMMARY_PRESENT_UNVERIFIED') for r in status) else 0


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--repair',action='store_true',help='After exhaustive validation, write ONLY missing summary JSON files')
    ap.add_argument('--report',type=Path,required=True,help='Fresh JSON report path outside source run outputs')
    ap.add_argument('--scope',choices=('baseline','full'),default='baseline')
    args=ap.parse_args()
    root=args.repo_root.resolve();report=(root/args.report).resolve()
    if report.is_relative_to(root/BASE):ap.error('Place diagnostic report outside simulation result directories')
    return execute(root,args.repair,report,args.scope)

if __name__=='__main__':sys.exit(main())
