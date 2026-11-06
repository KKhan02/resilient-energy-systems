#!/usr/bin/env python3
"""WP1 annual AC violation feedback, fixed hardware and chronological PyPSA.

Read an independently audited 8760-hour manufacturer-SOC baseline replay;
sample AC-feasible inverter P at *all* failed hours; enforce the sampled
operating corridors in the EXISTING PyPSA/Linopy annual battery optimization.
Recheck every formerly failed hour. This is NOT full-year AC validation:
run validate_annual_ac.py on the new trajectory afterwards.

No field certification, no inferred customer reassignments, no equipment resize,
no nighttime Q, no change to the original PyPSA or pandapower model files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from corridors import grid_points, choose_corridor, q_ratio_at_hour
from fixed_hardware import Hardware, solve_fixed
from run_pilot import imported, filter_territory, CASE_FOLDERS, CASE_HOUSE_IDS
from validate_annual_ac import validate_trajectory, sha256


def extract_bad_hours(data: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Reject partial/misaligned annual AC evidence, return exact failed hours."""
    required={'hour_index','timestamp','status','ac_feasible','p_inverter_kw','load_kw'}
    if not required.issubset(data):
        raise ValueError(f'Annual AC missing columns: {sorted(required-set(data.columns))}')
    if len(reference)!=8760 or len(data)!=8760:
        raise ValueError('Expected exactly 8,760 annual reference and AC rows')
    idx=pd.to_numeric(data.hour_index,errors='raise').to_numpy(dtype=float)
    if not np.array_equal(idx,np.arange(8760)):
        raise ValueError('Annual AC rows are not aligned by 0..8759 hour_index')
    ac_ts=pd.to_datetime(data.timestamp,errors='raise')
    ref_ts=pd.to_datetime(reference.timestamp_lst,errors='raise')
    if not ac_ts.reset_index(drop=True).equals(ref_ts.reset_index(drop=True)):
        raise ValueError('Annual AC timestamps differ from reference trajectory')
    for column in ['p_inverter_kw','load_kw']:
        want='inverter_ac_kw' if column=='p_inverter_kw' else 'demand_kw'
        if not np.allclose(pd.to_numeric(data[column],errors='raise'),
                           pd.to_numeric(reference[want],errors='raise'),atol=5e-4,rtol=0):
            raise ValueError(f'Annual AC {column} differs from saved manufacturer baseline')
    ok=data.status.astype(str).eq('CONVERGED') & data.ac_feasible.astype(str).str.lower().eq('true')
    return data.loc[~ok].copy()


def validate_annual_evidence(summary:dict, manifest:dict, baseline_path:Path,
                             annual_path:Path, pilot_manifest_path:Path,
                             max_failures:int)->None:
    """Avoid redispatch against stale, incomplete or mismatched annual evidence."""
    if summary.get('trajectory')!='manufacturer_baseline' or summary.get('scenario')!=manifest.get('scenario'):
        raise ValueError('Only exactly matching manufacturer baseline annual replay allowed')
    if str(summary.get('transformer'))!=str(manifest.get('transformer')):
        raise ValueError('Annual replay transformer mismatch')
    if summary.get('all_8760_evaluated') is not True or summary.get('hours_checked')!=8760:
        raise ValueError('Refusing to treat a partial annual sample as full-year evidence')
    if summary.get('nighttime_q')!='off' or manifest.get('nighttime_q_policy')!='off':
        raise ValueError('Nighttime Q policy must be off in the conservative pilot')
    if summary.get('source_trajectory_sha256')!=sha256(baseline_path):
        raise ValueError('Annual replay source trajectory SHA256 mismatch')
    if summary.get('source_pilot_manifest_sha256')!=sha256(pilot_manifest_path):
        raise ValueError('Annual replay source pilot manifest SHA256 mismatch')
    if not annual_path.exists():raise FileNotFoundError(annual_path)
    if not 0<=int(summary['ac_violation_or_failure_hours'])<=max_failures:
        raise ValueError('Unexpected number of failed hours: review manually or change explicit max-failures')
    if abs(float(summary['assumed_trafo_kva'])-float(manifest['assumed_nameplate_kva']))>1e-8:
        raise ValueError('Assumed transformer rating mismatch')
    if abs(float(summary['manufacturer_soc_floor'])-float(manifest['manufacturer_min_soc_fraction']))>1e-8:
        raise ValueError('SOC floor mismatch')
    if abs(float(summary['daylight_q_ratio'])-float(manifest['daylight_q_ratio']))>1e-8:
        raise ValueError('Daylight reactive capability mismatch')


