"""Presentation figures from solved hourly PyPSA output. No synthetic plotting data."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import numpy as np

def plot_all(frame:pd.DataFrame,fig_dir:Path,title,summary):
    fig_dir.mkdir(parents=True,exist_ok=True)
    for name,segment in [('day',frame.iloc[:24]),('week',frame.iloc[:168])]:
        if len(segment)<24:continue
        fig,axes=plt.subplots(4,1,figsize=(12,11),sharex=True,constrained_layout=True)
        x=segment.index
        axes[0].plot(x,segment.demand_kw,label='Requested demand, AC kW')
        axes[0].plot(x,segment.inverter_ac_kw,label='Inverter output, AC kW')
        axes[0].plot(x,segment.pv_dc_generated_kw,label='PV generation, DC kW',alpha=.7)
        axes[0].legend(ncol=3,fontsize=9);axes[0].set_ylabel('Power (kW)');axes[0].grid(alpha=.2)
        axes[1].plot(x,segment.battery_charge_dc_kw,label='Battery charging, DC kW')
        axes[1].plot(x,segment.battery_discharge_dc_kw,label='Battery discharging, DC kW')
        axes[1].set_ylabel('Battery power (kW)');axes[1].legend(ncol=2,fontsize=9);axes[1].grid(alpha=.2)
        ax_1b=axes[1].twinx();ax_1b.plot(x,segment.battery_soc_usable_kwh,
               label='Usable SOC (kWh)',color='black',lw=1.0,ls='--',alpha=.7)
        ax_1b.set_ylabel('Stored energy (kWh)')
        axes[2].plot(x,segment.grid_import_kw,label='Grid import, AC kW')
        axes[2].plot(x,segment.grid_export_kw,label='Grid export, AC kW')
        axes[2].set_ylabel('Grid power (kW)');axes[2].legend(ncol=2,fontsize=9);axes[2].grid(alpha=.2)
        if 'ghi_wh_m2' in segment:
            axes[3].plot(x,segment.ghi_wh_m2,label='NASA global horizontal irradiance',color='darkorange')
        axes[3].set_ylabel('GHI (Wh/m² per hour)');axes[3].grid(alpha=.2)
        if 'ghi_wh_m2' in segment:axes[3].legend(fontsize=9)
        fig.suptitle(f'{title} | {name} | PyPSA optimized | feeder AC validation NOT RUN',fontsize=13)
        for ext in ('png','svg'):fig.savefig(fig_dir/f'{name}_operation.{ext}',dpi=180)
        plt.close(fig)
    monthly=frame.resample('MS').sum(numeric_only=True)
    if len(monthly)<2:return
    demand=monthly.demand_kw; imported=monthly.grid_import_kw;ens=monthly.unserved_kw
    ss=(100*(demand-imported-ens)/demand).clip(0,100)
    labels=monthly.index.strftime('%b')
    fig,axs=plt.subplots(4,1,figsize=(12,12),constrained_layout=True)
    x=np.arange(len(monthly));w=.24
    for offset,col,label in [(-w,'demand_kw','Demand AC'),(0,'pv_dc_generated_kw','PV DC generation'),(w,'grid_import_kw','Grid imports AC')]:
        axs[0].bar(x+offset,monthly[col],width=w,label=label)
    axs[0].set_xticks(x,labels);axs[0].set_ylabel('Energy (kWh)');axs[0].legend(ncol=3);axs[0].grid(axis='y',alpha=.2)
    axs[1].bar(x-w/2,monthly.battery_charge_dc_kw,width=w,label='BESS charge DC')
    axs[1].bar(x+w/2,monthly.battery_discharge_dc_kw,width=w,label='BESS discharge DC')
    axs[1].set_xticks(x,labels);axs[1].set_ylabel('Battery energy (kWh)');axs[1].legend();axs[1].grid(axis='y',alpha=.2)
    axs[2].bar(x,ss);axs[2].set_ylim(0,100);axs[2].set_xticks(x,labels)
    axs[2].set_ylabel('Monthly self-sufficiency (%)');axs[2].grid(axis='y',alpha=.2)
    if 'ghi_wh_m2' in monthly:
        axs[3].bar(x,monthly.ghi_wh_m2/1000,color='darkorange')
    axs[3].set_xticks(x,labels);axs[3].set_ylabel('GHI (kWh/m²)');axs[3].grid(axis='y',alpha=.2)
    fig.suptitle(f'{title}: 2025 operational monthly summaries | no LV AC validation')
    for ext in ('png','svg'):fig.savefig(fig_dir/f'monthly_energy.{ext}',dpi=180)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,4.5),constrained_layout=True)
    ax.plot(frame.index,frame.grid_import_kw,label='Grid import',lw=.65)
    ax.plot(frame.index,frame.grid_export_kw,label='Grid export',lw=.65)
    ax.set_ylabel('Power (kW)');ax.set_title(f'{title}: 2025 hourly grid exchange | no AC validation');ax.legend();ax.grid(alpha=.2)
    for ext in ('png','svg'):fig.savefig(fig_dir/f'annual_grid_exchange.{ext}',dpi=180)
    plt.close(fig)
