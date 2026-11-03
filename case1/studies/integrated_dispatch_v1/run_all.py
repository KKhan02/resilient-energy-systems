#!/usr/bin/env python3
"""One command for the first reproducible 7/8/9/12-home campaign and sweep."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_integrated_dispatch import locate_repo,write_case,dispatch_case
from run_parameter_sweep import sweep,CASES
from pandapower_handoff import make_nodal_handoff


def campaign(root, output, run_sweep=True, export_handoff=True):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for label,node,extra in CASES:
        for design,panels,modules,battery_power,inv in (('no_der',0,0,0.,5.),('pv_bess',24,4,5.,10.)):
            folder=output/'territories'/label/design
            params=dict(territory=node,include=extra,panels=panels,modules=modules,
                        battery_power_kw=battery_power,inverter_kva=inv,cap_pu=.9,pf=.98,soc_mode='cyclic')
            m=write_case(root,folder,**params)
            # Optional pandapower-ready hourly nodal table, WITHOUT false AC results.
            if export_handoff:
                data,_=dispatch_case(root,**params)
                handoff=make_nodal_handoff(root,data,m,folder/'nodal_hourly_handoff.csv')
                m['nodal_handoff']=handoff
                (folder/'manifest.json').write_text(json.dumps(m,indent=2,default=str),encoding='utf-8')
            s=m['annual_score']
            rows.append(dict(case=label,design=design,node=node,houses=m['house_count'],
                             demand_kwh=s['demand_kwh'],import_kwh=s['grid_import_kwh'],
                             export_kwh=s['grid_export_kwh'],ens_kwh=s['grid_ens_kwh'],
                             self_sufficiency_demand_pct=s['one_minus_import_fraction_of_demand_pct'],
                             locally_supplied_requested_pct=s['locally_supplied_fraction_of_demand_pct'],
                             max_pcc_kva=s['max_trafo_kva'],
                             annualized_cost_usd=s['annual_total_no_credit_usd'],
                             transformer_assumption=m['nameplate_basis'],
                             actual_lv_powerflow='NOT_SIMULATED'))
    result=pd.DataFrame(rows)
    result.to_csv(output/'baseline_comparison.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,5))
    for design,portion in result.groupby('design'):
        offset=-.18 if design=='no_der' else .18
        xx=[list(dict.fromkeys(result.case)).index(v)+offset for v in portion.case]
        ax.bar(xx,portion.self_sufficiency_demand_pct,width=.35,label=design)
    ax.set_xticks(range(result.case.nunique()),list(dict.fromkeys(result.case)))
    ax.legend()
    ax.set(ylabel='1 - imports / requested demand (%)',
           title='Canonical 2025 DC-coupled dispatch, provisional territories (NOT AC validated)',ylim=(0,105))
    ax.tick_params(axis='x',rotation=20)
    fig.savefig(output/'case_comparison.png',dpi=180,bbox_inches='tight')
    fig.savefig(output/'case_comparison.svg',bbox_inches='tight')
    plt.close(fig)
    if run_sweep:
        sweep(root,output/'parameter_sweep')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--skip-sweep',action='store_true')
    p.add_argument('--skip-handoff',action='store_true')
    a=p.parse_args()
    c=campaign(locate_repo(a.repo_root),a.outdir,run_sweep=not a.skip_sweep,
               export_handoff=not a.skip_handoff)
    print(c.to_string(index=False))
