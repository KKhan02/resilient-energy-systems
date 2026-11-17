#!/usr/bin/env python3
"""2025 GROSS kVA transformer-only envelope for EPM 92395 (A0 and A1).

This is NOT an AC power flow, LV line reconstruction, or evidence of an
unconnected transformer. It purposefully does not assign house ownership by LV
segment availability. It reads signed v6.2 input sources and refuses overwrites.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import pandas as pd


def build_idealized_envelope(profiles, mapping, house_ids, pf, nameplate_kva):
    """Apply idealized P/PF/Sn screen without claiming feeder AC results."""
    if not 0 < pf <= 1 or nameplate_kva <= 0:
        raise ValueError('Invalid power factor or nameplate')
    if len(set(house_ids)) != len(house_ids) or any(h not in mapping for h in house_ids):
        raise ValueError('Invalid or repeated mapped house')
    power=profiles[[mapping[h] for h in house_ids]].sum(axis=1)
    if not (power >= -1e-9).all() or power.isna().any():
        raise ValueError('Invalid household load values')
    kva=power/pf
    ratio=100*kva/nameplate_kva
    return pd.DataFrame({'timestamp_lst':profiles.index,
                         'gross_demand_kw':power.to_numpy(float),
                         'ideal_apparent_demand_kva_no_losses':kva.to_numpy(float),
                         'ideal_nameplate_loading_pct_no_losses':ratio.to_numpy(float)})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True)
    ap.add_argument('--pf',type=float,choices=(.95,.98,1.0),default=.98)
    args=ap.parse_args()
    if args.outdir.exists():
        raise FileExistsError(f'No overwrites: {args.outdir}')
    manifest_path=args.manifest.resolve()
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('status')!='PREPARED_INPUTS_NO_ANNUAL_ENERGY_OR_AC_RUN':
        raise ValueError('Wrong source manifest state')
    repo=Path(manifest['repo_root'])
    runner=repo/'case1/studies/SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py'
    if hashlib.sha256(runner.read_bytes()).hexdigest()!=manifest['script_sha256']:
        raise ValueError('v6.2 runner changed since signed preparation')
    for rel,expected in manifest['model_source_hashes'].items():
        if hashlib.sha256((repo/rel).read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Existing power systems model changed: {rel}')
    sys.path.insert(0,str(runner.parent))
    import seed_study_a_v6 as runner_module
    _p1,_p2,mapping,profiles,groups,_alloc = runner_module.validated_sources(
        repo,Path(manifest['v4_run_dir']),manifest)
    for name,key in [('epm_network_relevant_sanitized.geojson','gis_geojson_sha256'),
                     ('houses_candidate_associations.csv','gis_house_sha256')]:
        p=repo/'case1/studies/epm_gis_pandapower_v1/data'/name
        if hashlib.sha256(p.read_bytes()).hexdigest()!=manifest[key]:
            raise ValueError(f'GIS evidence changed after signed manifest: {name}')
    if groups!=manifest['groups'] or mapping!=manifest['mapping']:
        raise ValueError('Current memberships or mappings differ from signed input')
    a0=groups['A0']['92395'];a1=groups['A1']['92395']
    if len(a0)!=4 or a0!=a1 or set(a0)!={'H30','H31','H32','H33'}:
        raise ValueError('92395 four-house membership no longer matches controlled A0/A1')
    nameplate_kva=float(manifest['nameplate_assumptions_kva']['92395'])
    if abs(nameplate_kva-5)>1e-9:
        raise ValueError('92395 expected source 5 kVA nameplate')
    output=build_idealized_envelope(profiles,mapping,a0,args.pf,nameplate_kva)
    ratio=output.ideal_nameplate_loading_pct_no_losses
    if len(output)!=8760 or abs(output.gross_demand_kw.sum()-4*1898)>0.1:
        raise ValueError('Unverified 2025 load energy or time coverage')
    args.outdir.mkdir(parents=False,exist_ok=False)
    file=args.outdir/'92395_gross_transformer_only_hourly.csv'
    output.to_csv(file,index=False,float_format='%.10f')
    worst=output.loc[output.ideal_nameplate_loading_pct_no_losses.idxmax()]
    meta={'status':'FULL_YEAR_GROSS_TRANSFORMER_ONLY_NO_AC_NETWORK',
          'scenarios':['A0','A1'],'transformer':'92395','house_ids':a0,
          'hours':8760,'pf':args.pf,'nominal_transformer_kva':nameplate_kva,
          'gross_annual_kwh':float(output.gross_demand_kw.sum()),
          'ideal_max_loading_pct_no_losses':float(ratio.max()),
          'ideal_over100_hours_no_losses':int((ratio>100).sum()),
          'peak_hour_local_standard_time':str(worst['timestamp_lst']),
          'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
          'hourly_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
          'NO_AC_voltage_line_losses_or_actual_service_evidence':True,
          'interpretation':'Ideal transformer kVA-only screen ignoring electrical losses, voltage drop, conductor ampacity, other EPM loads and phase imbalance. Missing GIS sections do not imply absent customer service.'}
    (args.outdir/'92395_gross_transformer_only_summary.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':
    main()
