#!/usr/bin/env python3
"""Audit of supplied five-edge R*0.5 all-nine annual pandapower research output, no solver calls."""
import csv, datetime, hashlib, io, json, math, re, sys, zipfile
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path('/mnt/data')
SRC=ROOT/'StudyA_A0_94022_Annual_five_allnine_Results_v1.zip'
PILOT=ROOT/'StudyA_A0_94022_Annual_five_pilot_Results_v1.zip'
OUT=ROOT/'SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17'
OUT.mkdir(parents=True, exist_ok=True)
issues=[]; entries=[]; cases=set(); pilot_exact={}; fmt={}
expected_ts=pd.date_range('2025-01-01 00:00:00','2025-12-31 23:00:00',freq='h')
sha=lambda b: hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(SRC) as z, zipfile.ZipFile(PILOT) as zp:
    top=json.loads(z.read('ANNUAL_RUN_SUMMARY.json'))
    print('archive sha256',sha(SRC.read_bytes()),'top',top['status'],top['jobs'],top['passing_jobs'],top['failing_jobs'])
    if z.testzip():issues.append('corrupt archive')
    fn=z.namelist(); summaries=sorted([f for f in fn if f.endswith('/annual_network_ac_summary.json')]); hourlies=[f for f in fn if f.endswith('/annual_network_ac_hourly.csv')]
    if len(summaries)!=36 or len(hourlies)!=36 or len(fn)!=73:issues.append(f'unexpected archive members: {len(summaries)}, {len(hourlies)}, {len(fn)}')
    if len(top['results'])!=36:issues.append('top-level case count not 36')
    master={(i['case'],i['dispatch'],round(float(i['pf']),3),round(float(i['length_factor']),3)):i for i in top['results']}
    if len(master)!=36:issues.append('top master keys are duplicated')
    for f in summaries:
        base=f.rsplit('/',1)[0]; name=f.replace('annual_network_ac_summary.json','annual_network_ac_hourly.csv')
        js=json.loads(z.read(f)); raw=z.read(name); df=pd.read_csv(io.BytesIO(raw)); key=(js['case'],js['dispatch'],round(float(js['pf']),3),round(float(js['length_factor']),3))
        if key in cases:issues.append(f'duplicate case key: {key}')
        cases.add(key)
        parsed=re.fullmatch(r'five_A0_94022_(min_cost_ref|ss90_ref)_(causal|optimized)_pf(095|098|100)_l(10|13|16)',base)
        if not parsed:issues.append(f'unexpected folder {base}')
        else:
            tier,dispatch,pf,l=parsed.groups()
            if key!=(f'A0_94022_{tier}',dispatch,int(pf)/100,int(l)/10):issues.append('path-key mismatch '+base)
        if name not in fn:issues.append('missing matching hourly '+name)
        if js['hourly_sha256']!=sha(raw):issues.append('hash mismatch '+base)
        if js.get('bundle')!='five' or js.get('branch_indices')!=[7,4,14,11,16] or js.get('r_multiplier')!=0.5:issues.append('bundle mismatch '+base)
        if js.get('physical_cable_selection_validated')!=False:issues.append('physical validation claim '+base)
        if not js.get('annual_8760_AC_validated'):issues.append('annual validation flag false '+base)
        if len(df)!=8760 or js['hours']!=8760 or js['converged_hours']!=8760:issues.append('hour count mismatch '+base)
        ts=pd.to_datetime(df['timestamp_lst'],errors='coerce')
        if not ts.equals(pd.Series(expected_ts)):
            issues.append('timestamp mismatch '+base)
        if df['status'].isna().any() or not df['status'].astype(str).str.contains('CONVERGED').all():issues.append('some nonconverged '+base)
        nums=['min_v_pu','max_v_pu','max_trafo_pct','max_line_pct','line_losses_kw','trafo_losses_kw','inverter_ac_kw']
        for c in nums:
            if c not in df:issues.append('missing column '+c+' '+base)
            elif not np.isfinite(df[c].values).all():issues.append('non-finite '+c+' '+base)
        values=df['min_v_pu'].ge(.95-1e-9)&df['max_v_pu'].le(1.05+1e-9)&df['max_trafo_pct'].le(100+1e-9)&df['max_line_pct'].le(100+1e-9)
        if not np.array_equal(values.values,df['ac_feasible'].astype(bool).values):issues.append('independent AC status mismatch '+base)
        if int((~values).sum())!=js['AC_infeasible_hours'] or js['AC_infeasible_hours']!=0:issues.append('violation counts differ '+base)
        metric_checks={'min_v_pu':df['min_v_pu'].min(),'max_v_pu':df['max_v_pu'].max(),'max_transformer_pct':df['max_trafo_pct'].max(),'max_line_pct':df['max_line_pct'].max(),'annual_line_loss_kwh':df['line_losses_kw'].sum(),'annual_transformer_loss_kwh':df['trafo_losses_kw'].sum()}
        for n,v in metric_checks.items():
            if not math.isclose(v,js[n],abs_tol=1e-7, rel_tol=1e-9):issues.append('annual summary mismatch '+n+' '+base)
        if key not in master:issues.append('not in master '+base)
        else:
            m=master[key]
            for c in ['min_v_pu','max_v_pu','max_transformer_pct','annual_line_loss_kwh']:
                if not math.isclose(float(js[c]),float(m[c]),abs_tol=1e-8):issues.append('master mismatch '+c+' '+base)
            if m['AC_infeasible_hours']!=0:issues.append('master failure '+base)
        for m,d in js['selected_hour_numerical_reproduction'].items():
            if abs(d)>1e-8:issues.append('historical control mismatch '+base+' '+m)
        if base.endswith('_pf095_l16'):
            if name not in zp.namelist() or f not in zp.namelist():issues.append('pilot missing case '+base)
            else:
                p_exact= z.read(name)==zp.read(name) and z.read(f)==zp.read(f)
                pilot_exact[base]=p_exact
                if not p_exact:issues.append('pilot reuse byte mismatch '+base)
        entries.append({'case':js['case'],'dispatch':js['dispatch'],'pf':js['pf'],'length_factor':js['length_factor'],'bundle':'five','branch_indices':'7|4|14|11|16','hours':len(df),'converged_hours':int(df['status'].str.contains('CONVERGED').sum()),'violations_independent':int((~values).sum()),'v_min_pu':metric_checks['min_v_pu'],'v_min_timestamp':str(ts.iloc[df['min_v_pu'].idxmin()]),'v_max_pu':metric_checks['max_v_pu'],'peak_transformer_pct':metric_checks['max_transformer_pct'],'peak_transformer_timestamp':str(ts.iloc[df['max_trafo_pct'].idxmax()]),'peak_line_pct':metric_checks['max_line_pct'],'line_loss_kwh':metric_checks['annual_line_loss_kwh'],'trafo_loss_kwh':metric_checks['annual_transformer_loss_kwh'],'total_ac_loss_kwh':metric_checks['annual_line_loss_kwh']+metric_checks['annual_transformer_loss_kwh'],'hourly_sha256':sha(raw),'pilot_reused_byte_exact':pilot_exact.get(base,'N/A')})
    for pf in (.95,.98,1.0):
        for length in (1.,1.3,1.6):
            for tier in ('min_cost_ref','ss90_ref'):
                for disp in ('causal','optimized'):
                    if (f'A0_94022_{tier}',disp,pf,length) not in cases:issues.append('absent combination '+str((tier,disp,pf,length)))
