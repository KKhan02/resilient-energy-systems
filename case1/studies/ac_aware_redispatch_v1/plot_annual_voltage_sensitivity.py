#!/usr/bin/env python3
"""Audit and plot saved full-year AC robustness results without new solves.

Read-only postprocessor. Voltage bands represent magnitude screening, not
formal national / EPM regulatory compliance or measured-network certification.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd

BANDS = [
    ('National magnitude reference', 0.90, 1.10),
    ('Historic EPM technical reference', 0.90, 1.05),
    ('Engineering study target', 0.95, 1.05),
    ('Original strict research', 0.97, 1.03),
]
REQUIRED = {'hour_index','timestamp','status','min_v_pu','max_v_pu',
            'max_trafo_pct','max_line_pct','load_pf','service_factor'}

def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_review(robustness_dir: Path):
    f = robustness_dir / 'sensitivity_ac_hours.csv'
    mf = robustness_dir / 'robustness_manifest.json'
    sf = robustness_dir / 'sensitivity_scenarios.csv'
    for p in (f,mf,sf):
        if not p.exists(): raise FileNotFoundError(p)
    man=json.loads(mf.read_text(encoding='utf-8'))
    if man.get('mode')!='full' or not man.get('full_year_each_case'):
        raise ValueError('This figure package requires completed full-year AC data')
    d=pd.read_csv(f)
    if not REQUIRED.issubset(d.columns):
        raise ValueError('Missing required columns '+str(REQUIRED-set(d.columns)))
    groups=d.groupby(['load_pf','service_factor'],sort=True,dropna=False)
    if len(groups)!=man['number_of_sensitivity_cases']:
        raise ValueError('Scenario count/manifest mismatch')
    rows=[]
    d['timestamp']=pd.to_datetime(d.timestamp)
    for (pf,sf_factor),g in groups:
        if len(g)!=8760 or not np.array_equal(np.sort(g.hour_index.to_numpy()),np.arange(8760)):
            raise ValueError('Incomplete or duplicated hourly snapshots in full-year case')
        if g.timestamp.isna().any() or g.timestamp.duplicated().any():
            raise ValueError('Invalid timestamps')
        for label,lo,hi in BANDS:
            feasible=(g.status.eq('CONVERGED') &
                np.isfinite(g[['min_v_pu','max_v_pu','max_trafo_pct','max_line_pct']]).all(axis=1) &
                g.min_v_pu.ge(lo-1e-6) & g.max_v_pu.le(hi+1e-6) &
                g.max_trafo_pct.le(100+1e-4) & g.max_line_pct.le(100+1e-4))
            rows.append(dict(load_pf=pf,service_factor=sf_factor,band=label,
                lower_pu=lo,upper_pu=hi,passed=int(feasible.sum()),failed=int((~feasible).sum()),
                hours=len(g),min_v_pu=float(g.min_v_pu.min()),max_v_pu=float(g.max_v_pu.max()),
                max_trafo_pct=float(g.max_trafo_pct.max()),max_line_pct=float(g.max_line_pct.max())))
    summary=pd.DataFrame(rows)
    orig=pd.read_csv(sf)
    for (pf,service),g in groups:
        ref=orig[(orig.load_pf==pf)&(orig.service_factor==service)]
        if len(ref)!=1: raise ValueError('Source summary missing or duplicated')
        r=ref.iloc[0]
        row=summary[(summary.load_pf==pf)&(summary.service_factor==service)&
                     (summary.band=='Original strict research')].iloc[0]
        if row.passed!=r.feasible_hours or abs(row.min_v_pu-r.min_v_pu)>1e-8:
            raise ValueError('Source strict AC results mismatch')
    return d, summary, man, {'sensitivity_ac_hours.csv':sha(f),
                             'robustness_manifest.json':sha(mf),
                             'sensitivity_scenarios.csv':sha(sf)}

def plot(d:pd.DataFrame, summary:pd.DataFrame, out:Path):
    import matplotlib.pyplot as plt
    groups=list(d.groupby(['load_pf','service_factor'],sort=True))
    if len(groups)!=1:
        # Multi-scenario output remains a CSV; avoid misleading single-series charts.
        return
    (pf,factor),g=groups[0]
    tag=f'PF {pf:g}; assumed service-length ×{factor:g}; 8,760 hours'
    fig,ax=plt.subplots(figsize=(9.4,5.1),layout='constrained')
    y=np.sort(g.min_v_pu.to_numpy(float))
    ax.plot(np.arange(1,len(y)+1),y,lw=1.8,label='Minimum household voltage')
    ax.axhline(.95,ls='--',lw=1.5,label='Engineering study minimum: 0.95 pu')
    ax.axhline(.97,ls=':',lw=1.5,label='Strict research minimum: 0.97 pu')
    ax.set(xlabel='Hours, sorted by increasing minimum voltage',ylabel='Minimum modelled household voltage (pu)',
           title='Full-year voltage duration, '+tag)
    ax.grid(alpha=.2);ax.legend(fontsize=9)
    fig.savefig(out/'full_year_voltage_duration.png',dpi=170);plt.close(fig)

    rows=summary[(summary.load_pf==pf)&(summary.service_factor==factor)].copy()
    fig,ax=plt.subplots(figsize=(9.4,5.1),layout='constrained')
    vals=rows.failed.to_numpy(int)
    labels=[f'{r.band}\n{r.lower_pu:.2f}–{r.upper_pu:.2f} pu' for r in rows.itertuples()]
    b=ax.bar(labels,vals)
    for bar,val in zip(b,vals):
        ax.text(bar.get_x()+bar.get_width()/2,val+max(2,max(vals)*.02),str(int(val)),ha='center',va='bottom')
    ax.set_ylim(0,max(1,int(max(vals)*1.18)))
    ax.set(ylabel='Failed modelled hourly magnitude screens',title='Full-year voltage bands, '+tag)
    ax.grid(axis='y',alpha=.2);ax.tick_params(axis='x',labelsize=8)
    fig.savefig(out/'full_year_voltage_band_failures.png',dpi=170);plt.close(fig)

    fail=g[g.min_v_pu < .97-1e-6]
    counts=fail.timestamp.dt.month.value_counts().reindex(range(1,13),fill_value=0).sort_index()
    fig,ax=plt.subplots(figsize=(9.4,4.7),layout='constrained')
    ax.bar([str(m) for m in counts.index],counts.values)
    ax.set(xlabel='Month of 2025',ylabel='Hours below 0.97 pu',title='Timing of strict-band failures, '+tag)
    ax.grid(axis='y',alpha=.2)
    fig.savefig(out/'full_year_strict_failures_by_month.png',dpi=170);plt.close(fig)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--robustness-dir',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True)
    args=ap.parse_args(argv)
    if args.outdir.exists():ap.error('Refusing to overwrite existing output directory')
    d,s,man,hashes=load_review(args.robustness_dir)
    args.outdir.mkdir(parents=True)
    s.to_csv(args.outdir/'full_year_voltage_band_summary.csv',index=False,float_format='%.9f')
    plot(d,s,args.outdir)
    audit={ 'status':'POSTPROCESS_ONLY', 'no_new_ac_or_pypsa_solve':True,
           'source_mode':man['mode'], 'full_year_hours_per_case':man['hours_per_case'],
           'source_sha256':hashes, 'voltage_bands':'magnitude_screen_only_not_compliance',
           'summary_records':len(s) }
    (args.outdir/'full_year_voltage_review_manifest.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(s[['band','passed','failed','min_v_pu']].to_string(index=False))

if __name__=='__main__':main()
