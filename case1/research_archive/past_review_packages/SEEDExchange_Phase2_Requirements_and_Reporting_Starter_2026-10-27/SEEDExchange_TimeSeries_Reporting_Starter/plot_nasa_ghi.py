#!/usr/bin/env python3
"""Visualize sourced NASA POWER 2025 solar radiation; NOT a PV+BESS result."""
from pathlib import Path
import argparse
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot(path:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    s=pd.read_csv(path,parse_dates=['timestamp_lst']).set_index('timestamp_lst').sort_index()
    required={'ALLSKY_SFC_SW_DWN','timestamp_lst'}
    if required - (set(s.columns) | set(s.index.names)):
        raise ValueError('Missing NASA POWER irradiation or timestamps')
    if len(s)!=8760 or (s.index!=pd.date_range('2025-01-01',periods=8760,freq='h')).any():
        raise ValueError('Expect full 2025 8760-h NASA POWER local-solar-time data')
    ghi=s['ALLSKY_SFC_SW_DWN'].astype(float)
    if (ghi<0).any():raise ValueError('NASA POWER fill/missing values detected')
    daily=ghi.resample('D').sum()/1000
    monthly=ghi.resample('MS').sum()/1000
    daily.to_csv(out/'NASA_2025_daily_ghi_kwh_m2.csv',header=['ghi_kwh_m2_day'])
    monthly.to_csv(out/'NASA_2025_monthly_ghi_kwh_m2.csv',header=['ghi_kwh_m2_month'])
    fig,ax=plt.subplots(figsize=(11,5),constrained_layout=True)
    ax.bar(monthly.index.strftime('%b'),monthly.values)
    ax.set_ylabel('Monthly horizontal irradiation (kWh/m²)')
    ax.set_title('San Rafael: NASA POWER GHI (2025, hourly native LST data)')
    ax.grid(axis='y',alpha=.25)
    for ext in ['png','svg']:
        fig.savefig(out/('NASA_2025_monthly_GHI.'+ext),dpi=180)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,4),constrained_layout=True)
    ax.plot(daily.index,daily.values,linewidth=.9)
    ax.set_ylabel('Daily horizontal irradiation (kWh/m²/day)')
    ax.set_title('San Rafael: daily NASA POWER GHI throughout 2025')
    ax.grid(alpha=.2)
    for ext in ['png','svg']:
        fig.savefig(out/('NASA_2025_daily_GHI.'+ext),dpi=180)
    plt.close(fig)
    return monthly

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--nasa',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True)
    a=p.parse_args();m=plot(a.nasa,a.outdir)
    print('2025 NASA GHI total:',round(m.sum(),3),'kWh/m²','best month:',m.idxmax().strftime('%B'),'lowest month:',m.idxmin().strftime('%B'))