report=pd.DataFrame(entries).sort_values(['case','dispatch','pf','length_factor']).reset_index(drop=True)
report.to_csv(OUT/'FIVE_BRANCH_36_ANNUAL_INDEPENDENT_AC_AUDIT.csv',index=False)
# Comparing conditional network variant to original portfolio overlays, without overwriting signed source records
prev=ROOT/'SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16/STUDYA_432_POST_A0_94022_PARTIAL_OVERLAY.csv'
source=pd.read_csv(prev)
source['hypothetical_five_edge_overlay']=False
source['hypothetical_five_edge_scope']='ORIGINAL_SITE_NETWORK'
source['conditional_five_edge_violation_hours']=source['adjusted_bad_hours'].astype(int)
source['conditional_five_edge_min_voltage_pu']=np.nan
source['conditional_five_edge_trafo_max_pct']=np.nan
source['conditional_five_edge_total_ac_loss_kwh']=np.nan
nchanged=0;nrestored=0
for r in entries:
    tier='min_cost' if r['case'].endswith('min_cost_ref') else 'ss90'
    mask=(source['scenario']=='A0')&(source['transformer'].astype(str)=='94022')&(source['tier']==tier)&(source['hardware_family']=='archived_reference')&(source['dispatch']==r['dispatch'])&(np.isclose(source['pf'],r['pf']))&(np.isclose(source['length_factor'],r['length_factor']))
    if mask.sum()!=1:issues.append('portfolio join mismatch '+str((r['case'],r['dispatch'],r['pf'],r['length_factor'],int(mask.sum()))))
    else:
        ix=source.index[mask][0]
        source.at[ix,'hypothetical_five_edge_overlay']=True
        source.at[ix,'hypothetical_five_edge_scope']='REVISED_R_ONLY_5_MODEL_EDGES_NOT_FIELD_VERIFIED'
        source.at[ix,'conditional_five_edge_violation_hours']=0
        source.at[ix,'conditional_five_edge_min_voltage_pu']=r['v_min_pu']
        source.at[ix,'conditional_five_edge_trafo_max_pct']=r['peak_transformer_pct']
        source.at[ix,'conditional_five_edge_total_ac_loss_kwh']=r['total_ac_loss_kwh']
        nchanged+=1
        if int(source.at[ix,'adjusted_bad_hours'])>0:nrestored+=1