def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--repo-root',type=Path,default=Path('.'))
    pa.add_argument('--pilot-dir',type=Path,required=True,
                    help='Existing v1.1 pilot dir, containing the manufacturer baseline and pilot_manifest.json')
    pa.add_argument('--annual-dir',type=Path,required=True,
                    help='Completed annual manufacturer baseline AC replay directory, read-only')
    pa.add_argument('--outdir',type=Path,required=True,
                    help='New folder for feedback, revised 8760h PyPSA solution and selected AC checks')
    pa.add_argument('--p-grid-points',type=int,default=9)
    pa.add_argument('--q-grid-points',type=int,default=9)
    pa.add_argument('--q-refine',type=int,default=0)
    pa.add_argument('--max-failures',type=int,default=100,
                    help='Guard against accidentally sampling thousands of failed hours')
    args=pa.parse_args()
    if args.p_grid_points<5 or args.q_grid_points<5 or not 0<=args.q_refine<=6 or args.max_failures<1:
        pa.error('Invalid sampling/search settings')
    repo=args.repo_root.resolve();pilot=args.pilot_dir.resolve();annual=args.annual_dir.resolve();out=args.outdir.resolve()
    if not (repo/'.git').exists():pa.error('Repository root must contain .git')
    if out.exists():pa.error('Output directory already exists, choose a new one')
    pilot_manifest_path=pilot/'pilot_manifest.json'
    baseline_path=pilot/'fixed_hardware_manufacturer_soc_baseline.csv'
    annual_path=annual/'annual_ac_hours.csv'
    summary_path=annual/'annual_ac_summary.json'
    m=json.loads(pilot_manifest_path.read_text(encoding='utf8'))
    ac_summary=json.loads(summary_path.read_text(encoding='utf8'))
    validate_annual_evidence(ac_summary,m,baseline_path,annual_path,pilot_manifest_path,args.max_failures)
    case=m['scenario']
    if case not in CASE_FOLDERS:raise ValueError('Unknown saved scenario')
    trafo,folder=CASE_FOLDERS[case]
    if m.get('selected_candidate_houses') != list(CASE_HOUSE_IDS[case]):
        raise ValueError('Household membership mismatch')
    saved=repo/'case1/studies/pypsa_joint_optimization_v1/outputs/full_study/shortlisted_hourly'/folder
    hw=Hardware.from_manifest(json.loads((saved/'model_manifest.json').read_text(encoding='utf8')))
    if abs(hw.inverter_kva-float(m['hardware']['inverter_kva']))>1e-5:
        raise ValueError('Inverter nameplate does not match pilot source')
    if abs(hw.transformer_kva-float(m['assumed_nameplate_kva']))>1e-5:
        raise ValueError('Transformer rating does not match pilot source')
    if hw.export_policy!='zero':raise ValueError('Expected zero export for this pilot')

    baseline=pd.read_csv(baseline_path)
    ac=pd.read_csv(annual_path)
    bad=extract_bad_hours(ac,baseline)
    if len(bad)!=int(ac_summary['ac_violation_or_failure_hours']):
        raise ValueError('Annual summary count differs from actual failure rows')
    if bad.empty:
        raise SystemExit('Annual manufacturer baseline already AC feasible: no feedback redispatch needed')
    (read_data,infer_assignments,build_territory,Territory,build_net,
     critical_indices,run_hour,load_source)=imported(repo)
    demand,pv_pu,ghi,source=load_source(repo,case)
    validate_trajectory(baseline,demand,hw,float(m['manufacturer_min_soc_fraction']),baseline_path.name)
    houses,trafos,lv=read_data()
    ass=infer_assignments(houses,trafos,lv,'base')
    territory=build_territory(trafo,houses,trafos,lv,ass,float(m.get('service_factor',1.0)))
    if territory is None:raise ValueError('EPM territory missing')
    territory=Territory(trafo={**territory.trafo,'kva':float(m['assumed_nameplate_kva'])},
                        graph=territory.graph,attachments=territory.attachments,
                        label=territory.label,root=territory.root,line_count=territory.line_count)
    territory,excluded=filter_territory(case,territory,Territory)
    if len(territory.attachments)!=len(CASE_HOUSE_IDS[case]):
        raise ValueError('GIS membership mismatch')
    from coordinated_q_control import ACLimits
    limits=ACLimits()
    siting=str(m.get('siting','head'))
    allocation=str(m.get('load_allocation','equal'))
    if siting not in ('head','middle','end') or allocation not in ('equal','far_end_heavy'):
        raise ValueError('Invalid siting or allocation')
    net,meta=build_net(territory,siting)
    qratio=float(m['daylight_q_ratio'])
    raw=[];bands=[];unresolved=[];corridors={}
    def evaluate(index,pp):
        row=baseline.iloc[index].copy()
        row['inverter_ac_kw']=float(pp)
        ratio=q_ratio_at_hour(float(row.pv_dc_available_kw),qratio,False)
        r=run_hour(net,meta,territory,row,float(hw.load_pf),allocation,siting,ratio,
                   'coordinated',limits,float(hw.inverter_kva),float(hw.inverter_kva),
                   args.q_grid_points,args.q_refine)
        r.update(hour_index=index,sampled_inverter_p_kw=float(pp),
                 pv_dc_available_kw=float(row.pv_dc_available_kw))
        return r
    out.mkdir(parents=True)
    for r in bad.itertuples(index=False):
        ix=int(r.hour_index)
        row=baseline.iloc[ix]
        p0=float(row.inverter_ac_kw)
        max_p=min(float(row.demand_kw),float(hw.inverter_kva))
        if max_p<p0-1e-5:
            raise ValueError('Baseline P exceeds physical zero-export upper limit')
        samples=[]
        for point in grid_points(max_p,p0,args.p_grid_points):
            obs=evaluate(ix,point)
            raw.append(obs)
            samples.append((point,bool(obs.get('status')=='CONVERGED' and obs.get('ac_feasible') is True)))
        band=choose_corridor(samples,p0)
        if band is None:
            unresolved.append({'hour_index':ix,'timestamp_lst':str(row.timestamp_lst),
                               'reason':'NO_AC_FEASIBLE_P_Q_FOUND_WITH_SAMPLED_POINTS'})
            continue
        ts=pd.Timestamp(row.timestamp_lst)
        corridors[ts]=(band.p_min_kw,band.p_max_kw)
        bands.append({'hour_index':ix,'timestamp_lst':str(ts),
                      'reference_p_kw':p0,'lo_kw':band.p_min_kw,'hi_kw':band.p_max_kw,
                      'feasible_sample_count':band.sampled_feasible,
                      'continuous_interval_verified':False})
        print(f'Hour {ix} {ts}: AC-sampled P band [{band.p_min_kw:.4f},{band.p_max_kw:.4f}] kW',flush=True)
    pd.DataFrame(raw).to_csv(out/'ac_p_samples.csv',index=False)
    pd.DataFrame(bands).to_csv(out/'sampled_corridors.csv',index=False)
    pd.DataFrame(unresolved,columns=['hour_index','timestamp_lst','reason']).to_csv(out/'unresolved_hours.csv',index=False)
    feedback={
        'scenario':case,'transformer':trafo,'source_annual_summary_sha256':sha256(summary_path),
        'source_annual_ac_csv_sha256':sha256(annual_path),
        'source_manufacturer_baseline_sha256':sha256(baseline_path),
        'source_pilot_manifest_sha256':sha256(pilot_manifest_path),
        'initial_ac_fail_hours':len(bad),'sampled_corridor_count':len(corridors),
        'unsampled_or_unresolved_hours':len(unresolved),
        'p_grid_points':args.p_grid_points,'q_grid_points':args.q_grid_points,'q_refine':args.q_refine,
        'hardware':vars(hw),'manufacturer_min_soc':float(m['manufacturer_min_soc_fraction']),
        'nighttime_q':'off','loads':'synthetic aggregated demand evenly allocated unless source pilot differs',
        'assumptions':'balanced LV GIS equivalent, provisional house connections and conductor properties',
        'AC_losses_included_in_energy_objective':False,
        'interpolation_AC_feasibility_guaranteed':False,
        'annual_AC_revalidated_after_feedback':False,
    }
    if unresolved:
        feedback['outcome']='HALTED_NO_SAMPLED_FEASIBLE_P_Q_FOR_ALL_FAILED_HOURS'
        (out/'feedback_manifest.json').write_text(json.dumps(feedback,indent=2)+'\n',encoding='utf8')
        raise SystemExit('At least one failed AC hour has no sampled feasible P/Q. No dispatch solve attempted.')

    # Crucially reoptimizes all 8760 hours. No free battery energy can be injected.
    try:
        revised,summary=solve_fixed(repo,hw,demand,pv_pu,corridors,
            min_physical_soc=float(m['manufacturer_min_soc_fraction']))
    except Exception as exc:
        feedback['outcome']='ANNUAL_PYPSA_REDISPATCH_FAILED_OR_INFEASIBLE'
        feedback['solver_failure']=str(exc)[:1000]
        (out/'feedback_manifest.json').write_text(json.dumps(feedback,indent=2)+'\n',encoding='utf8')
        raise
    revised.to_csv(out/'redispatched_hourly.csv')
    checks=[]
    for ix in bad.hour_index.astype(int):
        new_p=float(revised.iloc[ix].inverter_ac_kw)
        obs=evaluate(int(ix),new_p)
        obs['original_p_kw']=float(baseline.iloc[ix].inverter_ac_kw)
        obs['redispatched_p_kw']=new_p
        checks.append(obs)
    pd.DataFrame(checks).to_csv(out/'formerly_failing_hours_rechecked.csv',index=False)
    nfailed=sum(not bool(x.get('status')=='CONVERGED' and x.get('ac_feasible') is True) for x in checks)
    feedback['formerly_failing_hours_still_fail']=nfailed
    feedback['revised_annual_total_usd']=float(summary['annual_total_usd'])
    feedback['revised_grid_import_kwh']=float(summary['grid_import_kwh'])
    feedback['revised_unserved_kwh']=float(summary['unserved_kwh'])
    feedback['revised_min_store_usable_kwh']=float(revised.battery_soc_usable_kwh.min())
    feedback['initial_manufacturer_baseline_annual_total_usd']=float(m['manufacturer_soc_baseline_annual_total_usd'])
    feedback['AC_only_incremental_cost_usd_per_year']=float(summary['annual_total_usd'])-float(m['manufacturer_soc_baseline_annual_total_usd'])
    feedback['outcome']='RECHECKED_4_HOURS_PASS_ANNUAL_REPLAY_PENDING' if nfailed==0 else 'SOME_ORIGINAL_HOURS_STILL_FAIL_ANNUAL_REPLAY_PENDING'
    # Allows *existing* validate_annual_ac.py to load this new trajectory using
    # --pilot-dir <out> --trajectory redispatched, with the original source provenance.
    updated=dict(m)
    updated['feedback_run']='ANNUAL_AC_VIOLATION_FEEDBACK'
    updated['feedback_source_annual_ac_summary_sha256']=sha256(summary_path)
    updated['feedback_source_pilot_manifest_sha256']=sha256(pilot_manifest_path)
    updated['feedback_annual_ac_verified']=False
    (out/'pilot_manifest.json').write_text(json.dumps(updated,indent=2)+'\n',encoding='utf8')
    (out/'feedback_manifest.json').write_text(json.dumps(feedback,indent=2)+'\n',encoding='utf8')
    print(feedback['outcome'])
    print('Next: run validate_annual_ac.py --trajectory redispatched --pilot-dir',out,
          ' --outdir <new_annual_validation_folder>')


if __name__=='__main__':
    main()
