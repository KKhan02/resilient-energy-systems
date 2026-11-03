#!/usr/bin/env python3
"""Conditional 5-kVA pandapower feeder screen for optimized 2025 PyPSA dispatch.

Reuses the parameters and balanced single-phase representation of
SanRafael_pandapower_Grid_Check_v5_uncertainty.ipynb.
Run only with the project environment that has pandapower installed.
The feeder is representative, NOT the surveyed topology of candidate EPM nodes.
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE
SRC_DIR=HERE/'input'/'dispatch'
SCALE=3.0
MV_KV=7.621
LV_KV=0.240
TRAFO_KVA=5.0
MV_ROUTE_M=354.2
LV_ROUTE_M=324.5
PCC_ENERGY_LIMIT_KVA=4.5
REQ=['timestamp_lst','demand_kw','inverter_ac_kw','grid_import_kw','grid_export_kw','pcc_kva_proxy']


def load_dispatch(path:Path)->pd.DataFrame:
    df=pd.read_csv(path)
    missing=set(REQ)-set(df.columns)
    if missing: raise ValueError(f'{path}: missing columns: {sorted(missing)}')
    df['timestamp_lst']=pd.to_datetime(df['timestamp_lst'],errors='raise')
    df=df.sort_values('timestamp_lst').reset_index(drop=True)
    if len(df)!=8760: raise ValueError(f'{path}: expected 8,760 hourly rows, found {len(df)}')
    if df.timestamp_lst.duplicated().any(): raise ValueError(f'{path}: duplicate timestamps')
    vals=df[['demand_kw','inverter_ac_kw','grid_import_kw','grid_export_kw','pcc_kva_proxy']].to_numpy(dtype=float)
    if not np.isfinite(vals).all():raise ValueError(f'{path}: invalid dispatch numbers')
    if (vals[:,:2]<-1e-5).any():raise ValueError(f'{path}: negative load/inverter generation')
    if not np.allclose(df['demand_kw']-df['inverter_ac_kw'],df['grid_import_kw']-df['grid_export_kw'],atol=2e-4):
        raise ValueError(f'{path}: dispatch energy balance mismatch. Investigate before power flow.')
    return df


def critical_indices(df:pd.DataFrame, top_n:int=10)->np.ndarray:
    # Includes large gross load, net grid import, inverter output, and apparent PCC.
    # Important: gross-load peak can govern last-house voltage even when PCC is small.
    ix={0,len(df)-1}
    for col in ['demand_kw','inverter_ac_kw','grid_import_kw','pcc_kva_proxy']:
        order=np.argsort(df[col].to_numpy(dtype=float))
        ix.update(order[-top_n:].tolist())
        ix.update(order[:min(3,top_n)].tolist())
    ix.add(int(np.abs(df['demand_kw']-df['inverter_ac_kw']).to_numpy().argmax()))
    ix.add(int(np.abs(df['demand_kw']-df['inverter_ac_kw']).to_numpy().argmin()))
    # Include lowest SOC hours and selected January/July/November peak loads.
    if 'battery_soc_usable_kwh' in df:
        ix.update(np.argsort(df['battery_soc_usable_kwh'].to_numpy())[:top_n].tolist())
    for mo in (1,7,11):
        part=df[df.timestamp_lst.dt.month==mo]
        if not part.empty:
            ix.add(int(part['demand_kw'].idxmax()))
            ix.add(int(part['grid_import_kw'].idxmax()))
    return np.array(sorted(ix),dtype=int)


def siting_tap_index(taps:int, siting:str)->int:
    """Choose where the single combined PV/BESS AC inverter is connected.

    0 = transformer LV bus, taps = last feeder tap. Middle is the nearest
    downstream tap to 50% of the representative 324.5 m trunk length.
    """
    if taps < 1:
        raise ValueError('Expected positive tap count')
    if siting == 'lv_head':
        return 0
    if siting == 'middle':
        return (taps + 1) // 2
    if siting == 'far_end':
        return taps
    raise ValueError('Unknown inverter siting: '+str(siting))


def create_net(houses:int,inverter_siting:str):
    import pandapower as pp
    if inverter_siting not in {'lv_head','middle','far_end'}:
        raise ValueError('inverter_siting must be lv_head, middle or far_end')
    n=pp.create_empty_network(name=f'5kVA representative, {houses} homes, {inverter_siting}',f_hz=60.0,sn_mva=1.0)
    mv_eq=math.sqrt(3)*MV_KV; lv_eq=math.sqrt(3)*LV_KV
    upstream=pp.create_bus(n,vn_kv=mv_eq,name='MV_SOURCE_EQ')
    hv=pp.create_bus(n,vn_kv=mv_eq,name='TRF_HV_EQ')
    lv=pp.create_bus(n,vn_kv=lv_eq,name='TRF_LV_EQ')
    pp.create_ext_grid(n,upstream,vm_pu=1.0,name='UPSTREAM_FIXED_1PU')
    mv_line=pp.create_line_from_parameters(n,upstream,hv,length_km=MV_ROUTE_M/1000,
        r_ohm_per_km=.832,x_ohm_per_km=.4,c_nf_per_km=0.,max_i_ka=.184,name='MV_#2_ACSR')
    trafo=pp.create_transformer_from_parameters(n,hv,lv,sn_mva=TRAFO_KVA*SCALE/1000,
        vn_hv_kv=mv_eq,vn_lv_kv=lv_eq,vk_percent=3.0,vkr_percent=1.8,
        pfe_kw=.030*SCALE,i0_percent=2.5,shift_degree=0,name='5KVA_94022_PROXY')
    taps=math.ceil(houses/2)
    last=lv; loads=[]; lv_buses=[lv]; lv_lines=[]
    for k in range(taps):
        bus=pp.create_bus(n,vn_kv=lv_eq,name=f'LV_TAP_{k+1}')
        idx=pp.create_line_from_parameters(n,last,bus,length_km=(LV_ROUTE_M/taps)/1000,
            r_ohm_per_km=2*.656,x_ohm_per_km=2*.08,c_nf_per_km=0.,
            max_i_ka=.150,name=f'LV_TRUNK_{k+1}_1_0_AAC_LOOP')
        lv_buses.append(bus);lv_lines.append(idx)
        for j in range(k*2,min(k*2+2,houses)):
            loads.append(pp.create_load(n,bus,p_mw=0.,q_mvar=0.,name=f'HOUSE_{j+1}'))
        last=bus
    inv_tap=siting_tap_index(taps,inverter_siting)
    inv_bus=lv_buses[inv_tap]
    sgen=pp.create_sgen(n,inv_bus,p_mw=0.,q_mvar=0.,name='COMMUNITY_INVERTER_AC_INJECTION')
    return n, dict(houses=houses,loads=loads,lv_buses=lv_buses,lv_lines=lv_lines,
                   trafo=trafo,mv_line=mv_line,inverter=sgen,taps=taps,
                   inverter_tap=inv_tap,inverter_distance_m=round(LV_ROUTE_M*inv_tap/taps,3))


def allocation_weights(houses:int,mode:str)->np.ndarray:
    if mode=='equal':return np.ones(houses)/houses
    if mode=='far_end_heavy':
        # Stress test: last 25% of houses take 60% of instantaneous total load.
        # Not an inference about actual household usage.
        tail=max(1,math.ceil(houses*.25));n0=houses-tail
        w=np.concatenate([np.full(n0,.4/n0),np.full(tail,.6/tail)])
        return w
    raise ValueError(f'Unknown allocation {mode}')


def solve_hour(n,meta,row,pf:float,weights:np.ndarray,mode:str):
    import pandapower as pp
    demand=float(row.demand_kw);inverter=float(row.inverter_ac_kw)
    qfactor=math.tan(math.acos(pf))
    for ld,share in zip(meta['loads'],weights):
        n.load.at[ld,'p_mw']=SCALE*demand*share/1000.
        n.load.at[ld,'q_mvar']=SCALE*demand*share*qfactor/1000.
    n.sgen.at[meta['inverter'],'p_mw']=SCALE*inverter/1000.
    n.sgen.at[meta['inverter'],'q_mvar']=0.
    base={
        'timestamp_lst':str(row.timestamp_lst),'households':meta['houses'],
        'siting':mode,'load_allocation':'','load_pf':pf,
        'inverter_tap':meta['inverter_tap'],'inverter_distance_m':meta['inverter_distance_m'],
        'load_kw':demand,'inverter_ac_kw':inverter,
        'scheduled_pcc_kw':float(row.grid_import_kw-row.grid_export_kw),
        'scheduled_pcc_kva_proxy':float(row.pcc_kva_proxy),
    }
    try:
        pp.runpp(n,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                 max_iteration=100,tolerance_mva=1e-9)
        v=n.res_bus.loc[meta['lv_buses'],'vm_pu']
        trafo_loading=float(n.res_trafo.at[meta['trafo'],'loading_percent'])
        pcc_p=float(n.res_ext_grid.p_mw.sum())*1000/SCALE
        pcc_q=float(n.res_ext_grid.q_mvar.sum())*1000/SCALE
        pcc_kva=math.hypot(pcc_p,pcc_q)
        line_loading=float(n.res_line.loc[meta['lv_lines'],'loading_percent'].max())
        loss_kw=(float(n.res_line.pl_mw.sum())+float(n.res_trafo.pl_mw.sum()))*1000/SCALE
        base.update(status='CONVERGED_SCREEN_ONLY',min_lv_pu=float(v.min()),
            max_lv_pu=float(v.max()),min_house_tap=int(v.idxmin()),
            max_lv_line_loading_pct=line_loading,
            transformer_loading_pct=trafo_loading,
            pcc_import_kw_ac=pcc_p,pcc_import_kvar_ac=pcc_q,pcc_kva_ac=pcc_kva,
            total_network_losses_kw=loss_kw,
            pcc_ac_minus_energy_kw=pcc_p-base['scheduled_pcc_kw'],
            violates_097=bool(v.min()<.97-1e-7),
            violates_103=bool(v.max()>1.03+1e-7),
            violates_trafo_100=bool(trafo_loading>100+1e-7),
            violates_lv_line_100=bool(line_loading>100+1e-7),
            violates_pcc_nominal_5=bool(pcc_kva>TRAFO_KVA+1e-7),
            violates_energy_4p5_ac=bool(pcc_kva>PCC_ENERGY_LIMIT_KVA+1e-7),
            solver_error='')
        voltage=[{'timestamp_lst':str(row.timestamp_lst),'households':meta['houses'],
                'siting':mode,'load_pf':pf,'tap_index':i,'distance_m':LV_ROUTE_M*i/meta['taps'],
                'vm_pu':float(n.res_bus.at[bus,'vm_pu'])}
                for i,bus in enumerate(meta['lv_buses'])]
    except Exception as exc:
        base.update(status='NOT_CONVERGED',min_lv_pu=np.nan,max_lv_pu=np.nan,
            max_lv_line_loading_pct=np.nan,transformer_loading_pct=np.nan,
            pcc_import_kw_ac=np.nan,pcc_import_kvar_ac=np.nan,pcc_kva_ac=np.nan,
            total_network_losses_kw=np.nan,pcc_ac_minus_energy_kw=np.nan,
            violates_097=False,violates_103=False,violates_trafo_100=False,
            violates_lv_line_100=False,violates_pcc_nominal_5=False,
            violates_energy_4p5_ac=False,solver_error=str(exc)[:180]);voltage=[]
    return base,voltage


def summarize(results:pd.DataFrame,mode:str)->pd.DataFrame:
    out=[]
    groups=['households','siting','load_allocation','load_pf']
    for key,d in results.groupby(groups,sort=True):
        good=d[d.status=='CONVERGED_SCREEN_ONLY']
        row=dict(zip(groups,key));row.update(hours_tested=len(d),hours_converged=len(good),
            hours_not_converged=len(d)-len(good),coverage='YEAR_8760' if mode=='full' else 'SELECTED_CRITICAL_HOURS_ONLY')
        if not good.empty:
            for col,func,into in [('min_lv_pu','min','lowest_lv_pu'),
                    ('max_lv_pu','max','highest_lv_pu'),('transformer_loading_pct','max','max_trafo_pct'),
                    ('max_lv_line_loading_pct','max','max_lv_line_pct'),
                    ('pcc_kva_ac','max','peak_ac_pcc_kva'),('total_network_losses_kw','max','max_losses_kw')]:
                row[into]=float(getattr(good[col],func)())
            for col in ['violates_097','violates_103','violates_trafo_100','violates_lv_line_100',
                        'violates_pcc_nominal_5','violates_energy_4p5_ac']:
                row['tested_hours_'+col]=int(good[col].sum())
            row['worst_lv_timestamp']=str(good.loc[good.min_lv_pu.idxmin(),'timestamp_lst'])
            row['max_trafo_timestamp']=str(good.loc[good.transformer_loading_pct.idxmax(),'timestamp_lst'])
        out.append(row)
    return pd.DataFrame(out)


def make_plots(summary:pd.DataFrame,profiles:pd.DataFrame,outdir:Path):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    outdir.mkdir(parents=True,exist_ok=True)
    for metric,ylabel,basename,limit in [
        ('lowest_lv_pu','Minimum LV voltage (pu)','min_voltage_by_household',.97),
        ('max_trafo_pct','Maximum transformer loading (%)','transformer_loading_by_household',100.0),
        ('max_lv_line_pct','Maximum LV conductor loading (%)','lv_conductor_loading_by_household',100.0)]:
        fig,ax=plt.subplots(figsize=(8.1,4.9))
        for key,group in summary.groupby(['siting','load_allocation','load_pf']):
            group=group.sort_values('households');m=group[metric].notna()
            ax.scatter(group.loc[m,'households'],group.loc[m,metric],s=60,label=f'{key[0]}, {key[1]}, PF {key[2]:.2f}')
        ax.axhline(limit,ls='--',c='gray',lw=1)
        ax.set(xlabel='Number of households (representative route)',ylabel=ylabel)
        ax.set_xticks(sorted(summary.households.unique()))
        ax.grid(alpha=.2);ax.legend(loc='best',fontsize=7,ncol=2)
        fig.tight_layout();fig.savefig(outdir/f'{basename}.png',dpi=190);fig.savefig(outdir/f'{basename}.svg');plt.close(fig)
    if not profiles.empty:
        # One clearly labelled worst snapshot per number of homes, for base placement/allocation/pf.
        for homes in sorted(profiles.households.unique()):
            df=profiles[(profiles.households==homes)&(profiles.siting=='lv_head')&
                        (profiles.load_allocation=='equal')&(abs(profiles.load_pf-.98)<1e-4)]
            if df.empty:continue
            # idxmin() returns the timestamp GROUP LABEL, not an integer row index.
            # Do not use df.loc[ts, ...] on a RangeIndex.
            ts=df.groupby('timestamp_lst')['vm_pu'].min().idxmin()
            sel=df.loc[df['timestamp_lst']==ts].sort_values('distance_m')
            fig,ax=plt.subplots(figsize=(7.5,4.5));ax.plot(sel.distance_m,sel.vm_pu,'o-',lw=1.5)
            ax.axhline(.97,ls='--',c='gray');ax.axhline(1.03,ls='--',c='gray')
            ax.set(xlabel='Representative cumulative LV trunk distance (m)',ylabel='Voltage (pu)',
                   title=f'{homes} homes, LV-head inverter, worst tested hour {ts}')
            ax.grid(alpha=.25);fig.tight_layout();fig.savefig(outdir/f'{homes}_homes_worst_lv_profile.png',dpi=190);fig.savefig(outdir/f'{homes}_homes_worst_lv_profile.svg');plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['critical','full'],default='critical')
    ap.add_argument('--cases',type=int,nargs='+',default=[7,9,12])
    ap.add_argument('--siting',nargs='+',choices=['lv_head','middle','far_end'],default=['lv_head','middle','far_end'])
    ap.add_argument('--allocation',nargs='+',choices=['equal','far_end_heavy'],default=['equal','far_end_heavy'])
    ap.add_argument('--power-factors',type=float,nargs='+',default=[.98,.9])
    ap.add_argument('--critical-top-n',type=int,default=10)
    ap.add_argument('--input',type=Path,default=SRC_DIR)
    ap.add_argument('--output',type=Path,default=HERE/'outputs'/'validation')
    ap.add_argument('--plots-only',action='store_true',
                    help='Regenerate figures from saved scenario_summary.csv and tap_voltage_profiles.csv; no power flow')
    args=ap.parse_args()
    if args.plots_only:
        summary_file=args.output/'scenario_summary.csv'
        profiles_file=args.output/'tap_voltage_profiles.csv'
        if not summary_file.exists():
            ap.error(f'No saved AC summary found at {summary_file}. Run --mode critical first.')
        if not profiles_file.exists():
            ap.error(f'No saved tap voltage profiles found at {profiles_file}. Run --mode critical first.')
        summary=pd.read_csv(summary_file)
        profiles=pd.read_csv(profiles_file)
        make_plots(summary,profiles,args.output/'figures')
        print(f'Regenerated figures from saved AC results: {(args.output/"figures").resolve()}')
        return
    for pf in args.power_factors:
        if not 0<pf<=1:ap.error('power factors must be in (0,1]')
    if not args.cases or any(not 5 <= h <= 15 for h in args.cases):
        ap.error('Household counts must be integers from 5 through 15')
    missing=[str(args.input/f'{h}_homes_hourly_dispatch.csv') for h in args.cases
             if not (args.input/f'{h}_homes_hourly_dispatch.csv').is_file()]
    if missing:
        ap.error('Missing hourly dispatch for the requested household counts:\n  '
                 +'\n  '.join(missing)
                 +'\nRun export_missing_dispatch.py first; never substitute aggregated annual results.')
    try:import pandapower as pp
    except ImportError as exc:
        raise SystemExit('pandapower not installed in this Python environment. Activate your project env, then pip install pandapower.') from exc
    args.output.mkdir(parents=True,exist_ok=True)
    rows=[];profiles=[];info=[]
    for houses in args.cases:
        fname=args.input/f'{houses}_homes_hourly_dispatch.csv'
        df=load_dispatch(fname)
        indices=range(len(df)) if args.mode=='full' else critical_indices(df,args.critical_top_n)
        info.append(dict(households=houses,path=str(fname),annual_hours=len(df),tested_hours=len(indices),
                         demand_kwh=float(df.demand_kw.sum()),
                         scheduled_import_kwh=float(df.grid_import_kw.sum()),
                         scheduled_max_pcc_kva=float(df.pcc_kva_proxy.max())))
        for siting in args.siting:
            net,meta=create_net(houses,siting)
            for alloc in args.allocation:
                weights=allocation_weights(houses,alloc)
                for pf in args.power_factors:
                    print(f'{houses} homes | {siting} | {alloc} | PF={pf:.2f} | hours={len(indices)}',flush=True)
                    for j in indices:
                        rec,v=solve_hour(net,meta,df.iloc[int(j)],pf,weights,siting)
                        rec['load_allocation']=alloc
                        for item in v:item['load_allocation']=alloc
                        rows.append(rec);profiles.extend(v)
    result=pd.DataFrame(rows)
    summary=summarize(result,args.mode)
    p=pd.DataFrame(profiles)
    result.to_csv(args.output/'powerflow_hourly_or_critical.csv',index=False)
    summary.to_csv(args.output/'scenario_summary.csv',index=False)
    if not p.empty:p.to_csv(args.output/'tap_voltage_profiles.csv',index=False)
    make_plots(summary,p,args.output/'figures')
    meta={'status':'AC_POWERFLOW_EXECUTED','version':'v1','pandapower_version':pp.__version__,
        'source':'pandapower v5 reference feeder translated to standalone driver',
        'case_input':info,'mode':args.mode,'pf':args.power_factors,'load_allocation':args.allocation,
        'inverter_siting':args.siting,
        'siting_definition':'head=transformer LV; middle=nearest halfway tap; far_end=last tap; one combined PV+BESS AC inverter',
        'powerflow_results':len(result),
        'converged':int((result.status=='CONVERGED_SCREEN_ONLY').sum()),
        'network':'5 kVA 7.621kV/240V, 354.2m MV, 324.5m LV representative radial, two houses per tap',
        'not_a_surveyed_network':True,'full_annual_count_only_if_mode_full':True,
        'transformer_parameters_and_lv_ampacity':'proxies from v5 notebook; not nameplate verified',
        'pcc_energy_4p5_kva':'PyPSA pre-loss limit; AC PCC includes electrical losses, reactive power and transformer magnetizing current',
        'voltage_097_103':'design screening band only',
        'area_geographic_location':'not inferred from synthetic cable segments'}
    (args.output/'validation_manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    print('\nResults: '+str(args.output.resolve()))
    print(summary.to_string(index=False,max_cols=12))

if __name__=='__main__':main()
