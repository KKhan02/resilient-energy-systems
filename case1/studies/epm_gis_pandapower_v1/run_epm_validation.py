#!/usr/bin/env python3
"""Geographic EPM LV topology + assumed service drops + HIL Q(V) in pandapower.

Never claims verified customer metering, phases, conductor impedances or grid code compliance.
"""
import argparse,csv,json,math,sys
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd
from epm_topology import (read_data,infer_assignments,build_territory,
    conductor_params,farthest_house,split_for_middle)
from hil_voltvar import HILParams,solve_q,capability_kvar
from transformer_q_guard import enforce_transformer_limit

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
DISPATCH=REPO/'case1'/'studies'/'pandapower_dispatch_validation_v1'/'input'/'dispatch'
ROOT_FACTOR=3.0
MV_V_KV=math.sqrt(3)*7.621
LV_V_KV=math.sqrt(3)*.240
# Archived one-phase 240/120 V equipment approximated by a balanced 3-phase network.
# The balanced equivalent is NOT a model of actual split-phase imbalance or neutral currents.


def load_dispatch(base,h,design,cache):
    for p in (base/f'{h}_homes_hourly_dispatch.csv',base/f'{h}_homes'/'hourly_dispatch.csv'):
        if p.exists():break
    else:p=None
    if p is not None:
        if h not in cache:
            d=pd.read_csv(p)
            required=['timestamp_lst','demand_kw','inverter_ac_kw','grid_import_kw','grid_export_kw']
            if len(d)!=8760 or not all(c in d for c in required):raise ValueError(f'bad hourly file: {p}')
            d['timestamp_lst']=pd.to_datetime(d['timestamp_lst'])
            if d.timestamp_lst.isna().any() or d.timestamp_lst.duplicated().any():raise ValueError('bad timestamps')
            if not np.allclose(d.demand_kw-d.inverter_ac_kw,d.grid_import_kw-d.grid_export_kw,atol=.002):
                raise ValueError('PyPSA dispatch mismatch: '+str(p))
            cache[h]=d.sort_values('timestamp_lst').reset_index(drop=True)
        d=cache[h].copy()
        if design=='gross': d['inverter_ac_kw']=0.
        return d,'OPTIMIZED_DISPATCH' if design=='optimized' else 'COUNT_MATCHED_SYNTHETIC_GROSS'
    if design=='optimized':return None,'NO_EXACT_HOURLY_DISPATCH'
    # One to four homes: scale a five-house synthetic household aggregate.
    if h>4:return None,'MISSING_SYNTHETIC_GROSS_PROFILE'
    d,_=load_dispatch(base,5,'gross',cache)
    if d is None:return None,'NO_FIVE_HOUSE_BASELINE'
    d['demand_kw']*=h/5.
    return d,'FIVE_HOUSE_GROSS_SCALED'


def critical_indices(df,n=10):
    ix={0,len(df)-1}
    for col in ('demand_kw','inverter_ac_kw','grid_import_kw'):
        vals=df[col].to_numpy(float)
        ix.update(np.argsort(vals)[-n:].tolist())
        ix.update(np.argsort(vals)[:2].tolist())
    if 'battery_soc_usable_kwh' in df:
        ix.update(np.argsort(df['battery_soc_usable_kwh'].to_numpy(float))[:n].tolist())
    for month in (1,7,11):
        dd=df[df.timestamp_lst.dt.month==month]
        if len(dd):ix.add(int(dd.demand_kw.idxmax()))
    return sorted(ix)


