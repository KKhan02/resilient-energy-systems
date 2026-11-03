#!/usr/bin/env python3
"""ONE entry point for 5..15 household conditional PyPSA capacity studies.

Default: scan each exact feasible PV count and allow PyPSA MILP to co-optimize
battery modules, battery power, inverter choice and 8760 hourly dispatch.
For EVERY house count and assumed 5..25kVA rating, also run multi-objective
constraint variants. Resumable JSONL, with summary results and figures.
No new battery dispatch engine. No claims of pandapower AC validation.

Use --preview before full execution to inspect computational work.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import traceback
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from model import Settings, solve, extract, summarize, PANEL_KW
from run import load_source, sha, monthly_table
from pareto_panel_sweep import summarize_sweep, plot_sweep
from site_capacity import site_cases


def parse_float_list(s):
    values=[float(x) for x in s.split(',') if x.strip()]
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError('Numeric comma-separated list required')
    return sorted(set(values))


def house_variants(first=5, last=15, two_eight_variants=True):
    if first<1 or last>20 or first>last:
        raise ValueError('Household count must be between 1 and 20 and ordered')
    result=[]
    for n in range(first,last+1):
        profiles=list(range(1,n+1))
        result.append(dict(case=f'{n}_homes'+('_H01' if n==8 else ''),houses=n,profiles=profiles,
                           evidence='SYNTHETIC_2025_HOUSEHOLD_COUNT_ONLY',
                           anchor='94022_7_cANDIDATES' if n==7 else '106039_12_CANDIDATES' if n==12 else 'NONE'))
        if n==8 and two_eight_variants:
            result.append(dict(case='8_homes_H02',houses=8,profiles=list(range(1,8))+[9],
                               evidence='SYNTHETIC_EIGHT_H02_PROFILE_ALTERNATIVE',anchor='NONE'))
    return result


def design_tasks(houses, ratings, panel_upper, site_bounds, max_battery_modules, ss_targets, budgets, panel_step=1):
    if panel_step<1 or panel_upper<0:raise ValueError('panel step/upper invalid')
    exact=list(range(0,panel_upper+1,panel_step))
    if exact[-1]!=panel_upper:exact.append(panel_upper)
    for h in houses:
        for kva in ratings:
            for p in exact:
                yield dict(case=h['case'],houses=h['houses'],profiles=h['profiles'],kva=kva,
                           task='fixed_PV_economic',panels=p,battery_modules=None,ss_target=None,budget=None,area_max_panels=panel_upper)
            # Independent BESS sweep: fix each battery module count and optimize
            # PV, inverter and hourly dispatch with the conservative site-area bound.
            for modules in range(max_battery_modules+1):
                yield dict(case=h['case'],houses=h['houses'],profiles=h['profiles'],kva=kva,
                           task='fixed_BESS_economic',panels=None,battery_modules=modules,
                           ss_target=None,budget=None,area_max_panels=min(site_bounds))
            # These supplement, not replace, fixed-PV and fixed-BESS cost optima.
            for cap in sorted(set(site_bounds)):
                for ss in ss_targets:
                    yield dict(case=h['case'],houses=h['houses'],profiles=h['profiles'],kva=kva,
                               task='epsilon_SS_min_cost',panels=None,battery_modules=None,ss_target=ss,budget=None,
                               area_max_panels=cap)
                for budget in budgets:
                    yield dict(case=h['case'],houses=h['houses'],profiles=h['profiles'],kva=kva,
                               task='budget_max_SS',panels=None,battery_modules=None,ss_target=None,budget=budget,
                               area_max_panels=cap)


def task_key(t):
    return json.dumps([t['case'],t['kva'],t['task'],t['panels'],t['ss_target'],t['budget'],t['area_max_panels'],t['battery_modules']],separators=(',',':'))


def prepare(args):
    fractions=parse_float_list(args.usable_fractions)
    cases=site_cases(fractions,args.area_m2_per_panel,args.gross_area_m2,args.max_inverter_kva)
    maxp=max(row['model_panel_bound'] for row in cases)
    houses=house_variants(args.houses_start,args.houses_end,not args.single_eight)
    ratings=parse_float_list(args.transformer_ratings)
    ss=parse_float_list(args.ss_targets)
    budgets=parse_float_list(args.capex_budgets)
    if any(x<=0 for x in ratings) or any(not 0<=x<=1 for x in ss) or any(x<0 for x in budgets):
        raise ValueError('Invalid transformer, self-sufficiency or capital budget')
    if maxp>500:raise ValueError('Model Settings supports at most 500 panels')
    tasks=list(design_tasks(houses,ratings,maxp,[x['model_panel_bound'] for x in cases],args.battery_modules_limit,ss,budgets,args.panel_step))
    return cases,houses,ratings,tasks


def execute_task(t, inputs, base, maximum_panels, args):
    demand,pv,ghi,source=inputs[tuple(t['profiles'])]
    settings=replace(base,transformer_kva=t['kva'],max_panels=t['area_max_panels'],
                     fixed_panels=t['panels'],fixed_battery_modules=t['battery_modules'],
                     min_self_sufficiency=t['ss_target'],
                     capex_budget_usd=t['budget'],
                     objective='energy' if t['task']=='budget_max_SS' else 'economic')
    try:
        network=solve(demand,pv,settings)
        hourly=extract(network,settings,demand,ghi)
        s=summarize(network,hourly,settings,t['case'])
        s['status']='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER'
        s['source_sha256']=sha(source)
        s['house_count']=t['houses']
        s['profiles']=t['profiles']
        s['actual_lv_powerflow']='NOT_RUN'
        s['study_area']='USER_DIGITIZED_SITE_A_GEOMETRIC_SCREEN_ONLY'
        s['annual_hours']=len(hourly)
        return s
    except (ValueError,RuntimeError) as ex:
        # No silent deletion; distinguish infeasibility from runtime error.
        error=str(ex)
        is_infeasible='infeasib' in error.lower() or 'Reactive demand alone' in error
        return dict(status='INFEASIBLE_MODEL' if is_infeasible else 'ERROR_SOLVER_OR_INPUT',reason=error)


def add_task_columns(result,t,site_records):
    r=dict(t)
    r['task_key']=task_key(t)
    installed=t['panels'] if t['panels'] is not None else result.get('panels_equivalent',None)
    r['site_fractions_applicable']=','.join(str(row['usable_fraction']) for row in site_records
              if installed is None or installed<=row['model_panel_bound']+1.e-5)
    r.update(result)
    # Fixed-site upper bound applies to every solve, optimizer chose max panel count separately.
    return r


def recover_records(path):
    if not path.exists():return {},[]
    bykey={};logs=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try:
            obj=json.loads(line);key=obj['task_key']
        except (ValueError,KeyError):continue
        if key not in bykey:logs.append(obj)
        bykey[key]=obj
    return bykey,logs


def write_outputs(out, records, sites):
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(sites).to_csv(out/'site_capacity_scenarios.csv',index=False)
    df=pd.DataFrame(records)
    df.to_csv(out/'complete_study_results.csv',index=False)
    if df.empty:return
    for (name,kva),sub in df.groupby(['case','kva'],dropna=False):
        p=sub[sub.task=='fixed_PV_economic'].copy()
        if p.empty:continue
        p=summarize_sweep(p)
        stem=out/'figures'/f'{name}_{kva:g}kva'
        p.to_csv(out/f'{name}_{kva:g}kva_fixedPV_classified.csv',index=False)
        plot_sweep(p,stem,case=name,assumed_kva=kva)
        battery=sub[(sub.task=='fixed_BESS_economic') & sub.status.astype(str).str.startswith('OPTIMAL')].copy()
        if not battery.empty:
            plot_battery_sweep(battery,stem)
        plot_all_objective_candidates(sub,stem,case=name,assumed_kva=kva)
    passes=df[df.status.astype(str).str.startswith('OPTIMAL')].copy()
    if not passes.empty:
        passes['self_sufficiency_of_demand_pct']=pd.to_numeric(passes['self_sufficiency_of_demand_pct'],errors='coerce')
        passes['annual_total_usd']=pd.to_numeric(passes['annual_total_usd'],errors='coerce')
        f=passes[passes.task.isin(['fixed_PV_economic','fixed_BESS_economic','epsilon_SS_min_cost','budget_max_SS'])]
        result=[]
        for kva,g in f.groupby('kva'):
            for threshold in [0.,70.,80.,90.,95.]:
                q=g[g.self_sufficiency_of_demand_pct>=threshold-1e-6]
                result.append(dict(kva=kva,ss_threshold_pct=threshold,
                    max_conditional_house_count=int(q.houses.max()) if len(q) else None,
                    status='PROXY_ENERGY_ONLY_NOT_AC_VALIDATED',
                    study_upper_edge_reached=bool(len(q) and q.houses.max()>=15),
                    upper_edge_note='15 is tested upper limit; increase to 20 before claiming MAXIMUM' if len(q) and q.houses.max()>=15 else ''))
        pd.DataFrame(result).to_csv(out/'conditional_hosting_envelope.csv',index=False)
    manifest=dict(perfect_foresight=True,operational_mode='FULL_YEAR_IDEALIZED_PLANNING_BENCHMARK',assumptions='Single stochastic realization; no LV AC power flow; no meter verification',
      area='User-digitized Site A polygon, 6m2/panel default illustrative allowance',
      optimization='MILP fixed panel counts, optimize battery modules, battery kW, inverter options and 8760h operation',
      reporting='Do not claim complete Pareto frontier; epsilon objectives are sampled',
      results=int(len(df)),status_counts=df.status.value_counts().to_dict())
    (out/'study_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')


def plot_all_objective_candidates(sub,stem,case,assumed_kva):
    """All objectives on one labeled cost versus self-sufficiency candidate set."""
    import matplotlib.pyplot as plt
    q=sub[sub.status.astype(str).str.startswith('OPTIMAL')].copy()
    if q.empty:return
    for field in ('annual_total_usd','self_sufficiency_of_demand_pct','panels_equivalent',
                  'battery_usable_kwh','inverter_ac_kva_assumed_unity_pf'):
        q[field]=pd.to_numeric(q[field],errors='coerce')
    q=q[np.isfinite(q.annual_total_usd)&np.isfinite(q.self_sufficiency_of_demand_pct)].copy()
    if q.empty:return
    frontier=[]
    for idx,entry in q.iterrows():
        dominated=((q.annual_total_usd<=entry.annual_total_usd+1e-6)&
                   (q.self_sufficiency_of_demand_pct>=entry.self_sufficiency_of_demand_pct-1e-6)&
                   ((q.annual_total_usd<entry.annual_total_usd-1e-6)|
                    (q.self_sufficiency_of_demand_pct>entry.self_sufficiency_of_demand_pct+1e-6)))
        if not dominated.any():frontier.append(idx)
    nd=q.loc[frontier].sort_values('self_sufficiency_of_demand_pct')
    fig,ax=plt.subplots(figsize=(10,6))
    for task,g in q.groupby('task'):
        ax.scatter(g.self_sufficiency_of_demand_pct,g.annual_total_usd,
                   marker={'fixed_PV_economic':'o','fixed_BESS_economic':'x',
                           'epsilon_SS_min_cost':'s','budget_max_SS':'^'}.get(task,'o'),
                   alpha=.35,s=25,label=task)
    ax.plot(nd.self_sufficiency_of_demand_pct,nd.annual_total_usd,marker='o',
            linewidth=1.7,label='Nondominated among sampled candidates')
    # Label a handful of distinct equipment options for readability.
    sampled=nd.iloc[np.unique(np.linspace(0,len(nd)-1,min(7,len(nd)),dtype=int))]
    for _,v in sampled.iterrows():
        ax.annotate(f"{v.panels_equivalent:.0f}P / {v.battery_usable_kwh:.1f}kWh / {v.inverter_ac_kva_assumed_unity_pf:g}kVA",
            (v.self_sufficiency_of_demand_pct,v.annual_total_usd),
            xytext=(5,5),textcoords='offset points',fontsize=7)
    ax.set(xlabel='Annual operational self-sufficiency (%)',
        ylabel='Annualized equipment + net grid cost (USD/year)',
        title=f'{case}: sampled multiobjective candidate frontier; assumed {assumed_kva:g} kVA')
    ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(str(stem)+'_all_objectives_pareto.png',dpi=160)
    fig.savefig(str(stem)+'_all_objectives_pareto.svg')
    plt.close(fig)


def plot_battery_sweep(battery,stem):
    import matplotlib.pyplot as plt
    q=battery.copy().sort_values('battery_modules')
    for k in ['battery_modules','panels_equivalent','battery_usable_kwh','annual_total_usd','self_sufficiency_of_demand_pct']:
        q[k]=pd.to_numeric(q[k],errors='coerce')
    fig,axes=plt.subplots(2,1,figsize=(10,8),sharex=True)
    axes[0].plot(q.battery_modules,q.annual_total_usd,marker='o')
    axes[0].set_ylabel('Annualized cost incl. grid import (USD/year)')
    axes[1].plot(q.battery_modules,q.self_sufficiency_of_demand_pct,marker='o')
    axes[1].set_ylabel('Self-sufficiency (%)')
    axes[1].set_xlabel('Fixed battery module count (4.325 kWh usable/module)')
    for ax in axes:ax.grid(alpha=.25)
    fig.suptitle('Exact battery count, PV panels and inverter jointly optimized')
    fig.tight_layout()
    fig.savefig(str(stem)+'_battery_sweep.png',dpi=160)
    fig.savefig(str(stem)+'_battery_sweep.svg')
    plt.close(fig)


def rerun_shortlists(args,records,repo,base,max_p):
    """Export full 8760-hour traces for selected 7, 9 and 12 home designs."""
    from run import save_run
    df=pd.DataFrame(records)
    subset=df[(df.task=='fixed_PV_economic') & df.status.astype(str).str.startswith('OPTIMAL')]
    for count in [7,9,12]:
        candidate=subset[(subset.houses==count)&(subset.kva==5.)]
        if candidate.empty:continue
        row=candidate.loc[pd.to_numeric(candidate.annual_total_usd,errors='coerce').idxmin()]
        profiles=[int(x) for x in row.profiles]
        case='seven' if count==7 else 'nine' if count==9 else 'twelve'
        data=load_source(repo,case,limit_hours=8760,profile_ids=profiles)
        setting=replace(base,transformer_kva=5.,fixed_panels=int(row.panels),fixed_battery_modules=None,
                        max_panels=max_p,objective='economic',capex_budget_usd=None,
                        min_self_sufficiency=None)
        network=solve(data[0],data[1],setting)
        save_run(args.outdir/'shortlisted_hourly',case,f'best_fixedPV_{int(row.panels)}panels',
                 network,setting,data[0],data[2],data[3],repo,8760,profile_ids=profiles)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--outdir',type=Path,default=Path('case1/studies/pypsa_joint_optimization_v1/outputs/full_study'))
    ap.add_argument('--houses-start',type=int,default=5)
    ap.add_argument('--houses-end',type=int,default=15)
    ap.add_argument('--transformer-ratings',default='5,10,15,20,25',help='Hypothetical sensitivities except existing archived 5kVA cases')
    ap.add_argument('--usable-fractions',default='0.25,0.50,0.75')
    ap.add_argument('--area-m2-per-panel',type=float,default=6.0)
    ap.add_argument('--gross-area-m2',type=float,default=None,
        help='Override source site area. Default reads Site A polygon area from original repository GeoJSON.')
    ap.add_argument('--max-inverter-kva',type=float,default=24.)
    ap.add_argument('--battery-modules-limit',type=int,default=16)
    ap.add_argument('--ss-targets',default='0.70,0.80,0.90,0.95')
    ap.add_argument('--capex-budgets',default='12000,20000,30000')
    ap.add_argument('--panel-step',type=int,default=1)
    ap.add_argument('--single-eight',action='store_true',help='Omit alternative H02 synthetic profile realization')
    ap.add_argument('--hours',type=int,default=8760)
    ap.add_argument('--export-policy',choices=['zero','reference_credit'],default='zero')
    ap.add_argument('--continuous',action='store_true',help='LP model diagnostics only; fractional equipment not physically realizable')
    ap.add_argument('--preview',action='store_true',help='Only report task count and area-derived bounds, do not run a solver')
    ap.add_argument('--max-tasks',type=int,default=None,help='Safe staged execution then resume; not a new physics model')
    ap.add_argument('--no-shortlist',action='store_true',help='Skip selected 8760h hourly/monthly/day/week/year reruns when full study completes')
    args=ap.parse_args(argv)
    if args.gross_area_m2 is None:
        polygon=args.repo_root/'case1/studies/site_a_solar/site_a_user_digitized_boundary.geojson'
        if polygon.is_file():
            data=json.loads(polygon.read_text(encoding='utf-8'))
            args.gross_area_m2=float(data['features'][0]['properties']['area_geodesic_m2'])
        elif args.preview:
            args.gross_area_m2=1759.26 # explicitly source-verified fallback for preview only
        else:
            raise FileNotFoundError('Site A original polygon is absent; provide --gross-area-m2 to document deliberate override')
    sites,houses,ratings,tasks=prepare(args)
    max_p=max(x['model_panel_bound'] for x in sites)
    counts=dict(perfect_foresight=True,operational_mode='FULL_YEAR_IDEALIZED_PLANNING_BENCHMARK',house_scenarios=len(houses),transformer_ratings=ratings,
        site_scenarios=sites,panel_counts_per_house_transformer=max_p+1,
        total_distinct_solver_tasks=len(tasks),hours_per_task=args.hours,
        solver='MILP' if not args.continuous else 'LP_RELAXATION',
        panel_step=args.panel_step,nonlinear_AC_network_validation='NOT_INCLUDED')
    if args.preview:
        print(json.dumps(counts,indent=2))
        return counts
    repo=args.repo_root.resolve()
    if args.hours!=8760:
        print('PARTIAL HOUR WINDOW: reports must NOT be interpreted as annual costs or seasonal performance',file=sys.stderr)
    if not (repo/'Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv').is_file():
        raise FileNotFoundError('Run from a complete original repository checkout (input CSV missing)')
    args.outdir.mkdir(parents=True,exist_ok=True)
    (args.outdir/'run_plan.json').write_text(json.dumps(counts,indent=2),encoding='utf8')
    jsonl=args.outdir/'checkpoint.jsonl'
    known,all_records=recover_records(jsonl)
    # Retry previous model/runtime errors after code changes; preserve prior evidence.
    to_run=[t for t in tasks if task_key(t) not in known or str(known[task_key(t)].get('status','')).startswith('ERROR_')]
    inputs={}
    base=Settings(max_panels=max_p,max_battery_modules=args.battery_modules_limit,
                  max_inverter_kva=args.max_inverter_kva,discrete=not args.continuous,
                  export_policy=args.export_policy)
    completed=0
    for t in to_run:
        if args.max_tasks is not None and completed>=args.max_tasks:break
        key=tuple(t['profiles'])
        if key not in inputs:
            inputs[key]=load_source(repo,'seven',limit_hours=args.hours,profile_ids=t['profiles'])
        result=execute_task(t,inputs,base,max_p,args)
        enriched=add_task_columns(result,t,sites)
        with jsonl.open('a',encoding='utf8') as f:
            f.write(json.dumps(enriched,default=float)+'\n')
        all_records.append(enriched)
        completed+=1
        if completed%20==0:
            print('Completed this invocation',completed,'remaining',len(to_run)-completed,flush=True)
    # One record per exact task, keeping the latest retest result.
    latest={row['task_key']:row for row in all_records}
    all_records=list(latest.values())
    write_outputs(args.outdir,all_records,sites)
    if not args.no_shortlist and len(all_records)>=len(tasks):
        rerun_shortlists(args,all_records,repo,base,max_p)
    print(f"Study checkpoint: {len(all_records)}/{len(tasks)} completed. No pandapower AC validation.")
    return counts

if __name__=='__main__':main()