source.to_csv(OUT/'PORTFOLIO_432_ORIGINAL_PLUS_CONDITIONAL_FIVE_EDGE_OVERLAY.csv',index=False)
original_fail=(source['adjusted_bad_hours']>0).sum()
original_94022_bad_hours=int(source[(source['scenario']=='A0')&(source['transformer']==94022)]['adjusted_bad_hours'].sum())
alt_fail=(source['conditional_five_edge_violation_hours']>0).sum()
summary={
'archive_filename':SRC.name,'archive_sha256':sha(SRC.read_bytes()),
'independent_audit_status':'PASS' if not issues else 'ISSUES_FOUND',
'issues':issues,
'file_members':len(fn),'annual_cases':len(report),'complete_hourly_rows':int(report['hours'].sum()),'source_hourly_sha_checks_passed':len(entries) if not any('hash mismatch' in x for x in issues) else None,
'converged_hours':int(report['converged_hours'].sum()),'total_violations':int(report['violations_independent'].sum()),
'pilot_four_case_byte_exact':pilot_exact,'source_master_status':top['status'],'source_master_pass':top['passing_jobs'],'source_master_fail':top['failing_jobs'],
'overall_worst_min_voltage_pu':float(report.v_min_pu.min()),'overall_max_voltage_pu':float(report.v_max_pu.max()),'overall_peak_transformer_pct':float(report.peak_transformer_pct.max()),'overall_peak_line_pct':float(report.peak_line_pct.max()),
'weakest_case':report.loc[report.v_min_pu.idxmin()].to_dict(),
'portfolio_432_original_overlay_failing':int(original_fail),'portfolio_432_original_overlay_passing':int(432-original_fail),
'a0_94022_pre_retrofit_after_seq_remaining_violation_hours':original_94022_bad_hours,
'conditional_five_edge_overlay_rows':int(nchanged),'conditionally_restored_scenario_runs':int(nrestored),
'portfolio_432_conditional_combined_failing':int(alt_fail),'portfolio_432_conditional_combined_passing':int(432-alt_fail),
'not_equivalent_to_original_studyA_network':True,
'not_physical_cable_validation':True,
'not_ac_constrained_energy_optimization':True
}
(OUT/'INDEPENDENT_QA.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('weakest_case','pilot_four_case_byte_exact')},indent=2,default=str))
print('BY TIER',report.groupby(['case','dispatch']).agg(minv=('v_min_pu','min'),trafo=('peak_transformer_pct','max'),line=('peak_line_pct','max'),lossmin=('total_ac_loss_kwh','min'),lossmax=('total_ac_loss_kwh','max')).round(6).to_string())
print('pilot exact',pilot_exact)
if issues:sys.exit(1)
