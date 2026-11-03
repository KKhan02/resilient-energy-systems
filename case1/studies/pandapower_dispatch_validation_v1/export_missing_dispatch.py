#!/usr/bin/env python3
"""Export 8 missing 8760-hour PyPSA optimized dispatch cases for the AC sweep.

Re-solves the selected minimum-annual-cost fixed-panel MILP once per missing
household count. Does not reconstruct fictitious hourly flows from annual totals.
Read only from the existing 6840-case CSV; never edits that result population.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
STUDY=REPO/'case1/studies/pypsa_joint_optimization_v1'
DEFAULT_RESULTS=STUDY/'outputs/full_study/complete_study_results.csv'
DEFAULT_DISPATCH=HERE/'input/dispatch'


def selected_designs(results:pd.DataFrame,counts:list[int])->list[dict]:
    for col in ('houses','kva','status','task','annual_total_usd','panels','area_max_panels'):
        if col not in results:
            raise ValueError('Missing complete_study_results.csv column: '+col)
    choices=results[(results['kva'].astype(float)==5.0) &
                    (results['task']=='fixed_PV_economic') &
                    (results['status']=='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER')].copy()
    choices['annual_total_usd']=pd.to_numeric(choices['annual_total_usd'],errors='coerce')
    rows=[]
    for h in counts:
        d=choices[(choices['houses']==h)&choices['annual_total_usd'].notna()].copy()
        if d.empty:raise ValueError(f'No optimal fixed-PV economic result for {h} houses / 5 kVA')
        d=d.sort_values(['annual_total_usd','panels'],kind='mergesort')
        b=d.iloc[0]
        if abs(float(b.panels)-round(float(b.panels)))>1e-5:
            raise ValueError(f'Noninteger selected panel count for {h} houses')
        rows.append({'houses':h,'case':str(b['case']),'panels':int(round(float(b.panels))),
                     'max_panels':int(round(float(b.area_max_panels))),
                     'annual_total_usd':float(b.annual_total_usd),
                     'source_sha256':str(b.get('source_sha256','')),
                     'battery_modules_expected':float(b.get('battery_modules_equivalent',float('nan'))),
                     'inverter_kva_expected':float(b.get('inverter_ac_kva_assumed_unity_pf',float('nan')))})
    return rows


def run(args):
    if not args.results.exists():
        raise FileNotFoundError('Missing optimization result CSV: '+str(args.results))
    records=selected_designs(pd.read_csv(args.results,low_memory=False),args.cases)
    todo=[r for r in records if args.overwrite or not (args.dispatch_dir/f"{r['houses']}_homes_hourly_dispatch.csv").is_file()]
    for r in records:
        path=args.dispatch_dir/f"{r['houses']}_homes_hourly_dispatch.csv"
        print(f"{r['houses']:2d} homes: {r['panels']:2d} PV panels, best cost ${r['annual_total_usd']:.2f}/year; "
              +('SOLVE' if r in todo else 'REUSE EXISTING')+f'  [{path}]')
    print(f'New full-year PyPSA MILP runs needed: {len(todo)}')
    if args.dry_run or not todo:
        return
    if args.max_new>0:todo=todo[:args.max_new]
    sys.path.insert(0,str(STUDY))
    import model as pypsa_model
    from run import load_source,sha
    # Require the full-study model with the fixed-panel constraint.
    if 'fixed_panels' not in pypsa_model.Settings.__dataclass_fields__:
        raise RuntimeError('Expected the existing full_study model.py with Settings.fixed_panels')
    args.dispatch_dir.mkdir(parents=True,exist_ok=True)
    for r in todo:
        h=r['houses'];profiles=list(range(1,h+1))
        demand,pv,ghi,source=load_source(args.repo_root,'seven',limit_hours=None,profile_ids=profiles)
        if len(demand)!=8760:raise ValueError(f'Unexpected duration for {h} houses')
        reference_hash=r['source_sha256']
        if reference_hash not in ('','nan','None') and reference_hash!=sha(source):
            raise ValueError(f'{h} homes: source dataset hash differs from optimization result. Refuse to mix inputs.')
        st=pypsa_model.Settings(transformer_kva=5.0,loading_pu=.90,load_pf=.98,
            max_panels=r['max_panels'],fixed_panels=r['panels'],max_battery_modules=16,
            max_battery_power_kw=24.0,max_inverter_kva=24.0,
            objective='economic',export_policy='zero',discrete=True,
            allow_unserved=False,solver_name='highs')
        print(f'Running PyPSA fixed-PV dispatch: {h} households, {r["panels"]} panels',flush=True)
        net=pypsa_model.solve(demand,pv,st)
        dispatch=pypsa_model.extract(net,st,demand,ghi)
        if len(dispatch)!=8760 or not np.isfinite(dispatch.select_dtypes(include='number').to_numpy()).all():
            raise ValueError(f'Invalid hourly solver results for {h} houses')
        summary=pypsa_model.summarize(net,dispatch,st,f'{h}_homes')
        achieved=float(summary['annual_total_usd'])
        error=achieved-r['annual_total_usd']
        if abs(error)>max(10.0,0.01*abs(r['annual_total_usd'])):
            raise RuntimeError(f'{h} homes: rerun annual cost ${achieved:.2f} differs from saved best ${r["annual_total_usd"]:.2f}. Refusing mismatched dispatch.')
        path=args.dispatch_dir/f'{h}_homes_hourly_dispatch.csv'
        dispatch.to_csv(path,float_format='%.7f')
        # Reuse the pandapower input validator before marking export complete.
        from run_validation import load_dispatch
        load_dispatch(path)
        meta={'households':h,'profiles':profiles,'assumed_transformer_kva':5.0,
              'candidate_territory':'NOT_VERIFIED_FOR_THIS_HOUSEHOLD_SWEEP',
              'source_sha256':sha(source),'panels_fixed':r['panels'],
              'best_saved_annual_usd':r['annual_total_usd'],
              'rerun_annual_usd':achieved,'model_summary':summary,
              'interpretation':'Energy-only 8760h optimization dispatch; no AC feeder validation'}
        (args.dispatch_dir/f'{h}_homes_pypsa_manifest.json').write_text(json.dumps(meta,indent=2,default=float),encoding='utf-8')
        print(f'Wrote {path} ({len(dispatch):,} hours)')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=REPO)
    p.add_argument('--results',type=Path,default=DEFAULT_RESULTS)
    p.add_argument('--dispatch-dir',type=Path,default=DEFAULT_DISPATCH)
    p.add_argument('--cases',nargs='+',type=int,default=list(range(5,16)))
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--max-new',type=int,default=0,help='0=all new solves; positive=solve at most this many')
    p.add_argument('--overwrite',action='store_true')
    a=p.parse_args()
    if a.max_new<0 or not a.cases or any(h<5 or h>15 for h in a.cases):
        p.error('Cases must be 5..15 and max-new >= 0')
    run(a)

if __name__=='__main__': main()
