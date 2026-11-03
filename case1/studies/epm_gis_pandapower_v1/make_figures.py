"""Generate scatter-only, poster-ready comparisons from completed EPM AC results."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ORDER=['unity','fixed_pf_inject','fixed_pf_absorb','volt_var']
COLORS={'head':'#1677B9','middle':'#DE7B25','end':'#178E66'}

def write_figure(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=230,bbox_inches='tight')
    fig.savefig(out/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--transformers',nargs='+',default=['94022','106039'])
    ap.add_argument('--service-factor',type=float,default=1.)
    ap.add_argument('--load-pf',type=float,default=.98)
    ap.add_argument('--design',default='optimized')
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(args.input)
    df['trafo']=df['trafo'].astype(str)
    filtercols={'trafo':args.transformers,'service_factor':[args.service_factor],
                'load_pf':[args.load_pf],'design':[args.design]}
    for k,choices in filtercols.items():df=df[df[k].isin(choices)]
    if df.empty:raise SystemExit('No matching results. Check filters and CSV.')
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.18,'figure.facecolor':'white'})
    for tid in args.transformers:
        v=df[df.trafo.astype(str)==str(tid)]
        if v.empty:continue
        fig,ax=plt.subplots(figsize=(8.6,4.6))
        for j,(s,part) in enumerate(v.groupby('siting')):
            for i,control in enumerate(ORDER):
                sel=part[part.q_control_label==control]
                if len(sel):
                    x=i+{'head':-.18,'middle':0.,'end':.18}.get(s,0.)
                    ax.scatter([x],[sel.min_v.min()],color=COLORS[s],s=90,marker='o',label=s if i==0 else None)
                    ax.scatter([x],[sel.max_v.max()],color=COLORS[s],s=90,marker='^')
        ax.axhline(.97,linestyle=':',color='#A94442');ax.axhline(1.03,linestyle=':',color='#A94442')
        ax.set_xticks(range(len(ORDER)),['Unity PF','Fixed PF +Q','Fixed PF -Q','HIL Volt–Var'])
        ax.set_ylabel('LV voltage (pu)');ax.set_title(f'Transformer {tid}: voltage envelope by inverter control')
        ax.text(.01,.02,'Circles: minimum; triangles: maximum',transform=ax.transAxes,fontsize=9,alpha=.7)
        h,l=ax.get_legend_handles_labels();ax.legend(h[:3],l[:3],title='Inverter position',ncol=3,fontsize=9)
        write_figure(fig,args.output,f'{tid}_voltage_by_hil_control')
        fig,ax=plt.subplots(figsize=(8.6,4.6))
        for j,s in enumerate(('head','middle','end')):
            part=v[v.siting==s]
            for i,control in enumerate(ORDER):
                sel=part[part.q_control_label==control]
                if len(sel):
                    ax.scatter(i+[-.18,0,.18][j],sel.max_trafo_pct.max(),
                        color=COLORS[s],s=95,label=s if i==0 else None)
        ax.axhline(100,linestyle=':',color='#A94442')
        ax.set_xticks(range(len(ORDER)),['Unity PF','Fixed PF +Q','Fixed PF -Q','HIL Volt–Var'])
        ax.set_ylabel('Peak transformer loading (%)')
        ax.set_title(f'Transformer {tid}: loading under reactive control')
        ax.legend(title='Inverter position',ncol=3)
        write_figure(fig,args.output,f'{tid}_loading_by_hil_control')
    if {'below_097','above_103'}.issubset(df.columns):
        ss=df.groupby(['trafo','siting','q_control_label'],as_index=False).agg(
            low=('below_097','sum'),high=('above_103','sum'),hours=('hours','sum'))
        ss.to_csv(args.output/'violations_by_siting_and_controller.csv',index=False)
    print('Figures saved to',args.output)

if __name__=='__main__':main()
