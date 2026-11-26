#!/usr/bin/env python3
"""SEEDExchange Study A next-stage PV+BESS, local-only and immutable sources.

This script imports the signed v6.2 runner rather than changing it. Cohort-scale
fixed-hardware PyPSA runs, dedicated four-house MILP sizing, PV-first replay,
and conditional annual balanced-AC validation are separate commands.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

RUNNER_REL = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py')
MANIFEST_REL = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json')
BASE_REL = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
STAR_MST_REL = Path('case1/studies/SEEDExchange_StudyA_92395_STAR_MST_v1/run_92395_star_mst.py')
TERRITORIES=('94022','106039','113699','85398','92395')
RATINGS={'94022':5.,'106039':5.,'113699':3.,'85398':5.,'92395':5.}
FOUR_ONLY=(('A0','113699'),('A0','85398'),('A0','92395'))
DEFAULT_PF=(.95,.98,1.)
DEFAULT_LENGTH=(1.,1.3,1.6)



def windows_extended_path(path):
    """Use Windows extended-length path syntax for filesystem I/O only.

    This changes neither the target directory nor its contents.  The prefix
    bypasses the legacy MAX_PATH boundary for standard Python file operations.
    Leave ordinary paths unchanged on non-Windows hosts.
    """
    path = Path(path)
    if sys.platform != 'win32':
        return path
    raw = str(path)
    if raw.startswith('\\\\?\\'):
        return path
    raw = str(path if path.is_absolute() else path.absolute())
    if raw.startswith('\\\\'):
        return Path('\\\\?\\UNC\\' + raw[2:])
    return Path('\\\\?\\' + raw)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,Path(path))
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def resolve_signed_v4_path(repo, manifest):
    """Resolve the recorded historical repository-relative directory, never rewrite manifest."""
    from pathlib import PureWindowsPath, PurePosixPath
    old_root=str(manifest["repo_root"])
    old_input=str(manifest["v4_run_dir"])
    path_type=PureWindowsPath if PureWindowsPath(old_root).drive else PurePosixPath
    root=path_type(old_root); source=path_type(old_input)
    if not root.is_absolute() or not source.is_absolute():
        raise ValueError("Signed source paths must be absolute")
    rel=source.relative_to(root)
    expected=("case1","studies","SEEDExchange_StudyA_LocalPreflight_v4","outputs","run_02")
    if tuple(rel.parts)!=expected:
        raise ValueError("Signed v4 source directory identity changed")
    target=(repo/Path(*rel.parts)).resolve()
    if not target.is_relative_to(repo.resolve()) or not target.is_dir():
        raise ValueError("Signed v4 source directory unavailable in checkout")
    return target


def secure_context(repo, manifest_path):
    repo=repo.resolve()
    manifest_path=manifest_path.resolve()
    if not (repo/'.git').exists():
        raise ValueError('Run from the real local GitLab checkout, including .git')
    m=json.loads(manifest_path.read_text(encoding='utf-8'))
    if m.get('population_houses')!=35 or m.get('2025_hours')!=8760:
        raise ValueError('Wrong 35-home 2025 Study A manifest')
    runner=repo/RUNNER_REL
    if digest(runner)!=m['script_sha256']:
        raise ValueError('Frozen v6.2 runner differs from signed manifest, do not overwrite')
    for rel, expected in m['model_source_hashes'].items():
        if digest(repo/rel)!=expected:
            raise ValueError('Original model source changed: '+rel)
    v6=load_module(runner,'signed_study_a_v6_2')
    _,_,mapping,profiles,groups,_=v6.validated_sources(repo,resolve_signed_v4_path(repo,m),m)
    if groups!=m['groups'] or mapping!=m['mapping']:
        raise ValueError('Signed cohorts/profile mapping changed')
    return m,v6,mapping,profiles


def group_for(m,variant,transformer):
    if transformer not in TERRITORIES or variant not in ('A0','A1'):
        raise ValueError('Out-of-scope cohort')
    ids=list(m['groups'][variant][transformer])
    if len(ids)<4:
        raise ValueError('Study A model requires >=4 households')
    if transformer=='92395' and m['groups']['A0'][transformer]!=m['groups']['A1'][transformer]:
        raise ValueError('92395 A0/A1 must contain the same households')
    return ids


def source_trace(m,mapping,profiles,variant,transformer):
    ids=group_for(m,variant,transformer)
    trace=pd.DataFrame({h:profiles[mapping[h]].to_numpy(float) for h in ids},index=profiles.index)
    if abs(float(trace.to_numpy().sum())-len(ids)*1898.)>.1:
        raise AssertionError('Household profile chronology / annual demand changed')
    return ids,trace


def solar_per_unit(repo, index):
    src=repo/'Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv'
    frame=pd.read_csv(src,parse_dates=['timestamp']).set_index('timestamp')
    if len(frame)!=8760 or not frame.index.equals(index):
        raise ValueError('2025 source PV timestamps differ from 35-house profiles')
    val=frame['nasa_pv_dc_kw'].to_numpy(float)/5.22
    if not np.isfinite(val).all() or val.min() < -1e-9 or val.max()>1.00001:
        raise ValueError('Invalid original NASA PV normalized source')
    return pd.Series(val,index=index), src


def out_new(path):
    path=path.resolve()
    if path.exists():
        raise FileExistsError('Refusing to overwrite output: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+'\n',encoding='utf-8')


def case_slug(variant, tid, tier):
    if tid=='92395':return f'92395_A0eqA1_{tier}'
    return f'{variant}_{tid}_{tier}'


def create_plan():
    rec=[]
    for variant in ('A0','A1'):
        for tid in ('94022','106039','113699','85398'):
            for tier in ('min_cost','ss90'):
                rec.append({'variant':variant,'transformer':tid,'tier':tier,
                            'kind':'archived_hardware_fixed_dispatch',
                            'four_house_proxy':variant=='A0' and tid in ('113699','85398')})
    for tid in ('113699','85398','92395'):
        for tier in ('min_cost','ss90'):
            rec.append({'variant':'A0','transformer':tid,'tier':tier,
                        'kind':'new_four_house_milp', 'four_house_proxy':False})
    return rec


def check_portfolio_plan():
    p=create_plan()
    assert len(p)==22 and len(set((x['variant'],x['transformer'],x['tier'],x['kind']) for x in p))==22
    assert sum(x['kind']=='new_four_house_milp' for x in p)==6
    assert sum(x['kind']=='archived_hardware_fixed_dispatch' for x in p)==16
    return p


def evaluate_equipment(model,n,hourly,settings):
    summary=model.summarize(n,hourly,settings,'STUDYA_GEOGRAPHIC_FOUR_HOUSE')
    if abs(float(hourly.unserved_kw.sum()))>1e-5 or abs(float(hourly.grid_export_kw.sum()))>1e-5:
        raise AssertionError('New four-house design requires zero ENS and zero export')
    return summary


def four_house_optimize(repo, m, v6, mapping, profiles, variant, tid, tier, out_path, manifest_path):
    if (variant,tid) not in FOUR_ONLY:
        raise ValueError('New four-house MILP applies to A0 113699,85398 and 92395 only')
    if tier not in ('min_cost','ss90'):raise ValueError('Unknown hardware tier')
    ids, trace=source_trace(m,mapping,profiles,variant,tid)
    if len(ids)!=4:raise ValueError('Not a four-house cohort')
    pv, solar_src=solar_per_unit(repo,trace.index)
    model=load_module(repo/'case1/studies/pypsa_joint_optimization_v1/model.py','study_a_four_house_original_model')
    load=trace.sum(axis=1)
    settings=model.Settings(transformer_kva=RATINGS[tid],loading_pu=1.,load_pf=.98,
        max_panels=64,max_battery_modules=16,max_battery_power_kw=24.,max_inverter_kva=24.,
        export_policy='zero',objective='economic',discrete=True,allow_unserved=False,
        min_self_sufficiency=.90 if tier=='ss90' else None)
    n=model.make_network(load,pv,settings)
    n.optimize.create_model()
    model.add_investment_constraints(n,settings)
    opt=n.model
    e=opt.variables['Store-e_nom'].sel(name='BATTERY')
    stored=opt.variables['Store-e'].sel(name='BATTERY')
    pv_cap=opt.variables['Generator-p_nom'].sel(name='PV_DC')
    power=opt.variables['Link-p_nom'].sel(name='BAT_DISCHARGE')
    # The baseline 'economic' case here explicitly includes PV+BESS, rather
    # than allowing the trivial no-DER design to be mislabelled as PV+BESS.
    opt.add_constraints(e>=model.BATTERY_USABLE_KWH,name='one_battery_module_minimum')
    opt.add_constraints(pv_cap>=model.PANEL_KW,name='one_pv_panel_minimum')
    physical_floor_ratio=max(0.,model.BATTERY_USABLE_KWH-(1-.20)*5.12)/model.BATTERY_USABLE_KWH
    opt.add_constraints(stored>=physical_floor_ratio*e,name='manufacturer_physical_SOC_20pct')
    opt.add_constraints(power<=(2.24/model.BATTERY_USABLE_KWH)*e,
                        name='manufacturer_50A_continuous_power_both_directions')
    status, condition=n.optimize.solve_model(solver_name=settings.solver_name)
    if status!='ok' or condition!='optimal':
        raise RuntimeError(f'{tid} {tier} FOUR_HOUSE optimization: {status}/{condition}; no solution claimed')
    hourly=model.extract(n,settings,load)
    summary=evaluate_equipment(model,n,hourly,settings)
    panels=int(round(float(summary['panels_equivalent'])))
    modules=int(round(float(summary['battery_modules_equivalent'])))
    inv=float(summary['inverter_ac_kva_assumed_unity_pf'])
    bat=float(summary['battery_power_dc_kw'])
    if modules<1 or panels<1 or bat>2.24*modules+1e-5:
        raise AssertionError('Invalid discrete device count/manufacturer power')
    if abs(panels-summary['panels_equivalent'])>1e-5 or abs(modules-summary['battery_modules_equivalent'])>1e-5:
        raise AssertionError('New four-house capacity is not discrete')
    if float(hourly.battery_soc_usable_kwh.min()) < modules*(model.BATTERY_USABLE_KWH-4.096)-1e-4:
        raise AssertionError('Physical SOC floor not achieved')
    metrics=v6.metrics_for_dispatch(hourly,modules)
    out=out_new(out_path);out.mkdir()
    hourly.to_csv(out/'energy_hourly_2025.csv',float_format='%.10f')
    doc={'status':'FULL_8760H_NEW_FOUR_HOUSE_MILP_ENERGY_ONLY_NOT_AC_VALIDATED',
         'scenario':variant,'transformer':tid,'hardware_selection_tier':tier,
         'selected_house_ids':ids,'source_anchor_id':None,
         'source_anchor_provenance':'NEW_FOUR_HOUSE_DISCRETE_MILP_2025_GEOGRAPHIC_PROFILES',
         'hardware':{'pv_panels':panels,'battery_modules':modules,'battery_power_dc_kw':bat,
                     'inverter_kva':inv,'transformer_kva_assumed_or_evidenced':RATINGS[tid]},
         'battery_hardware_limits':{'min_physical_soc':.20,'continuous_kw_per_module':2.24,
                                    'nominal_kwh_per_module':5.12,'historical_usable_kwh_per_module':4.325},
         'metrics':metrics,'model_summary':summary,
         'source_model_sha256':digest(repo/'case1/studies/pypsa_joint_optimization_v1/model.py'),
         'original_pv_source_sha256':digest(solar_src),'input_manifest_sha256':digest(manifest_path),
         'energy_csv_sha256':digest(out/'energy_hourly_2025.csv'),
         'economic_reoptimized_for_new_households':True,'hardware_reoptimized':True,
         'archived_source_costs_transferred':False,
         'interpretation':'Energy-only new-cohort optimal under assumed tariff/equipment and PCC proxy; NOT AC-feasible certification or EPM connection approval. Civil, cables, protection and utility costs excluded.'}
    write_json(out/'energy_manifest.json',doc)
    return doc


def validated_energy_directory(energy_dir, m, mp, variant, tid, ids, trace):
    meta_path=energy_dir/'energy_manifest.json';csv_path=energy_dir/'energy_hourly_2025.csv'
    info=json.loads(meta_path.read_text(encoding='utf-8'))
    if info['input_manifest_sha256'] != digest(mp):raise ValueError('Energy input manifest differs')
    if info['transformer']!=tid or info['selected_house_ids']!=ids:
        raise ValueError('Wrong cohort in energy directory')
    expected_variant=variant if tid!='92395' else 'A0'
    if info['scenario']!=expected_variant:raise ValueError('Wrong geographic assignment')
    if digest(csv_path)!=info['energy_csv_sha256']:
        raise ValueError('Energy CSV SHA256 changed')
    df=pd.read_csv(csv_path,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    if len(df)!=8760 or not df.index.equals(trace.index):raise ValueError('Incomplete/different annual energy timestamps')
    cols=('demand_kw','inverter_ac_kw','pv_dc_available_kw','grid_export_kw','unserved_kw','battery_soc_usable_kwh')
    if any(k not in df.columns for k in cols) or not np.isfinite(df[list(cols)].to_numpy(float)).all():
        raise ValueError('Missing/non-finite dispatch fields')
    if np.max(np.abs(df.demand_kw.to_numpy(float)-trace.sum(axis=1).to_numpy(float)))>1e-5:
        raise ValueError('Aggregate energy load differs from individual house profiles')
    if df.grid_export_kw.abs().max()>1e-5 or df.unserved_kw.abs().max()>1e-5:
        raise ValueError('Energy dispatch includes export or ENS')
    hardware=info['hardware']; maxkw=float(hardware['inverter_kva'])
    if (df.inverter_ac_kw > maxkw+1e-5).any() or (df.inverter_ac_kw<-1e-5).any():
        raise ValueError('Inverter P violates fixed rating')
    return df,info


def causal_new_four(v6, energy_dir, mp, m, mapping, profiles, variant, tid, outdir):
    ids,trace=source_trace(m,mapping,profiles,variant,tid)
    df,meta=validated_energy_directory(energy_dir,m,mp,variant,tid,ids,trace)
    hw=meta['hardware']
    initial=float(df.battery_soc_usable_kwh.iloc[-1])
    causal=v6.causal_pv_first_dispatch(df.demand_kw.to_numpy(float),
        df.pv_dc_available_kw.to_numpy(float),initial,int(hw['pv_panels']),int(hw['battery_modules']),
        float(hw['inverter_kva']),float(hw['battery_power_dc_kw']))
    causal.index=df.index;causal.index.name='timestamp_lst'
    causal_metrics=v6.metrics_for_dispatch(causal.assign(pv_dc_generated_kw=
        causal.pv_dc_available_kw-causal.curtailed_pv_dc_kw),int(hw['battery_modules']))
    delta=float(causal.battery_soc_usable_kwh.iloc[-1])-initial
    out=windows_extended_path(out_new(outdir));out.mkdir();causal.to_csv(out/'causal_pv_first_2025.csv',float_format='%.10f')
    doc={'status':'FULL_8760H_CAUSAL_NONCYCLIC_CONTROLS_SENSITIVITY',
         'transformer':tid,'scenario':variant,'selected_houses':ids,
         'source_energy_manifest_sha256':digest(energy_dir/'energy_manifest.json'),
         'input_manifest_sha256':digest(mp),'output_sha256':digest(out/'causal_pv_first_2025.csv'),
         'metrics':causal_metrics,'initial_soc_kwh':initial,'terminal_soc_delta_kwh':delta,
         'comparison_caveat':'Not cyclic unless terminal SOC delta is zero; annual grid import is not a like-for-like optimal-dispatch comparison when it differs.'}
    write_json(out/'causal_summary.json',doc)
    return doc


def replay_ac(repo, mp, m, v6, mapping, profiles, variant, tid, energy_dir,
              outdir, topology, pf, length, hours, dispatch, causal_dir=None, q_ratio=.25):
    if pf not in DEFAULT_PF or length not in DEFAULT_LENGTH:
        raise ValueError('Only approved PF and service multiplier')
    if not 1<=hours<=8760:raise ValueError('Invalid hourly window')
    if tid=='92395' and topology not in ('star','mst'):
        raise ValueError('92395 AC requires explicit proposed STAR or MST')
    if tid!='92395' and topology!='mapped':
        raise ValueError('Mapped EPM territories require topology=mapped')
    ids,trace=source_trace(m,mapping,profiles,variant,tid)
    energy,meta=validated_energy_directory(energy_dir,m,mp,variant,tid,ids,trace)
    if dispatch=='causal':
        if causal_dir is None:raise ValueError('Require signed causal output directory')
        cm=json.loads((causal_dir/'causal_summary.json').read_text(encoding='utf-8'))
        cf=causal_dir/'causal_pv_first_2025.csv'
        if cm.get('source_energy_manifest_sha256')!=digest(energy_dir/'energy_manifest.json') and cm.get('reference_energy_manifest_sha256')!=digest(energy_dir/'energy_manifest.json'):
            raise ValueError('Causal input not from identical energy source')
        if cm.get('output_sha256')!=digest(cf):raise ValueError('Causal checksum mismatch')
        use=pd.read_csv(cf,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    elif dispatch=='optimized':use=energy
    else:raise ValueError('Use optimized or causal dispatch')
    if len(use)!=8760 or not use.index.equals(trace.index):
        raise ValueError('Dispatch chronology mismatch')
    if np.max(np.abs(use.demand_kw.to_numpy(float)-trace.sum(axis=1).to_numpy(float)))>1e-5:
        raise ValueError('AC dispatch load differs from named household loads')
    if tid=='92395':
        path=repo/STAR_MST_REL
        star=load_module(path,'study_a_92395_source_topology')
        read,_,_,Territory=v6.repo_modules(repo)
        houses,trafos,_=read()
        terr=star.make_territory(houses,trafos,Territory,topology,length)
    else:terr=v6.new_territory(repo,variant,tid,ids,length)
    from run_epm_validation import build_net
    net,node=build_net(terr,'head')
    if set(node['loads'])!=set(ids):raise ValueError('AC feeder changed household membership')
    import pandapower as pp
    records=[]
    kva=float(meta['hardware']['inverter_kva'])
    for i in range(hours):
        rec=v6.solve_ac_hour(net,node,terr,trace.index[i],trace.iloc[i],pf,
                  float(use.iloc[i].inverter_ac_kw),kva,float(use.iloc[i].pv_dc_available_kw),
                  q_ratio,9,'pvbess',pp)
        records.append(rec)
        if (i+1)%500==0:print(f'AC replay {i+1}/{hours}',flush=True)
    rows=pd.DataFrame(records)
    conv=rows[rows.status=='CONVERGED']
    # Apply extended-length syntax before creating/writing any result file.
    # Some original paths are 258 chars for CSV and 260 for JSON on Windows.
    out=windows_extended_path(out_new(outdir));out.mkdir()
    rows.to_csv(out/'ac_hourly.csv',index=False,float_format='%.10f')
    summary={'status':'ANNUAL_PVBESS_AC' if hours==8760 else 'PV_BESS_24H_SMOKE',
       'model':'fixed_active_power_replay_with_daylight_q_not_ac_constrained_energy_reoptimization',
       'scenario':variant,'transformer':tid,'topology':topology,'tier':meta['hardware_selection_tier'],
       'dispatch':dispatch,'selected_house_ids':ids,'hours':hours,'converged_hours':len(conv),
       'nonconverged_hours':hours-len(conv),
       'AC_infeasible_hours':int((~conv.ac_feasible).sum()),
       'voltage_below_095_hours':int(conv.voltage_below_095.sum()) if len(conv) else None,
       'transformer_overload_hours':int(conv.trafo_over_100.sum()) if len(conv) else None,
       'min_voltage_pu':float(conv.min_v_pu.min()) if len(conv) else None,
       'max_transformer_loading_pct':float(conv.max_trafo_pct.max()) if len(conv) else None,
       'annual_or_sample_losses_kwh':float(conv.loss_kw.sum()) if len(conv) else None,
       'pf':pf,'length_factor':length,'q_ratio_daylight':q_ratio,'night_q_disabled':True,
       'energy_manifest_sha256':digest(energy_dir/'energy_manifest.json'),
       'input_manifest_sha256':digest(mp), 'ac_hourly_sha256':digest(out/'ac_hourly.csv'),
       'evidence':'PROPOSED_GEOGRAPHIC_BALANCED_AC_ONLY'}
    write_json(out/'ac_summary.json',summary)
    return summary


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--manifest',type=Path)
    sp=ap.add_subparsers(dest='cmd',required=True)
    sp.add_parser('plan')
    opt=sp.add_parser('four-opt',help='New exact four-house joint hardware optimization, not old archived six thousand runs')
    opt.add_argument('--transformer',choices=['113699','85398','92395'],required=True)
    opt.add_argument('--tier',choices=['min_cost','ss90'],required=True)
    opt.add_argument('--outdir',type=Path,required=True)
    cause=sp.add_parser('four-causal')
    cause.add_argument('--transformer',choices=['113699','85398','92395'],required=True)
    cause.add_argument('--energy-dir',type=Path,required=True)
    cause.add_argument('--outdir',type=Path,required=True)
    ac=sp.add_parser('replay')
    ac.add_argument('--assignment',choices=['A0','A1'],required=True)
    ac.add_argument('--transformer',choices=TERRITORIES,required=True)
    ac.add_argument('--topology',choices=['mapped','star','mst'],required=True)
    ac.add_argument('--dispatch',choices=['optimized','causal'],default='optimized')
    ac.add_argument('--energy-dir',type=Path,required=True)
    ac.add_argument('--causal-dir',type=Path)
    ac.add_argument('--outdir',type=Path,required=True)
    ac.add_argument('--pf',type=float,default=.98)
    ac.add_argument('--length',type=float,default=1.)
    ac.add_argument('--hours',type=int,default=24)
    ac.add_argument('--q-ratio',type=float,default=.25)
    args=ap.parse_args(argv)
    if args.cmd=='plan':
        print(json.dumps({'status':'PLAN_ONLY_NO_NUMERIC_RUN','cases':check_portfolio_plan()},indent=2));return
    repo=args.repo_root.resolve();mp=(args.manifest or repo/MANIFEST_REL).resolve()
    m,v6,mapping,profiles=secure_context(repo,mp)
    if args.cmd in ('four-opt','four-causal'):
        if args.cmd=='four-opt':
            result=four_house_optimize(repo,m,v6,mapping,profiles,'A0',args.transformer,args.tier,args.outdir,mp)
        else:
            result=causal_new_four(v6,args.energy_dir.resolve(),mp,m,mapping,profiles,'A0',args.transformer,args.outdir)
    else:
        result=replay_ac(repo,mp,m,v6,mapping,profiles,args.assignment,args.transformer,args.energy_dir.resolve(),
                         args.outdir,args.topology,args.pf,args.length,args.hours,args.dispatch,
                         args.causal_dir.resolve() if args.causal_dir else None,args.q_ratio)
    print(json.dumps(result,indent=2,default=str))


if __name__=='__main__':main()
