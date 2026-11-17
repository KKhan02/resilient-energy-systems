#!/usr/bin/env python3
"""Signed, restart-safe FULL-YEAR AC replay portfolio for SEEDExchange Study A.

The source v6.2 runner and existing PV+BESS modelling scripts are imported/reused,
never edited. All runs are local. Dry run unless --run. One output folder per
case/dispatch/PF/route multiplier. All replays use 8,760 hours, never 24h.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

THIS = Path(__file__).resolve().parent
PVBESS_CODE = THIS.parent / 'SEEDExchange_StudyA_PVBESS_v1'
if not (PVBESS_CODE / 'study_a_pvbess.py').is_file():
    raise RuntimeError('Install beside SEEDExchange_StudyA_PVBESS_v1 in case1/studies')
sys.path.insert(0, str(PVBESS_CODE))
from study_a_pvbess import (BASE_REL, MANIFEST_REL, create_plan, digest, secure_context)

PFS = (0.95, 0.98, 1.0)
LENGTHS = (1.0, 1.3, 1.6)



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

def yearly_combinations(scope):
    if scope not in ('baseline', 'sensitivities', 'full'):
        raise ValueError('Unknown scope '+str(scope))
    for pf in PFS:
        for length in LENGTHS:
            base = (pf == 0.98 and length == 1.0)
            if (scope == 'baseline' and not base) or (scope == 'sensitivities' and base):
                continue
            yield pf, length


def build_jobs(repo, outbase, scope='baseline', dispatch='both', cases='all',
               transformer=None, assignment=None, tier=None):
    """Make exact A0/A1 and STAR/MST job list without loading raw datasets."""
    if dispatch not in ('optimized','causal','both'):raise ValueError('Unknown dispatch')
    if cases not in ('all','refs','new-four'):raise ValueError('Unknown case class')
    jobs=[]
    for c in create_plan():
        variant,tid,hw_tier,kind = c['variant'],c['transformer'],c['tier'],c['kind']
        new_four = kind == 'new_four_house_milp'
        if cases == 'refs' and new_four:continue
        if cases == 'new-four' and not new_four:continue
        if transformer is not None and tid != transformer:continue
        if assignment is not None and variant != assignment:continue
        if tier is not None and hw_tier != tier:continue
        # 92395 A0 and A1 are identical. Run each unique network topology only once.
        topologies = ('star','mst') if tid == '92395' else ('mapped',)
        kind_token = 'four' if new_four else 'ref'
        parent = f'{variant}_{tid}_{hw_tier}_{kind_token}'
        energy = outbase / ('energy_' + parent)
        causal = outbase / ('causal_' + parent)
        for topology in topologies:
            for pf,length in yearly_combinations(scope):
                for mode in (('optimized','causal') if dispatch=='both' else (dispatch,)):
                    token = (f'{parent}_{topology}_{mode}_pf{round(pf*100):03d}'
                             f'_length{round(length*10):02d}_annual8760')
                    output = outbase / 'annual_ac_replays_v1' / token
                    command = [sys.executable,str(PVBESS_CODE/'study_a_pvbess.py'),
                        '--repo-root',str(repo),'--manifest',str(repo/MANIFEST_REL),
                        'replay','--assignment',variant,'--transformer',tid,
                        '--topology',topology,'--dispatch',mode,
                        '--energy-dir',str(energy),'--hours','8760','--outdir',str(output),
                        '--pf',str(pf),'--length',str(length)]
                    if mode=='causal':command.extend(['--causal-dir',str(causal)])
                    jobs.append(dict(variant=variant,transformer=tid,tier=hw_tier,
                        kind=kind_token,topology=topology,dispatch=mode,pf=pf,
                        length=length,energy=energy,causal=causal,
                        output=output,command=command))
    if len({str(j['output']) for j in jobs})!=len(jobs):
        raise AssertionError('Two jobs produce the same output folder')
    return jobs


def verify_source(job, input_sha, manifest):
    """Fail before expensive replay if energy/causal is missing or stale."""
    mp=job['energy']/'energy_manifest.json'
    csv_path=job['energy']/'energy_hourly_2025.csv'
    if not (mp.is_file() and csv_path.is_file()):
        raise FileNotFoundError('Missing annual energy result '+str(job['energy']))
    e=json.loads(mp.read_text(encoding='utf-8'))
    if e.get('input_manifest_sha256') != input_sha:
        raise ValueError('Energy output input manifest signature changed')
    if digest(csv_path) != e.get('energy_csv_sha256'):
        raise ValueError('Energy output CSV signature mismatch')
    if (e.get('transformer') != job['transformer'] or
        e.get('scenario') != job['variant'] or
        e.get('hardware_selection_tier') != job['tier'] or
        e.get('selected_house_ids') != manifest['groups'][job['variant']][job['transformer']]):
        raise ValueError('Energy result refers to a different geographical cohort')
    if job['dispatch'] == 'causal':
        ca=job['causal']/'causal_summary.json'
        cc=job['causal']/'causal_pv_first_2025.csv'
        if not ca.is_file() or not cc.is_file():
            raise FileNotFoundError('Missing causal run '+str(job['causal']))
        c=json.loads(ca.read_text(encoding='utf-8'))
        if (digest(cc) != c.get('output_sha256') or
           c.get('input_manifest_sha256') != input_sha or
           c.get('reference_energy_manifest_sha256',c.get('source_energy_manifest_sha256')) != digest(mp)):
            raise ValueError('Causal dispatch source/CSV signature mismatch')
    return e,mp


def verify_completed(job, input_sha, manifest):
    """Skip only a fully signed and matching prior ANNUAL result."""
    # Without extended paths, ac_summary.json may exceed legacy Windows MAX_PATH.
    d=windows_extended_path(job['output'])
    if not d.exists():return False
    result=d/'ac_summary.json';hourly=d/'ac_hourly.csv'
    if not result.is_file() or not hourly.is_file():
        raise RuntimeError('Partial existing AC output. Inspect before resuming: '+str(d))
    rec=json.loads(result.read_text(encoding='utf-8'))
    expected=dict(status='ANNUAL_PVBESS_AC',hours=8760,
        scenario=job['variant'],transformer=job['transformer'],
        tier=job['tier'],topology=job['topology'],dispatch=job['dispatch'],
        input_manifest_sha256=input_sha)
    for k,v in expected.items():
        if rec.get(k)!=v:raise RuntimeError(f'Existing AC output mismatches {k}: {d}')
    if (abs(float(rec.get('pf',-1))-job['pf'])>1e-9 or
        abs(float(rec.get('length_factor',-1))-job['length'])>1e-9):
        raise RuntimeError('Existing AC output sensitivity mismatch '+str(d))
    if digest(hourly)!=rec.get('ac_hourly_sha256'):
        raise RuntimeError('Existing AC output CSV checksum differs '+str(d))
    if rec.get('energy_manifest_sha256')!=digest(job['energy']/'energy_manifest.json'):
        raise RuntimeError('Existing AC result has different energy manifest '+str(d))
    if rec.get('selected_house_ids')!=manifest['groups'][job['variant']][job['transformer']]:
        raise RuntimeError('Existing AC result has different house IDs '+str(d))
    # Ensure every completed output really covers exactly 2025 rather than 24 hours.
    with hourly.open(encoding='utf-8-sig',newline='') as f:
        rows=csv.DictReader(f)
        if 'timestamp_lst' not in rows.fieldnames:
            raise RuntimeError('Output has no hourly timestamp column '+str(d))
        count=0;first=None;last=None
        for row in rows:
            t=row['timestamp_lst']
            if count==0:first=t
            last=t;count+=1
        if count!=8760 or first!='2025-01-01 00:00:00' or last!='2025-12-31 23:00:00':
            raise RuntimeError('Existing AC output not full 2025 chronology '+str(d))
    return True


def run_jobs(repo,outbase,jobs,manifest):
    m,_,_,_=secure_context(repo,repo/MANIFEST_REL)
    if m['groups']!=manifest['groups']:
        raise ValueError('The signed 35-home assignments have changed')
    sha=digest(repo/MANIFEST_REL)
    completed, reused, blocked=[],[],[]
    for i,job in enumerate(jobs,1):
        print(f'ANNUAL {i}/{len(jobs)}: {job["variant"]} {job["transformer"]} '
              f'{job["tier"]}/{job["kind"]} {job["topology"]} '
              f'{job["dispatch"]} PF={job["pf"]:.2f} length={job["length"]:.1f}',flush=True)
        try:
            verify_source(job,sha,m)
            if verify_completed(job,sha,m):
                print('REUSED verified annual output:',job['output'],flush=True)
                reused.append(str(job['output']));continue
            if job['output'].exists():
                raise RuntimeError('Refuse to overwrite existing output')
            expected_parent = outbase/'annual_ac_replays_v1'
            if job['output'].parent != expected_parent:
                raise RuntimeError('Output escapes selected results parent')
            expected_parent.mkdir(parents=True,exist_ok=True)
            r=subprocess.run(job['command'],cwd=repo,check=False)
            if r.returncode:raise RuntimeError(f'AC runner exit status {r.returncode}')
            if not verify_completed(job,sha,m):
                raise RuntimeError('No signed complete AC output after runner returned')
            completed.append(str(job['output']))
        except Exception as ex:
            print('BLOCKED or FAILED:',str(ex),flush=True)
            blocked.append({'output':str(job['output']),'reason':str(ex)})
            # Continue independently signed cases. A numerical failure is not fabricated as feasibility.
    report={'status':'ANNUAL_PORTFOLIO_RESULTS_WITH_EXPLICIT_FAILURES',
            'requested':len(jobs),'completed_new':len(completed),
            'reused_verified':len(reused),'blocked_or_failed':len(blocked),
            'blocked_cases':blocked,'new_case_output_dirs':completed,
            'reused_case_output_dirs':reused,
            'source_manifest_sha256':sha,'numeric_work_performed_only_in_local_checkout':True}
    if outbase.is_dir():
        receipt=outbase/('annual_AC_replay_receipt_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        if receipt.exists():raise FileExistsError('Receipt collision '+str(receipt))
        receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('RECEIPT',receipt)
    print(json.dumps({k:report[k] for k in ['status','requested','completed_new','reused_verified','blocked_or_failed']},indent=2))
    return 0 if not blocked else 2


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--outbase',type=Path)
    ap.add_argument('--scope',choices=('baseline','sensitivities','full'),default='baseline')
    ap.add_argument('--dispatch',choices=('optimized','causal','both'),default='both')
    ap.add_argument('--cases',choices=('refs','new-four','all'),default='all')
    ap.add_argument('--transformer',choices=('94022','106039','113699','85398','92395'))
    ap.add_argument('--assignment',choices=('A0','A1'))
    ap.add_argument('--tier',choices=('min_cost','ss90'))
    ap.add_argument('--run',action='store_true',help='Dry-run and print plan unless present')
    args=ap.parse_args(argv)
    repo=args.repo_root.resolve();outbase=(args.outbase or repo/BASE_REL).resolve()
    # Never edit or create files in a dry run.
    jobs=build_jobs(repo,outbase,args.scope,args.dispatch,args.cases,
                    args.transformer,args.assignment,args.tier)
    if not jobs:raise ValueError('Filters selected no annual AC cases')
    print(json.dumps({'mode':'RUN_ANNUAL_8760' if args.run else 'DRY_RUN_NO_SOLVER_NO_WRITE',
        'scope':args.scope,'dispatch':args.dispatch,'cases':args.cases,
        'annual_8760_case_count':len(jobs),'A0_equal_A1_92395_deduplicated':True,
        'results_root':str(outbase/'annual_ac_replays_v1')},indent=2))
    if not args.run:
        for i,j in enumerate(jobs,1):
            print(f'{i:3d}. {j["variant"]} {j["transformer"]} {j["tier"]} '
                  f'{j["kind"]} {j["topology"]} {j["dispatch"]} '
                  f'PF={j["pf"]} length={j["length"]} -> {j["output"].name}')
        return 0
    path=repo/MANIFEST_REL
    manifest=json.loads(path.read_text(encoding='utf-8'))
    return run_jobs(repo,outbase,jobs,manifest)


if __name__=='__main__':sys.exit(main())
