#!/usr/bin/env python3
"""Stage-gate equipment shortlist from SAVED 6840-task energy-only results.

No new optimization or claim of AC feasibility. Saved 2025 costs/dispatch predate
manufacturer SOC and feeder losses and must be reoptimized before selection.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from validate_annual_ac import sha256

SOURCE = Path('case1/studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv')
COLUMNS = ('case','kva','status','export_policy','annual_hours','unserved_kwh',
 'annual_total_usd','self_sufficiency_of_demand_pct','panels_equivalent',
 'battery_modules_equivalent','battery_power_dc_kw','inverter_ac_kva_assumed_unity_pf')


def eligible_rows(raw:pd.DataFrame, cases:tuple[str,...], nameplate_kva:float) -> pd.DataFrame:
    absent = set(COLUMNS)-set(raw.columns)
    if absent: raise ValueError('Missing required columns '+str(sorted(absent)))
    df = raw.copy()
    for c in ('kva','annual_hours','unserved_kwh','annual_total_usd',
              'self_sufficiency_of_demand_pct','panels_equivalent',
              'battery_modules_equivalent','battery_power_dc_kw','inverter_ac_kva_assumed_unity_pf'):
        df[c] = pd.to_numeric(df[c],errors='coerce')
    keep = (df['case'].isin(cases) & df['kva'].sub(nameplate_kva).abs().lt(1e-5)
            & df['status'].eq('OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER')
            & df['export_policy'].eq('zero')
            & df['annual_hours'].eq(8760) & df['unserved_kwh'].abs().lt(1e-5)
            & df['annual_total_usd'].notna()
            & df['self_sufficiency_of_demand_pct'].between(-1e-5,100+1e-5))
    df=df.loc[keep].copy()
    if df.empty:raise ValueError('No source rows match the selected filters')
    for c in ('panels_equivalent','battery_modules_equivalent'):
        if (df[c]-df[c].round()).abs().gt(1e-4).any():
            raise ValueError('Non-buildable fractional panels or battery module counts found')
    df['panel_count']=df.panels_equivalent.round().astype(int)
    df['battery_module_count']=df.battery_modules_equivalent.round().astype(int)
    df['battery_nominal_kwh']=df.battery_module_count*5.12
    df['manufacturer_current_proxy_pass'] = df.battery_power_dc_kw.le(df.battery_module_count*2.24+1e-5)
    df['epm_territory_label']=df['case'].map({'7_homes':'94022: seven provisional',
        '9_homes':'94022: nine provisional','12_homes':'106039: twelve provisional'}).fillna('NO_ASSIGNED_GIS_CASE_IN_THIS_STUDY')
    df['validation_status']='ENERGY_SCREEN_ONLY_NOT_AC_VALIDATED_NOT_MANUFACTURER_SOC_REOPTIMIZED'
    return df


def dominated_frontier(df:pd.DataFrame) -> pd.DataFrame:
    """Known nondominated points in *saved sampled* cost vs self-suff data."""
    df=df.sort_values(['annual_total_usd','self_sufficiency_of_demand_pct'],
                      ascending=[True,False],kind='stable')
    keep=[]; highest=-np.inf
    for r in df.itertuples():
        if r.self_sufficiency_of_demand_pct > highest+1e-7:
            keep.append(r.Index);highest=r.self_sufficiency_of_demand_pct
    return df.loc[keep].copy()


def choose_shortlist(df:pd.DataFrame, cap_per_case:int=20, thresholds=(70.,80.,90.,95.)) -> pd.DataFrame:
    """Deterministically retain cost, SS and hardware diversity. Not optimum proof."""
    if cap_per_case < 5:raise ValueError('At least five selections per case required')
    chosen=[]
    for case,g in df.groupby('case',sort=True):
        scores={}
        def add(row,tag):
            key=row.name
            scores.setdefault(key,set()).add(tag)
        add(g.loc[g.annual_total_usd.idxmin()],'minimum_annual_cost_saved')
        add(g.loc[g.self_sufficiency_of_demand_pct.idxmax()],'highest_self_sufficiency_saved')
        for ss in thresholds:
            subset=g[g.self_sufficiency_of_demand_pct>=ss]
            if not subset.empty:
                add(subset.loc[subset.annual_total_usd.idxmin()],f'minimum_cost_at_{ss:g}pct_ss')
        for modules,m in g.groupby('battery_module_count',sort=True):
            if m.empty:continue
            add(m.loc[m.annual_total_usd.idxmin()],f'module_diversity_{modules}')
        for inverter,group in g.groupby('inverter_ac_kva_assumed_unity_pf',sort=True):
            if group.empty:continue
            add(group.loc[group.annual_total_usd.idxmin()],f'inverter_diversity_{inverter:g}kva')
        # Prioritize minimum costs and SS targets, then coverage of distinct battery sizes.
        prioritized=sorted(scores,key=lambda i:(
            not any('minimum_cost_at' in x or 'minimum_annual_cost' in x for x in scores[i]),
            not any('highest_self_sufficiency' in x for x in scores[i]),
            g.loc[i,'annual_total_usd'], -g.loc[i,'self_sufficiency_of_demand_pct'],i))
        for i in prioritized[:cap_per_case]:
            row=g.loc[[i]].copy()
            row['selection_reasons']=';'.join(sorted(scores[i]))
            chosen.append(row)
    return pd.concat(chosen,ignore_index=True)


def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--repo-root',type=Path,default=Path('.'))
    pa.add_argument('--outdir',type=Path,required=True)
    pa.add_argument('--cases',nargs='+',default=['7_homes','9_homes','12_homes'])
    pa.add_argument('--assumed-trafo-kva',type=float,default=5.0)
    pa.add_argument('--max-per-case',type=int,default=20)
    a=pa.parse_args()
    if a.assumed_trafo_kva<=0 or a.max_per_case<5:pa.error('Invalid rating/cap')
    repo=a.repo_root.resolve(); out=a.outdir.resolve();source=repo/SOURCE
    if out.exists():pa.error('New output directory must not exist')
    if not source.is_file():pa.error('Missing saved 6840-task CSV '+str(source))
    raw=pd.read_csv(source)
    eligible=eligible_rows(raw,tuple(a.cases),a.assumed_trafo_kva)
    requested=set(a.cases);found=set(eligible.case)
    if requested!=found:raise ValueError('No eligible saved cases: '+str(sorted(requested-found)))
    shortlist=choose_shortlist(eligible,a.max_per_case)
    frontier=pd.concat([dominated_frontier(g) for _,g in eligible.groupby('case')],ignore_index=True)
    out.mkdir(parents=True)
    shortlist.to_csv(out/'equipment_shortlist_energy_only.csv',index=False)
    frontier.to_csv(out/'saved_sampled_energy_cost_frontiers.csv',index=False)
    # Counts only; no AC/DoD claims, no optimization triggered.
    man={'status':'HISTORICAL_ENERGY_ONLY_SHORTLIST_NO_NEW_SOLVE',
         'source_csv_sha256':sha256(source),'source_rows':len(raw),
         'eligible_energy_only_rows':len(eligible),'shortlisted_rows':len(shortlist),
         'saved_sampled_frontier_rows':len(frontier),
         'cases':a.cases,'assumed_transformer_kva':a.assumed_trafo_kva,
         'status_gates':['manufacturer SOC reoptimization PENDING',
           'physical battery-bank continuous current and inverter compatibility check PENDING',
           'GIS-backed annual AC validation PENDING','stress/robustness PENDING',
           'site-specific costs and PV land/roof constraints PENDING'],
         'note':'A saved nondominated sample is not a complete Pareto frontier, and all rows are pre-AC economic estimates.'}
    (out/'equipment_shortlist_manifest.json').write_text(json.dumps(man,indent=2)+'\n',encoding='utf8')
    print('Screened',len(raw),'source rows to',len(eligible),'eligible energy rows and',
          len(shortlist),'shortlisted cases. Results:',out)

if __name__=='__main__':main()
