"""Case 1 v3 WP1 consolidated CLI. Run from any working directory.

Broad design sweep uses a causal DC-coupled dispatch. Annual/72 h figures are
for selected candidates from the SAME sweep; retained legacy independent code
is included in the archive for comparative checks and full pandapower rerun.
"""
from __future__ import annotations
import argparse,sys,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from wp1_v3 import model as m,plots

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results';FIG=OUT/'figures';FIG.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'legacy'))
import case1_v2 as reference_v2
reference_v2.NASA_PATH=ROOT/'data/NASA_POWER_SanRafael_hourly_2025.csv'
reference_v2.META_PATH=ROOT/'data/NASA_POWER_SanRafael_hourly_2025_metadata.json'
reference_v2.XML_PATH=ROOT/'data/SimulacionTampico1k(1).xml'


def choose_candidate(df,houses,target=90.):
    f=plots.eligible_designs(df[df.households==houses])
    qualified=f[f.self_sufficiency_pct>=target]
    if len(qualified):return qualified.sort_values('annual_total_no_credit_usd').iloc[0]
    if len(f):return f.sort_values(['self_sufficiency_pct','annual_total_no_credit_usd'],ascending=[False,True]).iloc[0]
    return None


def run(quick=False,require_pvlib=False,pf=.98,trafo_factor=.9):
    df,meta,sd=reference_v2.read_inputs()
    try:
        if require_pvlib:
            pv,diag=reference_v2.pvlib_nasa_pv(df)
        else:
            pv,diag=reference_v2.pvlib_nasa_pv(df)
    except ImportError:
        if require_pvlib:raise RuntimeError('Install pvlib: pip install pvlib')
        pv,diag=reference_v2.approximate_nasa_pv(df)
    loads=reference_v2.build_stochastic_load(sd,df.index,houses=20)
    PV=[12,16,20,24] if quick else list(range(8,41,4))+[48,56,64,72,80]
    BESS=[0,4,8] if quick else [0,2,4,6,8,10,12,16,20,24]
    HOUSES=[4,8,12] if quick else list(range(4,21))
    inverter_ratings=list(m.INVERTERS)
    candidate_rows=[];rejected=[]
    for h in HOUSES:
        load=loads[f'load_{h}hh_kw']
        for panels in PV:
            dc_kwp=panels*m.PANEL_KWP
            solar=pv*dc_kwp
            for inv in inverter_ratings:
                if dc_kwp>m.INVERTERS[inv][0]+1e-9:
                    for b in BESS:rejected.append((h,panels,b,inv,'DC_INPUT_NAMEPLATE_LIMIT'))
                    continue
                for b in BESS:
                    power_limit=5.0 if b else 0.
                    out=m.dispatch(load,solar,modules=b,inverter_kva=inv,cap_pu=trafo_factor,pf=pf,
                                   charge_discharge_kw=power_limit)
                    row=m.score(out,load,solar,b,panels,inv,h,trafo_factor,pf)
                    row['battery_power_cap_kw']=power_limit
                    candidate_rows.append(row)
    table=pd.DataFrame(candidate_rows)
    table.to_csv(OUT/'all_hardware_eligible_designs.csv',index=False,float_format='%.7f')
    pd.DataFrame(rejected,columns=['households','panels','bess_modules','inverter_kva','reason']).to_csv(OUT/'excluded_hardware_designs.csv',index=False)
    eligible=plots.eligible_designs(table)
    table.drop(index=eligible.index).to_csv(
        OUT/'excluded_grid_ens_designs.csv',index=False)
    eligible.to_csv(OUT/'PCC_screened_designs.csv',index=False)
    # Additional expanded-housing, battery-power feasibility search.
    # Does not overstate the fixed-5kW main sweep as a population limit.
    higher=[]
    for hh in range(12,21):
        if hh not in HOUSES:continue
        demand=loads[f'load_{hh}hh_kw']
        for pp in (40,48,56,64,72,80):
            solar=pv*pp*m.PANEL_KWP
            for inv in (12.,20.,24.):
                if pp*m.PANEL_KWP>m.INVERTERS[inv][0]:continue
                for modules in (8,12,16,20,24):
                    for power in (5.,7.5,10.,15.):
                        r=m.dispatch(demand,solar,modules,inv,cap_pu=trafo_factor,pf=pf,
                                     charge_discharge_kw=power)
                        k=m.score(r,demand,solar,modules,pp,inv,hh,trafo_factor,pf)
                        k['battery_power_cap_kw']=power
                        higher.append(k)
    pd.DataFrame(higher).to_csv(OUT/'higher_households_battery_power_extended_screen.csv',index=False)
    table=pd.concat([table,pd.DataFrame(higher)],ignore_index=True).drop_duplicates(subset=['households','panels','bess_modules','inverter_kva','battery_power_cap_kw'])
    table.to_csv(OUT/'ALL_designs_including_extended_battery_power.csv',index=False)
    frontier=[]
    for hh in HOUSES:
        eligible=plots.eligible_designs(table[table.households==hh])
        if not len(eligible):continue
        for regime,col in [('no_credit','annual_total_no_credit_usd'),('homer_credit','annual_total_homer_credit_usd')]:
            f=plots.frontier(eligible,col).copy();f['regime']=regime;frontier.append(f)
    pd.concat(frontier,ignore_index=True).to_csv(OUT/'pareto_all_households.csv',index=False)
    plots.pareto_panels(table,FIG)
    plots.expansion_plots(table,FIG)
    representatives=[];trafo_samples={};monthly_samples={}
    for hh in (4,8,12,15,17,20):
        if hh not in HOUSES:continue
        item=choose_candidate(table,hh)
        if item is None:continue
        representatives.append(item)
        load=loads[f'load_{hh}hh_kw']
        solar=pv*item.panels*m.PANEL_KWP
        hourly=m.dispatch(load,solar,modules=int(item.bess_modules),inverter_kva=float(item.inverter_kva),
                          cap_pu=trafo_factor,pf=pf,charge_discharge_kw=float(item.battery_power_cap_kw))
        label=f'{hh} households: {int(item.panels)}P / {int(item.bess_modules)}B / {item.inverter_kva:g} kVA / {item.battery_power_cap_kw:g} kW BESS'
        trafo_samples[label]=hourly
        monthly_samples[label]=(hourly,load,solar)
        hourly.assign(demand_kw=load,pv_dc_available_kw=solar).to_csv(OUT/f'hourly_selected_{hh}house.csv',index_label='timestamp',float_format='%.7f')
    if representatives:
        pd.DataFrame(representatives).to_csv(OUT/'selected_community_options.csv',index=False)
        plots.duration_plot(trafo_samples,FIG,cap_pu=trafo_factor)
        plots.monthly_balance(monthly_samples,FIG)
    power_rows=[]
    for hh in (4,8,12,15,17):
        if hh not in HOUSES:continue
        choice=choose_candidate(table,hh)
        if choice is None or choice.bess_modules<=0:continue
        demand=loads[f'load_{hh}hh_kw'];supply=pv*choice.panels*m.PANEL_KWP
        for limit in (2.5,5.0,7.5,10.0):
            power_result=m.dispatch(demand,supply,int(choice.bess_modules),float(choice.inverter_kva),
                         cap_pu=trafo_factor,pf=pf,charge_discharge_kw=limit)
            k=m.score(power_result,demand,supply,int(choice.bess_modules),int(choice.panels),
                      float(choice.inverter_kva),hh,trafo_factor,pf)
            k['system']=f'{hh} HH / {int(choice.panels)}P / {int(choice.bess_modules)}B'
            k['battery_power_cap_kw']=limit
            power_rows.append(k)
    power_table=pd.DataFrame(power_rows)
    power_table.to_csv(OUT/'battery_power_sensitivity.csv',index=False)
    plots.battery_power_plot(power_table,FIG)
    resilience_rows=[]
    # Run resilience only for the 8-household selected candidate (4 in quick mode).
    hh=8 if 8 in HOUSES else 4
    item=choose_candidate(table,hh)
    if item is not None and item.bess_modules>0:
        load=loads[f'load_{hh}hh_kw'];solar=pv*item.panels*m.PANEL_KWP
        # Retrospective lowest measured 3-day PV window, not a controller forecast.
        three=solar.resample('D').sum().rolling(3).sum()
        valid=three[(three.index>=pd.Timestamp('2025-01-10')) & (three.index<=pd.Timestamp('2025-12-26'))]
        low_end=valid.idxmin();start=low_end-pd.Timedelta(days=2)
        stress_index=pd.date_range(start,periods=72,freq='h')
        stress_pv=solar.copy();stress_load=load.copy()
        stress_pv.loc[stress_index]=stress_pv.loc[stress_index]*.50
        stress_load.loc[stress_index]=stress_load.loc[stress_index]*1.25
        on=np.ones(72,dtype=np.bool_);on[24:]=False
        traces={}
        for policy in ('conventional','fixed_reserve','adaptive','adaptive_lm'):
            annual=m.dispatch(load,solar,int(item.bess_modules),float(item.inverter_kva),cap_pu=trafo_factor,pf=pf,
                              policy=policy,charge_discharge_kw=float(item.battery_power_cap_kw))
            prev=annual.loc[:start].iloc[-2].soc_usable_kwh if start in annual.index else annual.loc[:start].iloc[-1].soc_usable_kwh
            em=int(item.bess_modules)*m.USABLE_KWH_MODULE
            actual_soc=.1+.9*float(prev)/em
            reserve_all=m.get_reserve(stress_pv,policy)
            reserves=pd.Series(reserve_all,index=stress_pv.index).loc[stress_index].to_numpy()
            r=m.dispatch(stress_load.loc[stress_index],stress_pv.loc[stress_index],int(item.bess_modules),
                         float(item.inverter_kva),cap_pu=trafo_factor,pf=pf,policy=policy,grid_on=on,
                         initial_soc_pu=actual_soc,reserve_override=reserves,
                         charge_discharge_kw=float(item.battery_power_cap_kw))
            traces[policy]=r
            r.assign(demand_kw=stress_load.loc[stress_index],pv_dc_available_kw=stress_pv.loc[stress_index],grid_available=on).to_csv(
                OUT/f'72hr_combined_stress_{policy}.csv',index_label='timestamp',float_format='%.7f')
            resilience_rows.append(dict(controller=policy,households=hh,panels=int(item.panels),bess_modules=int(item.bess_modules),
                 annual_self_sufficiency_pct=100*(1-annual.grid_import.sum()/load.sum()),
                 stress_ens_kwh=float(r.ens.sum()),stress_critical_ens_kwh=float(r.critical_ens.sum()),
                 deferred_backlog_at_end_kwh=float(r.deferred_backlog_kwh.iloc[-1]),
                 total_shortfall_including_backlog_kwh=float(r.ens.sum()+r.deferred_backlog_kwh.iloc[-1]),
                 low_solar_factor=.5,stress_demand_factor=1.25,outage_start_hour=24,outage_hours=48,
                 stress_window_start=str(start),islanding_confirmed=False))
        plots.resilience_plot(traces,{'stressed_load':stress_load.loc[stress_index],
              'stressed_pv_dc':stress_pv.loc[stress_index], 'usable_kwh':int(item.bess_modules)*m.USABLE_KWH_MODULE},
              FIG,stress_index[24],stress_index[-1])
    pd.DataFrame(resilience_rows).to_csv(OUT/'72hr_resilience_by_controller.csv',index=False)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (reference_v2.NASA_PATH,reference_v2.XML_PATH)}
    manifest={'solar_method':diag['method'],'original_v18_v5_pvlib_parity_claim':bool('PVLIB' in diag['method']),
       'solar_resource_annual_dc_at_5p22_kwh':diag['annual_dc_kwh_at_5p22'],
       'houses_swept':HOUSES,'panels_swept':PV,'battery_modules_swept':BESS,
       'inverter_rating_kva_swept':inverter_ratings,'trafo_loading_limit_ASSUMED':trafo_factor,
       'household_pf_ASSUMED':pf,'hardware_input_rejected':len(rejected),
       'screened_valid_dc_input':len(table),'screened_no_grid_ens':int((table.grid_ens_kwh<=1e-7).sum()),
       'higher_housing_power_extended_designs':len(higher),
       'pandapower_validation':'NOT_RUN; preserved independent package can test critical hours',
       'islanding_confirmed':False,'weather_and_homer_sha256':hashes,
       'costing':'Proportional HOMER component costs scaled to quote $11974.79 USD subtotal, no supplier price for larger designs',
       'parallel_inverter_20_or_24_kva':'HYPOTHETICAL_2x10_OR_2x12K_NO_WIRING_OR_APPROVAL_VALIDATION',
       'economic_tariff':'HOMER 0.29 USD/kWh import; 0 or 0.275 USD/kWh export; not EPM-approved tariff',
       'adaptive_reserve_formula':'AUTHOR_DEFINED_HEURISTIC_NOT_LITERATURE_VALIDATED',
       'scenario_results':'screening_only_not_network_certification'}
    (OUT/'RUN_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k in ('solar_method','screened_valid_dc_input','screened_no_grid_ens','hardware_input_rejected')},indent=2))
    print('Results:',OUT)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--quick',action='store_true',help='Small smoke-test sweep')
    p.add_argument('--require-pvlib',action='store_true',help='Fail if pvlib is missing')
    p.add_argument('--pf',type=float,default=.98,help='Household PF assumption, default 0.98')
    p.add_argument('--loading',type=float,default=.9,help='Transformer operating fraction, assumed')
    a=p.parse_args()
    run(a.quick,a.require_pvlib,a.pf,a.loading)
