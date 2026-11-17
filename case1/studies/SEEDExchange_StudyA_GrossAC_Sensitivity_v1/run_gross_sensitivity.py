#!/usr/bin/env python3
"""Local-only, restartable Study A gross PF x assumed-service-length sensitivity.

Reuses unchanged Study A v6.2 pandapower runner and signed source profiles.
No GitLab writes, no optimization, no edits to old results. Only 4 GIS-backed
transformers across A0 and A1; excludes unapproved 92395 provisional AC topology.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import csv

COHORTS={
  'A0':{'94022':10,'106039':12,'113699':4,'85398':4},
  'A1':{'94022':8,'106039':11,'113699':6,'85398':5},
}
EXPECTED_SHA='2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69'
MANIFEST_REL=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json')
RUNNER_REL=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py')
RESULT_REL=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/sensitivity_gross_v1')

@dataclass(frozen=True)
class Case:
    assignment:str
    transformer:str
    pf:float
    length:float
    phase:str

    @property
    def label(self):
        return f'{self.assignment}_{self.transformer}_pf{round(self.pf*100):03d}_length{round(self.length*10):02d}'


def planned_cases(phase:str, assignments=None, transformers=None):
    if phase not in ('main','interactions'):
        raise ValueError('Select main or interactions; full 3x3 is main + interactions + existing baseline')
    pairs=(((.95,1.),(1.,1.),(.98,1.3),(.98,1.6)) if phase=='main' else
           ((.95,1.3),(.95,1.6),(1.,1.3),(1.,1.6)))
    a=assignments if assignments else ('A0','A1')
    t=transformers if transformers else ('94022','106039','113699','85398')
    return [Case(x,y,pf,length,phase) for x in a for y in t for pf,length in pairs]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(repo,manifest,script):
    if not (repo/'.git').exists():
        raise RuntimeError('Run from your checked-out repository root with .git present')
    if not manifest.is_file() or not script.is_file():
        raise FileNotFoundError('Missing signed v6.2 manifest or unchanged seed runner')
    m=json.loads(manifest.read_text(encoding='utf-8'))
    if sha256(manifest)!=EXPECTED_SHA:
        raise ValueError('Signed input manifest has changed; stop and review')
    if sha256(script)!=m['script_sha256']:
        raise ValueError('Model runner no longer matches manifest script SHA; do not mix source versions')
    if m['population_houses']!=35 or m['2025_hours']!=8760:
        raise ValueError('Invalid profile manifest size')
    for ass,territories in COHORTS.items():
        for transformer,n in territories.items():
            if len(m['groups'][ass][transformer])!=n:
                raise ValueError(f'Changed cohorts: {ass}/{transformer}')
    for old,new in (('H03','113699'),('H06','113699'),('H13','85398')):
        if old not in m['groups']['A1'][new]:
            raise ValueError('A1 no longer preserves the approved 3-house proximity moves')
    if any('H30' not in m['groups'][s]['92395'] for s in ('A0','A1')):
        raise ValueError('92395 original source connection evidence changed')
    print('Preflight OK: signed 35-house manifest; frozen v6.2 runner; 8 GIS-backed cohorts')
    return m


def result_dir(root,case,hours):
    return root/(case.label+('_smoke24' if hours==24 else '_annual8760'))


def check_output(folder,case,hours,manifest_hash):
    """True when immutable output exists and metadata/CSV checksums validate.

    Raises on a partial/mismatched existing folder; never silently deletes it.
    """
    if not folder.exists():return False
    sp=folder/'ac_summary.json';cp=folder/'ac_hourly.csv'
    if not sp.is_file() or not cp.is_file():
        raise RuntimeError(f'Output exists but lacks BOTH files; inspect without overwriting: {folder}')
    summary=json.loads(sp.read_text(encoding='utf-8'))
    pairs={
      'scenario':case.assignment,'transformer':case.transformer,'mode':'gross',
      'simulation_hours':hours,'PF':case.pf,
      'service_length_multiplier':case.length,'input_manifest_sha256':manifest_hash,
      'ac_hourly_sha256':sha256(cp)
    }
    bad=[k for k,v in pairs.items() if summary.get(k)!=v]
    if bad:raise RuntimeError(f'Existing output metadata/hash mismatch {folder}: {bad}')
    if summary['converged_hours']+summary['nonconverged_hours']!=hours:
        raise RuntimeError('Existing summary convergence accounting error '+str(folder))
    return True


def run_case(script,manifest,root,case,hours):
    out=result_dir(root,case,hours)
    manifest_hash=sha256(manifest)
    if check_output(out,case,hours,manifest_hash):
        print(f'  PRESERVED existing {case.label} {hours}h',flush=True)
        return json.loads((out/'ac_summary.json').read_text(encoding='utf-8'))
    if out.exists():
        raise RuntimeError('Refusing to overwrite '+str(out))
    cmd=[sys.executable,str(script),'ac','--manifest',str(manifest),
      '--assignment',case.assignment,'--transformer',case.transformer,
      '--mode','gross','--hours',str(hours),'--pf',str(case.pf),
      '--service-factor',str(case.length),'--outdir',str(out)]
    print('  RUN',case.label,hours,'hours',flush=True)
    subprocess.run(cmd,check=True)
    if not check_output(out,case,hours,manifest_hash):
        raise RuntimeError('Runner did not produce final result '+str(out))
    return json.loads((out/'ac_summary.json').read_text(encoding='utf-8'))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--phase',choices=('main','interactions'),required=True)
    parser.add_argument('--assignment',choices=('A0','A1'),action='append',default=None)
    parser.add_argument('--transformer',choices=tuple(COHORTS['A0']),action='append',default=None)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--dry-run',action='store_true',help='List commands only, do not create outputs')
    action.add_argument('--run',action='store_true',help='Execute 24h smoke and then 8760h with original v6.2 runner')
    args=parser.parse_args(argv)
    repo=args.repo_root.resolve()
    manifest=repo/MANIFEST_REL;script=repo/RUNNER_REL;root=repo/RESULT_REL
    preflight(repo,manifest,script)
    cases=planned_cases(args.phase,args.assignment,args.transformer)
    print(f'{args.phase}: {len(cases)} sensitivity combinations, paired 24h + 8760h per combination')
    if args.dry_run:
        for c in cases:
            for hours in (24,8760):
                out=result_dir(root,c,hours)
                print(f'  {c.label} | {hours}h | {out.relative_to(repo)}')
        print('DRY RUN ONLY: no files written, no AC solved')
        return 0
    root.mkdir(parents=True,exist_ok=True)
    issues=[]
    for i,case in enumerate(cases,1):
        print(f'\n=== {i}/{len(cases)} {case.label} ===',flush=True)
        try:
            smoke=run_case(script,manifest,root,case,24)
            if smoke['nonconverged_hours']:
                print('  STOP THIS CASE: 24h nonconverged; preserved evidence',flush=True)
                issues.append((case.label,'24h_nonconvergence'))
                continue
            annual=run_case(script,manifest,root,case,8760)
            if annual['nonconverged_hours']:
                issues.append((case.label,'annual_nonconvergence'))
            print('  Annual infeasible:',annual['AC_infeasible_hours'],
                  'nonconverged:',annual['nonconverged_hours'],flush=True)
        except Exception as e:
            issues.append((case.label,str(e)))
            print('  ISSUE, preserved outputs:',str(e),flush=True)
    if issues:
        print('\nATTENTION: some cases need review. No outputs deleted:',issues)
        return 2
    print('\nPHASE COMPLETE: review ALL annual summary and hourly outputs before interpreting feasibility')
    return 0

if __name__=='__main__':sys.exit(main())
