"""WP1 figures. All figures use the SAME screened configuration table."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

COLORS={0:'#64748b',2:'#a855f7',4:'#2563eb',6:'#0d9488',8:'#d97706',10:'#be185d',12:'#16a34a',16:'#0e7490',20:'#b45309',24:'#7c3aed'}
MARKERS={8:'v',12:'o',16:'s',20:'D',24:'^',28:'P',32:'X',36:'h',40:'*',48:'<',56:'>',64:'p',72:'8',80:'d'}

def eligible_designs(df):
    """Algebraic PCC screen only: zero unmet grid demand, within kVA limit.
    This is not a feeder-voltage or protection feasibility certificate.
    """
    return df[(df.grid_ens_kwh<=1e-7) &
              (df.max_trafo_kva<=df.transformer_allow_kva+1e-7)]


def frontier(df,cost):
    # Positional uniqueness avoids duplicating rows when concat retains labels.
    d=df.reset_index(drop=True).sort_values(
        [cost,'self_sufficiency_pct'],ascending=[True,False])
    best=-float('inf'); picks=[]
    for row in d.itertuples(index=True):
        if row.self_sufficiency_pct>best+1e-6:
            picks.append(row.Index); best=row.self_sufficiency_pct
    return d.loc[picks].sort_values('self_sufficiency_pct')


def pareto_panels(df, out: Path):
    """Publication-ready static Pareto plots; every tested case carries BESS color.

    The frontier is computed separately for each household count and economic regime.
    Hardware-pre-screened cases with involuntary grid-connected ENS are shown as
    colored crosses, not silently omitted. Passing means PCC-screening only.
    """
    import matplotlib as mpl
    from matplotlib.cm import ScalarMappable
    from matplotlib.lines import Line2D
    from matplotlib.colors import Normalize

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    hhs = sorted(int(h) for h in df.households.unique())
    max_bess = float(df.bess_usable_kwh.max())
    norm = Normalize(vmin=0.0, vmax=max(1.0, max_bess))
    cmap = plt.get_cmap('viridis')
    regimes = [('self_consumption', 'annual_total_no_credit_usd', 'Exports not compensated'),
               ('homer_sellback', 'annual_total_homer_credit_usd', 'HOMER export credit: 0.275 USD/kWh')]

    def pv_bin(p):
        if p <= 16: return '8–16 panels'
        if p <= 32: return '20–32 panels'
        if p <= 56: return '36–56 panels'
        return '64–80 panels'

    markers = {'8–16 panels': 'o', '20–32 panels': 's',
               '36–56 panels': 'D', '64–80 panels': '^'}
    groups = list(markers)

    def draw_panel(ax, hh, cost_col, annotate=False):
        sub = df[df.households == hh]
        passing = eligible_designs(sub)
        failed = sub.drop(index=passing.index)
        # Color EVERY plotted point with the same continuous BESS-size scale.
        for g in groups:
            pass_g = passing[passing.panels.map(pv_bin) == g]
            if len(pass_g):
                ax.scatter(pass_g.self_sufficiency_pct, pass_g[cost_col],
                           c=pass_g.bess_usable_kwh, cmap=cmap, norm=norm,
                           marker=markers[g], s=23, alpha=.69, zorder=2,
                           linewidths=.1, edgecolors=(0, 0, 0, .12))
        # Physically infeasible in the algebraic PCC screen: same colors,
        # distinct cross marker and lower opacity, never included in frontier.
        if len(failed):
            ax.scatter(failed.self_sufficiency_pct, failed[cost_col],
                       c=failed.bess_usable_kwh, cmap=cmap, norm=norm,
                       marker='x', s=20, alpha=.23, zorder=1,linewidths=.7)
        if len(passing):
            line = frontier(passing,cost_col)
            ax.plot(line.self_sufficiency_pct, line[cost_col], '-',
                    color='black', lw=2.5, zorder=5, solid_capstyle='round')
            # Retain each frontier point's BESS color, with a black outline.
            ax.scatter(line.self_sufficiency_pct, line[cost_col],
                       c=line.bess_usable_kwh, cmap=cmap, norm=norm,
                       s=54, edgecolors='black', linewidths=.85, zorder=6)
            cheapest = passing.sort_values([cost_col,'self_sufficiency_pct'],
                                          ascending=[True,False]).iloc[0]
            ax.scatter([cheapest.self_sufficiency_pct],[cheapest[cost_col]],
                       s=140, marker='*', facecolors='none',
                       edgecolors='black', linewidths=1.5, zorder=7)
            if annotate:
                a = line.sort_values(cost_col).iloc[0]
                b = line.sort_values('self_sufficiency_pct').iloc[-1]
                for d,tag,offset in [(a,'Least annual cost',(12,-23)),
                                      (b,'Highest self-sufficiency',(-140,18))]:
                    ax.annotate(f'{tag}\n{int(d.panels)}P / {int(d.bess_modules)}B / {d.inverter_kva:g}kVA',
                                xy=(d.self_sufficiency_pct,d[cost_col]),
                                xytext=offset,textcoords='offset points',fontsize=8.4,
                                bbox=dict(boxstyle='round,pad=.25', fc='white',ec='0.8',alpha=.92),
                                arrowprops=dict(arrowstyle='-',lw=.7,color='0.3'))
        ax.set_title(f'{hh} households  |  {len(passing):,} pass / {len(sub):,} tested',fontsize=11)
        ax.set_xlabel('Annual demand self-sufficiency (%)',fontsize=9)
        ax.set_ylabel('Equipment + net grid cost (USD/year)',fontsize=9)
        ax.grid(True,alpha=.18,zorder=0)
        ax.tick_params(labelsize=8)
        if not len(passing):
            ax.text(.5,.93,'No PCC-passing design in tested range',
                    transform=ax.transAxes,ha='center',va='top',fontsize=8.5,
                    bbox=dict(fc='white',ec='none',alpha=.85))

    legend = [Line2D([],[],marker=markers[g], linestyle='None',
                     color='#444',markersize=6,label=g) for g in groups]
    legend += [Line2D([],[],color='black',lw=2.5,label='Nondominated PCC frontier'),
               Line2D([],[],marker='x', linestyle='None',color='#444',
                      markersize=6,label='Excluded: unserved grid demand'),
               Line2D([],[],marker='*',linestyle='None',markerfacecolor='none',
                      markeredgecolor='black',markersize=10,label='Lowest annual cost')]

    def attach_colorbar(fig,cax):
        sm = ScalarMappable(norm=norm,cmap=cmap)
        sm.set_array([])
        cb=fig.colorbar(sm,cax=cax)
        cb.set_label('Usable BESS capacity (kWh)',fontsize=11)
        cb.set_ticks(np.linspace(0,max_bess,6))
        cb.ax.tick_params(labelsize=9)

    # A single overview per tariff case, with 6 meaningful household levels.
    choices=[h for h in (4,8,12,15,17,20) if h in hhs]
    for code,col,title in regimes:
        fig,axes=plt.subplots(3,2,figsize=(15.3,15),dpi=160)
        for ax,hh in zip(axes.flat,choices):
            draw_panel(ax,hh,col)
        for ax in list(axes.flat)[len(choices):]:ax.axis('off')
        fig.suptitle(f'PV–BESS–inverter economic Pareto  |  {title}',
                     fontsize=17,y=.985)
        fig.subplots_adjust(left=.083,right=.873,top=.942,bottom=.115,
                            hspace=.38,wspace=.34)
        attach_colorbar(fig,fig.add_axes([.9,.23,.019,.60]))
        fig.legend(handles=legend,loc='lower center',ncol=4,
                   bbox_to_anchor=(.48,.017),fontsize=9,frameon=False,
                   columnspacing=1.5)
        fig.savefig(out/f'01_pareto_all_designs_{code}.png',dpi=175,facecolor='white')
        plt.close(fig)

        # Every household count has its own chart to avoid a cramped overview.
        detail=out/'pareto_per_household'
        detail.mkdir(parents=True,exist_ok=True)
        for hh in hhs:
            fig,ax=plt.subplots(figsize=(11.5,7.0),dpi=150)
            draw_panel(ax,hh,col,annotate=False)
            s_passing = eligible_designs(df[df.households == hh])
            fig.suptitle(f'PV–BESS sizing  |  {hh} households  |  {title}',fontsize=14)
            if len(s_passing):
                f = frontier(s_passing,col)
                a = f.sort_values(col).iloc[0]
                b = f.sort_values('self_sufficiency_pct').iloc[-1]
                fig.text(.45,.905,
                   f'Least cost: {int(a.panels)}P / {int(a.bess_modules)}B / {a.inverter_kva:g} kVA    |    '
                   f'Highest self-sufficiency: {int(b.panels)}P / {int(b.bess_modules)}B / {b.inverter_kva:g} kVA',
                   ha='center',fontsize=8.5,color='#444444')
            fig.subplots_adjust(left=.095,right=.81,top=.85,bottom=.20)
            attach_colorbar(fig,fig.add_axes([.85,.25,.024,.57]))
            fig.legend(handles=legend,loc='lower center',ncol=4,
                       bbox_to_anchor=(.44,.023),fontsize=8,frameon=False)
            fig.savefig(detail/f'pareto_{code}_{hh:02d}_households.png',
                        dpi=165,facecolor='white')
            plt.close(fig)

def expansion_plots(df,out:Path):
    feasible=eligible_designs(df)
    fig,axes=plt.subplots(1,2,figsize=(13,5.5),layout='constrained')
    for target,mark in [(80,'o'),(90,'s'),(95,'^')]:
        counts=[];households=sorted(df.households.unique())
        for h in households:
            s=feasible[(feasible.households==h)&(feasible.self_sufficiency_pct>=target)]
            counts.append(float(s.annual_total_no_credit_per_house_usd.min()) if len(s) else np.nan)
        axes[0].plot(households,counts,'-'+mark,label=f'{target}% self-sufficiency')
    axes[0].set_title('Least annual cost per household by target')
    axes[0].set_xlabel('Households');axes[0].set_ylabel('USD / household / year')
    axes[0].legend();axes[0].grid(alpha=.2)
    for panels in (16,24,40,56,80):
        a=feasible[feasible.panels==panels].groupby('households').self_sufficiency_pct.max()
        axes[1].plot(a.index,a.values,'-o',label=f'{panels} panels')
    axes[1].axhline(90,ls='--',color='0.4',label='90% illustrative target')
    axes[1].set_xlabel('Households');axes[1].set_ylabel('Best achievable self-sufficiency (%)')
    axes[1].set_title('Best with each PV size, across BESS and inverters')
    axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    fig.savefig(out/'02_household_expansion_feasible_designs.png',dpi=170);plt.close(fig)


def duration_plot(samples,out:Path,cap_pu=.9):
    fig,ax=plt.subplots(figsize=(10,5.8))
    for label,df in samples.items():
        curve=np.sort(df.pcc_kva.to_numpy())[::-1]
        ax.plot(np.arange(len(curve)),curve,label=label,lw=1.55)
    ax.axhline(5*cap_pu,ls='--',color='black',
               label=f'Assumed {100*cap_pu:g}% loading: {5*cap_pu:g} kVA')
    ax.axhline(5,ls=':',color='black',label='Transformer nameplate: 5 kVA')
    ax.set_title('Transformer loading duration, annual 2025 dispatch')
    ax.set_xlabel('Hours ranked from highest to lowest loading');ax.set_ylabel('PCC apparent power (kVA)')
    ax.set_xlim(0,8760);ax.grid(alpha=.2);ax.legend(fontsize=9)
    fig.tight_layout();fig.savefig(out/'03_transformer_loading_duration.png',dpi=170);plt.close(fig)


def monthly_balance(samples,out:Path):
    fig,axes=plt.subplots(len(samples),1,figsize=(12,3.6*len(samples)),sharex=True,layout='constrained')
    axes=np.atleast_1d(axes)
    for ax,(label,(frame,load,pv)) in zip(axes,samples.items()):
        d=frame.resample('MS').sum(numeric_only=True)
        x=np.arange(12);direct=d.pv_direct_ac.values;batt=d.battery_discharge_dc.values*.95;grid=d.grid_import.values
        ax.bar(x,direct,label='PV direct to demand')
        ax.bar(x,batt,bottom=direct,label='Battery discharge (AC)')
        ax.bar(x,grid,bottom=direct+batt,label='EPM imports')
        ax.plot(x,np.asarray(load.resample('MS').sum()),'k-o',markersize=3,lw=1,label='Demand')
        ax.set_ylabel('kWh/month');ax.set_title(label);ax.grid(alpha=.14,axis='y')
    axes[-1].set_xticks(np.arange(12),['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    axes[0].legend(ncol=4,fontsize=9)
    fig.savefig(out/'04_monthly_supply_multiple_community_sizes.png',dpi=170);plt.close(fig)


def resilience_plot(trace,summary,out:Path,event_start,event_end):
    fig,ax=plt.subplots(4,1,figsize=(13,11),sharex=True,layout='constrained')
    colors={'conventional':'#64748b','fixed_reserve':'#2563eb','adaptive':'#0d9488','adaptive_lm':'#d97706'}
    first=next(iter(trace.values()))
    t=first.index;load=summary['stressed_load'];pv=summary['stressed_pv_dc']
    ax[0].plot(t,load,color='black',lw=1.7,label='Stressed household demand')
    ax[0].plot(t,pv*.95,color='#eab308',lw=1.5,label='Available PV AC-equivalent')
    ax[0].set_ylabel('kW');ax[0].legend(fontsize=8)
    for name,r in trace.items():
        color=colors[name]
        cap=summary['usable_kwh']
        if cap>0:
            soc=(.1+r.soc_usable_kwh/cap*.9)*100
            ax[1].plot(t,soc,label=name,color=color,lw=1.4)
            ax[1].plot(t,r.reserve_soc*100,color=color,ls=':',alpha=.7,lw=1)
        ax[2].plot(t,r.battery_discharge_dc*.95,color=color,label=name)
        ax[3].plot(t,(r.ens.cumsum()+r.deferred_backlog_kwh),color=color,label=name)
    ax[1].set_ylabel('Actual SOC / reserve (%)');ax[1].legend(ncol=4,fontsize=8)
    ax[2].set_ylabel('Battery AC discharge (kW)');ax[2].legend(ncol=4,fontsize=8)
    ax[3].set_ylabel('Cumulative ENS + backlog (kWh)');ax[3].legend(ncol=4,fontsize=8)
    for a in ax:
        a.axvspan(event_start,event_end,facecolor='0.9',alpha=.65,zorder=-1)
        a.grid(alpha=.2)
    ax[0].set_title('72-hour combined stress: low solar + high demand + 48-hour EPM outage')
    ax[-1].set_xlabel('2025 local solar time, shaded region indicates EPM outage')
    fig.savefig(out/'05_72h_combined_stress_causal_controllers.png',dpi=170);plt.close(fig)


def battery_power_plot(df,out:Path):
    if df.empty:return
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for label,g in df.groupby('system'):
        g=g.sort_values('battery_power_cap_kw')
        axes[0].plot(g.battery_power_cap_kw,g.self_sufficiency_pct,'-o',label=label)
        axes[1].plot(g.battery_power_cap_kw,g.annual_total_no_credit_usd,'-o',label=label)
    axes[0].set_title('Battery power versus self-sufficiency')
    axes[0].set_ylabel('Self-sufficiency (%)')
    axes[1].set_title('Battery power versus annualized cost')
    axes[1].set_ylabel('Annualized total USD/year')
    for ax in axes:
        ax.set_xlabel('Maximum DC charge/discharge power (kW)');ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.savefig(out/'06_bess_power_sensitivity.png',dpi=170);plt.close(fig)
