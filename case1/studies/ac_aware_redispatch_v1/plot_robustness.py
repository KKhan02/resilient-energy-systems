#!/usr/bin/env python3
"""Plot conditional PF vs service-length-factor sensitivity results from run_robustness.

Figures are descriptive, never replace full-year AC checks or validation manifests.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np


def plot_sweep(results:pd.DataFrame, target:Path, title_prefix:str):
    import matplotlib.pyplot as plt
    pfs=sorted(results.load_pf.unique(),reverse=True)
    lengths=sorted(results.service_factor.unique())
    vals=np.full((len(pfs),len(lengths)),np.nan)
    counts=np.full((len(pfs),len(lengths)),np.nan)
    for r in results.itertuples():
        i=pfs.index(r.load_pf);j=lengths.index(r.service_factor)
        vals[i,j]=r.min_v_pu if pd.notna(r.min_v_pu) else np.nan
        counts[i,j]=r.violating_or_failed_hours
    fig,ax=plt.subplots(figsize=(max(6,len(lengths)*2.3),max(4,len(pfs)*1.6)))
    masked=np.ma.masked_invalid(vals)
    image=ax.imshow(masked,aspect='auto')
    fig.colorbar(image,ax=ax,label='Minimum modelled household voltage, pu')
    ax.set_xticks(range(len(lengths)),[str(f) for f in lengths]);ax.set_yticks(range(len(pfs)),[str(p) for p in pfs])
    ax.set_xlabel('Assumed service-length multiplier');ax.set_ylabel('Household load power factor')
    ax.set_title(title_prefix)
    for i in range(len(pfs)):
        for j in range(len(lengths)):
            s=(f'{vals[i,j]:.5f} pu\n{int(counts[i,j])} fail' if np.isfinite(vals[i,j])
               and np.isfinite(counts[i,j]) else 'No valid solve')
            ax.text(j,i,s,ha='center',va='center',fontsize=9,bbox=dict(boxstyle='round',facecolor='white',alpha=.75))
    fig.tight_layout()
    target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target,dpi=160)
    fig.savefig(target.with_suffix('.svg'))
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results-dir',type=Path,required=True)
    a=p.parse_args()
    d=a.results_dir.resolve()
    csv=d/'sensitivity_scenarios.csv'
    if not csv.is_file():p.error('Missing '+str(csv))
    df=pd.read_csv(csv)
    if df.empty:p.error('Empty sensitivity scenarios')
    kinds=set(df.conclusion.astype(str))
    mode='FULL-YEAR CHECK' if all(s.startswith('CONDITIONAL_FULL_YEAR') for s in kinds) else 'CRITICAL-HOUR SCREEN ONLY'
    plot_sweep(df,d/'figures'/'pf_service_voltage_sensitivity.png',
               f'WP1 {df.scenario.iloc[0]}, {mode}: P fixed, reactive control evaluated')
    print('Figures saved under',d/'figures')

if __name__=='__main__':main()
