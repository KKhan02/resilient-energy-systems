#!/usr/bin/env python3
"""Three compact figures after geographic AC study. Unconnected points only."""
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,default=Path('outputs/geographic_critical/ac_scenario_summary.csv'))
    ap.add_argument('--output',type=Path,default=None)
    a=ap.parse_args()
    if not a.input.exists():ap.error('No summary CSV: '+str(a.input))
    out=a.output or a.input.parent/'figures';out.mkdir(parents=True,exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    d=pd.read_csv(a.input)
    b=d[(d.assignment=='base')&(d.routing=='mst')&(np.isclose(d.route_factor,1.3))&(np.isclose(d.pf,.98))&(d.allocation=='equal')]
    if not len(b):
        b=d.copy()
    groups=['94022','106039','92395','85398','113699','98380','NORTH_25KVA']
    sitings=['head','middle','end'];color={'head':'#2166ac','middle':'#e59e32','end':'#c63c6f'}
    for metric,title,limit,name in [
      ('min_voltage_pu','Worst household voltage (pu)',.97,'01_worst_house_voltage'),
      ('max_trafo_pct','Maximum transformer loading (%)',100,'02_transformer_loading'),
      ('max_line_pct','Maximum LV line loading (%)',100,'03_lv_line_loading')]:
        fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
        for i,site in enumerate(sitings):
            cur=b[b.siting==site]
            # For each asset, prefer optimized dispatch if available, otherwise gross-only.
            selections=[]
            for k,v in cur.groupby('trafo'):
                selected=v[v.design=='optimized'] if (v.design=='optimized').any() else v
                if len(selected):selections.append(selected.iloc[0])
            if selections:
                sel=pd.DataFrame(selections)
                xs=[groups.index(t)+(-.23+i*.23) for t in sel.trafo if t in groups]
                yy=sel.loc[sel.trafo.isin(groups),metric]
                ax.scatter(xs,yy,s=75,edgecolor='white',linewidth=.5,color=color[site],label=site,zorder=3)
        ax.axhline(limit,color='black',linestyle='--',linewidth=1)
        ax.set_xticks(list(range(len(groups))));ax.set_xticklabels(groups,rotation=25,ha='right')
        ax.set_ylabel(title);ax.set_xlabel('Candidate transformer ID')
        ax.grid(alpha=.2,axis='y');ax.legend(frameon=False,ncol=3)
        for ext in ['png','svg']:fig.savefig(out/f'{name}.{ext}',dpi=220,bbox_inches='tight')
        plt.close(fig)
    print('Saved:',out.resolve())
if __name__=='__main__':main()
