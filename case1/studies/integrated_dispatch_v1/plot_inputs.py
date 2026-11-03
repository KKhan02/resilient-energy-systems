#!/usr/bin/env python3
"""Reference synthetic demand and sourced NASA 2025 irradiation. No PV/BESS outputs."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def generate(source,nasa,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(source,parse_dates=['timestamp']).set_index('timestamp')
    n=pd.read_csv(nasa,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    idx=pd.date_range('2025-01-01',periods=8760,freq='h')
    if not (d.index.equals(idx) and n.index.equals(idx)):
        raise ValueError('Need both full hourly 2025 LST inputs')
    for i in range(1,13):
        if f'house_{i}_kw' not in d.columns:raise ValueError('Missing original v18 house profiles')
    m=pd.DataFrame(index=idx.to_series().resample('MS').first().index)
    for k in (7,8,9,12):
        m[f'demand_{k}house_kwh']=d[[f'house_{i}_kw' for i in range(1,k+1)]].sum(axis=1).resample('MS').sum()
    m['NASA_GHI_kwh_m2']=n['ALLSKY_SFC_SW_DWN'].resample('MS').sum()/1000
    m.to_csv(out/'monthly_source_inputs.csv',index_label='month_start_lst',float_format='%.5f')
    fig,axs=plt.subplots(2,1,figsize=(11,8),constrained_layout=True)
    for k in (7,9,12):
        axs[0].plot(m.index.strftime('%b'),m[f'demand_{k}house_kwh'],marker='o',label=f'{k} synthetic households')
    axs[0].set(ylabel='Demand (kWh/month)',title='Reconstructed v18/HOMER synthetic household demand, 2025')
    axs[0].legend();axs[0].grid(alpha=.2)
    axs[1].bar(m.index.strftime('%b'),m.NASA_GHI_kwh_m2)
    axs[1].set(ylabel='Horizontal irradiation (kWh/m²/month)',title='NASA POWER 2025 measured/modelled solar resource, not PV energy')
    axs[1].grid(axis='y',alpha=.2)
    for ext in ('png','svg'):fig.savefig(out/f'input_monthly_household_demand_and_NASA_GHI.{ext}',dpi=180)
    plt.close(fig)
    return m

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--nasa',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    a=p.parse_args()
    m=generate(a.source,a.nasa,a.outdir)
    print('2025 input annual kWh:',{k:round(float(m[f'demand_{k}house_kwh'].sum()),3) for k in (7,8,9,12)})
