#!/usr/bin/env python3
"""Replay one already validated 8,760-hour dispatch under PF/route sensitivities.

Research screening. No redispatch, SOC modification, geometry certification or tariff
change. Critical mode is NOT a claim about a full-year robust operating envelope.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd

from corridors import q_ratio_at_hour
from fixed_hardware import Hardware
from run_pilot import imported, filter_territory, CASE_FOLDERS, CASE_HOUSE_IDS
from validate_annual_ac import validate_trajectory, sha256


def critical_hour_indices(ac: pd.DataFrame, hourly: pd.DataFrame,
                          threshold: float = 0.975, top_n: int = 15) -> list[int]:
    """Preserve all low-margin hours, sample additional diverse stresses and months.

    This is a *screen*. It cannot establish annual robustness or capture all
    potentially worst hours after changing PF or length.
    """
    if len(ac) != 8760 or len(hourly) != 8760:
        raise ValueError('Critical sampling requires 8760 aligned hours')
    if not 0 < threshold <= 1 or top_n < 1:
        raise ValueError('Bad critical sampling settings')
    required = {'min_v_pu', 'max_v_pu', 'max_trafo_pct', 'max_line_pct', 'hour_index'}
    if not required.issubset(ac):
        raise ValueError('AC replay missing required metrics')
    selected = set(ac.index[ac.min_v_pu <= threshold].astype(int))
    selected.update(ac.index[~ac.ac_feasible.astype(str).str.lower().eq('true')].astype(int))
    for col, asc in (('min_v_pu', True), ('max_v_pu', False),
                     ('max_trafo_pct', False), ('max_line_pct', False)):
        selected.update(ac.sort_values(col, ascending=asc, kind='stable').index[:top_n].astype(int))
    for col in ('demand_kw', 'inverter_ac_kw', 'grid_import_kw'):
        selected.update(hourly.sort_values(col, ascending=False, kind='stable').index[:top_n].astype(int))
    months = pd.to_datetime(hourly.timestamp_lst).dt.month
    for month in range(1,13):
        rows = ac.loc[months == month]
        if not rows.empty:
            selected.add(int(rows.min_v_pu.idxmin()))
    selected.update((0, 8759))
    return sorted(selected)


def verify_reference_evidence(m: dict, summary: dict, annual: pd.DataFrame,
                              trajectory_file: Path, ac_csv: Path) -> None:
    """Never use an annual AC file from a different 8760-hour trajectory."""
    if summary.get('scenario') != m.get('scenario') or summary.get('transformer') != m.get('transformer'):
        raise ValueError('Reference AC file belongs to a different case')
    if summary.get('trajectory') != 'redispatched':
        raise ValueError('Reference AC replay must concern the redispatched trajectory')
    if not (summary.get('all_8760_evaluated') and summary.get('ac_feasible_full_year')):
        raise ValueError('Expected a completed and passing reference annual AC replay')
    if summary.get('source_trajectory_sha256') != sha256(trajectory_file):
        raise ValueError('Annual AC source hash does not match the redispatched trajectory')
    if len(annual) != 8760 or not np.array_equal(annual.hour_index.to_numpy(), np.arange(8760)):
        raise ValueError('Expected ordered, complete 2025 annual AC rows')
    if not (annual.status.eq('CONVERGED') & annual.ac_feasible.astype(str).str.lower().eq('true')).all():
        raise ValueError('Stored annual AC rows conflict with passing summary')
    if m.get('nighttime_q_policy') != 'off' or summary.get('nighttime_q') != 'off':
        raise ValueError('Nighttime Q must remain off for this conservative comparison')
    if m.get('siting', 'head') != 'head' or m.get('load_allocation','equal') != 'equal':
        raise ValueError('Current study only reproduces head/equal reference')
    if float(m.get('service_factor', 1.0)) != 1.0:
        raise ValueError('Current study reference must have a service factor of 1.0')


def summarize_variation(df: pd.DataFrame, n_expected: int, mode: str) -> dict:
    ok = df.status.astype(str).eq('CONVERGED')
    feasible = ok & df.ac_feasible.astype(str).str.lower().eq('true')
    solved = df.loc[ok]
    def best(col, method):
        if solved.empty: return None
        s = pd.to_numeric(solved[col], errors='coerce')
        return float(getattr(s, method)()) if s.notna().any() else None
    return dict(hours_checked=len(df), hours_expected=n_expected,
                converged_hours=int(ok.sum()), feasible_hours=int(feasible.sum()),
                violating_or_failed_hours=int((~feasible).sum()),
                sample_all_feasible=bool(len(df)==n_expected and feasible.all()),
                min_v_pu=best('min_v_pu','min'), max_v_pu=best('max_v_pu','max'),
                max_trafo_loading_pct=best('max_trafo_pct','max'),
                max_line_loading_pct=best('max_line_pct','max'),
                min_voltage_margin_pu=(best('min_v_pu','min')-0.97 if not solved.empty else None),
                conclusion=('CONDITIONAL_FULL_YEAR_PASS' if mode=='full' and len(df)==8760 and feasible.all()
                            else 'CONDITIONAL_FULL_YEAR_FAIL' if mode=='full' and len(df)==8760
                            else 'CRITICAL_SAMPLE_PASS_ONLY' if feasible.all() else 'CRITICAL_SAMPLE_FAILURE'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, default=Path('.'))
    ap.add_argument('--feedback-dir', type=Path, required=True,
                    help='Completed annual feedback folder containing redispatched_hourly.csv and pilot_manifest.json')
    ap.add_argument('--annual-dir', type=Path, required=True,
                    help='Passing 8760-hour redispatched annual AC validation folder')
    ap.add_argument('--outdir', type=Path, required=True)
    ap.add_argument('--mode', choices=('critical','full'), default='critical')
    ap.add_argument('--power-factors', type=float, nargs='+', default=[.98,.95,.90])
    ap.add_argument('--service-factors', type=float, nargs='+', default=[1.,1.3,1.6])
    ap.add_argument('--critical-voltage-cutoff', type=float, default=.975)
    ap.add_argument('--top-n', type=int, default=15)
    ap.add_argument('--q-grid-points', type=int, default=9)
    ap.add_argument('--q-refine', type=int, default=0)
    ap.add_argument('--reference-voltage-tolerance', type=float, default=5.e-5)
    args = ap.parse_args()
    if not args.power_factors or any(not 0 < x <= 1 for x in args.power_factors):
        ap.error('Each load power factor must be within (0,1]')
    if not args.service_factors or any(x < 1 for x in args.service_factors):
        ap.error('Service factors must be >=1')
    if args.top_n < 1 or args.q_grid_points < 5 or not 0 <= args.q_refine <= 6:
        ap.error('Invalid numerical sample settings')
    if args.reference_voltage_tolerance <= 0:
        ap.error('Reference voltage tolerance must be positive')
    repo = args.repo_root.resolve(); feedback = args.feedback_dir.resolve()
    annual_dir = args.annual_dir.resolve(); out = args.outdir.resolve()
    if not (repo/'.git').exists(): ap.error('Repository root must contain .git')
    if out.exists(): ap.error('New output directory must not exist: '+str(out))
    manifest_file = feedback/'pilot_manifest.json'
    trajectory_file = feedback/'redispatched_hourly.csv'
    summary_file = annual_dir/'annual_ac_summary.json'
    ac_csv = annual_dir/'annual_ac_hours.csv'
    for path in (manifest_file, trajectory_file, summary_file, ac_csv):
        if not path.is_file(): ap.error('Missing required source: '+str(path))
    m = json.loads(manifest_file.read_text(encoding='utf8'))
    summ = json.loads(summary_file.read_text(encoding='utf8'))
    case = m['scenario']
    if case not in CASE_FOLDERS: raise ValueError('Unrecognized archived case')
    trafo, ref_folder = CASE_FOLDERS[case]
    if m['transformer'] != trafo or list(m.get('selected_candidate_houses',[])) != list(CASE_HOUSE_IDS[case]):
        raise ValueError('Saved GIS membership mismatch')
    ac = pd.read_csv(ac_csv)
    trajectory = pd.read_csv(trajectory_file)
    verify_reference_evidence(m,summ,ac,trajectory_file,ac_csv)
    if summ.get('source_pilot_manifest_sha256') != sha256(manifest_file):
        raise ValueError('Annual AC pilot-manifest hash mismatch')
    ac_ts = pd.to_datetime(ac.timestamp)
    series_ts = pd.to_datetime(trajectory.timestamp_lst)
    if not np.array_equal(ac_ts.to_numpy(),series_ts.to_numpy()):
        raise ValueError('AC reference and dispatched timestamps are not aligned')
    folder = repo/'case1/studies/pypsa_joint_optimization_v1/outputs/full_study/shortlisted_hourly'/ref_folder
    hw = Hardware.from_manifest(json.loads((folder/'model_manifest.json').read_text(encoding='utf8')))
    (read_data,infer_assignments,build_territory,Territory,build_net,
     critical_indices,run_hour,load_source) = imported(repo)
    demand, pv, ghi, raw = load_source(repo,case)
    validate_trajectory(trajectory,demand,hw,float(m['manufacturer_min_soc_fraction']),trajectory_file.name)
    expected_hardware=asdict(hw)
    for key in ('panels','battery_modules','battery_power_dc_kw','inverter_kva',
                'transformer_kva','loading_pu','load_pf'):
        if abs(float(expected_hardware[key])-float(m['hardware'][key]))>1e-5:
            raise ValueError('Archived hardware differs from fixed reference: '+key)
    if m['hardware']['export_policy'] != hw.export_policy:
        raise ValueError('Saved export policy changed')
    indices = (list(range(8760)) if args.mode=='full' else
               critical_hour_indices(ac,trajectory,args.critical_voltage_cutoff,args.top_n))
    houses,trafos,lv=read_data();ass=infer_assignments(houses,trafos,lv,'base')
    from coordinated_q_control import ACLimits
    limits=ACLimits()
    out.mkdir(parents=True)
    pd.DataFrame(dict(hour_index=indices,timestamp=series_ts.iloc[indices].astype(str).tolist(),
       reference_min_v_pu=ac.min_v_pu.iloc[indices].tolist())).to_csv(out/'evaluated_hour_indices.csv',index=False)
    rows=[]; n_cases=len(set(args.power_factors))*len(set(args.service_factors))
    start=time.monotonic()
    dest=out/'sensitivity_ac_hours.csv'
    with dest.open('w',newline='',encoding='utf8') as fh:
        writer=None
        for factor in sorted(set(args.service_factors)):
            territory = build_territory(trafo,houses,trafos,lv,ass,factor)
            if territory is None:raise ValueError(f'Missing GIS feeder for {trafo}')
            territory = Territory(trafo={**territory.trafo,'kva':float(m['assumed_nameplate_kva'])},
                        graph=territory.graph,attachments=territory.attachments,
                        label=territory.label,root=territory.root,line_count=territory.line_count)
            territory, excluded=filter_territory(case,territory,Territory)
            net,meta=build_net(territory,'head')
            for pf in sorted(set(args.power_factors),reverse=True):
                print(f'PF={pf:g} service factor={factor:g}, {len(indices)} hours',flush=True)
                count=0; fail=0; chunk=[]
                for i in indices:
                    row=trajectory.iloc[i]
                    ratio=q_ratio_at_hour(float(row.pv_dc_available_kw),float(m['daylight_q_ratio']),False)
                    rec=run_hour(net,meta,territory,row,pf,'equal','head',ratio,'coordinated',
                        limits,float(hw.inverter_kva),float(hw.inverter_kva),args.q_grid_points,args.q_refine)
                    rec.update(hour_index=i,service_factor=factor,source_trajectory='redispatched',
                               night_q='off',pv_dc_available_kw=float(row.pv_dc_available_kw))
                    if writer is None:
                        writer=csv.DictWriter(fh,fieldnames=list(rec.keys()),extrasaction='ignore')
                        writer.writeheader()
                    writer.writerow(rec)
                    chunk.append(rec)
                    count+=1
                    if rec['status']!='CONVERGED' or not bool(rec['ac_feasible']):fail+=1
                    if count%500==0:fh.flush()
                    if (abs(factor-1.)<1.e-8 and abs(pf-float(hw.load_pf))<1.e-8
                          and rec['status']=='CONVERGED'):
                        old=ac.iloc[i]
                        v=float(rec['min_v_pu'])
                        if abs(v-float(old.min_v_pu))>args.reference_voltage_tolerance:
                            raise RuntimeError('Failed baseline AC reproduction at hour '+str(i)+
                                 f': old {old.min_v_pu}, new {v}; do not trust sensitivity results')
                fh.flush()
                details=summarize_variation(pd.DataFrame(chunk),len(indices),args.mode)
                details.update(load_pf=pf,service_factor=factor,scenario=case,
                               transformer=trafo,nighttime_q='off')
                rows.append(details)
                print('Result:',details['conclusion'], 'failed=',fail,
                      'min_voltage=',details['min_v_pu'],flush=True)
    pd.DataFrame(rows).to_csv(out/'sensitivity_scenarios.csv',index=False)
    manifest = dict(label='CONDITIONAL_GIS_LV_SENSITIVITY_NOT_FIELD_VALIDATED',
       case=case,transformer=trafo,mode=args.mode,
       full_year_each_case=bool(args.mode=='full'),
       critical_screen_not_annual_evidence=bool(args.mode=='critical'),
       hours_per_case=len(indices),number_of_sensitivity_cases=n_cases,
       requested_pf=sorted(set(args.power_factors)),
       requested_service_factors=sorted(set(args.service_factors)),
       critical_voltage_cutoff=args.critical_voltage_cutoff,top_n=args.top_n,
       thresholds=asdict(limits),nighttime_q='off',daylight_q_ratio=m['daylight_q_ratio'],
       dispatch_refreshed_after_changed_pf_and_service_length=False,
       base_dispatch_source_sha256=sha256(trajectory_file),
       base_pilot_source_sha256=sha256(manifest_file),
       reference_annual_summary_sha256=sha256(summary_file),
       reference_annual_ac_csv_sha256=sha256(ac_csv),
       parent_git_revision=subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True).stdout.strip(),
       elapsed_seconds=round(time.monotonic()-start,2),
       assumptions=['provisional household attachments','balanced three-phase LV equivalent',
                    'proxy conductor resistance, reactance and ampacity',
                    '5 kVA sensitivity, not verified EPM nameplate for all territories',
                    'zero night-time Q even when battery supplies active power',
                    'unchanged dispatch, no AC losses in optimization and no revised economics'])
    (out/'robustness_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print('Completed',len(rows),'scenarios in',manifest['elapsed_seconds'],'seconds. Results:',out)

if __name__=='__main__':main()