def build_net(territory,siting):
    import pandapower as pp
    g=territory.graph.copy();end=farthest_house(territory)
    if siting=='head':inv_node=territory.root
    elif siting=='middle':inv_node=split_for_middle(g,territory.root,end)
    elif siting=='end':inv_node=end
    else:raise ValueError('bad siting')
    n=pp.create_empty_network(name='EPM_GIS_ASSUMED_HOUSES_'+territory.trafo['identifier'],f_hz=60,sn_mva=1)
    hv=pp.create_bus(n,vn_kv=MV_V_KV,name='IDEALIZED_MV_SOURCE')
    buses={node:pp.create_bus(n,vn_kv=LV_V_KV,name=node) for node in sorted(g)}
    pp.create_ext_grid(n,hv,vm_pu=1.)
    kva=territory.trafo['kva']
    tr=pp.create_transformer_from_parameters(n,hv,buses[territory.root],
        sn_mva=kva*ROOT_FACTOR/1000.,vn_hv_kv=MV_V_KV,vn_lv_kv=LV_V_KV,
        vk_percent=3.,vkr_percent=1.8,pfe_kw=.03*ROOT_FACTOR*kva/5.,
        i0_percent=2.5,shift_degree=0.,name='ASSUMED_TRAFO_IMPEDANCE_'+territory.trafo['identifier'])
    line_ids=[];fallback=[]
    for a,b,d in sorted(g.edges(data=True),key=lambda v:(v[2]['kind'],v[2]['source_fid'],v[0],v[1])):
        r,x,amp,known=conductor_params('AAC','4') if d['kind']=='assumed_service' else conductor_params(d['material'],d['calibre'])
        if not known:fallback.append(str(d['material'])+'/'+str(d['calibre']))
        li=pp.create_line_from_parameters(n,buses[a],buses[b],length_km=d['length_m']/1000.,
             r_ohm_per_km=r,x_ohm_per_km=x,c_nf_per_km=0.,max_i_ka=amp,
             name=d['kind']+'_'+d['source_fid'])
        line_ids.append(li)
    loads={a['house']:pp.create_load(n,buses['HOUSE_'+a['house']],p_mw=0.,q_mvar=0.,name=a['house'])
           for a in territory.attachments}
    inv=pp.create_sgen(n,buses[inv_node],p_mw=0.,q_mvar=0.,name='COMBINED_PV_BESS')
    dist=nx.single_source_dijkstra_path_length(g,territory.root,weight='length_m')
    return n,dict(trafo=tr,inv=inv,inv_bus=buses[inv_node],loads=loads,
                  buses=buses,line_ids=line_ids,graph=g,dist=dist,
                  node=inv_node,fallback_conductors=sorted(set(fallback)))


def weights(meta,allocation):
    hs=sorted(meta['loads']);n=len(hs)
    if allocation=='equal':return {h:1/n for h in hs}
    if allocation!='far_end_heavy':raise ValueError('bad allocation')
    far=sorted(hs,key=lambda h:meta['dist']['HOUSE_'+h])[-max(1,math.ceil(n*.25)):]
    near=[h for h in hs if h not in far]
    if not near:return {h:1/n for h in hs}
    return {h:(.6/len(far) if h in far else .4/len(near)) for h in hs}


