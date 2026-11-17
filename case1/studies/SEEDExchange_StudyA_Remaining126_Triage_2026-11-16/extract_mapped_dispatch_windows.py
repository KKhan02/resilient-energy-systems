#!/usr/bin/env python3
"""Study A read-only, source-hash-verified annual SOC windows for mapped failing cases.

This creates evidence for a later full-chronology AC-aware redispatch optimizer.
It DOES NOT simulate, edit source data, or claim any AC-feasible correction.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, zipfile
from pathlib import Path
import pandas as pd

BASE = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
EXPECTED_COLUMNS = ['timestamp_lst', 'demand_kw', 'pv_dc_available_kw', 'battery_charge_dc_kw',
                    'battery_discharge_dc_kw', 'inverter_ac_kw', 'battery_soc_usable_kwh',
                    'grid_import_kw', 'grid_export_kw', 'unserved_kw', 'curtailed_pv_dc_kw']

def xp(path:Path)->str:
    s=str(path.resolve())
    if os.name=='nt' and not s.startswith('\\\\?\\'):
        return '\\\\?\\'+s
    return s

def jread(path:Path):
    with open(xp(path),'r',encoding='utf-8') as f:return json.load(f)

def sha(path:Path):
    h=hashlib.sha256()
    with open(xp(path),'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def annual(path:Path):
    d=pd.read_csv(xp(path),parse_dates=['timestamp_lst'])
    if any(x not in d.columns for x in EXPECTED_COLUMNS):
        raise ValueError(f'Missing required columns in {path}')
    wanted=pd.date_range('2025-01-01 00:00:00',periods=8760,freq='h')
    if len(d)!=len(wanted) or not d.timestamp_lst.equals(pd.Series(wanted)):
        raise ValueError(f'Annual chronology mismatch in {path}')
    if d[EXPECTED_COLUMNS[1:]].isna().any().any():
        raise ValueError(f'Missing annual energy values in {path}')
    return d.set_index('timestamp_lst',verify_integrity=True)

def load_events(zip_path:Path):
    with zipfile.ZipFile(zip_path) as z:
        info=json.loads(z.read('EXTRACTION_QA.json'))
        raw=pd.read_csv(io.BytesIO(z.read('DEDUPLICATED_CONSTRAINT_EVENTS.csv')),dtype={'transformer':str})
    if info['issues'] or info['verified_failing_ac_cases']!=126 or len(raw)!=586:
        raise ValueError('Unexpected AC diagnostic source; stop and review')
    keys=['scenario','transformer','tier','hardware_family','topology','dispatch','timestamp_lst']
    if raw.duplicated(keys).any():raise ValueError('Event key duplicates')
    if raw.failing_pf_length_combinations.sum()!=1531:raise ValueError('Event-level 1531 case-hour sum mismatch')
    return raw.loc[raw.topology=='mapped'].copy()

def acquire(repo:Path,events:pd.DataFrame):
    base=repo/BASE
    allrows=[]; sigs=[]
    groupkeys=['scenario','transformer','tier','hardware_family','dispatch']
    for group,g in events.groupby(groupkeys,sort=True):
        scenario,transformer,tier,family,dispatch=group
        fam='four' if family=='four_house_new' else 'ref'
        case=f'{scenario}_{transformer}_{tier}_{fam}'
        ep=base/f'energy_{case}'
        meta=jread(ep/'energy_manifest.json')
        energy_csv=ep/'energy_hourly_2025.csv'
        if sha(energy_csv)!=meta['energy_csv_sha256']:raise ValueError('Energy SHA256 mismatch: '+case)
        if dispatch=='optimized':path=energy_csv
        else:
            cp=base/f'causal_{case}'
            cm=jread(cp/'causal_summary.json')
            path=cp/'causal_pv_first_2025.csv'
            if sha(path)!=cm['output_sha256']:raise ValueError('Causal SHA256 mismatch: '+case)
        data=annual(path)
        hw=meta['hardware']
        sigs.append({'case_family':case,'dispatch':dispatch,'year':2025,
                     'annual_file_sha256':sha(path),'pv_panels':int(hw['pv_panels']),
                     'battery_modules':int(hw['battery_modules']),
                     'battery_power_dc_kw':float(hw['battery_power_dc_kw']),
                     'inverter_kva':float(hw['inverter_kva'])})
        for r in g.itertuples(index=False):
            t=pd.Timestamp(r.timestamp_lst)
            if t not in data.index:raise ValueError('Missing event timestamp '+str(t))
            row=data.loc[t]
            if abs(float(row.inverter_ac_kw)-float(r.inverter_ac_kw))>2e-4 or abs(float(row.battery_soc_usable_kwh)-float(r.battery_soc_after_kwh))>2e-4:
                raise ValueError(f'Mismatched AC event energy source: {case} {dispatch} {t}')
            w=data.loc[t-pd.Timedelta(hours=24):t+pd.Timedelta(hours=4)]
            for at,item in w.iterrows():
                record={'case_family':case,'scenario':scenario,'transformer':transformer,
                        'tier':tier,'hardware_family':family,'dispatch':dispatch,
                        'event_timestamp':str(t),'hour_timestamp':str(at),
                        'hours_from_event':int((at-t).total_seconds()/3600),
                        'event_peak_trafo_pct':float(r.peak_trafo_pct),
                        'event_lowest_v_pu':float(r.lowest_v_pu),
                        'event_any_trafo_overload':bool(r.any_trafo_overload),
                        'event_any_low_voltage':bool(r.any_low_voltage),
                        'battery_modules':int(hw['battery_modules']),
                        'battery_power_limit_dc_kw':float(hw['battery_power_dc_kw']),
                        'inverter_nameplate_kva':float(hw['inverter_kva'])}
                for col in EXPECTED_COLUMNS[1:]:record[col]=float(item[col])
                record['operational_soc_floor_kwh']=int(hw['battery_modules'])*.229
                allrows.append(record)
    return pd.DataFrame(allrows),pd.DataFrame(sigs)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--events-zip',type=Path,default=Path('StudyA_Remaining_AC_And_PV_Diagnostics.zip'))
    ap.add_argument('--out',type=Path,default=Path('StudyA_Mapped_SOC_Windows_for_Redispatch.zip'))
    args=ap.parse_args()
    events=load_events(args.events_zip)
    if len(events)!=175:raise ValueError(f'Expected 175 mapped design-hour events, got {len(events)}')
    rows,sigs=acquire(args.repo_root.resolve(),events)
    if len(sigs)!=16 or len(rows)!=175*29:
        raise ValueError(f'Unexpected output size: signatures {len(sigs)}, rows {len(rows)}')
    out=args.out.resolve()
    if out.exists():raise FileExistsError('Refuse to overwrite output '+str(out))
    out.parent.mkdir(parents=True,exist_ok=True)
    manifest={'status':'READ_ONLY_ANNUAL_WINDOWS_VERIFIED',
              'source_event_archive_sha256':sha(args.events_zip),
              'event_count':len(events),'dispatch_source_count':len(sigs),'window_hour_rows':len(rows),
              'source_files_sha256':sigs.to_dict(orient='records'),
              'method':'24 hours preceding and 4 hours following each event, from the same signed 2025 annual dispatch. Does not assert existence of corrective shift.'}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        z.writestr('MAPPED_EVENT_SOC_WINDOWS.csv',rows.to_csv(index=False))
        z.writestr('MAPPED_EVENT_SELECTION.csv',events.to_csv(index=False))
        z.writestr('SOURCE_VERIFICATION.json',json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'output':str(out),'selected_events':len(events),'annual_dispatch_sources':len(sigs),'window_rows':len(rows)},indent=2))

if __name__=='__main__':main()
