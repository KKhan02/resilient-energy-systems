#!/usr/bin/env python3
"""Make 5 kVA PV/BESS scaling figures, from solved results. Pure post-processing."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import MaxNLocator, FuncFormatter

HERE=Path(__file__).resolve().parent

def selections(source:Path)->pd.DataFrame:
    raw=pd.read_csv(source)
    fixed=raw[(raw['kva'].eq(5.0)) &
              (raw['task'].eq('fixed_PV_economic')) &
              (raw['status'].eq('OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER'))].copy()
    # Pick a consistent optimization objective for every demand case.
    selected=fixed.loc[fixed.groupby('case')['annual_total_usd'].idxmin()].copy()
    assert set(selected.case)==set(raw.case.unique())
    assert len(selected)==12 and selected.houses.min()==5 and selected.houses.max()==15
    selected=selected.sort_values(['houses','case']).reset_index(drop=True)
    selected['annual_cost_per_house_usd']=selected['annual_total_usd']/selected['houses']
    selected['capex_per_house_usd']=selected['capex_usd_ex_vat']/selected['houses']
    selected['display_x']=selected['houses'].astype(float)
    # There are two distinct 8-house cases. Offset their markers slightly for legibility only.
    selected.loc[selected['case'].eq('8_homes_H01'),'display_x']=7.90
    selected.loc[selected['case'].eq('8_homes_H02'),'display_x']=8.10
    selected['case_label']=selected['case'].str.replace('_homes','',regex=False)
    selected.loc[selected['case'].eq('8_homes_H01'),'case_label']='8A'
    selected.loc[selected['case'].eq('8_homes_H02'),'case_label']='8B'
    selected['pv_panels']=selected['panels_equivalent'].round().astype(int)
    selected['bess_usable_kwh']=selected['battery_usable_kwh']
    selected['ss_pct']=selected['self_sufficiency_of_demand_pct']
    selected['annual_cost_usd']=selected['annual_total_usd']
    selected['capex_usd']=selected['capex_usd_ex_vat']
    return selected

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11.5,'axes.titlesize':13,
                     'axes.titleweight':'bold','axes.labelsize':12,'xtick.labelsize':10.5,
                     'ytick.labelsize':10.5,'svg.fonttype':'none','savefig.facecolor':'white'})
COST_NORM=None
SS_NORM=None
DATA=None

PLOTS={
 '01_houses_vs_pv_panels':('Optimized PV size', 'PV panels (435 Wp each)', 'pv_panels','annual_cost_usd','Annual cost (USD/year)','viridis'),
 '02_houses_vs_bess_kwh':('Optimized battery size', 'Usable BESS capacity (kWh)', 'bess_usable_kwh','annual_cost_usd','Annual cost (USD/year)','viridis'),
 '03_houses_vs_annual_cost':('Total annual cost', 'Annual total cost (USD/year)', 'annual_cost_usd','ss_pct','Self-sufficiency (%)','plasma'),
 '04_houses_vs_annual_cost_per_house':('Annual cost per house', 'Annual cost per house (USD/year)', 'annual_cost_per_house_usd','ss_pct','Self-sufficiency (%)','plasma'),
 '05_houses_vs_upfront_capex':('Upfront equipment investment', 'Upfront CAPEX (USD, ex. VAT)', 'capex_usd','ss_pct','Self-sufficiency (%)','plasma'),
}

def plot_on_ax(ax,df,key,include_title=True):
    title,ylabel,ykey,ckey,clabel,cmap=PLOTS[key]
    norm=COST_NORM if ckey=='annual_cost_usd' else SS_NORM
    # All 8-house variants are separate, with a minor X offset only for visibility.
    s=ax.scatter(df['display_x'],df[ykey],c=df[ckey],vmin=norm.vmin,vmax=norm.vmax,
                 cmap=cmap,s=112,edgecolors='white',linewidths=1.0,alpha=0.98,zorder=5)
    ax.set_xlabel('Number of households')
    ax.set_ylabel(ylabel)
    if include_title:ax.set_title(title,pad=12)
    ax.set_xticks(list(range(5,16)))
    ax.set_xlim(4.50,15.48)
    ax.grid(alpha=0.22,lw=0.75,zorder=0)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if ykey=='pv_panels':
        ax.set_ylim(0,76)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True,nbins=7))
    if ykey=='bess_usable_kwh':ax.set_ylim(0,55)
    if ykey=='annual_cost_usd':
        ax.set_ylim(1400,7000)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:'${:,.0f}'.format(x)))
    if ykey=='annual_cost_per_house_usd':
        ax.set_ylim(385,420)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:'${:,.0f}'.format(x)))
    if ykey=='capex_usd':
        ax.set_ylim(0,55000)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:'${:,.0f}k'.format(x/1000)))
    cb=plt.colorbar(s,ax=ax,shrink=0.91,pad=0.018,aspect=28)
    cb.set_label(clabel,fontsize=10)
    cb.ax.tick_params(labelsize=9)
    if ckey=='annual_cost_usd':
        cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:'${:,.0f}'.format(x)))
    else:
        cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:'{:.0f}%'.format(x)))
    return ax


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    df=selections(args.results)
    global COST_NORM,SS_NORM
    COST_NORM=Normalize(df.annual_cost_usd.min(),df.annual_cost_usd.max())
    SS_NORM=Normalize(70,95)
    (args.out/'source').mkdir(exist_ok=True)
    (args.out/'presentation').mkdir(exist_ok=True)
    (args.out/'poster').mkdir(exist_ok=True)
    selected_cols=['case','houses','pv_panels','pv_kwp','bess_usable_kwh',
        'battery_power_dc_kw','inverter_ac_kva_assumed_unity_pf',
        'annual_cost_usd','annual_cost_per_house_usd','capex_usd','capex_per_house_usd','ss_pct',
        'demand_kwh','grid_import_kwh','max_pcc_kva_proxy','status']
    df[selected_cols].to_csv(args.out/'source'/'cost_minimizing_5kva_designs.csv',index=False)
    for key in PLOTS:
        fig,ax=plt.subplots(figsize=(8.0,5.0),dpi=160)
        plot_on_ax(ax,df,key)
        fig.tight_layout(pad=1.5)
        for ext in ('png','svg'):
            fig.savefig(args.out/'presentation'/(key+'.'+ext),dpi=220 if ext=='png' else None,
                        bbox_inches='tight')
        plt.close(fig)
    # Four-chart poster contact sheet, with generous printable typography and space.
    keys=['01_houses_vs_pv_panels','02_houses_vs_bess_kwh',
          '05_houses_vs_upfront_capex','04_houses_vs_annual_cost_per_house']
    fig,axs=plt.subplots(2,2,figsize=(15.5,10.7),dpi=180)
    for ax,k in zip(axs.flat,keys):plot_on_ax(ax,df,k)
    fig.suptitle('PV + BESS scaling at an assumed 5 kVA connection',size=20,weight='bold',y=0.992)
    fig.subplots_adjust(left=0.075,right=0.95,bottom=0.08,top=0.925,wspace=0.20,hspace=0.29)
    for ext in ('png','svg'):
        fig.savefig(args.out/'poster'/('5kva_four_figure_scaling_panel.'+ext),dpi=250 if ext=='png' else None,
                    bbox_inches='tight')
    plt.close(fig)
    print(df[selected_cols].round(3).to_string(index=False))
    a=df.loc[df.houses.eq(14)].iloc[0];b=df.loc[df.houses.eq(15)].iloc[0]
    print('14->15 jump panel', b.pv_panels-a.pv_panels,
          'bess kWh',b.bess_usable_kwh-a.bess_usable_kwh,
          'capex',b.capex_usd-a.capex_usd,
          'annual cost',b.annual_cost_usd-a.annual_cost_usd)

if __name__=='__main__':main()