def simulate_hour(net,meta,terr,row,pf,allocation,design,qmode,params,inverter_pf,inverter_direction,s_kva,p_inst_kw,guard_mode="off",guard_limit_pct=100.,guard_points=33):
    import pandapower as pp
    demand=float(row.demand_kw);p=float(row.inverter_ac_kw)
    w=weights(meta,allocation);qfac=math.tan(math.acos(pf))
    for h,index in meta['loads'].items():
        net.load.at[index,'p_mw']=demand*w[h]*ROOT_FACTOR/1000.
        net.load.at[index,'q_mvar']=demand*w[h]*qfac*ROOT_FACTOR/1000.
    net.sgen.at[meta['inv'],'p_mw']=p*ROOT_FACTOR/1000.
    rec=dict(timestamp=str(row.timestamp_lst),trafo=terr.trafo['identifier'],houses=len(terr.attachments),
             design=design,placement=meta['node'],allocation=allocation,load_pf=pf,
             control=qmode,gross_demand_kw=demand,inverter_p_kw=p,inverter_rating_kva=s_kva,
             q_ratio=params.q_ratio,inverter_installed_active_kw=p_inst_kw,
             trafo_guard=guard_mode,trafo_guard_limit_pct=guard_limit_pct)
    try:
        if p>s_kva+1e-6:raise ValueError(f'P {p:.3f} kW > inverter apparent rating {s_kva:.3f} kVA')
        q,v_local,iters=solve_q(net,meta['inv'],meta['inv_bus'],p,s_kva,p_inst_kw,
                       qmode,params,ROOT_FACTOR,inverter_pf,inverter_direction)
        q_requested=q
        unguarded_loading=float(net.res_trafo.at[meta['trafo'],'loading_percent'])
        guard_status='OFF';guard_feasible=(unguarded_loading<=guard_limit_pct+1e-5)
        guard_evaluations=0;guard_unity_loading=float('nan')
        if guard_mode=='enforce' and unguarded_loading>guard_limit_pct+1e-5:
            def measured_loading(q_test):
                net.sgen.at[meta['inv'],'q_mvar']=q_test*ROOT_FACTOR/1000.
                pp.runpp(net,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                         max_iteration=75,tolerance_mva=1e-8)
                return float(net.res_trafo.at[meta['trafo'],'loading_percent'])
            choice=enforce_transformer_limit(q_requested,measured_loading,
                                          max_loading_pct=guard_limit_pct,
                                          sample_points=guard_points)
            q=choice.q_kvar
            # Restore final AC results even if guard search ended at another trial Q.
            measured_loading(q)
            guard_status=choice.status
            guard_feasible=choice.can_enforce
            guard_evaluations=choice.evaluations
            guard_unity_loading=choice.unity_loading_pct
        elif guard_mode=='enforce':
            guard_status='REQUEST_ACCEPTED'
        rec.update(q_requested_kvar=q_requested,trafo_loading_before_guard_pct=unguarded_loading,
                   trafo_loading_after_guard_pct=float(net.res_trafo.at[meta['trafo'],'loading_percent']),
                   q_reduced_kvar=abs(q_requested-q),guard_status=guard_status,
                   guard_feasible=guard_feasible,guard_evaluations=guard_evaluations,
                   guard_unity_loading_pct=guard_unity_loading)
        nodes=[meta['buses']['HOUSE_'+h] for h in meta['loads']]
        volts=net.res_bus.loc[nodes,'vm_pu'].astype(float)
        p_ext=float(net.res_ext_grid.p_mw.sum())*1000./ROOT_FACTOR
        q_ext=float(net.res_ext_grid.q_mvar.sum())*1000./ROOT_FACTOR
        pcc=math.hypot(p_ext,q_ext)
        loading=float(net.res_trafo.at[meta['trafo'],'loading_percent'])
        line_load=float(net.res_line.loc[meta['line_ids'],'loading_percent'].max())
        losses=(float(net.res_line.pl_mw.sum())+float(net.res_trafo.pl_mw.sum()))*1000./ROOT_FACTOR
        rec.update(status='CONVERGED_ASSUMPTION_ONLY',min_voltage_pu=volts.min(),max_voltage_pu=volts.max(),
            min_voltage_house=next(k for k in meta['loads'] if meta['buses']['HOUSE_'+k]==int(volts.idxmin())),
            max_voltage_house=next(k for k in meta['loads'] if meta['buses']['HOUSE_'+k]==int(volts.idxmax())),
            local_inverter_voltage_pu=v_local,inverter_q_kvar=q,inverter_q_headroom_kvar=capability_kvar(p,s_kva,p_inst_kw,params),
            iterations=iters,trafo_loading_pct=loading,max_line_loading_pct=line_load,
            ac_pcc_kva=pcc,ac_pcc_kw=p_ext,ac_pcc_kvar=q_ext,loss_kw=losses,
            v_below_097=int(volts.min()<.97-1e-7),v_below_095=int(volts.min()<.95-1e-7),
            v_above_103=int(volts.max()>1.03+1e-7),v_above_105=int(volts.max()>1.05+1e-7),
            trafo_over100=int(loading>100+1e-7),line_over100=int(line_load>100+1e-7),
            pcc_over_kva=int(pcc>terr.trafo['kva']+1e-7),error='')
    except Exception as e:
        rec.update(status='FAILED_OR_UNSETTLED',error=str(e)[:200])
    return rec


