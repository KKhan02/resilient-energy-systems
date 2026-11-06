#!/usr/bin/env python3
"""Postprocess completed AC-sensitivity samples against alternative voltage MAGNITUDES.

Strictly a reinterpretation of existing 77-hour samples under unchanged P/Q dispatch.
Does not establish Colombian/EPM regulatory compliance or change network physics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

BANDS = (
    ('national_magnitude_reference', 0.90, 1.10,
     'National voltage magnitude reference only; no duration/point-of-delivery compliance claim'),
    ('epm_nt13_2019_magnitude_reference', 0.90, 1.05,
     'Historic EPM technical reference; current applicability unverified'),
    ('engineering_target', 0.95, 1.05,
     'Proposed research engineering target, not a regulation'),
    ('original_strict_research', 0.97, 1.03,
     'Original WP1 sensitivity only, not regulatory limit'),
)
REQUIRED = {'load_pf','service_factor','hour_index','status','ac_feasible',
            'min_v_pu','max_v_pu','max_trafo_pct','max_line_pct'}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pass_flags(g: pd.DataFrame, low: float, high: float, tol_v: float=1e-6,
               tol_loading: float=1e-4) -> pd.Series:
    """Match upstream study's voltage and equipment-load numerical acceptance tolerances."""
    if not 0 < low < 1 < high:
        raise ValueError('Invalid voltage band')
    return (g.status.astype(str).eq('CONVERGED') &
            np.isfinite(g[['min_v_pu','max_v_pu','max_trafo_pct','max_line_pct']]).all(axis=1) &
            g.min_v_pu.ge(low-tol_v) & g.max_v_pu.le(high+tol_v) &
            g.max_trafo_pct.le(100.+tol_loading) &
            g.max_line_pct.le(100.+tol_loading))


def inspect_source(df: pd.DataFrame, manifest: dict, reference: pd.DataFrame) -> None:
    if manifest.get('mode') not in ('critical','full'):
        raise ValueError('Unrecognized replay mode')
    if not REQUIRED.issubset(df):
        raise ValueError('Missing AC columns: '+str(REQUIRED-set(df.columns)))
    if not {'load_pf','service_factor','feasible_hours','violating_or_failed_hours','min_v_pu','max_v_pu'}.issubset(reference):
        raise ValueError('Missing source summary columns')
    combos=list(df.groupby(['load_pf','service_factor'],sort=True,dropna=False))
    if len(combos) != int(manifest['number_of_sensitivity_cases']):
        raise ValueError('Scenario count differs from manifest')
    if len(df)!=len(combos)*int(manifest['hours_per_case']):
        raise ValueError('Hour count differs from manifest')
    base_ids=None
    for (pf,service),g in combos:
        if g.hour_index.duplicated().any() or len(g)!=int(manifest['hours_per_case']):
            raise ValueError('Duplicate or incomplete hour indices')
        ids=set(g.hour_index.astype(int))
        if base_ids is None: base_ids=ids
        elif ids!=base_ids: raise ValueError('Different hour selections across cases')
        matched=reference[(reference.load_pf==pf)&(reference.service_factor==service)]
        if len(matched)!=1:raise ValueError('Missing or duplicate official scenario summary')
        r=matched.iloc[0]
        if abs(g.min_v_pu.min()-r.min_v_pu)>1e-8 or abs(g.max_v_pu.max()-r.max_v_pu)>1e-8:
            raise ValueError('Source scenario min/max does not match hourly samples')
        passes=pass_flags(g,0.97,1.03)
        original=g.ac_feasible.astype(str).str.lower().eq('true')
        if not passes.equals(original):
            raise ValueError('Recomputed strict-limit flags disagree with original AC evaluator')
        if int(passes.sum())!=int(r.feasible_hours):
            raise ValueError('Original summary feasible hours mismatch')
    if int(manifest['hours_per_case'])<8760 and manifest['mode']=='full':
        raise ValueError('Full-year label on fewer than 8760 annual hours')


