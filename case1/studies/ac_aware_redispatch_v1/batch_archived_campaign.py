#!/usr/bin/env python3
"""Explicit, resumable WORK QUEUE across all GIS-addressable archived equipment.

Stage = energy: 8760h fixed-hardware manufacturer-SOC LP, never another
investment MILP. Stage = ac: 8760h AC per chosen PF/service scenario,
using stored energy trajectory. Dry run is the default; --execute is required.
Everything outside the current provisional GIS membership remains indexed.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent


def enumerate_candidates(plan_dir:Path,case:str|None=None,kva:float|None=None):
    eq=pd.read_csv(plan_dir/'all_distinct_equipment_candidates.csv',keep_default_na=False)
    eq=eq.loc[eq.existing_fixed_hardware_runner_eligible.astype(str).str.lower().eq('true')].copy()
    if case:
        names={'seven':'7_homes','nine':'9_homes','twelve':'12_homes'}
        eq=eq.loc[eq.case.eq(names.get(case,case))]
    if kva is not None:
        eq=eq.loc[(eq.assumed_transformer_kva.astype(float)-kva).abs()<1e-6]
    return eq.sort_values(['case','assumed_transformer_kva','historical_min_annual_total_usd','equipment_id']).to_dict('records')


def scenarios(choice:str):
    if choice=='reference':return [(0.98,1.0)]
    if choice=='nine':return [(pf,factor) for pf in (.98,.95,.90) for factor in (1.,1.3,1.6)]
    raise ValueError('Unrecognized AC scenario matrix')


def job_command(stage,repo,plan,energy_root,ac_root,row,pf=None,service=None):
    eid=row['equipment_id']
    if stage=='energy':
        return [sys.executable,str(HERE/'run_archived_energy.py'),'--repo-root',str(repo),
                '--plan-dir',str(plan),'--candidate-id',eid,'--out-root',str(energy_root)]
    if stage=='ac':
        assert pf is not None and service is not None
        sub=f'pf_{pf:.2f}_service_{service:.2f}'
        return [sys.executable,str(HERE/'validate_archived_candidate_ac.py'),'--repo-root',str(repo),
                '--pilot-dir',str(energy_root/eid),'--outdir',str(ac_root/eid/sub),
                '--load-pf',str(pf),'--service-factor',str(service),'--vmin','.95','--vmax','1.05']
    raise ValueError(stage)


def log_event(path:Path,event:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf8') as f:f.write(json.dumps(event,default=str)+'\n')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',choices=['energy','ac'],required=True)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--plan-dir',type=Path,required=True)
    ap.add_argument('--energy-root',type=Path,required=True)
    ap.add_argument('--ac-root',type=Path,required=True)
    ap.add_argument('--case',help='seven, nine, twelve, or original 7_homes etc; omitted means all GIS-supported cases')
    ap.add_argument('--kva',type=float,help='Optional rating filter, e.g. 5 (assumption for 106039)')
    ap.add_argument('--candidate-id',help='Optional exact candidate ID')
    ap.add_argument('--scenario-set',choices=['reference','nine'],default='reference')
    ap.add_argument('--max-candidates',type=int,default=0,
                    help='0=all eligible, N=first N candidates; no six-design limit')
    ap.add_argument('--execute',action='store_true',help='Without this flag only prints a dry-run work plan')
    ap.add_argument('--continue-on-error',action='store_true',help='Retain failures and proceed to next independent job')
    args=ap.parse_args(argv)
    if args.max_candidates<0:ap.error('max-candidates must be >=0')
    repo=args.repo_root.resolve();plan=args.plan_dir.resolve()
    energy=args.energy_root.resolve();ac=args.ac_root.resolve()
    data=enumerate_candidates(plan,args.case,args.kva)
    if args.candidate_id:data=[r for r in data if r['equipment_id']==args.candidate_id]
    if args.max_candidates:data=data[:args.max_candidates]
    jobs=[];skipped=0
    for row in data:
        eid=row['equipment_id'];energy_dir=energy/eid
        if args.stage=='energy':
            path=energy_dir/'pilot_manifest.json';csv_path=energy_dir/'fixed_hardware_manufacturer_soc_baseline.csv'
            if path.is_file() and csv_path.is_file():
                m=json.loads(path.read_text(encoding='utf8'))
                if m.get('candidate_id')!=eid or m.get('source_trajectory_sha256') is None:
                    raise ValueError('Existing energy checkpoint is not trustworthy: '+str(energy_dir))
                from audit_archived_campaign import sha256
                if sha256(csv_path)!=m['source_trajectory_sha256']:
                    raise ValueError('Existing energy checkpoint hash mismatch: '+str(energy_dir))
                plan_source=json.loads((plan/'campaign_reuse_manifest.json').read_text(encoding='utf8'))
                if m.get('source_campaign_sha256')!=plan_source.get('source_sha256'):
                    raise ValueError('Existing energy run belongs to a different archived campaign')
                skipped+=1;continue
            if energy_dir.exists():
                raise ValueError('Incomplete energy output requires inspection: '+str(energy_dir))
            jobs.append((eid,None,job_command('energy',repo,plan,energy,ac,row)))
        else:
            if not (energy_dir/'pilot_manifest.json').is_file():
                skipped+=1
                continue
            for pf,service in scenarios(args.scenario_set):
                dest=ac/eid/f'pf_{pf:.2f}_service_{service:.2f}'
                state_path=dest/'ac_checkpoint.json'
                cmd=job_command('ac',repo,plan,energy,ac,row,pf,service)
                if state_path.is_file():
                    state=json.loads(state_path.read_text(encoding='utf8'))
                    if state.get('status')=='COMPLETE':
                        # Still validate changed inputs in --resume path.
                        cmd.append('--resume')
                    else:cmd.append('--resume')
                elif dest.exists():
                    raise ValueError('Existing AC output with missing provenance state: '+str(dest))
                jobs.append((eid,f'{pf:.2f}/{service:.2f}',cmd))
    print(json.dumps({'stage':args.stage,'candidate_scope':len(data),
        'queued_jobs':len(jobs),'skipped_completed_or_missing_dependency':skipped,
        'scenario_set':args.scenario_set,'will_execute':args.execute,
        'historical_MILP_tasks_recomputed':0},indent=2))
    for eid,scenario,command in jobs[:5]: print('COMMAND',eid,scenario,' '.join(command))
    if not args.execute:
        print('DRY RUN ONLY. Add --execute to launch annual jobs. No arbitrary six-design truncation.')
        return
    log=plan/f'batch_{args.stage}_events.jsonl'
    for idx,(eid,scenario,command) in enumerate(jobs,start=1):
        print('RUN',idx,'/',len(jobs),eid,scenario or 'annual manufacturer SOC',flush=True)
        proc=subprocess.run(command,cwd=repo,check=False)
        event={'candidate_id':eid,'scenario':scenario,'stage':args.stage,'returncode':proc.returncode,
               'command':command}
        log_event(log,event)
        if proc.returncode!=0 and not args.continue_on_error:
            raise SystemExit(f'Job {eid} failed; inspect outputs. See {log}. Use --continue-on-error to preserve queue progress.')
    print('Completed all attempted jobs. Review outputs and aggregate with collate_archived_campaign.py')

if __name__=='__main__':main()