def summarize(df,keys):
    good=df[df.status=='CONVERGED_ASSUMPTION_ONLY']
    if good.empty:return pd.DataFrame()
    summary=good.groupby(keys,dropna=False).agg(hours=('timestamp','size'),
            min_v=('min_voltage_pu','min'),max_v=('max_voltage_pu','max'),
            max_trafo_pct=('trafo_loading_pct','max'),max_line_pct=('max_line_loading_pct','max'),
            max_pcc_kva=('ac_pcc_kva','max'),max_abs_q_kvar=('inverter_q_kvar',lambda x:abs(x).max()),
            below_097=('v_below_097','sum'),below_095=('v_below_095','sum'),
            above_103=('v_above_103','sum'),above_105=('v_above_105','sum'),
            trafo_over100_hours=('trafo_over100','sum'),pcc_over_kva_hours=('pcc_over_kva','sum'),
            avg_loss_kw=('loss_kw','mean'),
            guard_limited_hours=('guard_status',lambda x:int((x=='Q_REDUCED_TO_HOLD_TRAFO_LIMIT').sum())),
            guard_unresolved_hours=('guard_feasible',lambda x:int((~x.astype(bool)).sum())),
            max_q_reduction_kvar=('q_reduced_kvar','max'),
            avg_q_reduction_kvar=('q_reduced_kvar','mean'),
            max_unguarded_trafo_pct=('trafo_loading_before_guard_pct','max')).reset_index()
    failed=df[df.status!='CONVERGED_ASSUMPTION_ONLY'].groupby(keys,dropna=False).size().rename('failed_hours')
    summary=summary.merge(failed.reset_index(),how='left',on=keys).fillna({'failed_hours':0})
    summary['strict_pass']=(summary.min_v>=.97)&(summary.max_v<=1.03)&(summary.max_trafo_pct<=100)&(summary.max_line_pct<=100)&(summary.failed_hours==0)
    return summary


