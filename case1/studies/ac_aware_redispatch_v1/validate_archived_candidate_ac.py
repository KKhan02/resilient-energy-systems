#!/usr/bin/env python3
"""Resume-safe full-year pandapower AC replay of an indexed saved MILP design.

Calls the EXISTING EPM GIS build_net/run_hour and Q controller. Never invents
household service mappings or runs an independent battery heuristic. One run =
8760 hours, one fixed dispatch, one (PF, service-length, nameplate) scenario.
Nonoptimal/stressed scenarios are saved, not erased.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import shutil
import subprocess
from pathlib import Path
import pandas as pd
from audit_archived_campaign import sha256, resume_rows
from run_pilot import imported, filter_territory, CASE_HOUSE_IDS
from fixed_hardware import Hardware
from corridors import q_ratio_at_hour
from validate_annual_ac import validate_trajectory, summarize_ac
from voltage_band_protocol import validate_limits, reclassify_ac_hours


def run_signature(repo:Path, pilot:Path, meta:dict, trajectory:Path, pf:float,service:float,
                  vmin:float,vmax:float,qpoints:int,qrefine:int) -> dict:
    model=repo/'case1/studies/epm_gis_pandapower_v1/run_coordinated_q.py'
    return dict(candidate_id=meta['candidate_id'],scenario=meta['scenario'],
        transformer=meta['transformer'],assumed_transformer_kva=float(meta['assumed_nameplate_kva']),
        trajectory_sha256=sha256(trajectory),pilot_manifest_sha256=sha256(pilot/'pilot_manifest.json'),
        epm_coordinated_q_source_sha256=sha256(model),
        pf=float(pf),service_factor=float(service),voltage_min=float(vmin),voltage_max=float(vmax),
        q_grid_points=qpoints,q_refine=qrefine,nighttime_q='off',
        study_is_full_year=True)



def import_verified_existing_ac(old:Path, out:Path, pilot:Path, meta:dict, signature:dict,
                                 pf:float,service:float,vmin:float,vmax:float):
    """Reuse exact 8760 AC outcome without another pandapower calculation."""
    old=old.resolve()
    summary_path=old/'annual_ac_summary.json'
    hours_path=old/'annual_ac_hours.csv'
    if not summary_path.is_file() or not hours_path.is_file():
        raise ValueError('Existing annual AC source lacks summary and all hourly data')
    prev=json.loads(summary_path.read_text(encoding='utf8'))
    if (prev.get('scenario')!=meta['scenario'] or prev.get('transformer')!=meta['transformer'] or
        abs(float(prev.get('assumed_trafo_kva',-1))-float(meta['assumed_nameplate_kva']))>1e-8 or
        prev.get('source_trajectory_sha256')!=signature['trajectory_sha256']):
        raise ValueError('Existing annual AC does not match the candidate trajectory/nameplate')
    prior_meta_sha=meta.get('reused_original_pilot_manifest_sha256')
    if not prior_meta_sha or prev.get('source_pilot_manifest_sha256')!=prior_meta_sha:
        raise ValueError('Cannot prove same original pilot assumptions for reused annual AC')
    volt=prev.get('voltage_screen',{})
    if not volt or abs(float(volt.get('min_v_pu',-1))-vmin)>1e-8 or abs(float(volt.get('max_v_pu',-1))-vmax)>1e-8:
        raise ValueError('Previous AC used a different voltage control threshold')
    if abs(pf-float(meta['hardware']['load_pf']))>1e-8 or abs(service-float(meta.get('service_factor',1)))>1e-8:
        raise ValueError('Previous AC is not this PF/service sensitivity')
    if str(prev.get('nighttime_q'))!='off' or abs(float(prev.get('daylight_q_ratio',-1))-float(meta['daylight_q_ratio']))>1e-8:
        raise ValueError('Previous Q control assumptions differ')
    df=pd.read_csv(hours_path)
    if len(df)!=8760 or df.hour_index.tolist()!=list(range(8760)):
        raise ValueError('Previous AC result did not actually evaluate all 8760 hours')
    check=summarize_ac(df,8760)
    if not check['all_8760_evaluated'] or check['ac_feasible_hours']!=int(prev['ac_feasible_hours']):
        raise ValueError('Original AC summary does not match existing hourly data')
    for name in ('min_voltage_pu','max_voltage_pu','max_trafo_loading_pct','max_line_loading_pct'):
        if abs(check[name]-float(prev[name]))>1e-6:
            raise ValueError('Original AC reported an inconsistent '+name)
    out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(hours_path,out/'annual_ac_hours.csv')
    passed=df.status.astype(str).eq('CONVERGED') & df.ac_feasible.astype(str).str.lower().eq('true')
    df.loc[~passed].to_csv(out/'annual_ac_violating_hours.csv',index=False)
    df.sort_values('min_v_pu',ascending=True,na_position='last').head(30).to_csv(out/'annual_ac_worst_voltage_hours.csv',index=False)
    reclassify_ac_hours(df).to_csv(out/'voltage_band_comparison.csv',index=False)
    check.update({'candidate_id':meta['candidate_id'],'scenario':meta['scenario'],'transformer':meta['transformer'],
       'assumed_trafo_kva':meta['assumed_nameplate_kva'],
       'source_trajectory_sha256':signature['trajectory_sha256'],
       'source_pilot_manifest_sha256':signature['pilot_manifest_sha256'],
       'load_pf':pf,'service_factor':service,
       'voltage_screen':{'min_v_pu':vmin,'max_v_pu':vmax,'thermal_limit_pct':100},
       'manufacturer_soc_floor':meta['manufacturer_min_soc_fraction'],
       'nighttime_q':'off','daylight_q_ratio':meta['daylight_q_ratio'],
       'full_year_AC_checked':True,'AC_recomputed_by_this_script':False,
       'reused_prior_AC_hours_sha256':sha256(hours_path),
       'reused_prior_AC_summary_sha256':sha256(summary_path),
       'AC_losses_included_in_energy_optimization':False,
       'GIS_HOUSE_ASSIGNMENTS':'PROVISIONAL','field_certified':False})
    (out/'annual_ac_summary.json').write_text(json.dumps(check,indent=2,allow_nan=False)+'\n',encoding='utf8')
    (out/'ac_checkpoint.json').write_text(json.dumps({'status':'COMPLETE','signature':signature,
       'hours_saved':8760,'annual_ac_hours_sha256':sha256(out/'annual_ac_hours.csv'),
       'reused_verified_historical_AC':True},indent=2)+'\n',encoding='utf8')
    print('Reused verified 8760h AC result without rerunning:',out)


def main(argv=None):
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--repo-root',type=Path,default=Path('.'))
    pa.add_argument('--pilot-dir',type=Path,required=True,
                    help='Exact candidate output from run_archived_energy.py')
    pa.add_argument('--outdir',type=Path,required=True)
    pa.add_argument('--load-pf',type=float,default=.98)
    pa.add_argument('--service-factor',type=float,default=1.)
    pa.add_argument('--vmin',type=float,default=.95)
    pa.add_argument('--vmax',type=float,default=1.05)
    pa.add_argument('--q-grid-points',type=int,default=9)
    pa.add_argument('--q-refine',type=int,default=0)
    pa.add_argument('--reuse-existing-ac',type=Path,
                    help='Import an EXACT matching completed annual AC result, with source provenance checks')
    pa.add_argument('--resume',action='store_true',help='Continue only if exact input/signature is unchanged')
    args=pa.parse_args(argv)
    validate_limits(args.vmin,args.vmax)
    if not 0<args.load_pf<=1 or args.service_factor<1 or args.q_grid_points<5 or not 0<=args.q_refine<=6:
        pa.error('Invalid power factor, service factor or Q sampling')
    repo=args.repo_root.resolve();pilot=args.pilot_dir.resolve();out=args.outdir.resolve()
    if not (repo/'.git').exists():pa.error('Full local GitLab repository required')
    meta=json.loads((pilot/'pilot_manifest.json').read_text(encoding='utf8'))
    if meta.get('nighttime_q_policy')!='off' or 'candidate_id' not in meta:
        raise ValueError('Only archived-campaign manufacturer-SOC candidates with night Q off are supported')
    case=meta['scenario'];trafo=meta['transformer']
    if case not in ('seven','nine','twelve') or trafo!=('106039' if case=='twelve' else '94022'):
        raise ValueError('No archived household-specific GIS membership for this case')
    if meta.get('selected_candidate_houses')!=list(CASE_HOUSE_IDS[case]):
        raise ValueError('Provisional mapped houses differ from the source model')
    hw=Hardware(**meta['hardware'])
    if abs(hw.transformer_kva-float(meta['assumed_nameplate_kva']))>1e-6:
        raise ValueError('Incorrect transformer evidence/rating')
    if hw.export_policy!='zero':raise ValueError('This EPM GIS stage assumes zero export')
    src=pilot/'fixed_hardware_manufacturer_soc_baseline.csv'
    if sha256(src)!=meta.get('source_trajectory_sha256'):
        raise ValueError('Energy trajectory changed since manufacturer-SOC optimization')
    df=pd.read_csv(src)
    signature=run_signature(repo,pilot,meta,src,args.load_pf,args.service_factor,
                             args.vmin,args.vmax,args.q_grid_points,args.q_refine)
    state_path=out/'ac_checkpoint.json';csv_path=out/'annual_ac_hours.csv'
    if args.reuse_existing_ac:
        if out.exists():raise ValueError('Reuse target output already exists')
        import_verified_existing_ac(args.reuse_existing_ac,out,pilot,meta,signature,
                                    args.load_pf,args.service_factor,args.vmin,args.vmax)
        return
    if out.exists():
        if not args.resume:raise ValueError('Output already exists, use --resume ONLY for same exact scenario')
        if not state_path.exists():raise ValueError('Cannot resume without source signature')
        state=json.loads(state_path.read_text(encoding='utf8'))
        if state.get('signature')!=signature:raise ValueError('Cannot resume: source trajectory, model or assumptions changed')
        if state.get('status')=='COMPLETE':
            if sha256(csv_path)!=state.get('annual_ac_hours_sha256'):
                raise ValueError('Previously completed annual AC file changed since checkpoint')
            s=json.loads((out/'annual_ac_summary.json').read_text(encoding='utf8'))
            if not s.get('all_8760_evaluated'):raise ValueError('Invalid completed AC run')
            print('Verified existing completed 8760h result; did not rerun',out)
            return
        start=resume_rows(csv_path)
    else:
        start=0
    (read_data,infer_assignments,build_territory,Territory,build_net,
     critical_indices,run_hour,load_source)=imported(repo)
    demand,pv_pu,ghi,source_input=load_source(repo,case)
    if meta.get('source_input_sha256')!=sha256(source_input):
        raise ValueError('Input household and PV data changed since saved energy run')
    validate_trajectory(df,demand,hw,float(meta['manufacturer_min_soc_fraction']),src.name)
    houses,trafos,lv=read_data()
    assign=infer_assignments(houses,trafos,lv,'base')
    territory=build_territory(trafo,houses,trafos,lv,assign,args.service_factor)
    if territory is None:raise ValueError('Missing real GIS source topology')
    territory=Territory(trafo={**territory.trafo,'kva':hw.transformer_kva},
       graph=territory.graph,attachments=territory.attachments,label=territory.label,
       root=territory.root,line_count=territory.line_count)
    territory,exclusions=filter_territory(case,territory,Territory)
    if len(territory.attachments)!=len(CASE_HOUSE_IDS[case]):
        raise ValueError('GIS customer group differs from fixed scenario')
    net,acmeta=build_net(territory,'head')
    from coordinated_q_control import ACLimits
    limits=ACLimits(min_v=args.vmin,max_v=args.vmax,max_trafo_pct=100,max_line_pct=100)
    if not out.exists():
        out.mkdir(parents=True,exist_ok=False)
        state={'status':'RUNNING','signature':signature,'hours_saved':0}
        state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    else:
        state=json.loads(state_path.read_text(encoding='utf8'))
    # Critical: CSV writer appends only after checking exact signed provenance.
    mode='a' if start else 'w'
    with csv_path.open(mode,newline='',encoding='utf8') as file:
        fieldnames=None
        if start:
            with csv_path.open('r',newline='',encoding='utf8') as existing:
                fieldnames=next(csv.reader(existing))
        writer=csv.DictWriter(file,fieldnames=fieldnames,extrasaction='ignore') if fieldnames else None
        for i in range(start,8760):
            row=df.iloc[i]
            qratio=q_ratio_at_hour(float(row.pv_dc_available_kw),float(meta['daylight_q_ratio']),False)
            obs=run_hour(net,acmeta,territory,row,args.load_pf,'equal','head',
               qratio,'coordinated',limits,hw.inverter_kva,hw.inverter_kva,
               args.q_grid_points,args.q_refine)
            obs.update(hour_index=i,pv_dc_available_kw=float(row.pv_dc_available_kw),
                       load_pf_sensitivity=float(args.load_pf),service_factor=float(args.service_factor),
                       nighttime_q_disabled=(qratio==0))
            if writer is None:
                writer=csv.DictWriter(file,fieldnames=list(obs.keys()),extrasaction='ignore')
                writer.writeheader()
            writer.writerow(obs)
            if (i+1)%250==0:
                file.flush()
                state.update(hours_saved=i+1)
                state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
                print(f'{meta["candidate_id"]} PF {args.load_pf:g}, service {args.service_factor:g}: {i+1}/8760',flush=True)
    ac=pd.read_csv(csv_path)
    if len(ac)!=8760 or ac.hour_index.tolist()!=list(range(8760)):
        raise ValueError('AC annual output incomplete or out of order')
    summary=summarize_ac(ac,8760)
    summary.update({'candidate_id':meta['candidate_id'],'scenario':case,'transformer':trafo,
        'source_trajectory_sha256':sha256(src),'source_pilot_manifest_sha256':sha256(pilot/'pilot_manifest.json'),
        'load_pf':args.load_pf,'service_factor':args.service_factor,
        'voltage_screen':{'min_v_pu':args.vmin,'max_v_pu':args.vmax,'thermal_limit_pct':100},
        'manufacturer_soc_floor':meta['manufacturer_min_soc_fraction'],
        'nighttime_q':'off','daylight_q_ratio':meta['daylight_q_ratio'],
        'full_year_pypsa_energy_and_soc_reoptimized_by_this_script':False,
        'full_year_AC_checked':True,'AC_losses_included_in_energy_optimization':False,
        'GIS_HOUSE_ASSIGNMENTS':'PROVISIONAL','field_certified':False,
        'candidate_hardware_unchanged':True,
        'source_git_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True).stdout.strip(),
        'interpretation':'8760h magnitude and thermal power-flow screen; not EPM/legal duration-based certification.'})
    (out/'annual_ac_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf8')
    reclassify_ac_hours(ac).to_csv(out/'voltage_band_comparison.csv',index=False)
    passed=ac.status.astype(str).eq('CONVERGED') & ac.ac_feasible.astype(str).str.lower().eq('true')
    ac.loc[~passed].to_csv(out/'annual_ac_violating_hours.csv',index=False)
    ac.sort_values('min_v_pu',ascending=True,na_position='last').head(30).to_csv(out/'annual_ac_worst_voltage_hours.csv',index=False)
    state.update(status='COMPLETE',hours_saved=8760,annual_ac_hours_sha256=sha256(csv_path))
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
