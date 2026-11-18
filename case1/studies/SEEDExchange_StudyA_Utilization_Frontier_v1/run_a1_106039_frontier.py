#!/usr/bin/env python3
"""Study A A1-106039 hardware frontier, only user-local 2025 PyPSA simulations.

Imports signed historical Study A sources and the original fixed_hardware PyPSA
solver. Never changes source files, never assumes AC-feasibility. The tested
hardware is deliberately discrete and fixed for each 8760-hour annual LP.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd

ID = 'SEEDExchange_A1_106039_Utilization_Frontier_v1'
PILOT_IDS = ('SS_B9','SS_B10','SS_P45','SS_P41_KEEP20','MC_B9','MC_P37')
FULL_IDS = PILOT_IDS + ('SS_B9_POWER16','SS_P45_B9','MC_B10','MC_P33')
# Reference cases exist and are signed. Do not rerun them.
REFERENCE = {
    'MC_REF': dict(panels=41, modules=8, battery_kw=12.0, inverter_kva=12.0, source_tier='min_cost'),
    'SS_REF': dict(panels=49, modules=8, battery_kw=14.11017378393042, inverter_kva=20.0, source_tier='ss90'),
}
CANDIDATES = {
    'SS_B9': dict(panels=49, modules=9, battery_kw=14.11017378393042, inverter_kva=20.),
    'SS_B10': dict(panels=49, modules=10, battery_kw=14.11017378393042, inverter_kva=20.),
    'SS_P45': dict(panels=45, modules=8, battery_kw=14.11017378393042, inverter_kva=20.),
    'SS_P41_KEEP20': dict(panels=41, modules=8, battery_kw=14.11017378393042, inverter_kva=20.),
    'MC_B9': dict(panels=41, modules=9, battery_kw=12., inverter_kva=12.),
    'MC_P37': dict(panels=37, modules=8, battery_kw=12., inverter_kva=12.),
    'SS_B9_POWER16': dict(panels=49, modules=9, battery_kw=16.35, inverter_kva=20.),
    'SS_P45_B9': dict(panels=45, modules=9, battery_kw=14.11017378393042, inverter_kva=20.),
    'MC_B10': dict(panels=41, modules=10, battery_kw=12., inverter_kva=12.),
    'MC_P33': dict(panels=33, modules=8, battery_kw=12., inverter_kva=12.),
}
PORT_KW = {5.:5.76,6.:6.48,7.6:9.12,8.:9.12,10.:10.56,12.:12.,20.:21.12,24.:24.}
INDEX = pd.date_range('2025-01-01', periods=8760, freq='h')

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def verify_energy_csv_signature(path,expected):
    """Verify original signed bytes, tolerating ONLY an exact Git LF normalization.

    Historical 2025 candidate CSV manifests were hashed after writing on
    Windows with CRLF. Git stores the same numeric records with LF. Accept
    LF content only when converting its LF to CRLF reproduces the *exact*
    recorded manifest SHA256. Never accept arbitrary numeric similarity.
    """
    if not isinstance(expected,str) or len(expected)!=64:
        raise ValueError('Missing or invalid original signed CSV SHA256')
    direct=digest(path)
    if direct==expected:return 'SIGNED_BYTES_MATCH'
    data=path.read_bytes()
    if b'\r' not in data and b'\n' in data:
        restored=hashlib.sha256(data.replace(b'\n',b'\r\n')).hexdigest()
        if restored==expected:return 'EXACT_GIT_LF_TO_SIGNED_CRLF'
    raise ValueError('Signed existing candidate CSV differs from its manifest: '+str(path))


def validate_device(x):
    p,m,kw,inv=x['panels'],x['modules'],x['battery_kw'],x['inverter_kva']
    if not (isinstance(p,int) and isinstance(m,int) and p>=1 and m>=1):
        raise ValueError('Positive integer panel/module count required')
    if inv not in PORT_KW:raise ValueError('Non-source inverter rating')
    if kw<=0 or kw > 2.24*m+1.e-8:raise ValueError('Deye current screen exceeded')
    if kw > PORT_KW[inv]+1e-8 or kw > 1.152*inv+1e-8:
        raise ValueError('Inverter battery port capability exceeded')
    if p*.435 > 1.5*inv+1e-8:raise ValueError('DC PV / AC inverter ratio exceeded')
    return True

def all_cases():
    return {**REFERENCE, **CANDIDATES}

def selected(profile):
    return PILOT_IDS if profile=='pilot' else FULL_IDS

def module_paths(repo):
    code=repo/'case1/studies/SEEDExchange_StudyA_PVBESS_v1'
    ctrl=repo/'case1/studies/ac_aware_redispatch_v1'
    if not (code/'study_a_pvbess.py').is_file() or not (ctrl/'fixed_hardware.py').is_file():
        raise FileNotFoundError('Missing existing Study A PV/BESS or fixed hardware modules')
    for folder in (str(code),str(ctrl)):
        if folder not in sys.path:sys.path.insert(0,folder)
    import study_a_pvbess as st
    import fixed_hardware as fh
    return st,fh

def context(repo):
    st,fh=module_paths(repo)
    manifest=repo/st.MANIFEST_REL
    m,v6,mapping,profiles=st.secure_context(repo,manifest)
    houses,trace=st.source_trace(m,mapping,profiles,'A1','106039')
    pv,solar_path=st.solar_per_unit(repo,trace.index)
    if len(houses)!=11 or abs(trace.to_numpy().sum()-20878.)>1e-3:
        raise ValueError('A1 106039 household membership or annual demand changed')
    baseline={}
    for refid,design in REFERENCE.items():
        folder=repo/st.BASE_REL/f"energy_A1_106039_{design['source_tier']}_ref"
        hourly,meta=st.validated_energy_directory(folder,m,manifest,'A1','106039',houses,trace)
        h=meta['hardware']
        if (int(h['pv_panels'])!=design['panels'] or int(h['battery_modules'])!=design['modules']
                or abs(float(h['battery_power_dc_kw'])-design['battery_kw'])>1e-5
                or abs(float(h['inverter_kva'])-design['inverter_kva'])>1e-5):
            raise ValueError('Signed baseline hardware differs: '+refid)
        baseline[refid]=(hourly,meta,folder)
    return dict(repo=repo,st=st,fh=fh,m=m,v6=v6,manifest=manifest,houses=houses,
                trace=trace,pv=pv,solar_path=solar_path,baseline=baseline)

def check_chronology(df):
    if len(df)!=8760 or not isinstance(df.index,pd.DatetimeIndex) or not df.index.equals(INDEX):
        raise ValueError('Incorrect 2025 hourly timestamps')
    cols=['demand_kw','pv_dc_available_kw','curtailed_pv_dc_kw','battery_charge_dc_kw',
          'battery_discharge_dc_kw','battery_soc_usable_kwh','inverter_ac_kw',
          'grid_import_kw','grid_export_kw','unserved_kw']
    if not set(cols).issubset(df):raise ValueError('Missing energy columns')
    if not np.isfinite(df[cols].to_numpy(dtype=float)).all():raise ValueError('Nonfinite energy')
    if df.grid_export_kw.abs().max()>1e-5 or df.unserved_kw.abs().max()>1e-5:
        raise ValueError('Export or unserved load')
    if (df.inverter_ac_kw+df.grid_import_kw-df.demand_kw).abs().max()>1e-4:
        raise ValueError('AC energy balance')

def case_summary(id,design,frame,model,source,model_summary=None):
    validate_device(design)
    check_chronology(frame)
    panels=int(design['panels']); modules=int(design['modules']); bat=float(design['battery_kw']); inv=float(design['inverter_kva'])
    if abs(float(frame.pv_dc_available_kw.sum()) - panels/41*21657.242803252095)>1.: # compare to independently computed source below as well
        raise ValueError('Unexpected solar scaling')
    effective=.8*5.12*modules
    cost_pv=panels*.435*model.annualized_rate(model.PV_USD_KWP,25)
    cost_bat=modules*model.BATTERY_USABLE_KWH*model.annualized_rate(model.BAT_USD_KWH,20)
    cost_inv=inv*model.annualized_rate(model.INV_USD_KW_AC,15)
    cost_power=bat*model.annualized_rate(model.BAT_POWER_USD_KW,20)
    imports=float(frame.grid_import_kw.sum())
    equipment=cost_pv+cost_bat+cost_inv+cost_power
    total=equipment+imports*model.IMPORT_USD_KWH
    if model_summary is not None:
        if abs(float(model_summary['annual_total_usd'])-total)>0.05:
            raise ValueError('Summary and independent full equipment cost differ')
    minsoc=modules*(model.BATTERY_USABLE_KWH-(1-.20)*5.12)
    if float(frame.battery_soc_usable_kwh.min()) < minsoc-1e-4:
        raise ValueError('Manufacturer SOC floor violated')
    if float(frame.battery_soc_usable_kwh.max()) > modules*model.BATTERY_USABLE_KWH+1e-4:
        raise ValueError('Battery maximum SOC exceeded')
    if (frame.battery_charge_dc_kw>bat+1e-4).any() or (frame.battery_discharge_dc_kw>bat+1e-4).any():
        raise ValueError('Battery DC power exceeded')
    if (frame.inverter_ac_kw>inv+1e-4).any():raise ValueError('Inverter output exceeded')
    return dict(case_id=id,kind='SIGNED_REFERENCE' if source=='reference' else 'NEW_FIXED_HARDWARE_LP',
        pv_panels=panels,pv_kwp=panels*.435,battery_modules=modules,
        battery_nominal_kwh=modules*5.12,battery_modelled_usable_kwh=modules*model.BATTERY_USABLE_KWH,
        battery_operational_usable_kwh=effective,battery_power_dc_kw=bat,inverter_kva=inv,
        annual_demand_kwh=float(frame.demand_kw.sum()),pv_available_dc_kwh=float(frame.pv_dc_available_kw.sum()),
        curtailed_pv_dc_kwh=float(frame.curtailed_pv_dc_kw.sum()),
        curtailment_percent=100*frame.curtailed_pv_dc_kw.sum()/max(1.,frame.pv_dc_available_kw.sum()),
        grid_import_kwh=imports,self_sufficiency_percent=100*(1-imports/frame.demand_kw.sum()),
        battery_discharge_dc_kwh=float(frame.battery_discharge_dc_kw.sum()),
        equivalent_full_cycles=frame.battery_discharge_dc_kw.sum()/effective,
        soc_floor_kwh=float(frame.battery_soc_usable_kwh.min()),
        soc_end_kwh=float(frame.battery_soc_usable_kwh.iloc[-1]),
        annual_equipment_usd=float(equipment),annual_grid_import_usd=imports*model.IMPORT_USD_KWH,
        annual_total_usd=float(total),source_status='ENERGY_ONLY_NOT_AC_VALIDATED')

def monthly(id,frame):
    keys=['demand_kw','pv_dc_available_kw','curtailed_pv_dc_kw','grid_import_kw',
          'battery_charge_dc_kw','battery_discharge_dc_kw','inverter_ac_kw']
    grouped=frame[keys].groupby(frame.index.month).sum()
    return [dict(case_id=id,month=int(month),**{k+'_kwh':float(row[k]) for k in keys})
            for month,row in grouped.iterrows()]

def checked_reuse(path,expected,ctx):
    mpath=path/'energy_manifest.json'; cpath=path/'energy_hourly_2025.csv'
    if not path.exists():return None
    if not (mpath.is_file() and cpath.is_file()):raise RuntimeError('Partial output, inspect manually: '+str(path))
    m=json.loads(mpath.read_text(encoding='utf-8'))
    if (m.get('case_id')!=expected or m.get('input_manifest_sha256')!=digest(ctx['manifest'])
        or m.get('source_model_sha256')!=digest(ctx['repo']/'case1/studies/pypsa_joint_optimization_v1/model.py')
        ):
        raise RuntimeError('Existing output metadata mismatch: '+str(path))
    newline_mode=verify_energy_csv_signature(cpath,m.get('energy_csv_sha256'))
    if newline_mode=='EXACT_GIT_LF_TO_SIGNED_CRLF':
        print('REUSED_SIGNED_CSV_LINE_ENDINGS',expected,newline_mode,flush=True)
    frame=pd.read_csv(cpath,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    check_chronology(frame)
    return frame,m

def preflight_existing(ctx,profile,out):
    """Verify all existing signed output cases before any full-profile solves.

    Full profile explicitly reuses six published pilot solves. If any pilot
    folder is missing, stop rather than silently spending time recomputing it.
    This is a read-only source verification, not a PyPSA simulation.
    """
    if not out.is_absolute():out=ctx['repo']/out
    if profile=='full':
        missing=[x for x in PILOT_IDS if not (out/('energy_'+x)).is_dir()]
        if missing:
            raise FileNotFoundError('Full profile needs six existing signed pilot folders; missing '
                + ', '.join(missing) + '. Restore missing tracked outputs or inspect checkout.')
    reused=[]
    model=None
    for case_id in selected(profile):
        folder=out/('energy_'+case_id)
        if not folder.exists():continue
        frame,meta=checked_reuse(folder,case_id,ctx)
        if model is None:
            model=ctx['fh'].load_existing_pypsa_model(ctx['repo'])
        case_summary(case_id,CANDIDATES[case_id],frame,model,'new',meta.get('source_model_summary'))
        reused.append(case_id)
    return {'profile':profile,'source_reuse_checked':reused,
            'new_solves_expected':[x for x in selected(profile) if x not in reused],
            'preflight':'SOURCE_AND_PILOT_REUSE_PASS_NO_NUMERICAL_SOLVES'}


def run_one(case_id,ctx,out):
    design=CANDIDATES[case_id]
    validate_device(design)
    folder=out/('energy_'+case_id)
    existing=checked_reuse(folder,case_id,ctx)
    if existing is not None:
        frame,record=existing
        # Retest device and actual saved data, not just the filename / hash.
        return case_summary(case_id,design,frame,ctx['fh'].load_existing_pypsa_model(ctx['repo']),'new',record['source_model_summary']), 'REUSED_VERIFIED'
    fh=ctx['fh']; model=fh.load_existing_pypsa_model(ctx['repo'])
    hw=fh.Hardware(panels=design['panels'],battery_modules=design['modules'],
        battery_power_dc_kw=design['battery_kw'],inverter_kva=design['inverter_kva'],
        transformer_kva=5.,loading_pu=1.,load_pf=.98,export_policy='zero',
        annual_equipment_usd=float('nan'),annual_total_usd=float('nan'))
    frame,solved=fh.solve_fixed(ctx['repo'],hw,ctx['trace'].sum(axis=1),ctx['pv'],min_physical_soc=.20)
    frame.index.name='timestamp_lst'
    summary=case_summary(case_id,design,frame,model,'new',solved)
    # The manifest uses original Study A field names, so replay_ac can read it
    # later for independent balanced AC screening. No archived source is altered.
    record={'status':'FULL_8760H_FIXED_HARDWARE_FRONTIER_ENERGY_ONLY',
            'case_id':case_id,'scenario':'A1','transformer':'106039',
            'hardware_selection_tier':'frontier_'+case_id,'selected_house_ids':ctx['houses'],
            'hardware':{'pv_panels':design['panels'],'battery_modules':design['modules'],
                        'battery_power_dc_kw':design['battery_kw'],'inverter_kva':design['inverter_kva'],
                        'transformer_kva_assumed_or_evidenced':5.},
            'source_anchor_provenance':'NEW_FIXED_HARDWARE_8760H_PYPSA_SOURCE_MODEL',
            'economic_reoptimized_for_new_households':True,'hardware_reoptimized':False,
            'model_summary':solved,'metrics':summary,
            'source_model_summary':solved,
            'input_manifest_sha256':digest(ctx['manifest']),
            'source_model_sha256':digest(ctx['repo']/'case1/studies/pypsa_joint_optimization_v1/model.py'),
            'original_pv_source_sha256':digest(ctx['solar_path']),
            'note':'Zero export/ENS, 20% physical SOC and cyclic 8760-hour PyPSA; AC constraints checked separately. Historical USD, no field BOS/cables/protection.'}
    if folder.exists():raise FileExistsError('Refuse overwrite '+str(folder))
    # Write only after successful complete annual solve. Preserve any partial output for inspection.
    folder.mkdir(parents=True,exist_ok=False)
    cpath=folder/'energy_hourly_2025.csv'
    frame.to_csv(cpath,float_format='%.10f')
    record['energy_csv_sha256']=digest(cpath)
    (folder/'energy_manifest.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return summary,'NEW_VERIFIED'

def package_zip(out,zip_path):
    if zip_path.exists():raise FileExistsError('Refuse to overwrite '+str(zip_path))
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(out.rglob('*')):
            if f.is_file():z.write(f,arcname=out.name+'/'+str(f.relative_to(out)).replace('\\','/'))
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:raise RuntimeError('Output ZIP CRC failed')

def execute(ctx,profile,out,zipout):
    if not out.is_absolute():out=ctx['repo']/out
    out=out.resolve()
    if zipout:
        zp=Path(zipout)
        if not zp.is_absolute():zp=ctx['repo']/zp
        if zp.exists():raise FileExistsError('Protected frontier archive already exists: '+str(zp))
    out.mkdir(parents=True,exist_ok=True)
    model=ctx['fh'].load_existing_pypsa_model(ctx['repo'])
    results=[];month_rows=[];failures=[];reused=[];new=[]
    for id,design in REFERENCE.items():
        frame,meta,folder=ctx['baseline'][id]
        result=case_summary(id,design,frame,model,'reference',meta.get('source_model_summary'))
        result['reference_energy_manifest_sha256']=digest(folder/'energy_manifest.json')
        results.append(result);month_rows.extend(monthly(id,frame))
    for case_id in selected(profile):
        print('FRONTIER',case_id,flush=True)
        try:
            result,status=run_one(case_id,ctx,out)
            results.append(result)
            f=out/('energy_'+case_id)/'energy_hourly_2025.csv'
            frame=pd.read_csv(f,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
            month_rows.extend(monthly(case_id,frame))
            (reused if status=='REUSED_VERIFIED' else new).append(case_id)
        except Exception as exc:
            failures.append({'case_id':case_id,'error':str(exc)})
            print('UNRESOLVED_CASE',case_id,str(exc),flush=True)
    pd.DataFrame(results).to_csv(out/('FRONTIER_ANNUAL_SUMMARY_'+profile.upper()+'.csv'),index=False,float_format='%.9f')
    pd.DataFrame(month_rows).to_csv(out/('FRONTIER_MONTHLY_ENERGY_'+profile.upper()+'.csv'),index=False,float_format='%.9f')
    receipt={'study':ID,'profile':profile,'expected_new_cases':len(selected(profile)),
             'new_solved':new,'verified_reused':reused,'unresolved':failures,
             'signed_source_manifest_sha256':digest(ctx['manifest']),
             'solar_source_sha256':digest(ctx['solar_path']),
             'original_model_sha256':digest(ctx['repo']/'case1/studies/pypsa_joint_optimization_v1/model.py'),
             'reference_manifest_sha256':{i:digest(x[2]/'energy_manifest.json') for i,x in ctx['baseline'].items()},
             'status':'COMPLETE' if not failures else 'PARTIAL_WITH_UNRESOLVED_CASES',
             'note':'New cases only energy screened; baseline AC correction is not transferred to resized hardware.'}
    (out/('FRONTIER_RECEIPT_'+profile.upper()+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    if zipout:
        zp=Path(zipout)
        if not zp.is_absolute():zp=ctx['repo']/zp
        package_zip(out,zp.resolve());print('ZIP',zp,flush=True)
    print(json.dumps({k:receipt[k] for k in ['status','expected_new_cases','new_solved','verified_reused','unresolved']},indent=2))
    return 0 if not failures else 2

def cli(argv=None):
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--repo-root',type=Path,default=Path('.'))
    pa.add_argument('--profile',choices=('pilot','full'),default='pilot')
    mode=pa.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true')
    mode.add_argument('--preflight',action='store_true')
    mode.add_argument('--run',action='store_true')
    pa.add_argument('--out',default='StudyA_A1_106039_Utilization_v1')
    pa.add_argument('--zip-out',default='StudyA_A1_106039_Utilization_v1.zip')
    args=pa.parse_args(argv)
    for id,x in all_cases().items():validate_device(x)
    if args.plan:
        for i in ['MC_REF','SS_REF',*selected(args.profile)]:
            print(i,all_cases()[i],'SOURCE_REUSE' if i in REFERENCE else 'NEW_8760H_LP')
        return 0
    ctx=context(args.repo_root.resolve())
    print('SIGNED PREFLIGHT PASS, 11 A1/106039 households, year 2025, baseline references 2')
    reuse=preflight_existing(ctx,args.profile,Path(args.out))
    print(json.dumps(reuse,indent=2))
    if args.preflight:return 0
    return execute(ctx,args.profile,Path(args.out),args.zip_out)

if __name__=='__main__':sys.exit(cli())
