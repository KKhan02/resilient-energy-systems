#!/usr/bin/env python3
"""Extract signed Study A A1/106039 dispatch around overloaded evenings.

Read-only: no solver, no output-folder mutation and no manual inference of SOC.
Input repository must hold the original Study A v6 annual output tree.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import pandas as pd

ROOT_REL=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
TIERS=('min_cost_ref','ss90_ref')
MODES=('optimized','causal')
EVENTS=(pd.Timestamp('2025-10-13 20:00'),pd.Timestamp('2025-11-27 20:00'))
# Seven days around each event, retaining the charge trajectory preceding the overload.
RANGES=((pd.Timestamp('2025-10-10'),pd.Timestamp('2025-10-17')),
        (pd.Timestamp('2025-11-24'),pd.Timestamp('2025-12-01')))
AC_CASES=(
'A1_106039_min_cost_ref_mapped_optimized_pf098_length10_annual8760',
'A1_106039_ss90_ref_mapped_optimized_pf098_length10_annual8760',
'A1_106039_min_cost_ref_mapped_optimized_pf095_length16_annual8760',
'A1_106039_ss90_ref_mapped_optimized_pf095_length16_annual8760',
'A1_106039_ss90_ref_mapped_causal_pf098_length10_annual8760',
)


def winlong(p:Path)->Path:
    p=p.resolve()
    if os.name!='nt':return p
    s=str(p)
    if s.startswith('\\\\?\\'):return p
    if s.startswith('\\\\'):return Path('\\\\?\\UNC\\'+s[2:])
    return Path('\\\\?\\'+s)


def signed_annual(folder:Path, manifest:str, csvname:str, hashkey:str):
    meta=json.loads(winlong(folder/manifest).read_text(encoding='utf-8'))
    raw=winlong(folder/csvname).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    assert digest==meta.get(hashkey),f'Hash check failed {folder.name} ({hashkey})'
    frame=pd.read_csv(io.BytesIO(raw),parse_dates=['timestamp_lst'])
    t=frame.timestamp_lst
    assert len(frame)==8760 and t.is_unique and t.is_monotonic_increasing
    assert t.iloc[0]==pd.Timestamp('2025-01-01 00:00')
    assert t.iloc[-1]==pd.Timestamp('2025-12-31 23:00')
    assert t.diff().dropna().eq(pd.Timedelta(hours=1)).all()
    return frame,meta,digest


def sliced_frame(df:pd.DataFrame)->pd.DataFrame:
    mask=False
    for start,end in RANGES:
        mask=mask | ((df.timestamp_lst>=start)&(df.timestamp_lst<end))
    return df.loc[mask].copy()


def run(repo_root:Path,out:Path)->dict:
    base=repo_root.resolve()/ROOT_REL
    out=out.resolve()
    if out.exists():raise FileExistsError(f'Archive already exists; choose new --out: {out}')
    sources=[];records=[];event_records=[];issues=[]
    for tier in TIERS:
        for mode in MODES:
            suffix=f'A1_106039_{tier}'
            folder=base/('energy_'+suffix if mode=='optimized' else 'causal_'+suffix)
            manifest,csv,hashkey=(('energy_manifest.json','energy_hourly_2025.csv','energy_csv_sha256')
                                  if mode=='optimized' else
                                  ('causal_summary.json','causal_pv_first_2025.csv','output_sha256'))
            try:
                df,meta,sha=signed_annual(folder,manifest,csv,hashkey)
                required={'demand_kw','grid_import_kw','grid_export_kw','inverter_ac_kw',
                          'battery_soc_usable_kwh','battery_charge_dc_kw','battery_discharge_dc_kw',
                          'pv_dc_available_kw','curtailed_pv_dc_kw'}
                assert required.issubset(df.columns),(folder.name,required-set(df.columns))
                window=sliced_frame(df)
                assert len(window)==14*24, 'Expected two complete seven-day windows'
                window.insert(0,'case',suffix)
                window.insert(1,'operation',mode)
                cols=['case','operation','timestamp_lst'] + sorted(required)
                # Preserve all source columns useful for future analysis.
                records.append(window)
                for evt in EVENTS:
                    row=df[df.timestamp_lst.eq(evt)]
                    assert len(row)==1
                    r=row.iloc[0]
                    event_records.append({'case':suffix,'operation':mode,'event_timestamp_lst':str(evt),
                        'demand_kw':float(r.demand_kw),'grid_import_kw':float(r.grid_import_kw),
                        'inverter_ac_kw':float(r.inverter_ac_kw),
                        'battery_soc_usable_kwh_after_snapshot':float(r.battery_soc_usable_kwh),
                        'battery_charge_dc_kw':float(r.battery_charge_dc_kw),
                        'battery_discharge_dc_kw':float(r.battery_discharge_dc_kw),
                        'pv_dc_available_kw':float(r.pv_dc_available_kw),
                        'curtailed_pv_dc_kw':float(r.curtailed_pv_dc_kw)})
                sources.append({'folder':folder.name,'source_sha256':sha,'source_manifest':manifest,
                                'source_file':csv,'rows_verified':8760,'window_rows':len(window),
                                'hardware_or_dispatch_source':str(meta.get('source_case_id',meta.get('case',suffix)))})
            except Exception as exc:
                issues.append({'folder':folder.name,'error':str(exc)})
    acrows=[]
    for case in AC_CASES:
        folder=base/'annual_ac_replays_v1'/case
        try:
            df,meta,sha=signed_annual(folder,'ac_summary.json','ac_hourly.csv','ac_hourly_sha256')
            window=sliced_frame(df)
            assert len(window)==14*24
            window.insert(0,'case',case)
            acrows.append(window)
            sources.append({'folder':str(folder.relative_to(base)),'source_sha256':sha,
                            'source_manifest':'ac_summary.json','source_file':'ac_hourly.csv',
                            'rows_verified':8760,'window_rows':len(window)})
        except Exception as exc:
            issues.append({'folder':case,'error':str(exc)})
    if len(records)!=4 or len(acrows)!=5 or issues:
        raise RuntimeError('Extraction incomplete, no archive created: '+json.dumps(issues[:9]))
    with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=7) as z:
        z.writestr('A1_106039_14DAYS_ENERGY_4CASES.csv',pd.concat(records,ignore_index=True).to_csv(index=False))
        z.writestr('A1_106039_14DAYS_AC_5CASES.csv',pd.concat(acrows,ignore_index=True).to_csv(index=False))
        z.writestr('A1_106039_EVENT_HOUR_SOC.csv',pd.DataFrame(event_records).to_csv(index=False))
        z.writestr('SOURCE_SIGNATURES.json',json.dumps(sources,indent=2))
        z.writestr('EXTRACTION_STATUS.json',json.dumps({'status':'SIGNED_SOURCE_WINDOWS_COMPLETE',
             'energy_cases':4,'ac_cases':5,'days_per_case':14,'per_case_annual_verified':8760,
             'events':[str(x) for x in EVENTS],
             'method':'Read only selected 2025 windows. No SOC interpretation or simulation performed.'},indent=2))
    return {'archive':str(out),'energy_cases':4,'ac_cases':5,'energy_window_rows':sum(len(x) for x in records),
            'ac_window_rows':sum(len(x) for x in acrows),'issues':0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--out',type=Path,default=Path('StudyA_A1_106039_Event_Hour_SOC_Evidence.zip'))
    args=p.parse_args()
    print(json.dumps(run(args.repo_root,args.out),indent=2))

if __name__=='__main__':main()