def summarize(df: pd.DataFrame, bands=BANDS) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries=[]
    detailed=df[['load_pf','service_factor','hour_index']].copy()
    for band_name,lo,hi,label in bands:
        flag=pass_flags(df,lo,hi)
        detailed[band_name+'_sample_pass']=flag.to_numpy(bool)
        for (pf,service),g in df.groupby(['load_pf','service_factor'],sort=True):
            flags=pass_flags(g,lo,hi)
            summaries.append(dict(band=band_name,band_low_pu=lo,band_high_pu=hi,
                 description=label,load_pf=float(pf),service_factor=float(service),
                 hours_checked=len(g),hours_passing=int(flags.sum()),
                 hours_failing=int((~flags).sum()),min_v_pu=float(g.min_v_pu.min()),
                 max_v_pu=float(g.max_v_pu.max()),
                 voltage_margin_to_min_pu=float(g.min_v_pu.min()-lo),
                 max_trafo_loading_pct=float(g.max_trafo_pct.max()),
                 max_line_loading_pct=float(g.max_line_pct.max()),
                 scope='SAMPLED_AC_MAGNITUDE_SCREEN_NOT_REGULATORY_CERTIFICATION'))
    return pd.DataFrame(summaries), detailed


def make_plots(summary: pd.DataFrame, out: Path) -> None:
    # Optional, no new power flow. Plot each band as a separate, unclipped figure.
    import matplotlib.pyplot as plt
    for band in ('engineering_target','original_strict_research'):
        rows=summary[summary.band==band]
        table=rows.pivot(index='load_pf',columns='service_factor',values='hours_failing').sort_index(ascending=False)
        fig,ax=plt.subplots(figsize=(7.2,4.5),layout='constrained')
        mat=ax.imshow(table.values,aspect='auto',vmin=0,vmax=77)
        ax.set_xticks(range(len(table.columns)),[f'{x:g}' for x in table.columns])
        ax.set_yticks(range(len(table.index)),[f'{x:g}' for x in table.index])
        ax.set_xlabel('Assumed service length multiplier')
        ax.set_ylabel('Household power factor')
        ax.set_title(f'WP1 seven: {band.replace("_"," ")}, 77 sampled hours')
        for i in range(len(table.index)):
            for j in range(len(table.columns)):
                ax.text(j,i,str(int(table.iloc[i,j])),ha='center',va='center',
                        color='white' if table.iloc[i,j]>35 else 'black')
        cbar=fig.colorbar(mat,ax=ax)
        cbar.set_label('Hours failing sampled magnitude screen')
        fig.savefig(out/(band+'_critical_hour_failures.png'),dpi=160)
        plt.close(fig)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--robustness-dir',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True)
    ap.add_argument('--no-plots',action='store_true')
    args=ap.parse_args(argv)
    source=args.robustness_dir.resolve(); out=args.outdir.resolve()
    if out.exists():ap.error('Output folder already exists: '+str(out))
    paths={k:source/k for k in ('sensitivity_ac_hours.csv','sensitivity_scenarios.csv','robustness_manifest.json')}
    for path in paths.values():
        if not path.is_file():ap.error('Missing source: '+str(path))
    df=pd.read_csv(paths['sensitivity_ac_hours.csv'])
    official=pd.read_csv(paths['sensitivity_scenarios.csv'])
    manifest=json.loads(paths['robustness_manifest.json'].read_text(encoding='utf-8'))
    inspect_source(df,manifest,official)
    summary,hourly=summarize(df)
    out.mkdir(parents=True)
    summary.to_csv(out/'voltage_band_sample_summary.csv',index=False,float_format='%.9f')
    hourly.to_csv(out/'voltage_band_hourly_screen_flags.csv',index=False)
    audit=dict(status='POSTPROCESS_ONLY_NO_NEW_AC_OR_PYPSA_SOLVES',
         source_mode=manifest['mode'],source_hours_per_case=manifest['hours_per_case'],
         source_case=manifest.get('case'),source_transformer=manifest.get('transformer'),
         source_dispatch='UNCHANGED',source_manufacturer_soc='UNCHANGED',
         source_sha256={k:sha(v) for k,v in paths.items()},
         source_model_limit=manifest.get('thresholds'),
         bands=[dict(name=name,min_v=lo,max_v=hi,interpretation=label) for name,lo,hi,label in BANDS],
         caveat='Only voltage magnitudes at selected time points; no formal Colombian/EPM regulatory compliance claim. Old EPM NT13 applicability unconfirmed.',
         future_action='Complete annual validation on shortlisted PF/route cases before claiming robustness; manufacturer SOC and P/Q coupling needed for sizing.')
    (out/'voltage_band_postprocess_manifest.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    if not args.no_plots: make_plots(summary,out)
    print('Reclassified',len(df),'existing AC points across',len(BANDS),'bands; no new power flows.')
    print(summary.groupby('band').hours_failing.sum().to_string())
    return summary

if __name__=='__main__':main()
