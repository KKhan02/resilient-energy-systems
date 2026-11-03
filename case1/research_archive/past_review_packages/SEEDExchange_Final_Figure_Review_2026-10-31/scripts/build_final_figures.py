#!/usr/bin/env python3
"""Reproduce clean, unconnected PV and BESS sizing charts from SEEDExchange MILP results.

Dependencies: matplotlib (installed in the existing modelling environment). Uses only
built-in csv, json and pathlib for data loading. No optimizer run or network access.

Usage from repository root:
  python build_final_figures.py --results case1/studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv --out figures_curated
"""
import argparse
import csv
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import FuncFormatter, MaxNLocator

SUCCESS='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER'
CASES=(7,9,12,15)
MAIN=(7,9,12)
PALETTE='viridis_r'

def num(value):
    try:return float(value)
    except (TypeError,ValueError):return float('nan')

def load_rows(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def selected(rows,houses,kva,task):
    return [r for r in rows if r['case']==f'{houses}_homes' and num(r['kva'])==kva
            and r['task']==task and r['status']==SUCCESS]

def plot_sizing(rows,houses,tech,out):
    task='fixed_PV_economic' if tech=='PV' else 'fixed_BESS_economic'
    subset=selected(rows,houses,5.0,task)
    if not subset:
        raise ValueError(f'No successful rows for {houses} homes {task}')
    xs=[num(r['panels_equivalent']) if tech=='PV' else num(r['battery_usable_kwh']) for r in subset]
    ys=[num(r['self_sufficiency_of_demand_pct']) for r in subset]
    costs=[num(r['annual_total_usd']) for r in subset]
    if not all(math.isfinite(v) for v in xs+ys+costs):
        raise ValueError(f'Nonfinite chart values {houses}, {tech}')
    # Single cost scale per household case enables meaningful PV/BESS comparison.
    related=selected(rows,houses,5.0,'fixed_PV_economic')+selected(rows,houses,5.0,'fixed_BESS_economic')
    cost_range=[num(r['annual_total_usd']) for r in related]
    norm=Normalize(vmin=min(cost_range),vmax=max(cost_range))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':15,
                         'axes.labelsize':12,'axes.spines.top':False,'axes.spines.right':False,
                         'savefig.facecolor':'white'})
    fig,ax=plt.subplots(figsize=(10.8,6.0),layout='constrained')
    scat=ax.scatter(xs,ys,c=costs,cmap=PALETTE,norm=norm,s=52,
                    edgecolor='#202b36',linewidths=0.25,zorder=3)
    min_idx=min(range(len(costs)),key=lambda i:costs[i])
    ax.scatter([xs[min_idx]],[ys[min_idx]],s=175,facecolors='none',
               edgecolors='black',linewidths=1.6,label='Minimum annual cost',zorder=4)
    ax.legend(loc='lower right',frameon=False,fontsize=10)
    ax.set_ylim(0,101)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.set_ylabel('Annual self-sufficiency (%)')
    if tech=='PV':
        ax.set_xlabel('PV panel count (435 Wp per panel)')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True,nbins=9))
        ax.set_xlim(-3,85)
        title_tech='PV sizing'
    else:
        ax.set_xlabel('Usable BESS capacity (kWh)')
        ax.set_xlim(-4,74)
        title_tech='BESS sizing'
    ax.set_title(f'{houses} households | assumed 5 kVA | {title_tech}',loc='left',pad=13)
    ax.grid(True,alpha=.18,linewidth=.65)
    bar=fig.colorbar(scat,ax=ax,pad=.02,shrink=.92,aspect=28)
    bar.set_label('Annual total cost (USD/year)',rotation=90,labelpad=12)
    bar.ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f'${x:,.0f}'))
    name=f'{houses:02d}_homes_5kva_{tech.lower()}_sizing_cost_gradient'
    for ext in ['png','svg']:
        fig.savefig(out/f'{name}.{ext}',dpi=175)
    plt.close(fig)
    return {'households':houses,'technology':tech,'cases':len(subset),
            'best_cost_usd_year':round(min(costs),2),'pv_panels_at_best':num(subset[min_idx]['panels_equivalent']),
            'bess_kwh_at_best':num(subset[min_idx]['battery_usable_kwh']),
            'best_ss_pct':round(ys[min_idx],2),'filename':name+'.png'}

def plot_rating_sensitivity(rows,out):
    """One 12-home comparison: rating does not change the economic minimum."""
    rr=[]
    for kva in (5.,10.,15.,20.,25.):
        valid=[r for r in rows if r['case']=='12_homes' and num(r['kva'])==kva
               and r['status']==SUCCESS and r['task']=='fixed_PV_economic']
        rr.append(min(valid,key=lambda r:num(r['annual_total_usd'])))
    x=[num(r['kva']) for r in rr]
    y=[num(r['annual_total_usd']) for r in rr]
    peak=[num(r['max_pcc_kva_proxy']) for r in rr]
    fig,ax=plt.subplots(figsize=(9.8,5.6),layout='constrained')
    sc=ax.scatter(x,y,c=peak,cmap=PALETTE,s=135,edgecolors='#202b36',linewidths=.6)
    for xx,yy,pcc in zip(x,y,peak):
        ax.annotate(f'{pcc:.2f} kVA', (xx,yy),xytext=(0,13),
                    textcoords='offset points',ha='center',fontsize=10)
    ax.set_xticks(x)
    ax.set_xlim(2.5,27.5)
    ax.set_ylim(min(y)-320,max(y)+320)
    ax.set_ylabel('Minimum annual cost (USD/year)')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'${v:,.0f}'))
    ax.set_xlabel('Assumed transformer rating (kVA)')
    ax.set_title('12 households | transformer-rating sensitivity',loc='left',pad=13)
    ax.grid(alpha=.18)
    bar=fig.colorbar(sc,ax=ax,pad=.02,shrink=.9)
    bar.set_label('Peak PCC apparent-power proxy (kVA)')
    name='12_homes_transformer_rating_vs_annual_cost'
    for ext in ['png','svg']:fig.savefig(out/f'{name}.{ext}',dpi=175)
    plt.close(fig)
    return name+'.png'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--results',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    rows=load_rows(args.results)
    if len(rows)!=6840:raise ValueError(f'Expected 6840 task records, found {len(rows)}')
    import json
    metadata=[]
    for houses in CASES:
        for tech in ['PV','BESS']:
            metadata.append(plot_sizing(rows,houses,tech,args.out))
    optional=plot_rating_sensitivity(rows,args.out)
    (args.out/'plot_metadata.json').write_text(json.dumps({'plots':metadata,'optional_transformer_plot':optional},indent=2))
    print('Created',len(metadata),'technology figures and 1 transformer sensitivity figure in',args.out)
if __name__=='__main__':main()
