#!/usr/bin/env python3
"""Run the PyPSA-Linopy joint expansion model from the full GitLab checkout.

No CI activity or repo modifications by default. Each solution writes exact
hourly dispatch and monthly aggregates with explicit provisional evidence status.
"""
from __future__ import annotations
import argparse, json, sys, hashlib, traceback
from dataclasses import replace, asdict
from pathlib import Path
import numpy as np
import pandas as pd
from model import Settings,solve,extract,summarize,PANEL_KW,BATTERY_USABLE_KWH

SOURCE=Path('Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv')
NASA=Path('case1/data/NASA_POWER_SanRafael_hourly_2025.csv')
PROFILE_ASSIGNMENTS={
 'seven':[1,2,3,4,5,6,7],
 'eight_H01':[1,2,3,4,5,6,7,8],
 'eight_H02':[1,2,3,4,5,6,7,9],
 'nine':[1,2,3,4,5,6,7,8,9],
 'twelve':[1,2,3,4,5,6,7,8,9,10,11,12],
}
CASE_NODES={'seven':'931076','eight_H01':'931076','eight_H02':'931076',
            'nine':'931076','twelve':'923494'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def load_source(repo:Path,case:str, limit_hours=None, profile_ids=None):
    if case not in PROFILE_ASSIGNMENTS:raise ValueError('Unknown case '+case)
    path=repo/SOURCE
    df=pd.read_csv(path,parse_dates=['timestamp']).set_index('timestamp')
    expected=pd.date_range('2025-01-01',periods=8760,freq='h')
    if len(df)!=len(expected) or not df.index.equals(expected):
        raise ValueError('2025 NASA / stochastic source is not all 8760 LST hours')
    selected_profiles=profile_ids if profile_ids is not None else PROFILE_ASSIGNMENTS[case]
    if len(set(selected_profiles))!=len(selected_profiles) or any(k<1 or k>20 for k in selected_profiles):
        raise ValueError('Hosting uses at most 20 distinct archived synthetic profiles')
    columns=[f'house_{k}_kw' for k in selected_profiles]
    needed=columns+['nasa_pv_dc_kw']
    if not set(needed).issubset(df.columns):
        raise KeyError('Missing columns '+str(set(needed)-set(df.columns)))
    if df[needed].isna().any().any() or (df[needed]<0).any().any():
        raise ValueError('Missing/negative household/PV input')
    demand=df[columns].sum(axis=1)
    # Original v18/v5 'nasa_pv_dc_kw' corresponds to original 12 * 435W = 5.22kWp.
    pv_pu=(df['nasa_pv_dc_kw']/5.22).clip(lower=0)
    if pv_pu.max()>1.00001:
        raise ValueError('PV DC profile > 1pu at reference; inspect source')
    ghi=df['ALLSKY_SFC_SW_DWN'] if 'ALLSKY_SFC_SW_DWN' in df else None
    if limit_hours is not None:
        if limit_hours<=0:raise ValueError('Invalid partial test window')
        demand,pv_pu=demand.iloc[:limit_hours],pv_pu.iloc[:limit_hours]
        if ghi is not None:ghi=ghi.iloc[:limit_hours]
    return demand,pv_pu,ghi,path

def monthly_table(hourly):
    groups=hourly.resample('MS')
    rows=[]
    for ts,g in groups:
        demand=g.demand_kw.sum();imp=g.grid_import_kw.sum();ens=g.unserved_kw.sum()
        rows.append(dict(month=ts.strftime('%Y-%m'),demand_kwh=demand,
           pv_dc_kwh=g.pv_dc_generated_kw.sum(),pv_available_dc_kwh=g.pv_dc_available_kw.sum(),
           battery_charging_dc_kwh=g.battery_charge_dc_kw.sum(),
           battery_discharging_dc_kwh=g.battery_discharge_dc_kw.sum(),
           grid_import_kwh=imp,grid_export_kwh=g.grid_export_kw.sum(),
           curtailment_dc_kwh=g.curtailed_pv_dc_kw.sum(),ens_kwh=ens,
           self_sufficiency_pct=100*(demand-imp-ens)/demand if demand else np.nan,
           grid_import_free=(imp<1e-5 and ens<1e-5),
           total_ghi_kwh_m2=g.ghi_wh_m2.sum()/1000 if 'ghi_wh_m2' in g else np.nan))
    return pd.DataFrame(rows)

def save_run(out,case,tag,n,st,demand,ghi,src_path,repo,window_hours,profile_ids=None):
    target=out/f'{case}_{tag}'
    target.mkdir(parents=True,exist_ok=True)
    series=extract(n,st,demand,ghi)
    summary=summarize(n,series,st,case)
    summary.update({'household_count':len(profile_ids if profile_ids is not None else PROFILE_ASSIGNMENTS[case]),
                   'profile_indices':profile_ids if profile_ids is not None else PROFILE_ASSIGNMENTS[case],
                   'candidate_epm_node':CASE_NODES[case],
                   'connection_status':'USER_MAP_CANDIDATE_NOT_UTILITY_VERIFIED',
                   'model_horizon_hours':len(series),
                   'yearly_cost_interpretation':'VALID_8760_ONLY' if len(series)==8760 else 'NOT_ANNUAL_PARTIAL_WINDOW',
                   'source_sha256':sha(src_path)})
    series.to_csv(target/'hourly_dispatch.csv',float_format='%.7f')
    monthly_table(series).to_csv(target/'monthly_energy_balance.csv',index=False,float_format='%.6f')
    (target/'model_manifest.json').write_text(json.dumps({'settings':asdict(st),
        'summary':summary,'source':str(src_path.relative_to(repo)),
        'solar':'NASA-2025 pvlib-derived DC profile from original v18/v5',
        'households':'Seed 20250913, independent stochastic profiles, each renormalized to 1898kWh/year; no meters',
        'constraints':'PCC approximate S limit; pandapower LV AC NOT RUN',
        'costs':'historical HOMER/quote proxy; excludes LV, metering, EPM, permits and site-specific BOS'},
        indent=2,default=float),encoding='utf8')
    from plots import plot_all
    plot_all(series,target/'figures',case,summary)
    return summary

def attempt(repo,out,case,st,tag,hours,profile_ids=None,summary_only=False):
    demand,pv,ghi,path=load_source(repo,case,hours,profile_ids=profile_ids)
    try:
        n=solve(demand,pv,st)
        if summary_only:
            hourly=extract(n,st,demand,ghi)
            s=summarize(n,hourly,st,case)
            s.update({'household_count':len(profile_ids if profile_ids is not None else PROFILE_ASSIGNMENTS[case]),
                      'source_sha256':sha(path),'model_horizon_hours':len(hourly),
                      'candidate_epm_node':CASE_NODES[case],
                      'connection_status':'USER_MAP_CANDIDATE_NOT_UTILITY_VERIFIED',
                      'yearly_cost_interpretation':'VALID_8760_ONLY' if len(hourly)==8760 else 'NOT_ANNUAL_PARTIAL_WINDOW'})
        else:
            s=save_run(out,case,tag,n,st,demand,ghi,path,repo,hours,profile_ids=profile_ids)
        return s
    except (ValueError,RuntimeError) as e:
        return {'case':case,'tag':tag,'status':'INFEASIBLE_OR_FAILED', 'reason':str(e),
                'transformer_assumed_kva':st.transformer_kva,
                'assumed_kva':st.transformer_kva, 'export_policy':st.export_policy,
                'pandapower_status':'NOT_RUN'}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--outdir',type=Path,required=True)
    ap.add_argument('--mode',choices=['economic','energy','frontier','hosting','panel_sweep'],default='economic')
    ap.add_argument('--cases',default='seven,eight_H01,eight_H02,nine,twelve')
    ap.add_argument('--transformer-kva-12',default='5,10,15',
      help='Nameplates for node 923494 are HYPOTHETICAL kVA sensitivity, not EPM certification')
    ap.add_argument('--export',choices=['zero','reference_credit'],default='zero')
    ap.add_argument('--max-panels',type=int,default=64)
    ap.add_argument('--fixed-panels',type=int,default=None,help='Fix exact panel count for a detailed economic/frontier rerun')
    ap.add_argument('--panel-sweep-start',type=int,default=0)
    ap.add_argument('--panel-sweep-end',type=int,default=64)
    ap.add_argument('--panel-sweep-step',type=int,default=1)
    ap.add_argument('--sweep-keep-hourly',action='store_true',
                    help='Save hourly traces and all figures for EVERY PV count (large output)')
    ap.add_argument('--max-battery-modules',type=int,default=16)
    ap.add_argument('--max-inverter-kva',type=float,default=24)
    ap.add_argument('--budget-usd',type=float,default=None)
    ap.add_argument('--min-self-sufficiency',type=float,default=None)
    ap.add_argument('--continuous',action='store_true',help='LP relaxation for diagnostic sizing. Discrete MILP is default')
    ap.add_argument('--hours',type=int,default=8760,help='168 for first-week smoke; FULL ANNUAL =8760')
    ap.add_argument('--solver',default='highs')
    ap.add_argument('--hosting-start',type=int,default=7)
    ap.add_argument('--hosting-end',type=int,default=20)
    ap.add_argument('--hosting-panel-caps',default='32,48,64')
    ap.add_argument('--hosting-ss-targets',default='0.70,0.80,0.90')
    ap.add_argument('--hosting-case',choices=['seven','twelve'],default='seven')
    ap.add_argument('--frontier-budgets',default='5000,8000,12000,16000,22000')
    ap.add_argument('--frontier-ss-targets',default='0.50,0.65,0.75,0.85,0.95')
    args=ap.parse_args()
    repo=args.repo_root.resolve()
    if not (repo/SOURCE).is_file():raise FileNotFoundError('Requires full repository checkout '+str(repo/SOURCE))
    if args.mode=='energy' and args.budget_usd is None:ap.error('energy mode requires --budget-usd')
    if args.mode=='panel_sweep' and args.fixed_panels is not None:
        ap.error('--fixed-panels is for individual reruns, not --mode panel_sweep')
    cases=[x.strip() for x in args.cases.split(',') if x.strip()]
    ratings12=[float(x) for x in args.transformer_kva_12.split(',')]
    args.outdir.mkdir(parents=True,exist_ok=True)
    results=[]
    st=Settings(max_panels=args.max_panels,fixed_panels=args.fixed_panels,
         max_battery_modules=args.max_battery_modules,
         max_inverter_kva=args.max_inverter_kva,export_policy=args.export,
         objective='energy' if args.mode=='energy' else 'economic',
         capex_budget_usd=args.budget_usd,min_self_sufficiency=args.min_self_sufficiency,
         discrete=not args.continuous,solver_name=args.solver)
    if args.mode=='panel_sweep':
        # Exact 0..64 count; never conflate a PV cap with installed PV size.
        start,end,step=args.panel_sweep_start,args.panel_sweep_end,args.panel_sweep_step
        if start<0 or end<start or end>args.max_panels or step<1:
            ap.error('Require 0 <= start <= end <= max-panels and step >= 1')
        counts=list(range(start,end+1,step))
        if counts[-1]!=end:counts.append(end)
        for case in cases:
            if case not in PROFILE_ASSIGNMENTS:ap.error('Unknown case '+case)
            for kva in (ratings12 if case=='twelve' else [5.]):
                for panels in counts:
                    runst=replace(st, objective='economic', transformer_kva=kva,
                                  fixed_panels=panels, capex_budget_usd=None)
                    tag=f'panel_exact_{panels:02d}_{kva:g}kva_{args.export}'
                    print('PANEL SWEEP',case,tag,'MILP' if runst.discrete else 'LP',flush=True)
                    result=attempt(repo,args.outdir,case,runst,tag,args.hours,
                                   summary_only=not args.sweep_keep_hourly)
                    result.update({'panel_count_fixed':panels,'fixed_pv_kwp':panels*PANEL_KW,
                                   'sweep_kind':'EXACT_PV_COUNT_OPTIMIZE_BESS_INVERTER_DISPATCH',
                                   'transformer_capacity_is_hypothetical':case=='twelve',
                                   'annual_results':args.hours==8760})
                    results.append(result)
                    pd.DataFrame(results).to_csv(args.outdir/'panel_sweep_results.csv',index=False)
                from pareto_panel_sweep import summarize_sweep,plot_sweep
                current=pd.DataFrame(results)
                selected=current[(current['case']==case)&(current['transformer_assumed_kva']==kva)].copy()
                summary=summarize_sweep(selected)
                name=f'{case}_{kva:g}kva_{args.export}'
                summary.to_csv(args.outdir/f'panel_sweep_{name}_classified.csv',index=False)
                plot_sweep(summary,args.outdir/f'panel_sweep_{name}',case=case,assumed_kva=kva)
        print('Panel sweep complete. Points marked nondominated are ONLY from',
              'fixed-panel MINIMUM-COST runs, not the complete multiobjective Pareto frontier.')
        return
    if args.mode=='frontier':
        budgets=[float(v) for v in args.frontier_budgets.split(',')]
        ss_targets=[float(v) for v in args.frontier_ss_targets.split(',')]
        for case in cases:
            for kva in (ratings12 if case=='twelve' else [5.]):
                for budget in budgets:
                    runst=replace(st,objective='energy',transformer_kva=kva,
                                  capex_budget_usd=budget,min_self_sufficiency=None)
                    tag=f'Pareto_energy_budget{budget:g}_{kva:g}kva_{args.export}'
                    result=attempt(repo,args.outdir,case,runst,tag,args.hours)
                    result.update({'frontier_objective':'max_self_sufficiency',
                                   'budget_usd':budget,'ss_constraint':None})
                    results.append(result)
                    pd.DataFrame(results).to_csv(args.outdir/'pareto_points.csv',index=False)
                for target in ss_targets:
                    runst=replace(st,objective='economic',transformer_kva=kva,
                                  capex_budget_usd=None,min_self_sufficiency=target)
                    tag=f'Pareto_economic_SS{target:.2f}_{kva:g}kva_{args.export}'
                    result=attempt(repo,args.outdir,case,runst,tag,args.hours)
                    result.update({'frontier_objective':'min_annual_cost',
                                   'budget_usd':None,'ss_constraint':target})
                    results.append(result)
                    pd.DataFrame(results).to_csv(args.outdir/'pareto_points.csv',index=False)
        print('Generated Pareto points, with all infeasibilities preserved. No feeder AC validation.');return
    if args.mode=='hosting':
        if not (1 <= args.hosting_start <= args.hosting_end <= 20):
            ap.error('Hosting is limited to 1..20 independent precomputed profiles')
        pv_limits=[int(v) for v in args.hosting_panel_caps.split(',')]
        targets=[float(v) for v in args.hosting_ss_targets.split(',')]
        if any(not 0<=t<=1 for t in targets):ap.error('Invalid self-sufficiency thresholds')
        base=PROFILE_ASSIGNMENTS[args.hosting_case]
        # Incrementally preserve existing household profiles and introduce NEW
        # independent stochastic profiles, not duplicate ordinal indices.
        available=base+[j for j in range(1,21) if j not in base]
        for kva in (ratings12 if args.hosting_case=='twelve' else [5.]):
            for panel_cap in pv_limits:
                for target in targets:
                    for h in range(max(args.hosting_start,len(base)),args.hosting_end+1):
                        profile_ids=available[:h]
                        runst=replace(st,transformer_kva=kva,max_panels=panel_cap,
                               min_self_sufficiency=target)
                        tag=f'host_{h}houses_{kva:g}kva_{panel_cap}panels_SS{int(target*100)}'
                        case_id=args.hosting_case
                        print('TEST HOSTING',case_id,tag,'(candidate synthetic profiles)',flush=True)
                        result=attempt(repo,args.outdir,case_id,runst,tag,args.hours,profile_ids=profile_ids)
                        result.update({'tested_house_count':h,'profile_ids':','.join(map(str,profile_ids)),
                          'max_pv_panel_limit':panel_cap,'minimum_ss_target':target,
                          'transformer_capacity_is_hypothetical':case_id=='twelve'})
                        results.append(result)
                        pd.DataFrame(results).to_csv(args.outdir/'hosting_capacity_sensitivity.csv',index=False)
        print('Completed hosting sensitivity; no full feeder AC validation. See hosting_capacity_sensitivity.csv')
        return
    for case in cases:
        for kva in (ratings12 if case=='twelve' else [5.]):
            runst=replace(st,transformer_kva=kva)
            tag=f'{args.mode}_{kva:g}kva_{args.export}'
            print('SOLVING',case,tag, 'discrete' if st.discrete else 'LP relaxed',flush=True)
            result=attempt(repo,args.outdir,case,runst,tag,args.hours)
            results.append(result)
            pd.DataFrame(results).to_csv(args.outdir/'optimization_summary.csv',index=False)
    print(pd.DataFrame(results).to_string(index=False))

if __name__=='__main__': main()
