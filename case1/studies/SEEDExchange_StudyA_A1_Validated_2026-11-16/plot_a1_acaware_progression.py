#!/usr/bin/env python3
"""Read-only Stage 13 visual evidence of AC-aware A1 correction; requires supplied audited 36-row CSV."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib as mpl

HERE=Path(__file__).resolve().parent
mpl.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':13,
    'axes.labelsize':10,'figure.facecolor':'white','savefig.facecolor':'white',
    'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})

def exact(df,scenario,tier,pf,length):
    a=df[(df.scenario==scenario)&(df.tier==tier)&np.isclose(df.pf,pf)&np.isclose(df.length_factor,length)]
    assert len(a)==1,(scenario,tier,pf,length,len(a))
    return a.iloc[0]

def emit(fig,folder,name):
    folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/(name+'.png'),dpi=280,bbox_inches='tight',pad_inches=.2)
    fig.savefig(folder/(name+'.svg'),bbox_inches='tight',pad_inches=.2)
    plt.close(fig)

def plot1(df,folder):
    fig,axes=plt.subplots(1,2,figsize=(11.3,5.1),sharex=True)
    base0=exact(df,'A0','min_cost',.98,1.)
    ss0=exact(df,'A0','ss90',.98,1.)
    base1=exact(df,'A1','min_cost',.98,1.)
    ss1=exact(df,'A1','ss90',.98,1.)
    dat=[[
        ('Grid-only demand',base0.five_territory_gross_transformer_violation_hours,'#657385'),
        ('Minimum-cost PV+BESS',base0.five_territory_pvbess_transformer_violation_hours,'#3b8bb4'),
        ('Higher-SS PV+BESS',ss0.five_territory_pvbess_transformer_violation_hours,'#219377')],
        [('Grid-only demand',base1.five_territory_gross_transformer_violation_hours,'#657385'),
        ('Min-cost, energy-only dispatch',base1.five_territory_pvbess_transformer_violation_hours,'#3b8bb4'),
        ('Min-cost, AC-aware dispatch',base1.pvbess_after_ACaware_violation_hours,'#219377'),
        ('Higher-SS, energy-only dispatch',ss1.five_territory_pvbess_transformer_violation_hours,'#3b8bb4'),
        ('Higher-SS, AC-aware dispatch',ss1.pvbess_after_ACaware_violation_hours,'#219377')]]
    for ax,rows,sc in zip(axes,dat,['A0 portfolio: uncorrected','A1: validated AC-aware correction']):
        yy=list(range(len(rows)))
        ax.barh(yy,[r[1] for r in rows],height=.48,color=[r[2] for r in rows],zorder=3)
        for y,(name,val,color) in enumerate(rows):
            ax.text(float(val)+1.5,y,str(int(val)),va='center',ha='left',fontsize=10,fontweight='semibold',color='#1c2935')
        ax.set_yticks(yy,[r[0] for r in rows],fontsize=9)
        ax.set_xlim(0,120)
        ax.grid(axis='x',alpha=.15,zorder=0)
        ax.invert_yaxis();ax.set_title(sc,loc='left',fontsize=12,fontweight='semibold',pad=12)
        ax.set_xlabel('Summed annual violation territory-hours')
    fig.suptitle('A1: storage redispatch removes the last modelled AC violations',fontsize=14,x=.065,ha='left',y=1.015)
    fig.subplots_adjust(wspace=.65,bottom=.24,top=.83,left=.205,right=.98)
    fig.text(.062,.07,'2025, 34 households, proposed 92395 STAR, PF 0.98, service ×1.0; optimized energy schedules. A0 remains uncorrected.',fontsize=8.8,color='#53616c')
    emit(fig,folder,'P1_updated_A0_A1_gross_PVBESS_ACaware')

def plot2(df,folder):
    panels=[('A0: higher SS, unchanged','A0','five_territory_pvbess_transformer_violation_hours'),
            ('A1: higher SS, original','A1','five_territory_pvbess_transformer_violation_hours'),
            ('A1: higher SS, corrected','A1','pvbess_after_ACaware_violation_hours')]
    vals=[]
    for _,sc,col in panels:
        vals.append(np.array([[exact(df,sc,'ss90',pf,l)[col] for l in [1.,1.3,1.6]] for pf in [.95,.98,1.]],dtype=float))
    vmax=float(max(x.max() for x in vals))
    fig,axs=plt.subplots(1,3,figsize=(11.6,4.6))
    for ax,arr,(title,_,_) in zip(axs,vals,panels):
        im=ax.imshow(arr,cmap='viridis_r',vmin=0,vmax=max(1,vmax),aspect='equal')
        ax.set_xticks([0,1,2],['1.0×','1.3×','1.6×']);ax.set_yticks([0,1,2],['0.95','0.98','1.00'])
        ax.set_xlabel('Service multiplier');ax.set_title(title,fontsize=10.5,pad=12,fontweight='medium')
        ax.set_xticks(np.arange(-.5,3,1),minor=True);ax.set_yticks(np.arange(-.5,3,1),minor=True)
        ax.grid(which='minor',color='white',linewidth=2.8)
        ax.tick_params(which='minor',bottom=False,left=False,length=0)
        for i in range(3):
            for j in range(3):
                ax.text(j,i,str(int(arr[i,j])),fontsize=12,fontweight='semibold',color='white' if arr[i,j]>vmax*.55 else '#122530',ha='center',va='center')
    axs[0].set_ylabel('Power factor')
    cax=fig.add_axes([.91,.265,.014,.50])
    cb=fig.colorbar(im,cax=cax)
    cb.set_label('Annual violation territory-hours')
    fig.suptitle('AC-aware battery timing changes the nine-factor robustness result',x=.04,ha='left',fontsize=13.5,y=.995)
    fig.subplots_adjust(left=.06,right=.875,top=.84,bottom=.21,wspace=.27)
    fig.text(.055,.07,'2025, same 34 houses and 0.95–1.05 pu / 100% loading screens. A1 correction rechecks changed hours; unchanged hours reused.',fontsize=8.3,color='#53616c')
    emit(fig,folder,'P2_updated_A0_A1_ACaware_robustness')

if __name__=='__main__':
    a=pd.read_csv(HERE/'A0_A1_36_AGGREGATES_WITH_ACAWARE.csv')
    assert len(a)==36 and len(a.drop_duplicates(['scenario','tier','pf','length_factor']))==36
    assert (a[a.scenario=='A1'].pvbess_after_ACaware_violation_hours==0).all()
    o=HERE/'figures';plot1(a,o);plot2(a,o)
    print('Wrote',*(x.name for x in sorted(o.iterdir())),sep='\n - ')
