#!/usr/bin/env python3
"""Read-only, source-signed B9 vs eight-battery corrected AC-loss economic sensitivity.

No PyPSA/pandapower runs. Reconstructs all 36 case-factor loss/cost records
using the earlier signed 2025 eight-battery reference annual AC summaries,
their validated changed-hour redispatch, and the new signed B9 annual overlay.
Assumed US$0.29/kWh is a RESEARCH sensitivity only, not a Colombian tariff.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

FACTOR=[(.95,1.),(.95,1.3),(.95,1.6),(.98,1.),(.98,1.3),(.98,1.6),(1.,1.),(1.,1.3),(1.,1.6)]
BASE='case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01/annual_ac_replays_v1'
PATHS={
 'cost':'case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17/ALL_8_DESIGNS_COST_IMPORT_FRONTIER.csv',
 'old_manifest':'StudyA_A1_106039_Redispatch_Trial_v1/trial_manifest.json',
 'old_changes':'StudyA_A1_106039_Redispatch_Trial_v1/changed_hour_ac_checks.csv',
 'new_manifest':'StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1/ANNUAL_AC_MANIFEST.json',
 'new_annual':'StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1/ANNUAL_NINE_FACTOR_B9_RESULTS.csv',
}
# Canonical LF SHA-256 of the *committed* GitLab source bytes. Windows CRLF
# checkouts normalize to LF before hashing, never skipping source integrity.
PINS={
 'cost':'18717d0fc598c6ec0561e7bbd5c9d1d48a56116f0a4b2c4ada3535e710d89a10',
 'old_manifest':'5e25acbcc8b860b5e4b09ecfb7a10c0f64990d5cc6f5508449d73b232a030262',
 'old_changes':'cc75dae71ca0f3d93be50d3afc3ddb95dfcc65c7c098b128a3afa2bd996ea77b',
 'new_manifest':'3a8f5fc954419e927008bb50aee5062c9c49f4e363256e61cafbecc47e173a19',
 'new_annual':'03da7cd415f31caf5e3a90731d9c05d1ece550f965f45e5d21894659cb895cc8',
}
TIERS={'MC_REF':('min_cost_ref','MC_B9'),'SS_REF':('ss90_ref','SS_B9')}
PAIR_FIELDS=['reference','new_case','pf','lf','refImports','newImports','refL','newL','savings','referenceLossReduction','baseCost','lossCostDiff','fullDiff','referenceCost','newCost','breakeven']
ALL_FIELDS=['id','source','pf','lf','panels','modules','imports','curtail','loss','annualEquipment','energyTotal','lossAdder','adjusted']


def read_checked(root,key):
    path=root/PATHS[key]
    data=path.read_bytes().replace(b'\r\n',b'\n')
    got=hashlib.sha256(data).hexdigest()
    if got!=PINS[key]:
        raise ValueError(f'Source {key} SHA mismatch: {got}. Never bypass signature checks')
    if key.endswith('manifest'):
        return json.loads(data)
    return list(csv.DictReader(data.decode('utf-8-sig').splitlines()))



INDEX_FILE='SIGNED_REFERENCE_AC_LOSS_INDEX_18.json'
INDEX_SHA256='4ab845a71ae969af0796a36091bce192db4ab65dfbb316617b1d2f5baed9ef75'


def signed_reference_index():
    """Validate an exact GitLab-indexed copy of 18 historical AC summaries.

    Source summaries may not have been materialized in a partial checkout.
    The index was extracted from the 18 unchanged GitLab files, with their
    individual blob SHA256 and original ac_hourly SHA256 provenance.
    """
    path=Path(__file__).with_name(INDEX_FILE)
    raw=path.read_bytes().replace(b'\r\n',b'\n')
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=INDEX_SHA256:
        raise ValueError(f'Signed reference AC-loss index SHA mismatch: {digest}')
    payload=json.loads(raw)
    if payload.get('status')!='GITLAB_SIGNED_HISTORICAL_AC_SUMMARY_INDEX' or (
        payload.get('source_commit')!='2ab70535bbe22fa7490b16b7ae8ac60674a38455'):
        raise ValueError('Historical AC index provenance changed')
    entries=payload.get('entries',[])
    expected={(tier,pf,lf) for tier in ('min_cost_ref','ss90_ref') for pf,lf in FACTOR}
    if len(entries)!=18 or {(e['tier'],float(e['pf']),float(e['length_factor'])) for e in entries}!=expected:
        raise ValueError('Historical AC index incomplete or duplicated')
    return {(e['tier'],float(e['pf']),float(e['length_factor'])):e for e in entries}


def checked_reference_summary(root,tier,pf,lf,old_entry,expected_energy,index):
    """Use an exact local source summary if present, else signed GitLab index.

    Both modes require historical annual AC SHA from the already independently
    audited eight-battery redispatch manifest; there is no invented data.
    """
    name=f'A1_106039_{tier}_mapped_optimized_pf{round(pf*100):03d}_length{round(lf*10):02d}_annual8760'
    relative=f'{BASE}/{name}/ac_summary.json'
    row=index[(tier,pf,lf)]
    if (row['relative_path']!=relative or row['ac_hourly_sha256']!=old_entry['original_ac_sha256'] or
        row['energy_manifest_sha256']!=expected_energy or
        int(row['hours'])!=8760 or int(row['converged_hours'])!=8760 or
        len(row['gitlab_source_content_sha256'])!=64):
        raise ValueError('Historical summary index disagrees with signed reference: '+name)
    path=root/relative
    if not path.is_file():
        return {'hours':8760,'converged_hours':8760,
                'ac_hourly_sha256':row['ac_hourly_sha256'],
                'energy_manifest_sha256':row['energy_manifest_sha256'],
                'pf':pf,'length_factor':lf,
                'annual_or_sample_losses_kwh':row['annual_ac_loss_kwh']},'GITLAB_INDEX_FALLBACK',relative
    m=json.loads(path.read_text(encoding='utf-8'))
    if (m.get('hours')!=8760 or m.get('converged_hours')!=8760 or
        m.get('ac_hourly_sha256')!=old_entry['original_ac_sha256'] or
        m.get('energy_manifest_sha256')!=expected_energy or
        abs(float(m['pf'])-pf)>1e-9 or abs(float(m['length_factor'])-lf)>1e-9 or
        abs(float(m['annual_or_sample_losses_kwh'])-float(row['annual_ac_loss_kwh']))>1e-8):
        raise ValueError('Local historical AC summary conflicts with GitLab source index: '+relative)
    return m,'LOCAL_SUMMARY_VERIFIED',relative


def one(items,what):
    if len(items)!=1:
        raise ValueError(f'Expected exactly one {what}: found {len(items)}')
    return items[0]


def build(root,tariff=.29):
    sources={key:read_checked(root,key) for key in PATHS}
    old=sources['old_manifest'];fresh=sources['new_manifest']
    if old['status']!='ALL_NINE_PF_LENGTH_CASES_FEASIBLE' or fresh['status']!='FULL_ANNUAL_ALL_NINE_MODELLED_AC_PASS':
        raise ValueError('Original or B9 annual correction is not all-nine feasible')
    if len(old['screens'])!=18 or len(fresh['results'])!=18 or len(sources['old_changes'])!=108:
        raise ValueError('Signed reference/B9 annual and hourly coverage is incomplete')
    if any(float(s['corrected_bad_hours'])!=0 or int(s['year_hours'])!=8760 for s in fresh['results']):
        raise ValueError('B9 full-year AC case not feasible')
    if any(int(s['candidate_bad_hours'])!=0 or s['all_8760_hours_accounted_for'] is not True for s in old['screens']):
        raise ValueError('Eight-battery AC reference not feasible')
    equip={r['case_id']:r for r in sources['cost']}
    index=signed_reference_index()
    pair=[];all_rows=[];provenance=[]
    for ref,(tier,updated) in TIERS.items():
        for pf,lf in FACTOR:
            old_entry=one([r for r in old['screens'] if r['tier']==tier and float(r['pf'])==pf and float(r['length_factor'])==lf],'old reference')
            new_entry=one([r for r in fresh['results'] if r['case_id']==updated and float(r['pf'])==pf and float(r['length_factor'])==lf],'B9 annual')
            if old_entry['candidate_bad_hours']!=0 or new_entry['corrected_bad_hours']!=0:
                raise ValueError('Not modelled AC feasible')
            m,source_mode,source_path=checked_reference_summary(
                root,tier,pf,lf,old_entry,old['source_annual_signatures'][tier],index)
            provenance.append({'tier':tier,'pf':pf,'length_factor':lf,
                'reference_source_mode':source_mode,'historical_source_path':source_path,
                'gitlab_summary_content_sha256':index[(tier,pf,lf)]['gitlab_source_content_sha256']})
            events=[r for r in sources['old_changes'] if r['tier']==tier and float(r['pf'])==pf and float(r['length_factor'])==lf]
            stamps=sorted(set(r['timestamp_lst'] for r in events))
            expected=4 if tier=='min_cost_ref' else 2
            if len(stamps)!=expected or len(events)!=2*expected:
                raise ValueError('Reference changed-hour evidence incomplete')
            dloss=0.
            for stamp in stamps:
                a=one([r for r in events if r['timestamp_lst']==stamp and r['change']=='original'],'old hourly')
                c=one([r for r in events if r['timestamp_lst']==stamp and r['change']=='candidate'],'corrected hourly')
                if a['status']!='CONVERGED' or c['status']!='CONVERGED' or c['ac_feasible']!='True':
                    raise ValueError('Reference corrected AC hour did not pass')
                dloss+=float(c['loss_kw'])-float(a['loss_kw'])
            lossref=float(m['annual_or_sample_losses_kwh'])+dloss
            lossnew=float(new_entry['corrected_ac_losses_kwh'])
            if not all(math.isfinite(v) and v>=0 for v in (lossref,lossnew)):
                raise ValueError('Invalid annual AC losses')
            old_hw=equip[ref];new_hw=equip[updated]
            oldimp=float(old_hw['grid_import_kwh']);newimp=float(new_hw['grid_import_kwh'])
            oldcost=float(old_hw['annual_total_usd']);newcost=float(new_hw['annual_total_usd'])
            oldeq=float(old_hw['annual_equipment_usd']);neweq=float(new_hw['annual_equipment_usd'])
            if abs(oldcost-oldeq-tariff*oldimp)>1e-5 or abs(newcost-neweq-tariff*newimp)>1e-5:
                raise ValueError('Cost-source tariff differs from historical 0.29')
            saved=lossref-lossnew
            obj={'reference':ref,'new_case':updated,'pf':pf,'lf':lf,'refImports':oldimp,'newImports':newimp,
              'refL':lossref,'newL':lossnew,'savings':saved,'referenceLossReduction':dloss,
              'baseCost':newcost-oldcost,'lossCostDiff':-saved*tariff,
              'fullDiff':newcost-oldcost-saved*tariff,
              'referenceCost':oldcost+lossref*tariff,'newCost':newcost+lossnew*tariff,
              'breakeven':(neweq-oldeq)/(oldimp-newimp+saved)}
            pair.append(obj)
            for case,source,hardware,loss in [
                (ref,'8-battery AC-corrected reference',old_hw,lossref),
                (updated,'9-battery AC-corrected design',new_hw,lossnew)]:
                all_rows.append({'id':case,'source':source,'pf':pf,'lf':lf,'panels':int(hardware['pv_panels']),
                    'modules':int(hardware['battery_modules']),'imports':float(hardware['grid_import_kwh']),
                    'curtail':float(hardware['curtailed_pv_dc_kwh']),'loss':loss,
                    'annualEquipment':float(hardware['annual_equipment_usd']),
                    'energyTotal':float(hardware['annual_total_usd']),
                    'lossAdder':loss*tariff,'adjusted':float(hardware['annual_total_usd'])+loss*tariff})
    if len(pair)!=18 or len(all_rows)!=36:
        raise ValueError('Incomplete AC loss-cost sensitivity coverage')
    return pair,all_rows,provenance


def formatted(row,headers):
    return ','.join(f'{row[k]:.6f}' if isinstance(row[k],float) else str(row[k]) for k in headers)


def serialize(rows,headers):
    return ','.join(headers)+'\n'+'\n'.join(formatted(r,headers) for r in rows)+'\n'


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--repo-root',type=Path,default=Path.cwd())
    a.add_argument('--out',type=Path,help='New output directory, optional')
    args=a.parse_args()
    pair,all_rows,provenance=build(args.repo_root.resolve())
    s=[r for r in pair if r['pf']==.95 and r['lf']==1.6]
    report={'status':'SIGNED_18_FACTOR_PAIR_AC_LOSS_SENSITIVITY_PASS',
            'pair_comparisons':18,'case_factor_records':36,'assumed_tariff_USD_kWh':.29,
            'historical_reference_local_summaries':sum(p['reference_source_mode']=='LOCAL_SUMMARY_VERIFIED' for p in provenance),
            'historical_reference_gitlab_index_fallbacks':sum(p['reference_source_mode']=='GITLAB_INDEX_FALLBACK' for p in provenance),
            'historical_reference_provenance':provenance,
            'historical_reference_index_SHA256':INDEX_SHA256,
            'assumption':'community purchases feeder losses at research tariff, NOT VERIFIED',
            'stress_pair_result':[{'reference':r['reference'],'candidate':r['new_case'],
                'losses_saved_kwh':r['savings'],'loss_adjusted_cost_delta_USD_a':r['fullDiff']} for r in s]}
    if args.out:
        out=args.out.resolve()
        if out.exists():raise FileExistsError(f'Cannot overwrite: {out}')
        out.mkdir(parents=True)
        (out/'FOUR_DESIGN_BY_FACTOR_36.csv').write_text(serialize(all_rows,ALL_FIELDS),encoding='utf-8',newline='\n')
        (out/'PAIRWISE_BATTERY_LOSS_ECONOMICS_18.csv').write_text(serialize(pair,PAIR_FIELDS),encoding='utf-8',newline='\n')
        (out/'AUDIT_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
