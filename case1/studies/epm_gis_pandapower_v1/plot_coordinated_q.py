#!/usr/bin/env python3
"""Poster-readable, unconnected Q sweep comparisons. Only plots actual AC results."""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

STYLES={'unity':('#686f7f','D'),'hil':('#C78325','o'),'coordinated':('#138B84','s')}


def plot(data,out):
    needed={'trafo','siting','load_pf','service_factor','policy','q_ratio',
            'min_v_pu','max_v_pu','max_trafo_pct','hours','feasible_hours'}
    missing=needed-set(data.columns)
    if missing:raise ValueError('Missing result columns: '+', '.join(sorted(missing)))
    out.mkdir(parents=True,exist_ok=True)
    made=[]
    for keys,g in data.groupby(['trafo','siting','load_pf','service_factor'],dropna=False):
        tr,siting,pf,factor=keys
        fig,ax=plt.subplots(2,2,figsize=(11,7.8),layout='constrained')
        series=[('min_v_pu','Minimum house voltage (pu)',.97),
                ('max_v_pu','Maximum house voltage (pu)',1.03),
                ('max_trafo_pct','Peak transformer loading (%)',100.),
                ('feasible_fraction','Hours passing all AC limits (%)',100.)]
        g=g.copy();g['feasible_fraction']=100*g.feasible_hours/g.hours
        for policy,pg in g.groupby('policy'):
            color,marker=STYLES.get(policy,('#8860a8','o'))
            for a,(col,title,limit) in zip(ax.flat,series):
                valid=pg[['q_ratio',col]].replace([np.inf,-np.inf],np.nan).dropna()
                a.scatter(valid.q_ratio,valid[col],c=color,marker=marker,s=72,
                          edgecolors='white',linewidths=.6,label=policy,zorder=3)
        for a,(col,label,limit) in zip(ax.flat,series):
            a.axhline(limit,color='#A34C4C' if col!='feasible_fraction' else '#4C8477',ls='--',lw=1)
            a.set_xlabel('Q capability ratio, Qmax / installed P')
            a.set_ylabel(label)
            a.grid(alpha=.2)
            a.set_xlim(max(-.03,float(g.q_ratio.min())-.04),min(1.03,float(g.q_ratio.max())+.04))
        handles,labels=ax.flat[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='outside upper center',ncol=3,frameon=False)
        fig.suptitle(f'Transformer {tr} | inverter: {siting} | load PF {pf:.2f} | service x{factor:g}',fontsize=13)
        stem=f'Q_sweep_{tr}_{siting}_pf{pf:.2f}_service{factor:g}'.replace('.','p')
        for ext in ('.png','.svg'):
            fig.savefig(out/(stem+ext),dpi=200)
        plt.close(fig);made.append(stem)
    # These are not automatically 'optimal'; they are passing configurations from discrete tested grid.
    passes=data.loc[(data.feasible_hours==data.hours)&(data.failed_hours==0)].copy()
    passes.to_csv(out/'all_sampled_hours_feasible.csv',index=False)
    return made,len(passes)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    d=pd.read_csv(a.input)
    n,k=plot(d,a.output)
    print('Created',len(n),'four-panel figures; passing scenarios:',k)

if __name__=='__main__':main()
