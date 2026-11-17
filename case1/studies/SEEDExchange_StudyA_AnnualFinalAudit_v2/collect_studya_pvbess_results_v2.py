#!/usr/bin/env python3
"""Study A PV+BESS 2025 annual evidence collector v2, read-only.

From the repository root, in Miniforge or Anaconda Prompt:
  python collect_studya_pvbess_results_v2.py --repo-root . --out StudyA_PVBESS_Annual_Result_Summary_FINAL.zip

Audits 22 energy + 22 causal + 432 AC outputs, checks each 2025 hourly
chronology and SHA256, validates AC metadata and unique case dimensions, and
creates a concise ZIP with signed source summaries, receipts, inventories and
comparison tables. Does NOT modify the simulation data or invoke any solver.
Windows long paths use extended-length syntax strictly for filesystem I/O.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys
import zipfile

BASE = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
MANIFEST_REL = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json')
EXPECT = {'energy':22, 'causal':22, 'ac':432}
HOUR_LABELS = tuple((datetime(2025,1,1) + timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(8760))


def winpath(path:Path)->Path:
    """Use Windows NT extended syntax for filesystem I/O, never for archive names."""
    path=Path(path)
    if sys.platform!='win32':return path
    s=str(path if path.is_absolute() else path.absolute())
    if s.startswith('\\\\?\\'):return path
    if s.startswith('\\\\'):return Path('\\\\?\\UNC\\'+s[2:])
    return Path('\\\\?\\'+s)


def load_json(path:Path):
    with winpath(path).open('r',encoding='utf-8') as f:return json.load(f)


def digest_and_chronology(path:Path):
    h=hashlib.sha256()
    with winpath(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    with winpath(path).open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f)
        hdr=next(reader,[])
        if 'timestamp_lst' not in hdr: raise ValueError('Missing timestamp_lst column')
        t_index=hdr.index('timestamp_lst')
        total=0
        first=None; last=None; bad=0
        for row in reader:
            if not row:continue
            val=row[t_index] if len(row)>t_index else ''
            if first is None:first=val
            last=val
            if total>=8760 or val!=HOUR_LABELS[total]:
                bad+=1
            total+=1
    return {'sha256':h.hexdigest(),'hours':total,'first_timestamp':first,'last_timestamp':last,
            'chronology_exact_2025': total==8760 and bad==0}


def boolish(v):
    if isinstance(v,bool):return v
    return str(v).strip().lower() in ('true','1')


def ac_record(meta:dict,case_name:str):
    cols=('scenario','transformer','tier','topology','dispatch','pf','length_factor')
    row={key:meta.get(key,'') for key in cols}
    row.update(case=case_name,households=len(meta.get('selected_house_ids',[])),
        hours=meta.get('hours'),converged_hours=meta.get('converged_hours'),
        nonconverged_hours=meta.get('nonconverged_hours'),
        infeasible_hours=meta.get('AC_infeasible_hours'),
        below_095_hours=meta.get('voltage_below_095_hours'),
        transformer_overload_hours=meta.get('transformer_overload_hours'),
        minimum_voltage_pu=meta.get('min_voltage_pu'),
        maximum_transformer_loading_pct=meta.get('max_transformer_loading_pct'),
        annual_network_losses_kwh=meta.get('annual_or_sample_losses_kwh'),
        recovered_summary='recovery_provenance' in meta,
        input_manifest_sha256=meta.get('input_manifest_sha256',''))
    return row


def cases(outbase:Path):
    for kind,pattern,sname,cname,hfield in (
        ('energy','energy_*','energy_manifest.json','energy_hourly_2025.csv','energy_csv_sha256'),
        ('causal','causal_*','causal_summary.json','causal_pv_first_2025.csv','output_sha256')):
        for folder in sorted(outbase.glob(pattern)):
            if winpath(folder).is_dir():yield kind,folder,sname,cname,hfield
    acdir=outbase/'annual_ac_replays_v1'
    if winpath(acdir).is_dir():
        for folder in sorted(acdir.iterdir()):
            if winpath(folder).is_dir():yield 'ac',folder,'ac_summary.json','ac_hourly.csv','ac_hourly_sha256'


def csv_text(rows,fields):
    buf=io.StringIO(newline='')
    writer=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore');writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def add_file(z:zipfile.ZipFile,path:Path,root:Path):
    arcname=path.relative_to(root).as_posix()
    with winpath(path).open('rb') as src,z.open(arcname,mode='w') as dst:
        shutil.copyfileobj(src,dst,1<<20)


def run(root:Path,destination:Path,include_hourly:bool=False,progress:int=50):
    root=root.resolve();outbase=root/BASE
    if not winpath(outbase).is_dir():raise ValueError(f'Missing results directory: {outbase}')
    if destination.exists():raise FileExistsError('Refusing to overwrite existing ZIP: '+str(destination))
    if destination.is_relative_to(outbase):raise ValueError('ZIP must be outside results directory')
    if not destination.parent.is_dir():raise ValueError('ZIP parent directory does not exist')
    original_manifest=root/MANIFEST_REL
    manifest_sha=''
    if winpath(original_manifest).is_file():
        with winpath(original_manifest).open('rb') as f:manifest_sha=hashlib.sha256(f.read()).hexdigest()
    inventory=[];ac_rows=[];energy_rows=[];causal_rows=[];files_to_zip=[];seen_ac=set()
    found=list(cases(outbase))
    for n,(kind,folder,summary_name,hourly_name,hash_key) in enumerate(found,1):
        summary=folder/summary_name;hourly=folder/hourly_name
        errors=[];m={};stats={}
        if not winpath(summary).is_file():errors.append('SUMMARY_MISSING')
        else:
            try:m=load_json(summary)
            except Exception as ex:errors.append('SUMMARY_UNREADABLE:'+type(ex).__name__)
        if not winpath(hourly).is_file():errors.append('HOURLY_MISSING')
        else:
            try:stats=digest_and_chronology(hourly)
            except Exception as ex:errors.append('HOURLY_UNREADABLE:'+type(ex).__name__+':'+str(ex)[:100])
        if stats:
            if not stats['chronology_exact_2025']:errors.append('NOT_EXACT_2025_CHRONOLOGY')
            if m.get(hash_key)!=stats['sha256']:errors.append('HASH_MISMATCH_OR_MISSING')
        if manifest_sha and m.get('input_manifest_sha256')!=manifest_sha:
            errors.append('INPUT_MANIFEST_HASH_MISMATCH')
        if kind=='ac' and m:
            if m.get('status')!='ANNUAL_PVBESS_AC':errors.append('UNEXPECTED_AC_STATUS')
            if (m.get('hours')!=8760 or m.get('converged_hours')!=8760 or m.get('nonconverged_hours')!=0):
                errors.append('INCOMPLETE_AC_CONVERGENCE')
            if len(m.get('selected_house_ids',[]))<4:errors.append('UNEXPECTED_HOUSE_COUNT')
            try:
                key=(str(m['scenario']),str(m['transformer']),str(m['tier']),str(m['topology']),str(m['dispatch']),round(float(m['pf']),4),round(float(m['length_factor']),4))
                if key in seen_ac:errors.append('DUPLICATE_AC_DIMENSIONS')
                seen_ac.add(key)
                if key[0] not in ('A0','A1') or key[4] not in ('optimized','causal') or key[5] not in (0.95,0.98,1.0) or key[6] not in (1.,1.3,1.6):
                    errors.append('UNEXPECTED_AC_DIMENSIONS')
                if key[3] not in ('star','mst','mapped') or (key[1]=='92395') != (key[3] in ('star','mst')):
                    errors.append('INVALID_TOPOLOGY_LABEL')
            except (KeyError,ValueError,TypeError):errors.append('MISSING_AC_DIMENSIONS')
            for a in ('AC_infeasible_hours','voltage_below_095_hours','transformer_overload_hours'):
                try:
                    v=float(m[a]);
                    if not math.isfinite(v) or not 0<=v<=8760:errors.append('INVALID_'+a)
                except (KeyError,TypeError,ValueError):errors.append('MISSING_'+a)
            for a in ('min_voltage_pu','max_transformer_loading_pct','annual_or_sample_losses_kwh'):
                try:
                    if not math.isfinite(float(m[a])):errors.append('NONFINITE_'+a)
                except (KeyError,TypeError,ValueError):errors.append('MISSING_'+a)
            row=ac_record(m,folder.name)
            row['audit_issue']=';'.join(errors) if errors else 'NONE'
            ac_rows.append(row)
        if kind=='energy' and m:
            hw=m.get('hardware',{});met=m.get('metrics',{})
            energy_rows.append(dict(case=folder.name,scenario=m.get('scenario'),transformer=m.get('transformer'),
                tier=m.get('hardware_selection_tier'),households=len(m.get('selected_house_ids',[])),
                panels=hw.get('pv_panels'),battery_modules=hw.get('battery_modules'),
                inverter_kva=hw.get('inverter_kva'),battery_power_dc_kw=hw.get('battery_power_dc_kw'),
                demand_kwh=met.get('demand_kwh'),self_sufficiency_pct=met.get('self_sufficiency_pct'),
                imports_kwh=met.get('grid_import_kwh'),curtailment_kwh=met.get('curtailed_pv_dc_kwh'),
                equivalent_battery_cycles=met.get('approx_equivalent_full_discharge_cycles'),
                annual_cost_usd=m.get('source_model_summary',{}).get('annual_total_usd'),
                audit_issue=';'.join(errors) if errors else 'NONE'))
        if kind=='causal' and m:
            met=m.get('metrics',{})
            causal_rows.append(dict(case=folder.name,scenario=m.get('scenario'),transformer=m.get('transformer'),
                tier=m.get('hardware_tier'),self_sufficiency_pct=met.get('self_sufficiency_pct'),
                imports_kwh=met.get('grid_import_kwh'),curtailment_kwh=met.get('curtailed_pv_dc_kwh'),
                terminal_minus_initial_store_kwh=met.get('terminal_minus_initial_store_kwh'),
                audit_issue=';'.join(errors) if errors else 'NONE'))
        inventory.append(dict(kind=kind,case=folder.name,summary_present=winpath(summary).is_file(),
             hourly_present=winpath(hourly).is_file(),rows=stats.get('hours',''),
             chronology_2025=stats.get('chronology_exact_2025',False),
             expected_sha256=m.get(hash_key,''),actual_sha256=stats.get('sha256',''),
             status=m.get('status',''),audit_issue=';'.join(errors) if errors else 'NONE'))
        if winpath(summary).is_file():files_to_zip.append(summary)
        if include_hourly and winpath(hourly).is_file():files_to_zip.append(hourly)
        if progress and n%progress==0:print(f'Checked {n}/{len(found)} case folders',flush=True)

    bykind={k:sum(x['kind']==k for x in inventory) for k in EXPECT}
    valid={k:sum(x['kind']==k and x['audit_issue']=='NONE' for x in inventory) for k in EXPECT}
    ac_baseline=[r for r in ac_rows if r['pf']==.98 and r['length_factor']==1.0]
    ac_sens=[r for r in ac_rows if not (r['pf']==.98 and r['length_factor']==1.0)]
    percombo={}
    for r in ac_rows:
        try:
            tup=(r['scenario'],str(r['transformer']),r['tier'],r['topology'],r['dispatch'])
            percombo[tup]=percombo.get(tup,0)+1
        except KeyError:continue
    coverage=[{'scenario':key[0],'transformer':key[1],'tier':key[2],
               'topology':key[3],'dispatch':key[4],'pf_length_cases_found':count,
               'expected':9} for key,count in sorted(percombo.items())]
    coverage_ok=(len(coverage)==48 and all(x['pf_length_cases_found']==9 for x in coverage))
    issues=[{'kind':r['kind'],'case':r['case'],'issue':r['audit_issue']}
           for r in inventory if r['audit_issue']!='NONE']
    receipts=sorted(outbase.glob('annual_*receipt_*.json'))
    receipt_out=[]
    for path in receipts:
        try:
            d=load_json(path)
            receipt_out.append({'file':path.name,'requested':d.get('requested'),
                'completed_new':d.get('completed_new'),
                'reused_verified':d.get('reused_verified'),
                'blocked_or_failed':d.get('blocked_or_failed'),
                'status':d.get('status')})
            files_to_zip.append(path)
        except Exception as e:issues.append({'kind':'receipt','case':path.name,'issue':'UNREADABLE_RECEIPT:'+str(e)})
    if winpath(original_manifest).is_file():files_to_zip.append(original_manifest)
    report={'collector_version':'2.0','generated_utc':datetime.now(timezone.utc).isoformat(),
        'model_year':2025,'expected':EXPECT,'found':bykind,'signed_chronology_verified':valid,
        'ac_baseline_found':len(ac_baseline),'ac_sensitivity_found':len(ac_sens),
        'distinct_ac_design_dispatch_pairs':len(coverage),'ac_design_dispatch_9_case_coverage_complete':coverage_ok,
        'all_expected_verified':bykind==EXPECT and valid==EXPECT and coverage_ok and not issues,
        'issues':issues,'receipts':receipt_out,'includes_raw_hourly':include_hourly,
        'verification_method':'Each CSV SHA256 is checked against its signed summary, all 8760 timestamps compared to the exact 2025 LST chronology, AC metadata dimensions and convergence checked, signed input manifest compared. Not an independent pandapower rerun.'}
    tabdefs=[('CASE_INVENTORY.csv',inventory,['kind','case','summary_present','hourly_present','rows','chronology_2025','expected_sha256','actual_sha256','status','audit_issue']),
        ('AC_432_CASE_METRICS.csv',ac_rows,['case','scenario','transformer','tier','topology','dispatch','households','pf','length_factor','hours','converged_hours','nonconverged_hours','infeasible_hours','below_095_hours','transformer_overload_hours','minimum_voltage_pu','maximum_transformer_loading_pct','annual_network_losses_kwh','recovered_summary','input_manifest_sha256','audit_issue']),
        ('ENERGY_22_CASE_METRICS.csv',energy_rows,['case','scenario','transformer','tier','households','panels','battery_modules','inverter_kva','battery_power_dc_kw','demand_kwh','self_sufficiency_pct','imports_kwh','curtailment_kwh','equivalent_battery_cycles','annual_cost_usd','audit_issue']),
        ('CAUSAL_22_CASE_METRICS.csv',causal_rows,['case','scenario','transformer','tier','self_sufficiency_pct','imports_kwh','curtailment_kwh','terminal_minus_initial_store_kwh','audit_issue']),
        ('AC_48_DESIGN_COVERAGE.csv',coverage,['scenario','transformer','tier','topology','dispatch','pf_length_cases_found','expected'])]
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        z.writestr('COLLECTION_REPORT.json',json.dumps(report,indent=2))
        for name,rows,fields in tabdefs:z.writestr(name,csv_text(rows,fields))
        for f in files_to_zip:add_file(z,f,root)
    print(json.dumps({'zip':str(destination),'found':bykind,'verified':valid,
       'baseline_ac':len(ac_baseline),'sensitivity_ac':len(ac_sens),
       'coverage_48x9':coverage_ok,'issue_count':len(issues),
       'all_expected_verified':report['all_expected_verified'],
       'zip_mb':round(destination.stat().st_size/(1024*1024),2)},indent=2))
    if issues:print('Do not infer complete audit from the receipt alone. Upload this ZIP for diagnosis.')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--out',type=Path,default=Path('StudyA_PVBESS_Annual_Result_Summary_FINAL.zip'))
    ap.add_argument('--include-hourly',action='store_true',help='Include all hourly CSVs. Large; not necessary for first review.')
    a=ap.parse_args()
    root=a.repo_root.resolve()
    output=(root/a.out).resolve() if not a.out.is_absolute() else a.out.resolve()
    run(root,output,a.include_hourly)

if __name__=='__main__':main()
