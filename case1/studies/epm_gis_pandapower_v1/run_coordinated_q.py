#!/usr/bin/env python3
"""EPM LV GIS AC-feasibility feedback with continuous Q-ratio sensitivity.

Requires existing geographic EPM package and 8760-hour optimized dispatch.
No new PV/BESS capacity search. An hourly Q-only controller cannot assure
SOC-consistent full-year redispatch or certify the real network.
"""
import argparse,csv,json,math
from pathlib import Path
import pandas as pd
import numpy as np
from epm_topology import read_data,infer_assignments,build_territory
from run_epm_validation import (HERE,DISPATCH,ROOT_FACTOR,build_net,load_dispatch,
                                weights,critical_indices,preflight)
from hil_voltvar import HILParams,solve_q,capability_kvar
from coordinated_q_control import (ACLimits,ACPoint,choose_q,build_ratio_grid,
                                   feasible,margin,violations)


def run_hour(net,meta,territory,row,pf,allocation,siting,qratio,policy,limits,
             nameplate_kva,installed_p_kw,grid_points,refine):
    import pandapower as pp
    p=float(row.inverter_ac_kw);demand=float(row.demand_kw)
    rec=dict(trafo=territory.trafo['identifier'],houses=len(territory.attachments),
        timestamp=str(row.timestamp_lst),siting=siting,load_pf=pf,
        allocation=allocation,q_ratio=qratio,policy=policy,
        load_kw=demand,p_inverter_kw=p,inverter_kva=nameplate_kva,
        installed_active_kw=installed_p_kw)
    # Stable CSV schema even when the first AC solve fails.
    rec.update({k:None for k in ('q_requested_kvar','q_selected_kvar','q_capability_kvar',
        'q_changed_kvar','ac_feasible','controller_status','ac_evaluations','control_iterations',
        'min_v_pu','max_v_pu','max_trafo_pct','max_line_pct','loss_kw','pcc_kva',
        'voltage_margin_pu','trafo_margin_pct','v_below_097','v_above_103',
        'trafo_over_limit','line_over_limit','v_lower_violation_pu',
        'v_upper_violation_pu','trafo_over_pct','max_normalized_violation','error')})
    try:
        if abs(p)>nameplate_kva+1e-6:raise ValueError('Active inverter power exceeds apparent rating')
        share=weights(meta,allocation);qfac=math.tan(math.acos(pf))
        for house,idx in meta['loads'].items():
            net.load.at[idx,'p_mw']=ROOT_FACTOR*demand*share[house]/1000.
            net.load.at[idx,'q_mvar']=ROOT_FACTOR*demand*share[house]*qfac/1000.
        net.sgen.at[meta['inv'],'p_mw']=ROOT_FACTOR*p/1000.
        hp=HILParams(q_ratio=qratio)
        cap=capability_kvar(p,nameplate_kva,installed_p_kw,hp)
        q_hil,vlocal,iters=solve_q(net,meta['inv'],meta['inv_bus'],p,nameplate_kva,
                                   installed_p_kw,'volt_var',hp,ROOT_FACTOR)
        cache={}
        def measure(q):
            key=round(q,11)
            if key not in cache:
                net.sgen.at[meta['inv'],'q_mvar']=ROOT_FACTOR*q/1000.
                pp.runpp(net,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                         max_iteration=75,tolerance_mva=1e-8)
                vs=net.res_bus.loc[[meta['buses']['HOUSE_'+h] for h in meta['loads']],'vm_pu'].astype(float)
                loading=float(net.res_trafo.at[meta['trafo'],'loading_percent'])
                lines=float(net.res_line.loc[meta['line_ids'],'loading_percent'].max())
                losses=(float(net.res_line.pl_mw.sum())+float(net.res_trafo.pl_mw.sum()))*1000/ROOT_FACTOR
                extp=float(net.res_ext_grid.p_mw.sum())*1000/ROOT_FACTOR
                extq=float(net.res_ext_grid.q_mvar.sum())*1000/ROOT_FACTOR
                cache[key]=ACPoint(q,vs.min(),vs.max(),loading,lines,losses,math.hypot(extp,extq))
            return cache[key]
        if policy=='unity':q=0.;choice=None
        elif policy=='hil':q=q_hil;choice=None
        elif policy=='coordinated':
            choice=choose_q(measure,cap,q_hil,limits,grid_points,refine)
            q=choice.point.q_kvar
        else:raise ValueError('Unknown policy')
        pt=measure(q)
        # The AC graph must end at the selected Q, not an intermediate sampled point.
        net.sgen.at[meta['inv'],'q_mvar']=ROOT_FACTOR*q/1000.
        pp.runpp(net,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                 max_iteration=75,tolerance_mva=1e-8)
        op=feasible(pt,limits)
        vm,tm=margin(pt,limits)
        v=violations(pt,limits)
        rec.update(status='CONVERGED',q_requested_kvar=q_hil,q_selected_kvar=q,
            q_capability_kvar=cap,q_changed_kvar=q-q_hil,
            ac_feasible=op,controller_status=(choice.status if choice else ('BASELINE_AC_FEASIBLE' if op else 'BASELINE_AC_VIOLATION')),
            ac_evaluations=len(cache)+iters,control_iterations=iters,
            min_v_pu=pt.v_min,max_v_pu=pt.v_max,
            max_trafo_pct=pt.trafo_pct,max_line_pct=pt.line_pct,
            loss_kw=pt.loss_kw,pcc_kva=pt.pcc_kva,
            voltage_margin_pu=vm,trafo_margin_pct=tm,
            v_below_097=int(pt.v_min<limits.min_v-1e-6),
            v_above_103=int(pt.v_max>limits.max_v+1e-6),
            trafo_over_limit=int(pt.trafo_pct>limits.max_trafo_pct+1e-4),
            line_over_limit=int(pt.line_pct>limits.max_line_pct+1e-4),
            v_lower_violation_pu=max(0.,limits.min_v-pt.v_min),
            v_upper_violation_pu=max(0.,pt.v_max-limits.max_v),
            trafo_over_pct=max(0.,pt.trafo_pct-limits.max_trafo_pct),
            max_normalized_violation=max(v),error='')
    except Exception as exc:
        rec.update(status='AC_FAILURE',ac_feasible=False,controller_status='AC_FAILED',error=str(exc)[:230])
    return rec


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--mode',choices=['critical','full'],default='critical')
    a.add_argument('--trafos',nargs='+',default=['94022','106039'])
    a.add_argument('--siting',nargs='+',choices=['head','middle','end'],default=['head','middle'])
    a.add_argument('--power-factors',type=float,nargs='+',default=[.98])
    a.add_argument('--allocation',choices=['equal','far_end_heavy'],default='equal')
    a.add_argument('--service-factors',type=float,nargs='+',default=[1.0])
    a.add_argument('--policies',nargs='+',choices=['unity','hil','coordinated'],default=['unity','hil','coordinated'])
    a.add_argument('--q-start',type=float,default=0.0)
    a.add_argument('--q-max',type=float,default=.60)
    a.add_argument('--q-step',type=float,default=.10)
    a.add_argument('--q-extra',nargs='*',type=float,default=[.25,.48])
    a.add_argument('--q-ratios',nargs='+',type=float,default=None,help='Override grid with explicit Q ratio list')
    a.add_argument('--q-grid-points',type=int,default=21)
    a.add_argument('--q-refine',type=int,default=2)
    a.add_argument('--vmin',type=float,default=.97)
    a.add_argument('--vmax',type=float,default=1.03)
    a.add_argument('--trafo-limit-pct',type=float,default=100.)
    a.add_argument('--line-limit-pct',type=float,default=100.)
    a.add_argument('--inverters',nargs='+',default=['94022:10','106039:12'])
    a.add_argument('--p-installed',nargs='+',default=[],help='Use actual P_inst where known, otherwise P_inst=S_kVA assumption')
    a.add_argument('--assignment',choices=['base','nearest_mapped'],default='base')
    a.add_argument('--input',type=Path,default=DISPATCH)
    a.add_argument('--output',type=Path,default=HERE/'outputs'/'coordinated_q_critical')
    a.add_argument('--max-hours',type=int,default=0)
    a.add_argument('--top-n',type=int,default=10)
    args=a.parse_args()
    try:
        lim=ACLimits(args.vmin,args.vmax,args.trafo_limit_pct,args.line_limit_pct)
        ratios=build_ratio_grid(args.q_start,args.q_max,args.q_step,args.q_extra) if args.q_ratios is None else sorted(set(args.q_ratios))
        for r in ratios:
            if not 0<=r<=1:raise ValueError('Invalid Q ratio')
        if any(not 0<pf<=1 for pf in args.power_factors):raise ValueError('Invalid load power factor')
        if any(x<1 for x in args.service_factors):raise ValueError('Service factor below 1')
        if args.max_hours<0:raise ValueError('Negative max hours')
        if args.q_grid_points<5:raise ValueError('q-grid-points below 5')
        inverters={k:float(v) for k,v in (entry.split(':') for entry in args.inverters)}
        p_install={k:float(v) for k,v in (entry.split(':') for entry in args.p_installed)}
        if any(x<=0 for x in inverters.values()):raise ValueError('Invalid inverter kVA')
    except (ValueError,TypeError) as ex:a.error(str(ex))
    try:import pandapower as pp
    except ImportError as ex:raise SystemExit('pandapower required in your Miniforge env') from ex
    houses,trafos,lv=read_data();ass=infer_assignments(houses,trafos,lv,args.assignment)
    args.output.mkdir(parents=True,exist_ok=True)
    preflight(houses,trafos,lv,ass,args.output,args.assignment)
    tasks=[];skip=[];cache={}
    for tr in args.trafos:
        if tr not in inverters:skip.append(dict(trafo=tr,reason='MISSING_RATED_INVERTER'));continue
        if tr=='92395':skip.append(dict(trafo=tr,reason='NO_EPM_LV_NETWORK'));continue
        for factor in args.service_factors:
            territory=build_territory(tr,houses,trafos,lv,ass,factor)
            if territory is None or not territory.attachments:
                skip.append(dict(trafo=tr,reason='NO_ATTACHED_HOUSES_OR_LV_NETWORK'));continue
            d,src=load_dispatch(args.input,len(territory.attachments),'optimized',cache)
            if d is None:skip.append(dict(trafo=tr,reason=src));continue
            ids=critical_indices(d,args.top_n) if args.mode=='critical' else list(range(len(d)))
            if args.max_hours:ids=ids[:args.max_hours]
            for siting in args.siting:
                net,meta=build_net(territory,siting)
                for pf in args.power_factors:
                    for ratio in ratios:
                        for policy in args.policies:
                            if policy=='unity' and ratio!=ratios[0]:continue
                            tasks.append((tr,factor,territory,d,ids,siting,net,meta,pf,(0.0 if policy=='unity' else ratio),policy,src))
    if not tasks:raise SystemExit('No valid cases available; check dispatch paths')
    out=args.output/'ac_hours.csv'
    nrows=0;nfail=0
    # Incremental disk output so a long run can be inspected even if interrupted.
    with out.open('w',newline='',encoding='utf-8') as f:
        writer=None
        for k,(tr,factor,territory,d,ids,siting,net,meta,pf,ratio,policy,src) in enumerate(tasks,1):
            print(f'[{k}/{len(tasks)}] {tr} {len(territory.attachments)} homes {siting} route x{factor} PF {pf} Q ratio {ratio} {policy} hours {len(ids)}',flush=True)
            group=[]
            for ix in ids:
                r=run_hour(net,meta,territory,d.iloc[ix],pf,args.allocation,siting,ratio,policy,
                           lim,inverters[tr],p_install.get(tr,inverters[tr]),args.q_grid_points,args.q_refine)
                r.update(service_factor=factor,assignment=args.assignment,source_dispatch=src)
                if writer is None:
                    writer=csv.DictWriter(f,fieldnames=list(r.keys()),extrasaction='ignore')
                    writer.writeheader()
                # Record field structure is consistent across successes and failures.
                writer.writerow(r);group.append(r);nrows+=1
                nfail+=r['status']!='CONVERGED'
            f.flush()
    rows=pd.read_csv(out)
    keys=['trafo','houses','siting','service_factor','load_pf','allocation','q_ratio','policy']
    summary=[]
    for vals,g in rows.groupby(keys,dropna=False,sort=True):
        ok=g[g.status=='CONVERGED']
        row=dict(zip(keys,vals));row.update(hours=len(g),converged_hours=len(ok),failed_hours=len(g)-len(ok),
                                           feasible_hours=int(ok.ac_feasible.astype(bool).sum()))
        row['all_hours_feasible']=bool(len(ok)==len(g) and ok.ac_feasible.astype(bool).all())
        if len(ok):
            row.update(min_v_pu=float(ok.min_v_pu.min()),max_v_pu=float(ok.max_v_pu.max()),
                max_trafo_pct=float(ok.max_trafo_pct.max()),max_line_pct=float(ok.max_line_pct.max()),
                voltage_low_hours=int(ok.v_below_097.sum()),voltage_high_hours=int(ok.v_above_103.sum()),
                trafo_over_hours=int(ok.trafo_over_limit.sum()),
                mean_loss_kw=float(ok.loss_kw.mean()),max_abs_q_kvar=float(ok.q_selected_kvar.abs().max()),
                mean_abs_q_kvar=float(ok.q_selected_kvar.abs().mean()),
                control_override_hours=int((abs(ok.q_changed_kvar)>.01).sum()),
                no_ac_feasible_q_hours=int((ok.controller_status=='NO_SAMPLED_AC_FEASIBLE_Q_AT_FIXED_P').sum()))
        summary.append(row)
    pd.DataFrame(summary).to_csv(args.output/'ac_scenario_summary.csv',index=False)
    pd.DataFrame(skip,columns=['trafo','reason']).to_csv(args.output/'skipped_cases.csv',index=False)
    man=dict(model='EPM GIS candidate LV service attachments, balanced 3-phase equivalent',
       controller='Hourly steady-state HIL Q(U) reference, coordinated AC Vmin/Vmax/trafo/line checks',
       policies=args.policies,limits=vars(lim),q_ratios=ratios,q_search=dict(grid_points=args.q_grid_points,refine=args.q_refine),
       active_power_fixed=True,source_electricity='PyPSA 8760-hour combined inverter dispatch',
       feeder_impedances='screening proxies, NOT EPM measured',service_lengths='uncertain drops, EPM backbone preserved',
       transformer_trafo_kva_label='modelled ratings 3/5 kVA, 1-phase approximated x3 balanced equivalent',
       counts=dict(rows=nrows,converged=nrows-nfail,failed=nfail,scenarios=len(tasks)),
       pandapower_version=pp.__version__,parameters=dict(mode=args.mode,power_factors=args.power_factors,
       siting=args.siting,service_factors=args.service_factors,assignment=args.assignment,
       inverter_ratings=inverters,p_installed=p_install),skipped=skip)
    (args.output/'validation_manifest.json').write_text(json.dumps(man,indent=2)+'\n',encoding='utf-8')
    print('DONE',args.output,'AC hours',nrows,'failures',nfail)


if __name__=='__main__':main()