def preflight(houses,trafos,lv,ass,folder,policy):
    folder.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(ass).to_csv(folder/'house_assignments.csv',index=False)
    rows=[];attach=[];edges=[];skips=[]
    for t in trafos:
        if t=='92395':
            skips.append(dict(trafo=t,reason='EPM_GIS_EXPORT_HAS_ZERO_LV_SECTIONS'))
            continue
        terr=build_territory(t,houses,trafos,lv,ass,1.)
        if terr is None:skips.append(dict(trafo=t,reason='NO_LV_FEATURES'));continue
        rows.append(terr.metrics());attach.extend(terr.attachments)
        for a,b,d in terr.graph.edges(data=True):
            edges.append(dict(trafo=t,from_node=a,to_node=b,length_m=d['length_m'],
                    kind=d['kind'],gis_segment=d['source_fid'],material=d['material'],calibre=d['calibre']))
    pd.DataFrame(rows).to_csv(folder/'territory_topology.csv',index=False)
    pd.DataFrame(attach).to_csv(folder/'house_service_assumptions.csv',index=False)
    pd.DataFrame(edges).to_csv(folder/'network_edges.csv',index=False)
    pd.DataFrame(skips,columns=['trafo','reason']).to_csv(folder/'missing_topologies.csv',index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    if skips:print('Gaps:',skips)
    print('House assignments:',len(ass),'changes:',sum(a['changed'] for a in ass))
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['preflight','critical','full'],default='preflight')
    ap.add_argument('--assignment',choices=['base','nearest_mapped'],default='base',
                    help='base keeps user supply hypothesis; nearest_mapped overrides by nearest LV of five identified trafos')
    ap.add_argument('--trafos',nargs='+',default=['94022','106039','113699','85398','98380'])
    ap.add_argument('--design',nargs='+',choices=['gross','optimized'],default=['gross','optimized'])
    ap.add_argument('--siting',nargs='+',choices=['head','middle','end'],default=['head','middle','end'])
    ap.add_argument('--q-controls',nargs='+',choices=['unity','fixed_pf_inject','fixed_pf_absorb','volt_var'],default=['unity','fixed_pf_inject','fixed_pf_absorb','volt_var'])
    ap.add_argument('--power-factors',nargs='+',type=float,default=[.98])
    ap.add_argument('--allocation',nargs='+',choices=['equal','far_end_heavy'],default=['equal'])
    ap.add_argument('--service-factors',nargs='+',type=float,default=[1.,1.3,1.6])
    ap.add_argument('--q-ratios',nargs='+',type=float,default=[.48])
    ap.add_argument('--fixed-inverter-pf',type=float,default=.98)
    ap.add_argument('--trafo-guards',nargs='+',choices=['off','enforce'],default=['off'],
                    help='Compare original Q controller with transformer-aware Q curtailment')
    ap.add_argument('--trafo-max-loading-pct',type=float,default=100.,
                    help='Thermal limit; default 100 percent of nominal transformer kVA')
    ap.add_argument('--trafo-guard-points',type=int,default=33,
                    help='Grid samples along zero to requested Q before feasibility refinement')
    ap.add_argument('--inverters',nargs='+',default=['94022:10','106039:12'],
                    help='inverter kVA by transformer, e.g. 94022:10 106039:12; no unverified default for others')
    ap.add_argument('--p-installed',nargs='+',default=[],help='installed active-power rating by trafo e.g. 94022:9.5; default assumes P_inst=S_kVA')
    ap.add_argument('--input',type=Path,default=DISPATCH)
    ap.add_argument('--output',type=Path,default=HERE/'outputs'/'epm_screen')
    ap.add_argument('--top-n',type=int,default=10)
    ap.add_argument('--max-hours',type=int,default=0)
    args=ap.parse_args()
    if any(not 0<x<=1 for x in args.power_factors):ap.error('load PF must be 0..1')
    if any(not 0<=r<=1 for r in args.q_ratios):ap.error('Q ratio outside 0..1')
    if any(k<1 for k in args.service_factors):ap.error('service factors >=1 only')
    if args.max_hours<0:ap.error('negative max hours')
    if not 0<args.trafo_max_loading_pct<=200:ap.error('invalid transformer limit')
    if args.trafo_guard_points<5:ap.error('trafo-guard-points must be at least 5')
    inverters={}
    for s in args.inverters:
        key,sep,val=s.partition(':')
        if not sep or float(val)<=0:ap.error('inverter rating syntax TRAFO:kVA required')
        inverters[key]=float(val)
    p_installed={}
    for spec in args.p_installed:
        key,sep,val=spec.partition(':')
        if not sep or float(val)<0:ap.error('--p-installed requires TRAFO:kW')
        p_installed[key]=float(val)
    houses,trafos,lv=read_data();ass=infer_assignments(houses,trafos,lv,args.assignment)
    if any(t not in trafos for t in args.trafos):ap.error('unknown trafo')
    args.output.mkdir(parents=True,exist_ok=True)
    preflight(houses,trafos,lv,ass,args.output,args.assignment)
    if args.mode=='preflight':return
    try:import pandapower as pp
    except ImportError as ex:raise SystemExit('pandapower required: conda install -c conda-forge pandapower') from ex
    records=[];skips=[];cache={};tot=0
    for t in args.trafos:
        if t=='92395':
            skips.append(dict(trafo=t,reason='NO_EPM_LV_GRAPH'))
            continue
        if not any(a['transformer']==t for a in ass):continue
        for factor in args.service_factors:
            terr=build_territory(t,houses,trafos,lv,ass,factor)
            for design in args.design:
                d,source=load_dispatch(args.input,len(terr.attachments),design,cache)
                if d is None:
                    skips.append(dict(trafo=t,design=design,reason=source));continue
                indices=critical_indices(d,args.top_n) if args.mode=='critical' else range(len(d))
                if args.max_hours:indices=list(indices)[:args.max_hours]
                for siting in args.siting:
                    net,meta=build_net(terr,siting)
                    for alloc in args.allocation:
                        for pf in args.power_factors:
                            for control in args.q_controls:
                                for qratio in args.q_ratios:
                                    if design=='gross' and control!='unity':continue # no inverter, no reactive support
                                    if design=='optimized' and t not in inverters:
                                        skips.append(dict(trafo=t,design=design,reason='INVERTER_RATING_NOT_SUPPLIED'));continue
                                    if design=='gross':rating=max(inverters.get(t,0.),.001)
                                    else:rating=inverters[t]
                                    installed_kw=p_installed.get(t,rating) if design=='optimized' else 0.
                                    params=HILParams(q_ratio=qratio)
                                    qmode='fixed_pf' if control.startswith('fixed_pf') else control
                                    direction='absorb' if control=='fixed_pf_absorb' else 'inject'
                                    for guard_mode in args.trafo_guards:
                                        print(f'{t} {len(terr.attachments)} houses {design} {siting} service x{factor} pf {pf} {control} QRATIO {qratio} GUARD {guard_mode} hours {len(indices)}',flush=True)
                                        for ix in indices:
                                            rec=simulate_hour(net,meta,terr,d.iloc[ix],pf,alloc,design,qmode,params,args.fixed_inverter_pf,direction,rating,installed_kw,
                                                guard_mode,args.trafo_max_loading_pct,args.trafo_guard_points)
                                            rec.update(assignment=args.assignment,service_factor=factor,source_dispatch=source,
                                                       siting=siting,q_control_label=control)
                                            records.append(rec)
    pd.DataFrame(skips,columns=['trafo','design','reason']).to_csv(args.output/'skipped_cases.csv',index=False)
    if not records:raise SystemExit('No cases executed; check --input and --design')
    df=pd.DataFrame(records)
    df.to_csv(args.output/'ac_hours.csv',index=False)
    group=['trafo','houses','design','assignment','service_factor','siting','allocation','load_pf','q_control_label','q_ratio','trafo_guard']
    summary=summarize(df,group)
    summary.to_csv(args.output/'ac_scenario_summary.csv',index=False)
    manifest=dict(method='EPM LV GIS node graph + assumed household drops',
        matched_lv_nodes='5 existing assets; 92395 absent from GIS LV export',
        house_assignment=args.assignment,assumption='nearest EPM LV geometry DOES NOT prove customer electrical supply',
        conductor_registry='explicit screening proxies for loop R/X and ampacity, not measured EPM data',
        q_control='HIL U1=.96 U2=.99 U3=1.01 U4=1.04; Qmax=q_ratio*P_inst bounded by inverter S circle',
        q_dynamics='T95=10 s available in code; steady-state for hourly AC flow',
        pv_storage='single combined inverter, fixed hourly active dispatch, no AC energy redispatch',
        trafo_guard=dict(modes=args.trafo_guards,limit_loading_pct=args.trafo_max_loading_pct,
                         samples=args.trafo_guard_points,
                         policy='limit Q along zero-to-requested control direction; keep P and loads unchanged; flag infeasible'),
        source_impedance='ideal upstream MV; 3-phase equivalent x3 one-phase power',
        mode=args.mode,counts=dict(hypothesis_hours=len(df),converged=int((df.status=='CONVERGED_ASSUMPTION_ONLY').sum()),
             failed=int((df.status!='CONVERGED_ASSUMPTION_ONLY').sum())),pandapower_version=pp.__version__,
        inverter_nameplate_kva=inverters,installed_active_kw_overrides=p_installed,skipped_cases=skips)
    (args.output/'validation_manifest.json').write_text(json.dumps(manifest,indent=2,default=str)+'\n')
    print('Results:',args.output,'AC rows',len(df),'successful',manifest['counts']['converged'])

if __name__=='__main__':main()
