"""Classify exact-PV-count cost minima and plot clearly identified equipment alternatives.

A nondominated fixed-panel minimum-cost point is a *candidate*. The full
multiobjective Pareto frontier additionally needs epsilon-constraint runs across
self-sufficiency or investment budgets, as already supported by run.py frontier.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd


def summarize_sweep(rows:pd.DataFrame)->pd.DataFrame:
    r=rows.copy().reset_index(drop=True)
    r['nondominated_among_min_cost_at_fixed_pv']=False
    needed=['annual_total_usd','self_sufficiency_of_demand_pct']
    for k in needed:
        if k not in r:r[k]=np.nan
        r[k]=pd.to_numeric(r[k],errors='coerce')
    valid=r.index[(r.get('status',pd.Series(['']*len(r))).astype(str).str.startswith('OPTIMAL'))
                  & np.isfinite(r['annual_total_usd'])
                  & np.isfinite(r['self_sufficiency_of_demand_pct'])]
    for i in valid:
        c=float(r.at[i,'annual_total_usd']); ss=float(r.at[i,'self_sufficiency_of_demand_pct'])
        other=r.loc[valid].drop(index=i)
        dominating=(other['annual_total_usd']<=c+1.e-7)&(other['self_sufficiency_of_demand_pct']>=ss-1.e-7)&(
            (other['annual_total_usd']<c-1.e-7)|(other['self_sufficiency_of_demand_pct']>ss+1.e-7))
        r.at[i,'nondominated_among_min_cost_at_fixed_pv']=not dominating.any()
    return r


def plot_sweep(df:pd.DataFrame, stem:Path, case:str, assumed_kva:float):
    """Plot only results from the same territory, kVA, objective and export policy."""
    import matplotlib.pyplot as plt
    stem=Path(stem);stem.parent.mkdir(parents=True,exist_ok=True)
    q=df[df['status'].astype(str).str.startswith('OPTIMAL')].copy()
    if q.empty:
        return
    # full_study.py records the exact fixed panel count in the task field
    # 'panels'. The older standalone panel sweep uses 'panel_count_fixed'.
    # Normalize both formats here so either runner can generate its plots.
    if 'panel_count_fixed' not in q.columns:
        if 'panels' not in q.columns:
            raise ValueError('Fixed-PV plot requires panels or panel_count_fixed')
        q['panel_count_fixed'] = q['panels']
    for k in ['panel_count_fixed','pv_kwp','annual_total_usd','grid_import_kwh',
              'self_sufficiency_of_demand_pct','battery_usable_kwh',
              'inverter_ac_kva_assumed_unity_pf']:
        q[k] = pd.to_numeric(q[k],errors='coerce')
    # Some checkpoints contain failed tasks or partial/incomplete rows.
    # Plot only complete solved points and keep the raw CSV unchanged.
    q = q.dropna(subset=['panel_count_fixed','annual_total_usd',
                         'self_sufficiency_of_demand_pct'])
    if q.empty:
        return
    q = q.sort_values('panel_count_fixed')
    fig,ax=plt.subplots(figsize=(10,6))
    ax.scatter(q.self_sufficiency_of_demand_pct,q.annual_total_usd,c=q.panel_count_fixed,
               cmap='viridis',s=32,alpha=.55,zorder=2)
    nd=q[q.nondominated_among_min_cost_at_fixed_pv.astype(bool)].sort_values('self_sufficiency_of_demand_pct')
    ax.plot(nd.self_sufficiency_of_demand_pct,nd.annual_total_usd,linewidth=1.8,
            marker='o',markersize=5,label='Nondominated among fixed-PV economic optima',zorder=4)
    # Label useful representative points instead of cluttering all 65.
    if len(q):
        idxs=set([q.index[0],q.index[-1],q.annual_total_usd.idxmin(),q.self_sufficiency_of_demand_pct.idxmax()])
        for j in [8,16,24,32,40,48,56,64]:
            sub=q[q.panel_count_fixed==j]
            if not sub.empty:idxs.add(sub.index[0])
        for i in idxs:
            v=q.loc[i]
            ax.annotate(f"{int(v.panel_count_fixed)}P / {v.battery_usable_kwh:.1f} kWh / {v.inverter_ac_kva_assumed_unity_pf:g} kVA",
                        (v.self_sufficiency_of_demand_pct,v.annual_total_usd),
                        xytext=(4,6),textcoords='offset points',fontsize=7)
    ax.set(xlabel='Operational self-sufficiency (% of annual demand)',
           ylabel='Annualized total cost incl. grid purchases (USD/year)',
           title=f'{case}: exact PV-count sweep ({int(q.panel_count_fixed.min())}–{int(q.panel_count_fixed.max())}), assumed transformer {assumed_kva:g} kVA')
    ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best');fig.tight_layout()
    fig.savefig(str(stem)+'_cost_self_sufficiency.png',dpi=170)
    fig.savefig(str(stem)+'_cost_self_sufficiency.svg');plt.close(fig)
    fig,axs=plt.subplots(3,1,figsize=(10,9),sharex=True)
    x=q.panel_count_fixed
    axs[0].plot(x,q.self_sufficiency_of_demand_pct,marker='.',label='Self-sufficiency');axs[0].set_ylabel('Self-sufficiency (%)')
    axs[1].plot(x,q.annual_total_usd,marker='.');axs[1].set_ylabel('Annualized total (USD/y)')
    axs[2].plot(x,q.battery_usable_kwh,marker='.',label='BESS usable kWh')
    axs[2].plot(x,q.inverter_ac_kva_assumed_unity_pf,marker='.',label='Inverter kVA')
    axs[2].set_ylabel('Optimized equipment size');axs[2].legend(fontsize=8)
    axs[2].set_xlabel('Installed PV panel count (435 W per panel)')
    for ax in axs:ax.grid(alpha=.2)
    fig.suptitle(f'{case}: fixed PV count, optimized battery/inverter/dispatch, assumed {assumed_kva:g} kVA')
    fig.tight_layout()
    fig.savefig(str(stem)+'_pv_sizing_curve.png',dpi=170)
    fig.savefig(str(stem)+'_pv_sizing_curve.svg');plt.close(fig)
