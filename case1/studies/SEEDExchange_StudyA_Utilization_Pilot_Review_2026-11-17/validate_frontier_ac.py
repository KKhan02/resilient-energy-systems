#!/usr/bin/env python3
"""Independent 2025 annual A1 106039 pandapower screen for NEW fixed-hardware PV/BESS designs.

Loads the original local signed v6.2 inputs and local full-year PyPSA outputs; never
changes the signed source, reference dispatch, or existing AC outputs. Selected cases
must receive their OWN full-year replay; earlier reference AC corrections do not transfer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import numpy as np
import pandas as pd

CASES=('SS_B9','MC_B9','SS_B10','SS_P45','SS_P41_KEEP20','MC_P37')
FACTORS={'stress':[(.95,1.6)],'reference':[(.98,1.0)],
         'all-nine':[(pf,length) for pf in (.95,.98,1.) for length in (1.,1.3,1.6)]}
EXPECTED=pd.date_range('2025-01-01',periods=8760,freq='h')
REQUIRED={'status','ac_feasible','min_v_pu','max_v_pu','max_trafo_pct','max_line_pct','timestamp_lst'}


def xp(path):
    s=str(Path(path).resolve())
    if os.name=='nt' and not s.startswith('\\\\?\\'):
        s='\\\\?\\UNC\\'+s[2:] if s.startswith('\\\\') else '\\\\?\\'+s
    return s


def sha(path):
    h=hashlib.sha256()
    with open(xp(path),'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def save_json(path,doc):
    with open(xp(path),'w',encoding='utf-8') as f:json.dump(doc,f,indent=2,allow_nan=False)


def case_plan(case_ids,mode):
    if mode not in FACTORS:raise ValueError('Unknown factor mode')
    c=case_ids.split(',') if isinstance(case_ids,str) else list(case_ids)
    if not c or len(set(c))!=len(c) or any(k not in CASES for k in c):raise ValueError('Unknown or duplicate case name')
    return [(k,pf,lf) for k in c for pf,lf in FACTORS[mode]]


def valid_ac(df):
    if not REQUIRED.issubset(df):raise ValueError('Missing AC result columns')
    if df[list(('min_v_pu','max_v_pu','max_trafo_pct','max_line_pct'))].isna().any().any():
        raise ValueError('Non-finite AC metric')
    return ((df.status=='CONVERGED') & (df.min_v_pu>=.95-1e-10) & (df.max_v_pu<=1.05+1e-10) &
            (df.max_trafo_pct<=100+1e-9) & (df.max_line_pct<=100+1e-9))


def signed_energy(repo,root,cid,st,ctx):
    d=root/('energy_'+cid)
    df,m=st.validated_energy_directory(d,ctx['m'],ctx['mp'],'A1','106039',ctx['houses'],ctx['trace'])
    if m.get('case_id')!=cid or m.get('status')!='FULL_8760H_FIXED_HARDWARE_FRONTIER_ENERGY_ONLY':
        raise ValueError('Not a frontier source: '+cid)
    if m.get('source_model_sha256')!=sha(repo/'case1/studies/pypsa_joint_optimization_v1/model.py'):
        raise ValueError('Original fixed-hardware model changed')
    if m.get('original_pv_source_sha256')!=sha(ctx['solar_path']):
        raise ValueError('Solar reference changed')
    if len(df)!=8760 or not df.index.equals(EXPECTED):raise ValueError('Wrong 2025 chronology')
    hw=m['hardware']
    modules=int(hw['battery_modules']);bp=float(hw['battery_power_dc_kw']);inv=float(hw['inverter_kva'])
    if bp>2.24*modules+1e-6 or bp>inv*1.152+1e-6:raise ValueError('Hardware current/port screen')
    if float(hw['pv_panels'])*.435>1.5*inv+1e-6:raise ValueError('DC/AC panel ratio')
    if abs(df.grid_export_kw).max()>1e-6 or abs(df.unserved_kw).max()>1e-6:
        raise ValueError('Zero export/ENS source violated')
    if df.battery_soc_usable_kwh.min() < .229*modules-1e-5:
        raise ValueError('20pct SOC floor source violated')
    return df,m,sha(d/'energy_manifest.json')


def make_context(repo):
    code=repo/'case1/studies/SEEDExchange_StudyA_PVBESS_v1'
    epm=repo/'case1/studies/epm_gis_pandapower_v1'
    for folder in (str(code),str(epm)):
        if folder not in sys.path:sys.path.insert(0,folder)
    import study_a_pvbess as st
    m,v6,mapping,profiles=st.secure_context(repo,repo/st.MANIFEST_REL)
    houses,trace=st.source_trace(m,mapping,profiles,'A1','106039')
    _,solar_path=st.solar_per_unit(repo,trace.index)
    if len(houses)!=11 or abs(float(trace.to_numpy().sum())-20878.)>.01:
        raise ValueError('11-house source changed')
    return st,dict(m=m,v6=v6,mp=repo/st.MANIFEST_REL,houses=houses,trace=trace,solar_path=solar_path)


def check_saved(case_dir,provenance):
    c=case_dir/'ac_hourly.csv'; j=case_dir/'ac_summary.json'
    exists=os.path.isfile(xp(c)),os.path.isfile(xp(j))
    if not any(exists):return None
    if not all(exists):raise ValueError('Partial existing AC output. Preserve and inspect: '+str(case_dir))
    with open(xp(j),encoding='utf-8') as f:meta=json.load(f)
    for k,v in provenance.items():
        if meta.get(k)!=v:raise ValueError('Existing AC provenance mismatch: '+k)
    if meta.get('ac_hourly_sha256')!=sha(c):raise ValueError('AC CSV checksum changed')
    d=pd.read_csv(xp(c))
    if len(d)!=8760 or not pd.to_datetime(d.timestamp_lst).equals(pd.Series(EXPECTED)):
        raise ValueError('Saved AC chronology invalid')
    if not np.isfinite(d[['min_v_pu','max_v_pu','max_trafo_pct','max_line_pct']].to_numpy(float)).all():
        raise ValueError('Saved AC has nonfinite electrical output')
    if not valid_ac(d).equals(d.ac_feasible.astype(bool)):
        raise ValueError('Saved AC flags mismatch')
    if int((~d.ac_feasible.astype(bool)).sum())!=meta['AC_infeasible_hours']:
        raise ValueError('Saved AC failure count mismatch')
    return meta


def run_case(repo,energy_root,out,cid,pf,lf,st,ctx,pp,build_net):
    df,m,e_sha=signed_energy(repo,energy_root,cid,st,ctx)
    case_dir=out/f'{cid}_pf{round(pf*100):03d}_l{round(lf*10):02d}'
    ident={'case_id':cid,'scenario':'A1','transformer':'106039',
           'pf':pf,'length_factor':lf,'2025_hours':8760,
           'new_energy_manifest_sha256':e_sha,'source_v6_2_sha256':sha(repo/st.RUNNER_REL),
           'input_manifest_sha256':sha(ctx['mp']),
           'q_ratio_daylight':.25,'night_q_disabled':True,
           'method':'independent_hourly_balanced_pandapower_replay'}
    prior=check_saved(case_dir,ident)
    if prior is not None:return prior,'REUSED_VERIFIED'
    if os.path.exists(xp(case_dir)):
        raise FileExistsError('Empty or partial existing result directory: '+str(case_dir))
    os.makedirs(xp(case_dir),exist_ok=False)
    territory=ctx['v6'].new_territory(repo,'A1','106039',ctx['houses'],lf)
    net,nodes=build_net(territory,'head')
    if set(nodes['loads'])!=set(ctx['houses']):raise ValueError('Wrong household members in network')
    kva=float(m['hardware']['inverter_kva']);records=[]
    for i,t in enumerate(ctx['trace'].index):
        rec=ctx['v6'].solve_ac_hour(net,nodes,territory,t,ctx['trace'].iloc[i],pf,
             float(df.inverter_ac_kw.iloc[i]),kva,float(df.pv_dc_available_kw.iloc[i]),.25,9,'pvbess',pp)
        records.append(rec)
        if (i+1)%500==0:print(f'AC {cid} pf{pf} length{lf}: {i+1}/8760',flush=True)
    d=pd.DataFrame(records)
    if not REQUIRED.issubset(d):raise ValueError('Missing source solver outputs')
    if len(d)!=8760 or not pd.to_datetime(d.timestamp_lst).equals(pd.Series(EXPECTED)):
        raise ValueError('New AC chronology mismatch')
    conv=int((d.status=='CONVERGED').sum());failed=8760-conv
    # Non-convergence is a failure. Write evidence anyway; do not report a passing design.
    bad=int((~d.ac_feasible.astype(bool)).sum());voltage=int(((d.min_v_pu<.95)|(d.max_v_pu>1.05)).sum())
    thermal=int(((d.max_trafo_pct>100)|(d.max_line_pct>100)).sum())
    c=case_dir/'ac_hourly.csv';d.to_csv(xp(c),index=False,float_format='%.10f')
    outdoc={**ident,'status':'FULL_ANNUAL_AC_VERIFIED_RESULTS_WITH_EXPLICIT_FAILURES',
      'converged_hours':conv,'nonconverged_hours':failed,'AC_infeasible_hours':bad,
      'voltage_violation_hours':voltage,'thermal_violation_hours':thermal,
      'min_voltage_pu':float(d.min_v_pu.min()) if conv else None,
      'max_voltage_pu':float(d.max_v_pu.max()) if conv else None,
      'max_trafo_pct':float(d.max_trafo_pct.max()) if conv else None,
      'max_line_pct':float(d.max_line_pct.max()) if conv else None,
      'losses_kwh':float(d.loss_kw.sum()) if conv==8760 else None,
      'ac_hourly_sha256':sha(c)}
    save_json(case_dir/'ac_summary.json',outdoc)
    return outdoc,'NEW'


def export_zip(root,outpath):
    if os.path.isfile(xp(outpath)):raise FileExistsError('Refuse overwrite '+str(outpath))
    with zipfile.ZipFile(xp(outpath),'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(xp(p),arcname=root.name+'/'+str(p.relative_to(root)).replace('\\','/'))
    with zipfile.ZipFile(xp(outpath)) as z:
        if z.testzip():raise ValueError('Output zip CRC failure')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--energy-root',type=Path,default=Path('StudyA_A1_106039_Utilization_v1'))
    ap.add_argument('--out',type=Path,default=Path('StudyA_A1_106039_Utilization_AC_v1'))
    ap.add_argument('--zip-out',type=Path,default=Path('StudyA_A1_106039_Utilization_AC_stress_v1.zip'))
    ap.add_argument('--cases',default='SS_B9,MC_B9')
    ap.add_argument('--mode',choices=tuple(FACTORS),default='stress')
    ap.add_argument('--preflight',action='store_true')
    args=ap.parse_args(argv)
    repo=args.repo_root.resolve();root=args.energy_root.resolve();out=args.out.resolve()
    plan=case_plan(args.cases,args.mode)
    st,ctx=make_context(repo)
    checked={}
    for case,pf,lf in plan:
        if case not in checked:
            frame,meta,s=signed_energy(repo,root,case,st,ctx)
            checked[case]=dict(source_manifest_sha256=s,pv_panels=meta['hardware']['pv_panels'],
                          battery_modules=meta['hardware']['battery_modules'],
                          inverter_kva=meta['hardware']['inverter_kva'])
    if args.preflight:
        print(json.dumps(dict(status='PREFLIGHT_PASS_NO_SOLVER',jobs=len(plan),cases=checked,
             factor_grid=args.mode,source_2025_hours=8760),indent=2));return
    if os.path.isfile(xp(args.zip_out.resolve())):raise FileExistsError('ZIP already exists')
    from run_epm_validation import build_net
    import pandapower as pp
    os.makedirs(xp(out),exist_ok=True)
    items=[]
    for case,pf,lf in plan:
        doc,state=run_case(repo,root,out,case,pf,lf,st,ctx,pp,build_net)
        items.append({**{k:doc[k] for k in ('case_id','pf','length_factor','converged_hours','AC_infeasible_hours','min_voltage_pu','max_trafo_pct')},
           'execution':state})
    pd.DataFrame(items).to_csv(xp(out/'PORTFOLIO_AC_RECEIPT.csv'),index=False)
    summary=dict(status='NEW_AC_PILOT_COMPLETE_WITH_EXPLICIT_FAILURES',items=items,
       job_count=len(items),reused=sum(x['execution']=='REUSED_VERIFIED' for x in items),
       blocked=0,AC_failed_cases=sum(x['AC_infeasible_hours']>0 for x in items),
       scope='NEW_FRONTIER_DISPATCH_AC_ONLY_NOT_EQUIPMENT_OR_NETWORK_CERTIFICATION')
    save_json(out/'PORTFOLIO_AC_RECEIPT.json',summary)
    export_zip(out,args.zip_out.resolve())
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
