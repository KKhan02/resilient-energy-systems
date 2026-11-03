#!/usr/bin/env python3
"""Visualize *canonical* 8760h PV/BESS dispatch; does not implement dispatch.

Usage: python report_timeseries.py --input annual_dispatch_8760.csv --outdir figures
Output: PNG/SVG figures, daily/monthly/yearly CSVs, README_RESULTS.md.
Input values represent hourly mean kW, except irradiance as hourly Wh/m2 and SOC as kWh.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = [
    'timestamp_lst','demand_requested_kw','demand_served_kw','ens_kw',
    'ghi_wh_m2','pv_ac_kw','battery_charge_dc_kw','battery_discharge_dc_kw',
    'soc_usable_kwh','grid_import_kw','grid_export_kw','curtailment_kw'
]
METRICS = [
    ('demand_requested_kw','demand_requested_kwh'),
    ('demand_served_kw','demand_served_kwh'),
    ('ens_kw','unserved_load_kwh'),
    ('pv_ac_kw','pv_ac_generation_kwh'),
    ('battery_charge_dc_kw','battery_charge_dc_kwh'),
    ('battery_discharge_dc_kw','battery_discharge_dc_kwh'),
    ('grid_import_kw','grid_import_kwh'),
    ('grid_export_kw','grid_export_kwh'),
    ('curtailment_kw','curtailment_kwh'),
]


def load(path):
    df = pd.read_csv(path)
    absent = sorted(set(BASE)-set(df.columns))
    if absent:
        raise ValueError('Missing canonical dispatch columns: '+', '.join(absent))
    df['timestamp_lst'] = pd.to_datetime(df['timestamp_lst'],errors='raise')
    if df['timestamp_lst'].isna().any() or df['timestamp_lst'].duplicated().any():
        raise ValueError('Missing or duplicate local-solar-time timestamps')
    df=df.sort_values('timestamp_lst').set_index('timestamp_lst')
    expected=pd.date_range('2025-01-01',periods=8760,freq='h')
    if len(df)!=8760 or not df.index.equals(expected):
        raise ValueError('Expected continuous calendar-year 2025, 8760 hourly LST timestamps; got '+str(len(df)))
    for c in BASE[1:]:
        df[c]=pd.to_numeric(df[c],errors='raise')
        if not np.isfinite(df[c]).all():
            raise ValueError(c+' contains non-finite values')
    if (df[[c for c in BASE[1:] if c!='soc_usable_kwh']] < -1e-8).any().any():
        raise ValueError('Non-negative column has negative values')
    if (df['demand_served_kw'] + df['ens_kw'] - df['demand_requested_kw']).abs().max()>1e-3:
        raise ValueError('Demand requested != served + ENS (tolerance 1e-3 kW)')
    if ((df['battery_charge_dc_kw']>1e-7) & (df['battery_discharge_dc_kw']>1e-7)).any():
        raise ValueError('Simultaneous DC charge/discharge detected')
    return df


def aggregates(df,frequency):
    out=pd.DataFrame(index=df.resample(frequency).sum().index)
    for source, target in METRICS:
        out[target]=df[source].resample(frequency).sum()  # 1-hour records
    out['ghi_kwh_m2']=df['ghi_wh_m2'].resample(frequency).sum()/1000
    out['battery_soc_start_kwh']=df['soc_usable_kwh'].resample(frequency).first()
    out['battery_soc_end_kwh']=df['soc_usable_kwh'].resample(frequency).last()
    demand=out['demand_requested_kwh']
    out['self_sufficiency_pct']=np.where(demand>0,100*(1-out['grid_import_kwh']/demand),np.nan)
    out['pv_to_demand_pct']=np.where(demand>0,100*out['pv_ac_generation_kwh']/demand,np.nan)
    out['fully_grid_independent_and_served']=(out['grid_import_kwh'].abs()<1e-6)&(out['unserved_load_kwh'].abs()<1e-6)
    if 'lv_min_pu' in df.columns:
        out['lowest_lv_voltage_pu']=df['lv_min_pu'].resample(frequency).min()
    if 'lv_max_pu' in df.columns:
        out['highest_lv_voltage_pu']=df['lv_max_pu'].resample(frequency).max()
    if 'transformer_loading_pct' in df.columns:
        out['maximum_transformer_loading_pct']=df['transformer_loading_pct'].resample(frequency).max()
    return out


def save(fig, out, name):
    fig.savefig(out/(name+'.png'),dpi=180,bbox_inches='tight')
    fig.savefig(out/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)


def detail(df, start, periods, out, name, label):
    part=df.loc[start:start+pd.Timedelta(hours=periods-1)]
    if len(part)!=periods:
        raise ValueError('Incorrect '+label+' window size')
    fig,axes=plt.subplots(4,1,figsize=(13,11),sharex=True,constrained_layout=True)
    axes[0].plot(part.index,part.demand_requested_kw,label='Demand',linewidth=1.3)
    axes[0].plot(part.index,part.pv_ac_kw,label='PV AC',linewidth=1.3)
    axes[0].set_ylabel('Power (kW)'); axes[0].legend(loc='upper right',ncol=2)
    axes[1].bar(part.index,part.battery_charge_dc_kw,width=.030,label='Charge (DC kW)',alpha=.75)
    axes[1].bar(part.index,-part.battery_discharge_dc_kw,width=.030,label='Discharge (DC kW)',alpha=.75)
    axes[1].set_ylabel('Battery DC power (kW)'); axes[1].legend(loc='upper right',ncol=2)
    axes[2].plot(part.index,part.soc_usable_kwh,label='SOC usable energy',linewidth=1.6)
    axes[2].plot(part.index,part.grid_import_kw,label='Import kW',linewidth=1)
    axes[2].plot(part.index,-part.grid_export_kw,label='Export kW (negative)',linewidth=1)
    axes[2].set_ylabel('kWh / kW, see legend'); axes[2].legend(loc='upper right',ncol=3)
    axes[3].bar(part.index,part.ghi_wh_m2/1000,width=.030,label='GHI per hour, kWh/m²',alpha=.75)
    axes[3].set_ylabel('Hourly GHI (kWh/m²)'); axes[3].set_xlabel('2025 local solar time')
    axes[3].legend(loc='upper right')
    fig.suptitle(label+' beginning '+str(start)+' (battery SOC continues from annual simulation)')
    save(fig,out,name)


def yearly_graphs(df, daily, monthly, out):
    x=np.arange(12)
    fig,axes=plt.subplots(3,1,figsize=(13,11),constrained_layout=True)
    axes[0].bar(x,monthly['demand_requested_kwh'],label='Demand kWh',alpha=.75)
    axes[0].bar(x,monthly['pv_ac_generation_kwh'],label='PV AC generation kWh',alpha=.65)
    axes[0].set_ylabel('Energy (kWh)'); axes[0].legend()
    axes[1].bar(x,monthly['grid_import_kwh'],label='Grid imports',alpha=.85)
    axes[1].bar(x,-monthly['grid_export_kwh'],label='Grid exports (negative)',alpha=.75)
    axes[1].set_ylabel('Energy (kWh)'); axes[1].legend()
    axes[2].bar(x,monthly['self_sufficiency_pct'],label='Operational self-sufficiency')
    axes[2].set_ylabel('Self-sufficiency (%)'); axes[2].set_ylim(0,105)
    axes[2].axhline(100,linestyle=':',linewidth=1)
    axes[2].set_xticks(x,monthly.index.strftime('%b'))
    fig.suptitle('Calendar-month community energy balance (2025, same 8760h simulation)')
    save(fig,out,'03_monthly_energy_and_self_sufficiency')

    fig,axes=plt.subplots(2,1,figsize=(13,7),constrained_layout=True)
    axes[0].bar(x,monthly['ghi_kwh_m2'],label='Monthly GHI irradiation')
    axes[0].set_ylabel('GHI (kWh/m² / month)')
    axes[1].bar(x,monthly['battery_charge_dc_kwh'],label='Battery charge DC')
    axes[1].bar(x,-monthly['battery_discharge_dc_kwh'],label='Battery discharge DC, negative')
    axes[1].set_ylabel('DC battery energy (kWh)')
    for ax in axes:ax.set_xticks(x,monthly.index.strftime('%b'));ax.legend()
    fig.suptitle('Solar resource and battery throughput by month, 2025')
    save(fig,out,'04_monthly_solar_irradiation_and_battery')

    fig,axs=plt.subplots(3,1,figsize=(13,10),sharex=True,constrained_layout=True)
    axs[0].plot(daily.index,daily.demand_requested_kwh,label='Demand')
    axs[0].plot(daily.index,daily.pv_ac_generation_kwh,label='PV AC')
    axs[0].set_ylabel('kWh/day'); axs[0].legend()
    axs[1].plot(daily.index,daily.grid_import_kwh,label='Import')
    axs[1].plot(daily.index,daily.grid_export_kwh,label='Export')
    axs[1].set_ylabel('kWh/day'); axs[1].legend()
    axs[2].plot(daily.index,daily.self_sufficiency_pct)
    axs[2].set_ylim(0,105);axs[2].set_ylabel('Daily self-sufficiency (%)')
    axs[2].set_xlabel('2025 calendar date')
    fig.suptitle('Full-year daily time series, derived from 8760h hourly results')
    save(fig,out,'05_annual_daily_time_series')


def run(source, destination):
    destination.mkdir(parents=True,exist_ok=True)
    hourly=load(source)
    daily=aggregates(hourly,'D')
    weekly=aggregates(hourly,'W-SUN')
    monthly=aggregates(hourly,'MS')
    yearly=aggregates(hourly,'YS')
    for name,tab in [('daily',daily),('weekly',weekly),('monthly',monthly),('annual',yearly)]:
        tab.to_csv(destination/(name+'_energy_summary.csv'),index_label='period_start_lst')
    # Highest demand, and lowest GHI:demand day, selected from actual full-year values.
    worst_dem=daily.demand_requested_kwh.idxmax()
    low_pv_ratio=(daily.ghi_kwh_m2 / daily.demand_requested_kwh.clip(lower=1e-9))
    stress=low_pv_ratio.idxmin()
    detail(hourly,worst_dem,24,destination,'01_day_highest_demand','Highest-demand day')
    detail(hourly,stress,24,destination,'01b_day_low_solar_relative_to_load','Low-solar/high-demand day')
    start=max(pd.Timestamp('2025-01-01'),worst_dem-pd.Timedelta(days=worst_dem.weekday()))
    if start+pd.Timedelta(days=7)>pd.Timestamp('2026-01-01'):
        start=pd.Timestamp('2025-12-22')
    detail(hourly,start,168,destination,'02_week_containing_high_demand','Week of high demand')
    yearly_graphs(hourly,daily,monthly,destination)
    full_months=monthly.index[monthly.fully_grid_independent_and_served]
    (destination/'README_RESULTS.md').write_text(
        '# Canonical annual dispatch visual report\n\n'
        'Input: '+str(source)+'\n\n'
        '**Energy results only until independently coupled to pandapower.**\n\n'
        'Full grid-independence requires zero monthly import AND zero unserved load.\n'
        'Self-sufficiency uses requested demand; inspect ENS alongside this metric.\n\n'
        'Grid-independent and fully served months: '+(', '.join(full_months.strftime('%B').tolist()) if len(full_months) else 'none')+'\n\n'
        'Year demand: %.3f kWh; grid imports %.3f kWh; annual self-sufficiency %.3f%%; ENS %.3f kWh.\n'
        % (yearly.demand_requested_kwh.iloc[0],yearly.grid_import_kwh.iloc[0],yearly.self_sufficiency_pct.iloc[0],yearly.unserved_load_kwh.iloc[0])
        ,encoding='utf-8')
    return monthly,yearly


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True,help='Canonical full-year 8760-hour dispatch CSV')
    p.add_argument('--outdir',type=Path,required=True)
    args=p.parse_args()
    run(args.input,args.outdir)
