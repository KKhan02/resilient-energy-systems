#!/usr/bin/env python3
"""Read-only collection of Study A PV+BESS annual portfolio evidence.

Run from repository root in Miniforge Prompt / Anaconda Prompt:
  python collect_studya_pvbess_results.py --repo-root .

Outputs a compact ZIP of JSON summaries, receipts and a cryptographic hourly
CSV inventory. Does not include huge hourly CSV files or edit simulation outputs.
Optionally --include-hourly to include all hourly CSV data (can be very large).
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import zipfile

RESULT_REL = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
MANIFEST_REL = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json')
EXPECTED = {'energy':22, 'causal':22, 'ac':432}


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        return {'_collector_parse_error':str(e)}


def csv_stats(path: Path):
    # Count actual records. Do not trust newline counts or file names as full-year evidence.
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f)
        head=next(reader,[])
        count=0
        for row in reader:
            if row: count+=1
    return count, bool(head)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--out',type=Path,default=Path('StudyA_PVBESS_Annual_Result_Summary.zip'))
    parser.add_argument('--include-hourly',action='store_true',help='Include all hourly CSVs in ZIP (large)')
    a=parser.parse_args()
    root=a.repo_root.resolve()
    res=root/RESULT_REL
    if not res.is_dir():parser.error('Study A results folder does not exist: '+str(res))
    dest=(root/a.out).resolve() if not a.out.is_absolute() else a.out.resolve()
    if dest.is_relative_to(res):parser.error('Choose an output ZIP OUTSIDE simulation results')
    if dest.exists():parser.error('Destination ZIP already exists, do not overwrite: '+str(dest))
    if not dest.parent.is_dir():parser.error('ZIP output parent must exist: '+str(dest.parent))

    candidates=[]
    for case_type,prefix,summary_name,hourly_name,hash_name in [
        ('energy','energy_','energy_manifest.json','energy_hourly_2025.csv','energy_csv_sha256'),
        ('causal','causal_','causal_summary.json','causal_pv_first_2025.csv','output_sha256')]:
        for case in sorted(res.glob(prefix+'*')):
            if case.is_dir():candidates.append((case_type,case,summary_name,hourly_name,hash_name))
    acparent=res/'annual_ac_replays_v1'
    if acparent.is_dir():
        for case in sorted(acparent.iterdir()):
            if case.is_dir():candidates.append(('ac',case,'ac_summary.json','ac_hourly.csv','ac_hourly_sha256'))
    if not candidates:parser.error('No annual results folders were found under: '+str(res))
    items=[]; included=[]
    inventory=[]
    for idx,(kind,folder,summary_name,hourly_name,hash_field) in enumerate(candidates,1):
        summ=folder/summary_name; hourly=folder/hourly_name
        meta=read_json(summ) if summ.is_file() else {}
        expected_sha=meta.get(hash_field,'')
        report={'kind':kind,'case':folder.name,'summary_file':str(summ.relative_to(res)),
                'hourly_file':str(hourly.relative_to(res)),
                'summary_present':summ.is_file(),'hourly_present':hourly.is_file(),
                'recorded_status':meta.get('status',''),
                'recorded_hours':meta.get('hours',meta.get('simulation_hours',meta.get('2025_hours',''))),
                'row_count':'','expected_sha256':expected_sha,'actual_sha256':'',
                'sha256_matches':'','issue':''}
        problems=[]
        if not summ.is_file():problems.append('SUMMARY_MISSING')
        if '_collector_parse_error' in meta:problems.append('SUMMARY_INVALID_JSON')
        if not hourly.is_file():problems.append('HOURLY_MISSING')
        if not expected_sha:problems.append('SUMMARY_HASH_MISSING')
        if hourly.is_file():
            try:
                report['actual_sha256']=sha256(hourly)
                count,header=csv_stats(hourly)
                report['row_count']=count
                report['sha256_matches']=report['actual_sha256']==expected_sha
                if not header:problems.append('EMPTY_CSV_HEADER')
                if count!=8760:problems.append('NOT_8760_ROWS')
                if report['sha256_matches'] is False:problems.append('HOURLY_HASH_MISMATCH')
            except Exception as e:
                problems.append('HOURLY_READ_ERROR:'+type(e).__name__)
        report['issue']=';'.join(problems) if problems else 'NONE'
        inventory.append(report)
        if summ.is_file(): included.append(summ)
        if a.include_hourly and hourly.is_file():included.append(hourly)
        if idx%50==0:print(f'Checked {idx}/{len(candidates)} case folders',flush=True)

    receipts=sorted(res.glob('annual_*receipt_*.json'))
    included.extend(receipts)
    manifest=root/MANIFEST_REL
    if manifest.is_file(): included.append(manifest)
    totals={k:sum(i['kind']==k for i in inventory) for k in EXPECTED}
    valid={k:sum(i['kind']==k and i['issue']=='NONE' for i in inventory) for k in EXPECTED}
    failures=[{'kind':i['kind'],'case':i['case'],'issue':i['issue']} for i in inventory if i['issue']!='NONE']
    receipt_reports=[]
    for rec in receipts:
        d=read_json(rec)
        receipt_reports.append({'filename':rec.name,'stage':d.get('stage'), 'requested':d.get('requested',d.get('annual_jobs_requested')), 'blocked_or_failed':d.get('blocked_or_failed',d.get('failures')), 'source_status':d.get('status')})
    overview={'collector_version':'1.0', 'generated_utc':datetime.now(timezone.utc).isoformat(),
              'source':'Local user-run SEEDExchange Study A annual PV+BESS portfolio',
              'year':2025,'expected_cases':EXPECTED,'found_case_folders':totals,
              'verified_full_year_hourly_cases':valid,'all_expected_verified':all(valid.get(k,0)==v for k,v in EXPECTED.items()),
              'issues':failures,'receipts':receipt_reports,
              'includes_hourly_csv':a.include_hourly,
              'note':'The inventory checks annual row counts and hourly CSV SHA256 hashes against each local JSON. Full independent electrical audit requires selected/raw hourly CSV files. No source simulation files are changed.'}
    out=io.StringIO(newline='')
    fields=['kind','case','summary_file','hourly_file','summary_present','hourly_present','recorded_status','recorded_hours','row_count','expected_sha256','actual_sha256','sha256_matches','issue']
    writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader();writer.writerows(inventory)
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        z.writestr('COLLECTION_REPORT.json',json.dumps(overview,indent=2))
        z.writestr('CASE_INVENTORY.csv',out.getvalue())
        for path in included:
            z.write(path,path.relative_to(root).as_posix())
    print(json.dumps({'archive':str(dest),'case_folders':totals,'full_year_checksum_valid':valid,
                      'issues':len(failures),'receipts':len(receipts),
                      'archive_megabytes':round(dest.stat().st_size/1024**2,2)},indent=2))
    if failures:print('Some results are missing or inconsistent. Upload the ZIP anyway so they can be diagnosed.')

if __name__=='__main__':main()
