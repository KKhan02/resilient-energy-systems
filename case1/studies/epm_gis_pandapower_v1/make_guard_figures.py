"""Poster-style, unconnected comparison of transformer-aware Q guarding.

Use only after actual pandapower runs have produced ac_scenario_summary.csv.
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--service-factor',type=float,default=1.0)
    ap.add_argument('--power-factor',type=float,default=.98)
    ap.add_argument('--transformers',nargs='+',default=['94022','106039'])
    ap.add_argument('--siting',nargs='+',default=['head','middle'])
    ap.add_argument('--controls',nargs='+',default=['unity','volt_var'])
    a=ap.parse_args()
    if not a.input.is_file():raise SystemExit('Missing summary CSV: '+str(a.input))
    df=pd.read_csv(a.input)
    needed={'trafo','design','service_factor','load_pf','siting','q_control_label','q_ratio','trafo_guard',
            'min_v','max_v','max_trafo_pct','below_097','above_103','trafo_over100_hours',
            'guard_limited_hours','guard_unresolved_hours','failed_hours'}
    missing=needed-set(df.columns)
    if missing:raise SystemExit('This is not a guarded v1.1 output; missing '+', '.join(sorted(missing)))
    df['trafo']=df['trafo'].astype(str)
    df=df[(df.design=='optimized') & np.isclose(df.service_factor,a.service_factor) &
          np.isclose(df.load_pf,a.power_factor) & df.siting.isin(a.siting) &
          df.q_control_label.isin(a.controls)]
    a.output.mkdir(parents=True,exist_ok=True)
    if df.empty:raise SystemExit('No matching rows for this comparison')
    plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.14})
    colors={.25:'#277DA1',.48:'#CF7722'}
    settings=[('min_v','Minimum voltage (pu)',.97),
              ('max_v','Maximum voltage (pu)',1.03),
              ('max_trafo_pct','Peak transformer loading (%)',100.),
              ('guard_unresolved_hours','Unresolved transformer-overload hours',None)]
    labels=[f'{site}\n{ctrl.replace("volt_var","Volt–Var").replace("unity","Unity")}' for site in a.siting for ctrl in a.controls]
    for t in a.transformers:
        xdf=df[df.trafo==str(t)]
        if xdf.empty:continue
        fig,axs=plt.subplots(2,2,figsize=(11,7.4),layout='constrained')
        for ax,(col,lab,threshold) in zip(axs.flat,settings):
            for idx,(site,ctrl) in enumerate([(s,c) for s in a.siting for c in a.controls]):
                sub=xdf[(xdf.siting==site)&(xdf.q_control_label==ctrl)]
                for _,r in sub.iterrows():
                    guard=str(r.trafo_guard)
                    ratio=float(r.q_ratio)
                    offset=(-.14 if guard=='off' else .14)+(-.035 if ratio<.4 else .035)
                    color=colors.get(ratio,'#6B70A9')
                    ax.scatter(idx+offset,float(r[col]),s=86,marker=('o' if guard=='off' else 'D'),
                               color=color,edgecolor='#172337',linewidth=.7,zorder=3)
            if threshold is not None:
                ax.axhline(threshold,color='#BD3E44',lw=1.2,ls=':',alpha=.8)
            ax.set_xticks(range(len(labels)),labels)
            ax.tick_params(axis='x',labelsize=8)
            ax.set_ylabel(lab)
            ax.set_xlim(-.6,len(labels)-.4)
        handles=[]
        from matplotlib.lines import Line2D
        for ratio,c in colors.items():
            handles.append(Line2D([0],[0],marker='o',linestyle='None',color=c,label=f'Q ratio {ratio:.2f}',markersize=7))
        for guard,marker in [('off','o'),('enforce','D')]:
            handles.append(Line2D([0],[0],marker=marker,linestyle='None',color='#30343B',label=f'Guard {guard}',markersize=7))
        fig.legend(handles=handles,ncol=4,loc='outside lower center',bbox_to_anchor=(.5,-.01),frameon=False)
        fig.suptitle(f'EPM transformer {t}: reactive control with / without thermal safeguard')
        out=a.output/f'{t}_q_guard_scatter'
        fig.savefig(out.with_suffix('.png'),dpi=220,bbox_inches='tight')
        fig.savefig(out.with_suffix('.svg'),bbox_inches='tight')
        plt.close(fig)
    df.to_csv(a.output/'filtered_guard_comparisons.csv',index=False)
    print('Wrote guarded comparison charts to',a.output)

if __name__=='__main__':main()
