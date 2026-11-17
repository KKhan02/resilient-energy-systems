#!/usr/bin/env python3
"""Plan and run geographically specific annual PV+BESS jobs, locally only.

Run order: mapped-energy, four-opt, mapped-causal, four-causal.
Source/frozen model verification and signed-result reuse; no GitLab changes.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

from study_a_pvbess import (MANIFEST_REL, RUNNER_REL, BASE_REL, digest,
                            create_plan, secure_context, group_for)


def proposed_jobs(repo, outbase, stage, transformer=None, assignment=None):
    entries=[]
    for case in create_plan():
        v,t,tier,kind=case['variant'],case['transformer'],case['tier'],case['kind']
        if transformer and t!=transformer:continue
        if assignment and v!=assignment:continue
        slug=f'{v}_{t}_{tier}_{"four" if kind=="new_four_house_milp" else "ref"}'
        energy=outbase/('energy_'+slug)
        causal=outbase/('causal_'+slug)
        if kind=='archived_hardware_fixed_dispatch':
            if stage in ('mapped-energy','all-energy','all'):
                args=[sys.executable,str(repo/RUNNER_REL),'energy','--manifest',str(repo/MANIFEST_REL),
                     '--assignment',v,'--transformer',t,'--anchor-tier',tier,'--outdir',str(energy)]
                entries.append({'job':'mapped_energy','variant':v,'trafo':t,'tier':tier,'outdir':energy,'args':args})
            if stage in ('mapped-causal','all-causal','all'):
                args=[sys.executable,str(repo/RUNNER_REL),'causal','--manifest',str(repo/MANIFEST_REL),
                     '--assignment',v,'--transformer',t,'--anchor-tier',tier,
                     '--energy-dir',str(energy),'--outdir',str(causal)]
                entries.append({'job':'mapped_causal','variant':v,'trafo':t,'tier':tier,
                                'outdir':causal,'energy':energy,'args':args})
        else:
            if stage in ('four-opt','all-energy','all'):
                args=[sys.executable,str(Path(__file__).resolve().parent/'study_a_pvbess.py'),
                      '--repo-root',str(repo),'--manifest',str(repo/MANIFEST_REL),'four-opt',
                      '--transformer',t,'--tier',tier,'--outdir',str(energy)]
                entries.append({'job':'four_opt','variant':v,'trafo':t,'tier':tier,'outdir':energy,'args':args})
            if stage in ('four-causal','all-causal','all'):
                args=[sys.executable,str(Path(__file__).resolve().parent/'study_a_pvbess.py'),
                      '--repo-root',str(repo),'--manifest',str(repo/MANIFEST_REL),'four-causal',
                      '--transformer',t,'--energy-dir',str(energy),'--outdir',str(causal)]
                entries.append({'job':'four_causal','variant':v,'trafo':t,'tier':tier,
                                'outdir':causal,'energy':energy,'args':args})
    if stage=='all':
        # chronological stages: solve all energies first, only then causal.
        entries.sort(key=lambda e:(0 if e['job'].endswith('energy') or e['job']=='four_opt' else 1,
                                   e['trafo'],e['variant'],e['tier']))
    return entries


def check_reuse(job, input_sha, manifest):
    folder=job['outdir']
    if not folder.exists():return False
    if job['job'] in ('mapped_energy','four_opt'):
        mf=folder/'energy_manifest.json';cf=folder/'energy_hourly_2025.csv'
        if not (mf.is_file() and cf.is_file()):
            raise RuntimeError('Partial existing output, manually inspect: '+str(folder))
        rec=json.loads(mf.read_text(encoding='utf-8'))
        if rec.get('energy_csv_sha256')!=digest(cf) or rec.get('input_manifest_sha256')!=input_sha:
            raise RuntimeError('Existing energy output signature differs: '+str(folder))
        if rec.get('transformer')!=job['trafo'] or rec.get('hardware_selection_tier')!=job['tier']:
            raise RuntimeError('Existing output cohort/tier differs: '+str(folder))
        intended=manifest['groups'][job['variant']][job['trafo']]
        if rec.get('selected_house_ids')!=intended:
            raise RuntimeError('Existing output houses differ: '+str(folder))
    else:
        mf=folder/'causal_summary.json';cf=folder/'causal_pv_first_2025.csv'
        if not (mf.is_file() and cf.is_file()):
            raise RuntimeError('Partial existing causal output: '+str(folder))
        rec=json.loads(mf.read_text(encoding='utf-8'))
        if rec.get('output_sha256')!=digest(cf) or rec.get('input_manifest_sha256')!=input_sha:
            raise RuntimeError('Existing causal output checksum differs: '+str(folder))
        signed=job['energy']/'energy_manifest.json'
        if not signed.exists() or rec.get('reference_energy_manifest_sha256',rec.get('source_energy_manifest_sha256'))!=digest(signed):
            raise RuntimeError('Causal output references a different PyPSA baseline')
    return True


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--outbase',type=Path)
    parser.add_argument('--stage',choices=('mapped-energy','four-opt','mapped-causal','four-causal',
                                           'all-energy','all-causal','all'),required=True)
    parser.add_argument('--transformer',choices=('94022','106039','113699','85398','92395'))
    parser.add_argument('--assignment',choices=('A0','A1'))
    parser.add_argument('--run',action='store_true',help='Otherwise show commands only')
    args=parser.parse_args(argv)
    repo=args.repo_root.resolve()
    outbase=(args.outbase or repo/BASE_REL).resolve()
    jobs=proposed_jobs(repo,outbase,args.stage,args.transformer,args.assignment)
    if not jobs:raise ValueError('Selected stage and filter match no cases')
    if not args.run:
        print('DRY RUN ONLY. Planned jobs:',len(jobs))
        for i,job in enumerate(jobs,1):
            print(i,job['job'],job['variant'],job['trafo'],job['tier'],'->',job['outdir'])
        print('No simulations run, no outputs written.')
        return 0
    manifest=repo/MANIFEST_REL
    m,_,_,_=secure_context(repo,manifest)
    input_sha=digest(manifest)
    success=0
    for i,job in enumerate(jobs,1):
        print(f'CASE {i}/{len(jobs)}: {job["job"]} {job["variant"]} {job["trafo"]} {job["tier"]}',flush=True)
        if check_reuse(job,input_sha,m):
            print('REUSED verified unchanged output:',job['outdir']);continue
        if 'energy' in job:
            if not (job['energy']/'energy_manifest.json').is_file():
                raise RuntimeError('Required annual PyPSA energy solve missing: '+str(job['energy']))
        # The signed v6.2 runner deliberately refuses to create missing output
        # parents. Create only the parent, after source verification and the
        # existing-output checks, without touching the requested case folder.
        if job['outdir'].parent != outbase:
            raise RuntimeError('Job output is outside the selected output base: '+str(job['outdir']))
        outbase.mkdir(parents=True, exist_ok=True)
        r=subprocess.run(job['args'],cwd=repo,check=False)
        if r.returncode:
            raise SystemExit('Job failed (stopped, no results claimed): '+str(job['outdir']))
        if not check_reuse(job,input_sha,m):
            raise RuntimeError('New job finished without signed output')
        success+=1
    print(json.dumps({'status':'ALL_REQUESTED_JOBS_SIGNED_OR_REUSED',
                      'number_jobs':len(jobs),'new_jobs':success,'unchanged_reused':len(jobs)-success},indent=2))
    return 0


if __name__=='__main__':sys.exit(main())
