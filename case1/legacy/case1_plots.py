"""SEEDExchange Case 1 figures. Primary charts use full-year data.

The figures display conclusions without repeated caveat footers.
Assumptions, solar source and limitations are documented in figures/README.md.
Usage: python Case1_v2/case1_v2.py --plots-only
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
DEFAULT_RESULTS=HERE/'results'


def generate_case1_figures(results: Path=DEFAULT_RESULTS) -> list[Path]:
    results=Path(results)
    target=results/'figures'
    target.mkdir(parents=True,exist_ok=True)
    required=['sizing_screen_v2.csv','battery_power_sensitivity.csv',
              'outage_stress_SENSITIVITY_ONLY.csv','model_provenance.json',
              'solar_conversion_hourly_2025.csv',
              'reference_hourly_dispatch_12p_5kva.csv','reference_hourly_dispatch_16p_5kva.csv']
    absent=[name for name in required if not (results/name).exists()]
    if absent:
        raise FileNotFoundError('Missing inputs: '+', '.join(absent)+'. Rerun case1_v2.py first.')
    metadata=json.loads((results/'model_provenance.json').read_text())
    sizing=pd.read_csv(results/'sizing_screen_v2.csv')
    battery=pd.read_csv(results/'battery_power_sensitivity.csv')
    outage=pd.read_csv(results/'outage_stress_SENSITIVITY_ONLY.csv')
    resource=pd.read_csv(results/'solar_conversion_hourly_2025.csv',parse_dates=['timestamp_LST']).set_index('timestamp_LST')

    def hourly(name):
        return pd.read_csv(results/name,parse_dates=['timestamp_LST']).set_index('timestamp_LST')
    h12=hourly('reference_hourly_dispatch_12p_5kva.csv')
    h16=hourly('reference_hourly_dispatch_16p_5kva.csv')
    h16_8=hourly('reference_hourly_dispatch_16p_5kva_8b.csv') if (results/'reference_hourly_dispatch_16p_5kva_8b.csv').exists() else None
    h24_export=hourly('export_envelope_24p_7p6kva_8b.csv') if (results/'export_envelope_24p_7p6kva_8b.csv').exists() else None
    old=sorted(target.glob('*.png'))
    for p in old:
        p.unlink()
    done=[]
    def canvas(title,ylabel=None,figsize=(10.5,5.3)):
        f,ax=plt.subplots(figsize=figsize)
        ax.set_title(title,loc='left',fontsize=13,pad=14)
        if ylabel:ax.set_ylabel(ylabel)
        ax.grid(axis='y',alpha=.22)
        ax.set_axisbelow(True)
        return f,ax
    def save(f,filename):
        f.tight_layout()
        path=target/filename
        f.savefig(path,dpi=175,bbox_inches='tight')
        plt.close(f)
        done.append(path)
    def fmt_dates(ax):
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.tick_params(axis='x',rotation=0)
    # Select the smallest DC-input-eligible inverter for each central PV + BESS pair.
    # This keeps all three sizing axes physical without claiming installed compatibility.
    base=sizing[(sizing.policy=='conventional') & (np.isclose(sizing.export_cap_kw,0))].copy()
    best=base.sort_values('inverter_kva').drop_duplicates(['panels','bess_modules'])
    best=best.sort_values(['panels','bess_modules'])
    panels=sorted(best.panels.unique())
    modules=sorted(best.bess_modules.unique())
    def heatmetric(column,title,unit,filename,fmt='.1f'):
        data=best.pivot(index='bess_modules',columns='panels',values=column).reindex(index=modules,columns=panels)
        fig,ax=canvas(title,figsize=(9.4,5.8))
        im=ax.imshow(data.to_numpy(),aspect='auto',origin='lower',cmap='viridis')
        ax.set_xticks(range(len(panels)),[f'{p} ({p*.435:.2f})' for p in panels])
        ax.set_yticks(range(len(modules)),[f'{m} ({m*17.3/4:.1f})' for m in modules])
        ax.set_xlabel('Central PV panels (kWp DC)')
        ax.set_ylabel('Shared battery modules (usable kWh)')
        cb=fig.colorbar(im,ax=ax,pad=.025)
        cb.set_label(unit)
        vals=data.to_numpy()
        for i in range(len(modules)):
            for j in range(len(panels)):
                val=vals[i,j]
                if np.isfinite(val):
                    norm=im.norm(val)
                    ax.text(j,i,format(val,fmt),ha='center',va='center',
                            color='white' if norm<.55 else 'black',fontsize=10)
        ax.grid(False)
        save(fig,filename)
    heatmetric('self_sufficiency_pct','Annual self-sufficiency: PV × battery sizing','Self-sufficiency (%)','01_pv_bess_self_sufficiency.png')
    heatmetric('pv_curtailment_pct','PV curtailed: PV × battery sizing','PV curtailment (%)','02_pv_bess_curtailment.png')
    heatmetric('approx_annual_cost_usd_no_export','Annualized cost proxy: PV × battery sizing',
               'Annual cost (USD/year, HOMER proxy)','03_pv_bess_annual_cost.png',fmt='.0f')

    # 04: Real NASA irradiance, plane irradiance, technical output, and conversion losses.
    month=resource.resample('MS').sum(numeric_only=True)
    months=[t.strftime('%b') for t in month.index]
    x=np.arange(len(months))
    fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11.2,7.7),sharex=True)
    fig.suptitle('Solar resource and conversion to electricity, 12 panels (5.22 kWp)',x=.08,ha='left',fontsize=13)
    ax1.bar(x-.19,month.ghi_wh_m2.to_numpy()/1000,width=.38,label='NASA horizontal irradiance (GHI)')
    ax1.bar(x+.19,month.poa_wh_m2.to_numpy()/1000,width=.38,label='Calculated tilted-plane irradiance (POA)')
    ax1.set_ylabel('Monthly irradiation (kWh/m²)')
    ax1.legend(loc='upper right',fontsize=9)
    ax1.grid(axis='y',alpha=.22);ax1.set_axisbelow(True)
    ideal=month.ideal_poa_kw_per_kwp.to_numpy()*5.22
    dc=month.pv_dc_kw_per_kwp.to_numpy()*5.22
    ac=month.pv_ac_equiv_kw_per_kwp.to_numpy()*5.22
    ax2.plot(x,ideal,marker='o',label='Ideal 5.22-kWp output from POA, before losses')
    ax2.plot(x,dc,marker='s',label='Modelled PV DC, after derating and temperature')
    ax2.plot(x,ac,marker='^',label='AC-equivalent PV potential, after inverter efficiency')
    ax2.set_ylabel('Monthly electrical potential (kWh)')
    ax2.set_xlabel('2025, NASA local solar time')
    ax2.set_xticks(x,months)
    ax2.grid(axis='y',alpha=.22)
    ax2.legend(loc='upper right',fontsize=9)
    save(fig,'04_solar_irradiation_pv_losses.png')

    # 05: Annual energy-versus-seasonality, full 365 days with smoothed lines.
    daily=h12[['load_kw','pv_dc_available_kw']].resample('D').sum()
    fig,ax=canvas('Full-year household demand and available solar PV, 2025','Daily energy (kWh)',(12,5.4))
    ax.plot(daily.index,daily.load_kw,linewidth=.6,alpha=.40,label='Daily household demand')
    ax.plot(daily.index,daily.pv_dc_available_kw,linewidth=.65,alpha=.40,label='Daily available PV DC')
    ax.plot(daily.index,daily.load_kw.rolling(14,min_periods=1,center=True).mean(),linewidth=2,label='Demand, 14-day average')
    ax.plot(daily.index,daily.pv_dc_available_kw.rolling(14,min_periods=1,center=True).mean(),linewidth=2,label='PV DC, 14-day average')
    ax.set_xlabel('2025')
    fmt_dates(ax);ax.legend(ncol=2,fontsize=9)
    save(fig,'05_full_year_daily_demand_solar.png')

    # 06: Real annual AC energy balance at the consumer loads, not inverter total duplicated.
    pv_direct=h12.pv_dc_used_for_ac_kw*.95-h12.grid_export_kw
    batt_ac=h12.battery_dc_discharge_kw*.95
    supply=pd.DataFrame({'PV direct AC':pv_direct,'Battery AC discharge':batt_ac,
                         'Grid import':h12.grid_import_kw},index=h12.index).resample('MS').sum()
    load_month=h12.load_kw.resample('MS').sum()
    err=np.abs(supply.sum(axis=1)-load_month)
    if err.max()>1e-2:
        raise AssertionError(f'AC supply and demand do not balance ({err.max():.3f} kWh)')
    fig,ax=canvas('Monthly electricity supplied to four households, 2025','Monthly energy (kWh)',(11.2,5.5))
    supply.plot.bar(stacked=True,ax=ax,width=.72,rot=0)
    ax.plot(np.arange(12),load_month.to_numpy(),'k.-',linewidth=1.6,label='Total household demand')
    ax.set_xticks(np.arange(12),[t.strftime('%b') for t in supply.index])
    ax.set_xlabel('2025');ax.legend(ncol=2,fontsize=9)
    save(fig,'06_monthly_electricity_supply.png')

    # 07: What happens to the DC PV generation after the PV model produces it.
    allocated=pd.DataFrame({'PV DC to AC path':h12.pv_dc_used_for_ac_kw,
                            'PV DC to battery charge':h12.pv_dc_charge_kw,
                            'PV DC curtailed':h12.pv_dc_curtailed_kw},index=h12.index).resample('MS').sum()
    if not np.allclose(allocated.sum(axis=1).to_numpy(),
                       h12.pv_dc_available_kw.resample('MS').sum().to_numpy(),atol=.02):
        raise AssertionError('PV DC allocations do not balance')
    fig,ax=canvas('Where generated PV DC energy goes, 12 panels / 4 modules','Monthly PV DC energy (kWh)',(11.2,5.3))
    allocated.plot.bar(stacked=True,ax=ax,rot=0,width=.72)
    ax.set_xticks(np.arange(12),[t.strftime('%b') for t in allocated.index])
    ax.set_xlabel('2025');ax.legend(ncol=1,fontsize=9)
    save(fig,'07_monthly_pv_allocation.png')

    # 08: Annual storage SOC, use daily average + low/high, not 168 hours only.
    fig,ax=canvas('Battery stored energy over the whole year','Usable battery energy (kWh)',(12,5.4))
    entries=[(h12,'12 panels / 4 battery modules'),(h16,'16 panels / 4 battery modules')]
    if h16_8 is not None:entries.append((h16_8,'16 panels / 8 battery modules'))
    for df,label in entries:
        soc=df.soc_usable_kwh.resample('D').agg(['min','mean','max'])
        ax.plot(soc.index,soc['mean'],linewidth=1.4,label=label)
        if '8 battery' in label:
            ax.fill_between(soc.index,soc['min'],soc['max'],alpha=.10)
    ax.set_xlabel('2025');fmt_dates(ax);ax.legend(fontsize=9)
    save(fig,'08_year_round_battery_soc.png')

    # 09: Annual duration curve and controlled transformer export case.
    fig,ax=canvas('Transformer apparent-power duration curve, all 8,760 hours','Transformer loading (kVA)',(11,5.4))
    cases=[(h12,'12 panels / 4 batteries, no export'),(h16,'16 panels / 4 batteries, no export')]
    if h24_export is not None:cases.append((h24_export,'24 panels / 8 batteries, export to transformer cap'))
    for df,label in cases:
        ordered=np.sort(df.transformer_s_kva.to_numpy())[::-1]
        ax.plot(np.arange(len(ordered)),ordered,label=label,linewidth=1.5)
    cap=float(metadata.get('baseline_transformer_max_pu',.9))*5
    ax.axhline(cap,linestyle='--',label=f'Assumed operating ceiling {cap:g} kVA')
    ax.axhline(5,linestyle=':',label='Transformer 5 kVA nameplate')
    ax.set_xlabel('Hours per year at or above loading on vertical axis')
    ax.set_xlim(0,8760)
    ax.legend(fontsize=8)
    save(fig,'09_annual_transformer_duration.png')

    # 10: Representative 72h with *maximum import*, not the misleading sunniest week.
    end=h12.grid_import_kw.rolling(72,min_periods=72).sum().idxmax()
    st=end-pd.Timedelta(hours=71)
    w=h12.loc[st:end]
    pv_ac=np.clip(w.pv_dc_used_for_ac_kw.to_numpy()*.95-w.grid_export_kw.to_numpy(),0,None)
    batt_ac=w.battery_dc_discharge_kw.to_numpy()*.95
    grid=w.grid_import_kw.to_numpy()
    demand=w.load_kw.to_numpy()
    if not np.allclose(pv_ac+batt_ac+grid+w.unserved_kw.to_numpy(),demand,atol=1e-4):
        raise AssertionError('Representative week supply and load mismatch')
    fig,ax=canvas('How the PV, battery and grid supply demand: three-day example','Power (kW)',(12.1,5.4))
    ax.stackplot(w.index,pv_ac,batt_ac,grid,labels=['PV supplied to load (AC)','Battery discharge to load (AC)','Grid import'])
    ax.plot(w.index,demand,'k-',linewidth=1.5,label='Household load')
    ax.set_xlabel(f'{st:%d %b} to {end:%d %b %Y}, NASA local solar time')
    ax.legend(loc='upper left',fontsize=9,ncol=2)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    save(fig,'10_three_day_dispatch_explained.png')

    # 11: outages presented by severity; islanding remains hypothetical.
    case_names={'24hr_outage_low_solar':'24-hour outage\nlow solar',
        '72hr_outage_low_solar':'72-hour outage\nlow solar',
        '72hr_outage_plus_demand_and_solar':'72-hour outage\n+50% load, half solar'}
    fig,ax=canvas('Unserved energy in three hypothetical outage tests','Energy not served (kWh)',(10,5.2))
    p=outage.copy()
    p['case_label']=p['case'].map(case_names).fillna(p['case'])
    wide=p.pivot(index='case_label',columns='policy',values='ens_kwh')
    order=[case_names[s] for s in case_names if case_names[s] in wide.index]
    wide=wide.loc[order]
    wide.rename(columns={'conventional':'Conventional','fixed_reserve':'Fixed SOC reserve','adaptive_reactive':'Reactive SOC reserve'}).plot.bar(ax=ax,rot=0,width=.76)
    ax.set_xlabel('Assumed outage scenario');ax.legend(title='Operating strategy',fontsize=9)
    save(fig,'11_outage_energy_not_served.png')

    # 12: battery power vs battery energy, independent sweep, small inset not a main headline.
    bs=battery[(battery.panels==16)&(np.isclose(battery.inverter_kva,6)) &
       np.isclose(battery.requested_charge_dc_kw,battery.requested_discharge_dc_kw)]
    fig,ax=canvas('Battery energy versus charging/discharging power','Annual self-sufficiency (%)',(9.7,5.2))
    for power,g in bs.groupby('requested_charge_dc_kw'):
        g=g.sort_values('bess_usable_kwh')
        ax.plot(g.bess_usable_kwh,g.self_sufficiency_pct,marker='o',label=f'{power:g} kW charge/discharge')
    ax.set_xlabel('Battery usable energy (kWh)')
    ax.legend(fontsize=9)
    save(fig,'12_bess_power_vs_energy.png')

    # 13: hardware matrix as a compact secondary reference, with plain ratings.
    valid=sizing[['panels','inverter_kva']].drop_duplicates()
    opts=[5.,6.,7.6,8.,10.]
    arr=np.array([[int(((valid.panels==p)&np.isclose(valid.inverter_kva,i)).any()) for p in panels] for i in opts])
    fig,ax=canvas('PV DC nameplate compatibility, inverter family',(None),figsize=(8.7,4.8))
    ax.imshow(arr,cmap='Greys',vmin=0,vmax=1,aspect='auto')
    ax.set_xticks(range(len(panels)),[f'{p} panels' for p in panels]);ax.set_yticks(range(len(opts)),[f'{i:g} kVA' for i in opts])
    ax.set_xlabel('Central PV capacity');ax.set_ylabel('Inverter rating')
    for k in range(len(opts)):
        for j in range(len(panels)):
            ax.text(j,k,'Yes' if arr[k,j] else 'No',ha='center',va='center',
                    color='white' if arr[k,j] else 'black',fontsize=10)
    ax.grid(False)
    save(fig,'13_inverter_dc_input_screen.png')

    readme='''# Guide to Case 1 figures

The default visualizations prioritize the research questions: central PV/BESS sizing,
solar-to-electricity conversion, annual operation, the 5 kVA transformer and disturbances.
All graphics are derived from the saved CSV data. No numbers were estimated from the images.

## Plots and interpretation

1. **01:** Joint PV and BESS self-sufficiency. Each cell uses the smallest inverter model passing the listed DC input nameplate test. Zero export, conventional causal control.
2. **02:** Same configurations, fraction of the PV DC generation curtailed. Higher PV capacity can increase curtailment.
3. **03:** Same configurations, illustrative HOMER-based annualized cost with no export revenue. This is *not* a local installed-price comparison.
4. **04:** NASA horizontal irradiation versus modeled irradiance on the 5-degree tilted plane; ideal POA-based PV electricity versus DC output after 80% derating/temperature and AC-equivalent output after 95% inverter efficiency. AC-equivalent means electrical potential *before dispatch*, not energy delivered to consumers, exported or stored.
5. **05:** Every day of 2025, with 14-day moving means for readability. Daily PV DC and household load are intentionally plotted on the same energy scale.
6. **06:** Monthly electricity meeting household demand. PV direct AC + battery discharge AC + grid import equals load, subject to rounding. Battery charging appears in 07, not as additional electricity consumed by households.
7. **07:** Monthly PV DC allocated to the AC conversion path, battery charging and curtailment. All bars together equal available PV DC.
8. **08:** Entire-year daily mean battery state of charge. 8-module size is shown if its dispatch file exists; daily min–max band depicts its range.
9. **09:** Annual transformer apparent-power duration. The export-to-envelope case is a *controlled PCC algebra screen*, not a verified pandapower or single-phase/split-phase network assessment.
10. **10:** The 72 hours with the highest grid imports. Stacked AC contributions show what actually meets household demand, with a separate black load line. This replaces the overlapping curves in the earlier sunny-week plot.
11. **11:** Three hypothetical outage stresses. Energy-not-served is conditional on backup/islanding being installed and approved; no islanding was verified.
12. **12:** Battery energy and charging/discharging power independently varied for a 16-panel 6-kVA inverter case. DC power limits are constrained by modeled BMS/inverter ratings.
13. **13:** Solar DC nameplate compatibility only. This does not verify module string Voc/Isc, MPPT or installed equipment.

## Reproducibility and limits

- Primary demand is the unchanged 2025 four-house HOMER-normalized stochastic series.
- Weather is NASA POWER hourly 2025 in LST at the recorded source coordinates.
- The 5 kVA EPM transformer operating limit is treated as an *assumed* 90% of nameplate. Household PF is a sensitivity, not a site measurement.
- No grid-connected export or island operation has been commissioned/approved based on the available evidence.
- The model uses one shared PV and BESS installation, no individual rooftop systems.
- The PV method is documented in `../model_provenance.json`. When `pvlib` is unavailable, only the explicitly labelled approximation can be regenerated here. Re-run on a machine with `pvlib` for source-aligned solar conversion.
- The pandapower network has not been revalidated for these figures. The power balance and PCC apparent loading alone cannot establish LV voltage or conductor feasibility.
- Figure labels do not repeat method caveats. Use this file and the project methods section when presenting results.
'''
    readme+='\nModel method: `'+str(metadata.get('method','unknown'))+'`\n'
    (target/'README.md').write_text(readme,encoding='utf-8')
    return done

if __name__=='__main__':
    files=generate_case1_figures()
    print(f'Created {len(files)} figures in {files[0].parent}')
