#!/usr/bin/env python3
"""Conditional per-transformer LV AC study from recorded coordinates and candidate houses.

This is NOT as-built feeder reconstruction or a definitive grid hosting certificate.
Uses the v5 balanced-equivalent assumptions. All physical routes are hypotheses.
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from topology import build_territories, evidence_rows, TRAFO_ORDER
from voltvar_control import solve_inverter_q

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
DISPATCH_DIR=REPO/'case1'/'studies'/'pandapower_dispatch_validation_v1'/'input'/'dispatch'
ROOT_FACTOR=3.0  # 3phase balanced equivalent of one 120/240 V single-phase service
MV_LN_KV=7.621
LV_LN_KV=.240
# v5 representative 2-conductor 1/0 AAC loop, not site-verified
LV_R_OHM_KM=2*.656
LV_X_OHM_KM=2*.08
LV_MAX_I_KA=.150


def get_dispatch_path(base,h):
    for p in [base/f'{h}_homes_hourly_dispatch.csv',base/f'{h}_homes'/'hourly_dispatch.csv']:
        if p.is_file():return p
    return None


def read_dispatch(path):
    df=pd.read_csv(path)
    necessary=['timestamp_lst','demand_kw','inverter_ac_kw','grid_import_kw','grid_export_kw']
    missing=set(necessary)-set(df)
    if missing:raise ValueError(f'{path}: missing {sorted(missing)}')
    if len(df)!=8760:raise ValueError(f'{path}: expected 8760 rows, found {len(df)}')
    df['timestamp_lst']=pd.to_datetime(df['timestamp_lst'])
    if df.timestamp_lst.isna().any() or df.timestamp_lst.duplicated().any():
        raise ValueError(f'{path}: invalid timestamps')
    if df[necessary[1:]].isna().any().any():raise ValueError(f'{path}: missing dispatch values')
    if (df['demand_kw']<-1e-7).any() or (df['inverter_ac_kw']<-1e-7).any():
        raise ValueError(f'{path}: unexpected negative demand/inverter')
    if not np.allclose(df.demand_kw-df.inverter_ac_kw,df.grid_import_kw-df.grid_export_kw,atol=2e-3):
        raise ValueError(f'{path}: dispatch P mismatch')
    return df.sort_values('timestamp_lst').reset_index(drop=True)


def load_profile(h,variant,base,cache):
    if variant not in ('gross','optimized'):raise ValueError(variant)
    exact=get_dispatch_path(base,h)
    if exact and h not in cache:cache[h]=read_dispatch(exact)
    if variant=='optimized':
        if not exact:return None, f'NO_OPTIMIZED_SCHEDULE_FOR_{h}_HOUSES'
        df=cache[h].copy()
        df['input_status']='OPTIMIZED_GENERIC_HOUSE_COUNT_DISPATCH'
        return df,'OPTIMIZED_GENERIC_HOUSE_COUNT_DISPATCH'
    # Gross-load baseline: use the exact household-count synthetic demand if possible;
    # for 1-4 houses use a 5-house profile divided by 5 and multiplied by count.
    if exact:
        df=cache[h].copy()
        label='EXACT_HOUSE_COUNT_SYNTHETIC_GROSS_DEMAND'
    else:
        basefive=get_dispatch_path(base,5)
        if basefive is None:
            raise FileNotFoundError('Gross baseline for small/altered territories needs 5_homes_hourly_dispatch.csv')
        if 5 not in cache:cache[5]=read_dispatch(basefive)
        df=cache[5].copy()
        df['demand_kw']=df['demand_kw']*h/5.
        label='FIVE_HOUSE_PER_HOME_DEMAND_PROXY_SCALED_TO_'+str(h)
    df['inverter_ac_kw']=0.
    df['grid_import_kw']=df['demand_kw']
    df['grid_export_kw']=0.
    df['input_status']=label
    return df,label


def stress_hours(df,top_n=10):
    indices={0,len(df)-1}
    for col in ['demand_kw','inverter_ac_kw','grid_import_kw']:
        a=df[col].to_numpy(float);indices.update(np.argsort(a)[-top_n:].tolist())
        indices.update(np.argsort(a)[:min(2,top_n)].tolist())
    if 'battery_soc_usable_kwh' in df:
        indices.update(np.argsort(df['battery_soc_usable_kwh'].to_numpy())[:top_n].tolist())
    for m in [1,7,11]:
        sl=df[df.timestamp_lst.dt.month==m]
        if len(sl):indices.add(int(sl.demand_kw.idxmax()))
    return sorted(indices)


def create_net(t,siting):
    import pandapower as pp
    if not t.houses:raise ValueError('Cannot simulate transformer without assigned houses')
    n=pp.create_empty_network(name=f'PROVISIONAL_{t.name}_{t.routing}_{siting}',f_hz=60,sn_mva=1)
    hv=pp.create_bus(n,vn_kv=math.sqrt(3)*MV_LN_KV,name=f'EPM_{t.name}_HV_EQ')
    lv=pp.create_bus(n,vn_kv=math.sqrt(3)*LV_LN_KV,name=f'EPM_{t.name}_LV_EQ')
    pp.create_ext_grid(n,hv,vm_pu=1.0,name='IDEALIZED_UPSTREAM_MV_SOURCE')
    kva=t.transformer['kva']
    ti=pp.create_transformer_from_parameters(n,hv,lv,sn_mva=kva*ROOT_FACTOR/1000,
        vn_hv_kv=math.sqrt(3)*MV_LN_KV,vn_lv_kv=math.sqrt(3)*LV_LN_KV,
        vk_percent=3.0,vkr_percent=1.8,pfe_kw=.03*ROOT_FACTOR*kva/5.,
        i0_percent=2.5,shift_degree=0.,name=f'EPM_{t.name}_{kva:g}KVA_PROXY')
    buses={'TRAFO':lv};loads={};lines=[]
    # Split the selected branch so the midpoint option really lies halfway
    # along the longest candidate *electrical path*, even for a one-house star.
    mid_child=None;mid_fraction=None
    if siting=='middle':
        target=t.max_m/2
        for node in t.houses:
            par=t.parent[node]
            parent_d=t.root_dist_m.get(par,0.)
            if parent_d-1e-8<=target<=t.root_dist_m[node]+1e-8:
                # Only use the ancestral route to the farthest house.
                cur=t.farthest;ancestors={cur}
                while t.parent[cur]!='TRAFO':cur=t.parent[cur];ancestors.add(cur)
                if node in ancestors:
                    mid_child=node
                    mid_fraction=max(0.000001,min(.999999,(target-parent_d)/t.lengths_m[node]))
                    break
        if mid_child is None:raise RuntimeError('Cannot locate halfway point')
    def line(a,b,length,name):
        ix=pp.create_line_from_parameters(n,a,b,length_km=length/1000.,
            r_ohm_per_km=LV_R_OHM_KM,x_ohm_per_km=LV_X_OHM_KM,
            c_nf_per_km=0.,max_i_ka=LV_MAX_I_KA,name=name)
        lines.append(ix)
    remaining=set(t.houses)
    mid_bus=None
    while remaining:
        possible=sorted([h for h in remaining if t.parent[h] in buses])
        if not possible:raise RuntimeError('Tree parent cycle')
        for h in possible:
            bus=pp.create_bus(n,vn_kv=math.sqrt(3)*LV_LN_KV,name=h)
            pbus=buses[t.parent[h]];dist=t.lengths_m[h]
            if h==mid_child:
                mid_bus=pp.create_bus(n,vn_kv=math.sqrt(3)*LV_LN_KV,name='PV_BESS_MIDPOINT_TAP')
                line(pbus,mid_bus,dist*mid_fraction,f'{t.parent[h]}_to_mid')
                line(mid_bus,bus,dist*(1-mid_fraction),f'mid_to_{h}')
            else:line(pbus,bus,dist,f'{t.parent[h]}_to_{h}')
            buses[h]=bus
            loads[h]=pp.create_load(n,bus,p_mw=0.,q_mvar=0.,name=h)
            remaining.remove(h)
    invbus={'head':lv,'middle':mid_bus,'end':buses[t.farthest]}[siting]
    inv=pp.create_sgen(n,invbus,p_mw=0.,q_mvar=0.,name='SINGLE_COMBINED_PV_BESS_AC_INVERTER')
    return n,{'traf':ti,'lv':lv,'buses':buses,'load':loads,'line':lines,'inv':inv,
              'inverter_bus':invbus,'inverter_location':siting}


def load_weights(t,mode):
    ids=sorted(t.houses)
    if mode=='equal':return {h:1/len(ids) for h in ids}
    if mode!='far_end_heavy':raise ValueError(mode)
    far=sorted(ids,key=lambda h:t.root_dist_m[h])[-max(1,math.ceil(len(ids)*.25)):]
    near=[h for h in ids if h not in far]
    if not near:return {h:1/len(ids) for h in ids}
    return {h:(.6/len(far) if h in far else .4/len(near)) for h in ids}


def one_hour(n,meta,t,row,pf,allocation,design,inverter_control="unity",inverter_kva=None,fixed_inverter_pf=.98,q_fraction=.48):
    import pandapower as pp
    weights=load_weights(t,allocation)
    demand=float(row.demand_kw);inverter=float(row.inverter_ac_kw)
    qfac=math.tan(math.acos(pf))
    for h,ix in meta['load'].items():
        n.load.at[ix,'p_mw']=demand*weights[h]*ROOT_FACTOR/1000.
        n.load.at[ix,'q_mvar']=demand*weights[h]*qfac*ROOT_FACTOR/1000.
    n.sgen.at[meta['inv'],'p_mw']=inverter*ROOT_FACTOR/1000.
    rec={'timestamp':str(row.timestamp_lst),'trafo':t.name,'houses':len(t.houses),
         'kva':t.transformer['kva'],'design':design,'siting':meta['inverter_location'],
         'allocation':allocation,'pf':pf,'routing':t.routing,'route_factor':t.route_factor,
         'gross_demand_kw':demand,'inverter_ac_kw':inverter,
         'scheduled_net_import_kw':demand-inverter,
         'profile_evidence':row.input_status,'inverter_control':inverter_control,
         'inverter_kva_rating':inverter_kva if design=='optimized' else 0.0}
    try:
        if design!='optimized' and inverter_control!='unity':
            raise ValueError('No inverter capacity has been installed in a gross-load-only design')
        if inverter_control=='unity':
            n.sgen.at[meta['inv'],'q_mvar']=0.0
            pp.runpp(n,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                     max_iteration=75,tolerance_mva=1e-8)
            q_result={'q_kvar':0.0,'iterations':1,'q_cap_kvar':0.0}
        else:
            if inverter_kva is None:raise ValueError('Non-unity Q control requires --inverter-kva from optimized design')
            direction='absorb' if inverter_control=='fixed_pf_absorb' else 'inject'
            mode='fixed_pf' if inverter_control.startswith('fixed_pf') else 'volt_var'
            q_result=solve_inverter_q(n,meta['inv'],meta['inverter_bus'],inverter,inverter_kva,
                 mode=mode,fixed_pf=fixed_inverter_pf,fixed_direction=direction,q_fraction=q_fraction,root_factor=ROOT_FACTOR)
        rec.update(inverter_q_kvar=q_result['q_kvar'],inverter_q_cap_kvar=q_result['q_cap_kvar'],
                   inverter_q_iterations=q_result['iterations'])
        volts={h:float(n.res_bus.at[b,'vm_pu']) for h,b in meta['buses'].items() if h!='TRAFO'}
        worst=min(volts,key=volts.get);best=max(volts,key=volts.get)
        a=float(n.res_ext_grid.p_mw.sum())*1000/ROOT_FACTOR
        b=float(n.res_ext_grid.q_mvar.sum())*1000/ROOT_FACTOR
        pcc=math.hypot(a,b)
        trafo_pct=float(n.res_trafo.at[meta['traf'],'loading_percent'])
        line_pct=float(n.res_line.loc[meta['line'],'loading_percent'].max())
        losses=(float(n.res_line.pl_mw.sum())+float(n.res_trafo.pl_mw.sum()))*1000/ROOT_FACTOR
        rec.update(status='CONVERGED_CONDITIONAL',min_voltage_pu=volts[worst],max_voltage_pu=volts[best],
                   worst_house=worst,best_house=best,transformer_loading_pct=trafo_pct,
                   max_line_loading_pct=line_pct,ac_pcc_kva=pcc,ac_pcc_kw=a,
                   ac_pcc_kvar=b,loss_kw=losses,
                   below_097=int(volts[worst]<.97-1e-7),below_095=int(volts[worst]<.95-1e-7),
                   above_103=int(volts[best]>1.03+1e-7),above_105=int(volts[best]>1.05+1e-7),
                   trafo_over_100=int(trafo_pct>100+1e-7),
                   line_over_100=int(line_pct>100+1e-7),
                   pcc_over_nameplate=int(pcc>t.transformer['kva']+1e-7),
                   pcc_over_90pct=int(pcc>.9*t.transformer['kva']+1e-7),
                   error='')
    except Exception as ex:
        rec.update(status='NOT_CONVERGED',error=str(ex)[:220])
    return rec


def summarize(data):
    keys=['assignment','trafo','houses','kva','design','siting','allocation','pf','routing','route_factor',
          'inverter_control','inverter_kva_rating']
    out=[]
    for group,d in data.groupby(keys,dropna=False,sort=True):
        row=dict(zip(keys,group));good=d[d.status=='CONVERGED_CONDITIONAL'];row['hours_tested']=len(d)
        row['hours_converged']=len(good);row['hours_not_converged']=len(d)-len(good)
        if len(good):
            for c,what,name in [('min_voltage_pu','min','min_voltage_pu'),
                  ('max_voltage_pu','max','max_voltage_pu'),
                  ('transformer_loading_pct','max','max_trafo_pct'),
                  ('max_line_loading_pct','max','max_line_pct'),
                  ('ac_pcc_kva','max','max_pcc_kva'),('loss_kw','sum','summed_loss_kwh'),
                  ('inverter_q_kvar','min','min_inverter_q_kvar'),
                  ('inverter_q_kvar','max','max_inverter_q_kvar')]:
                row[name]=float(getattr(good[c],what)())
            for c in ['below_097','below_095','above_103','above_105','trafo_over_100',
                      'line_over_100','pcc_over_nameplate','pcc_over_90pct']:
                row['hours_'+c]=int(good[c].sum())
            row['worst_house']=str(good.loc[good.min_voltage_pu.idxmin(),'worst_house'])
            row['worst_voltage_hour']=str(good.loc[good.min_voltage_pu.idxmin(),'timestamp'])
        out.append(row)
    return pd.DataFrame(out)


def plot_topology(territories,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=plt.get_cmap('tab10').colors
    fig,ax=plt.subplots(figsize=(11,7),layout='constrained')
    for i,t in enumerate(territories):
        c=colors[i%len(colors)]
        if t.houses:
            nodes={'TRAFO':t.transformer,**t.houses}
            for child,par in t.parent.items():
                a,b=nodes[child],nodes[par]
                ax.plot([a['lon'],b['lon']],[a['lat'],b['lat']],color=c,linewidth=1,alpha=.48,linestyle=':')
            ax.scatter([h['lon'] for h in t.houses.values()], [h['lat'] for h in t.houses.values()],
                       s=47,c=[c],edgecolors='white',linewidths=.6,zorder=4)
            for h,d in t.houses.items():
                ax.annotate(h[1:],(d['lon'],d['lat']),xytext=(4,3),textcoords='offset points',fontsize=7)
        ax.scatter([t.transformer['lon']],[t.transformer['lat']],s=135,c=[c],edgecolors='black',
                   linewidths=.7,marker='*',zorder=5,label=f"{t.name} / {t.transformer['kva']:g} kVA ({len(t.houses)})")
    ax.set(xlabel='Longitude (WGS84)',ylabel='Latitude (WGS84)')
    ax.grid(alpha=.2)
    ax.legend(loc='upper left',bbox_to_anchor=(1,1),fontsize=8,frameon=False)
    # Correct approximate visual aspect for lon-lat at local latitude.
    ax.set_aspect(1/math.cos(math.radians(6.243)),adjustable='datalim')
    output.mkdir(parents=True,exist_ok=True)
    fig.savefig(output/'candidate_topology.png',dpi=210,bbox_inches='tight')
    fig.savefig(output/'candidate_topology.svg',bbox_inches='tight');plt.close(fig)


def write_geojson(territories,output):
    features=[]
    for t in territories:
        features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[t.transformer['lon'],t.transformer['lat']]},
           'properties':{'type':'transformer','id':t.name,'kva':t.transformer['kva'],'evidence':'USER_EPM_RECORD'}})
        nodes={'TRAFO':t.transformer,**t.houses}
        for h,d in t.houses.items():
            features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[d['lon'],d['lat']]},
                  'properties':{'type':'house','id':h,'candidate_transformer':t.name,'verification':'UNCONFIRMED'}})
            par=t.parent[h]
            features.append({'type':'Feature','geometry':{'type':'LineString',
                     'coordinates':[[nodes[par]['lon'],nodes[par]['lat']],[d['lon'],d['lat']]]},
                  'properties':{'type':'HYPOTHETICAL_LV_LINK_NOT_AS_BUILT','transformer':t.name,
                                'from':par,'to':h,'electrical_length_m':round(t.lengths_m[h],2),
                                'geometry_length_multiplier':t.route_factor,'routing':t.routing}})
    output.mkdir(parents=True,exist_ok=True)
    (output/'candidate_feeder_topology.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['preflight','critical','full'],default='preflight')
    ap.add_argument('--assignments',nargs='+',choices=['base','north','h10','h29','all_alternates'],default=['base'])
    ap.add_argument('--trafos',nargs='+',default=TRAFO_ORDER,help='EPM trafo IDs or NORTH_25KVA')
    ap.add_argument('--routing',nargs='+',choices=['mst','star'],default=['mst'])
    ap.add_argument('--distance-factors',nargs='+',type=float,default=[1.3])
    ap.add_argument('--siting',nargs='+',choices=['head','middle','end'],default=['head','middle','end'])
    ap.add_argument('--design',nargs='+',choices=['gross','optimized'],default=['gross','optimized'])
    ap.add_argument('--q-controls',nargs='+',choices=['unity','fixed_pf_inject','fixed_pf_absorb','volt_var'],default=['unity'])
    ap.add_argument('--inverter-kva',type=float,help='Actual rated AC kVA of selected optimized system')
    ap.add_argument('--fixed-inverter-pf',type=float,default=.98)
    ap.add_argument('--q-cap-fraction',type=float,default=.48)
    ap.add_argument('--allocation',nargs='+',choices=['equal','far_end_heavy'],default=['equal'])
    ap.add_argument('--power-factors',nargs='+',type=float,default=[.98,.90])
    ap.add_argument('--input',type=Path,default=DISPATCH_DIR)
    ap.add_argument('--output',type=Path,default=HERE/'outputs'/'geographic_screen')
    ap.add_argument('--top-n',type=int,default=10)
    ap.add_argument('--max-hours',type=int,default=0,help='For quick pipeline testing; do not call the output full-year')
    args=ap.parse_args()
    if any(t not in TRAFO_ORDER for t in args.trafos):ap.error('Unknown trafo ID')
    if any(d<1 for d in args.distance_factors):ap.error('Distance multipliers must be >= 1')
    if any(not 0<pf<=1 for pf in args.power_factors):ap.error('Invalid PF')
    if args.max_hours<0:ap.error('--max-hours must be >=0')
    if not 0<args.fixed_inverter_pf<=1:ap.error('--fixed-inverter-pf must be (0,1]')
    if not 0<=args.q_cap_fraction<=1:ap.error('--q-cap-fraction must be [0,1]')
    if any(c!='unity' for c in args.q_controls):
        if args.inverter_kva is None or args.inverter_kva<=0:ap.error('Non-unity control requires --inverter-kva')
        if 'gross' in args.design:ap.error('Use --design optimized when testing inverter Q control')
    args.output.mkdir(parents=True,exist_ok=True)
    topo=[];rows=[];cache={};skips=[]
    for assignment in args.assignments:
        for routing in args.routing:
            for factor in args.distance_factors:
                territories=build_territories(assignment,routing,factor)
                topo.extend(evidence_rows(territories,assignment))
                if args.mode=='preflight' and assignment==args.assignments[0] and routing==args.routing[0] and factor==args.distance_factors[0]:
                    plot_topology(territories,args.output);write_geojson(territories,args.output)
                if args.mode=='preflight':continue
                try:import pandapower as pp
                except ImportError as ex:raise SystemExit('Install pandapower in Miniforge first: python -m pip install pandapower') from ex
                for t in territories:
                    if t.name not in args.trafos or not t.houses:continue
                    for design in args.design:
                        df,evidence=load_profile(len(t.houses),design,args.input,cache)
                        if df is None:
                            skips.append({'assignment':assignment,'transformer':t.name,'houses':len(t.houses),
                                         'design':design,'reason':evidence})
                            continue
                        ix=stress_hours(df,args.top_n) if args.mode=='critical' else list(range(len(df)))
                        if args.max_hours:ix=ix[:args.max_hours]
                        for site in args.siting:
                            n,meta=create_net(t,site)
                            for alloc in args.allocation:
                                for pf in args.power_factors:
                                  for control in args.q_controls:
                                    print(f'{control} {assignment} {t.name}: {len(t.houses)} houses, {design}, {routing} x{factor:g}, {site}, {alloc}, pf {pf}, {len(ix)} hours',flush=True)
                                    for j in ix:
                                        r=one_hour(n,meta,t,df.iloc[j],pf,alloc,design,control,args.inverter_kva,
                                                   args.fixed_inverter_pf,args.q_cap_fraction)
                                        r['assignment']=assignment
                                        rows.append(r)
    pd.DataFrame(topo).drop_duplicates().to_csv(args.output/'candidate_territory_summary.csv',index=False)
    if args.mode=='preflight':
        print(pd.DataFrame(topo).to_string(index=False));print('PRE-FLIGHT ONLY, no power-flow simulations run')
        return
    if not rows:
        raise SystemExit('No AC cases executed. Check dispatch inputs and skipped cases.')
    result=pd.DataFrame(rows);summary=summarize(result)
    result.to_csv(args.output/'ac_hourly_or_critical.csv',index=False)
    summary.to_csv(args.output/'ac_scenario_summary.csv',index=False)
    pd.DataFrame(skips,columns=['assignment','transformer','houses','design','reason']).to_csv(args.output/'skipped_optimized_cases.csv',index=False)
    manifest={'status':'AC_EXECUTED_CONDITIONAL_TOPOLOGY',
        'warning':'Not as-built. House-to-transformer assignments, links and equipment impedances unverified.',
        'mode':args.mode,'time_coverage':'FULL_8760_EACH' if args.mode=='full' and not args.max_hours else 'SUBSET_ONLY',
        'source_dispatch_dir':str(args.input),'counts':{'scenario_hours':len(result),
             'converged':int((result.status=='CONVERGED_CONDITIONAL').sum()),
             'not_converged':int((result.status!='CONVERGED_CONDITIONAL').sum())},
        'transformer_names':args.trafos,'assignment_modes':args.assignments,
        'routing_hypotheses':args.routing,'route_length_multipliers':args.distance_factors,
        'pf_values':args.power_factors,'design_variants':args.design,'siting':args.siting,
        'lv_ohm_per_km':{'loop_R':LV_R_OHM_KM,'loop_X':LV_X_OHM_KM},
        'max_line_current_ka_proxy':LV_MAX_I_KA,
        'transformer_impedance_assumed':{'vk_percent':3.0,'vkr_percent':1.8},
        'model_equivalence':'balanced 3ph equivalent with sqrt(3) line voltage and x3 power of 240V 1ph single-phase',
        'upstream':'ideal voltage source, MV feeder impedance excluded',
        'load_allocation':'Equal or farthest 25% assigned 60% for stress; no measured meter profiles',
        'inverter':'one combined PV+BESS, fixed PyPSA P dispatch; Q according to selected control with S and Q limits',
        'inverter_q_controls':args.q_controls,'inverter_kva':args.inverter_kva,
        'fixed_inverter_pf':args.fixed_inverter_pf,'q_cap_fraction':args.q_cap_fraction,
        'distinct_source_limit':'transformers modeled individually, no interconnection of their LV networks',
        'pandapower_version':pp.__version__,'skipped_cases':skips}
    (args.output/'validation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('\nSaved:',args.output.resolve())
    print(summary[['trafo','houses','design','siting','pf','hours_tested','hours_converged','min_voltage_pu','max_trafo_pct']].to_string(index=False))

if __name__=='__main__':main()
