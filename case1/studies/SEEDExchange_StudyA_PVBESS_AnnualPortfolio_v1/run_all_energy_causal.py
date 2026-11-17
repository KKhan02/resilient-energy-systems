#!/usr/bin/env python3
"""Run ALL independent annual energy+causal Study A cases, without stopping at one failure.

Uses source v1.1 portfolio planner/checks, never edits the frozen source model.
Runs in two stages, all energy cases then all causal cases; signs/reuses outputs.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
CODE=HERE.parent/'SEEDExchange_StudyA_PVBESS_v1'
if not (CODE/'run_portfolio.py').is_file():
    raise RuntimeError('Install beside SEEDExchange_StudyA_PVBESS_v1')
sys.path.insert(0,str(CODE))
from run_portfolio import proposed_jobs,check_reuse
from study_a_pvbess import MANIFEST_REL,BASE_REL,digest,secure_context


def get_jobs(repo,outbase,stage='both'):
    if stage not in ('energy','causal','both'):raise ValueError('Invalid stage')
    plan=[]
    if stage in ('energy','both'):
        plan.extend(proposed_jobs(repo,outbase,'all-energy'))
    if stage in ('causal','both'):
        plan.extend(proposed_jobs(repo,outbase,'all-causal'))
    if len({str(j['outdir']) for j in plan})!=len(plan):
        raise AssertionError('Job output folders collide')
    return plan


def run(repo,outbase,stage):
    m,_,_,_=secure_context(repo,repo/MANIFEST_REL)
    signed=digest(repo/MANIFEST_REL)
    jobs=get_jobs(repo,outbase,stage)
    new=[];reused=[];failures=[]
    for i,job in enumerate(jobs,1):
        label=f'{job["job"]} {job["variant"]} {job["trafo"]} {job["tier"]}'
        print(f'YEARLY {i}/{len(jobs)} {label}',flush=True)
        try:
            if check_reuse(job,signed,m):
                reused.append(label);print('REUSED verified complete output',flush=True);continue
            if 'energy' in job and not (job['energy']/'energy_manifest.json').is_file():
                raise FileNotFoundError('No annual PyPSA energy input for causal: '+str(job['energy']))
            if job['outdir'].parent!=outbase:raise RuntimeError('Unexpected output parent')
            outbase.mkdir(parents=True,exist_ok=True)
            r=subprocess.run(job['args'],cwd=repo,check=False)
            if r.returncode!=0:
                raise RuntimeError(f'Numerical subprocess exit code {r.returncode}')
            if not check_reuse(job,signed,m):
                raise RuntimeError('Output missing signed data after numerical runner succeeded')
            new.append(label)
        except Exception as e:
            failures.append({'case':label,'output_dir':str(job['outdir']),'error':str(e)})
            print('BLOCKED/FAILED:',label,':',e,flush=True)
    doc={'stage':stage,'annual_jobs_requested':len(jobs),
         'new_complete':len(new),'verified_reused':len(reused),
         'failures':len(failures),'failure_details':failures,
         'source_manifest_sha256':signed,'status':'COMPLETE_WITH_FAILURES_RECORDED' if failures else 'ALL_COMPLETE_SIGNED_OR_REUSED'}
    if outbase.exists():
        target=outbase/('annual_energy_causal_receipt_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        if target.exists():raise FileExistsError('Receipt collision')
        target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
        print('RECEIPT',target)
    print(json.dumps({k:doc[k] for k in ('stage','annual_jobs_requested','new_complete','verified_reused','failures','status')},indent=2))
    return 2 if failures else 0


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--outbase',type=Path)
    p.add_argument('--stage',choices=('energy','causal','both'),default='both')
    p.add_argument('--run',action='store_true')
    x=p.parse_args(argv)
    repo=x.repo_root.resolve();outbase=(x.outbase or repo/BASE_REL).resolve()
    jobs=get_jobs(repo,outbase,x.stage)
    if not x.run:
        print('DRY RUN; no outputs written; all jobs 8760 hours; planned jobs:',len(jobs))
        for n,j in enumerate(jobs,1):
            print(f'{n:3d}. {j["job"]} {j["variant"]} {j["trafo"]} {j["tier"]} -> {j["outdir"].name}')
        return 0
    return run(repo,outbase,x.stage)

if __name__=='__main__':sys.exit(main())
