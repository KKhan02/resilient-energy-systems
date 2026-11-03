#!/usr/bin/env python3
"""Canonical energy-only PV/BESS sensitivity grid, no AC hosting-capacity claims."""
from __future__ import annotations
import argparse
import itertools
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from run_integrated_dispatch import locate_repo, dispatch_case, source_data

CASES = (
    ('seven','931076',()),
    ('eight_H01','931076',('H01',)),
    ('eight_H02','931076',('H02',)),
    ('nine','931076',('H01','H02')),
    ('twelve_assumed5kva','923494',()),
)


def sweep(root, outdir, panels=(0,12,24,32), modules=(0,4,8),
          inverters=(5.,10.,12.), cap_pu=.9, pf=.98, cyclic=True):
    out=Path(outdir)
    out.mkdir(parents=True,exist_ok=True)
    raw,nasa=source_data(root)
    records=[]
    for label,node,added in CASES:
        for pp,mm,inv in itertools.product(panels,modules,inverters):
            if pp==0 and mm==0 and inv != inverters[0]:
                continue  # One no-DER counterfactual, not artificial inverter variants.
            for batt_power in ((0.,) if mm==0 else (5.,10.)):
                try:
                    _,meta=dispatch_case(root,territory=node,include=added,panels=pp,modules=mm,
                        battery_power_kw=batt_power,inverter_kva=inv,cap_pu=cap_pu,pf=pf,
                        soc_mode=('cyclic' if cyclic else 'fixed'),source_override=(raw,nasa))
                except ValueError as exc:
                    # Explicitly record rejected hardware cases instead of silently dropping them.
                    records.append(dict(case=label,epm_node=node,houses=len(meta['houses']) if False else 7+len(added) if node=='931076' else 12,
                        panels=pp,pv_kwp=pp*.435,battery_modules=mm,battery_kwh=mm*4.325,
                        battery_power_kw=batt_power,inverter_kva=inv,status='HARDWARE_REJECTED',reason=str(exc)))
                    continue
                s=meta['annual_score'];qa=meta['qa'];b=meta['battery_soc_boundary']
                status='ENERGY_SCREEN_ONLY' if qa['ens_kwh']<=1e-3 and b['soc_boundary_closed'] else 'UNSERVED_OR_SOC_UNCLOSED'
                records.append(dict(case=label,epm_node=node,houses=meta['house_count'],
                    panels=pp,pv_kwp=meta['pv_kwp'],battery_modules=mm,
                    battery_kwh=meta['battery_usable_kwh'],battery_power_kw=batt_power,inverter_kva=inv,
                    status=status,reason='',demand_kwh=s['demand_kwh'],
                    grid_import_kwh=s['grid_import_kwh'],grid_export_kwh=s['grid_export_kwh'],
                    unserved_kwh=s['grid_ens_kwh'],
                    annual_self_sufficiency_pct=s['one_minus_import_fraction_of_demand_pct'],
                    locally_supplied_fraction_of_demand_pct=s['locally_supplied_fraction_of_demand_pct'],
                    annual_cost_usd=s['annual_total_no_credit_usd'],
                    capex_usd=s['capex_ex_vat_usd'],
                    peak_pcc_kva=s['max_trafo_kva'],
                    peak_grid_import_kw=qa['peak_grid_import_kw'],
                    initial_terminal_soc_drift_kwh=b['soc_boundary_drift_kwh']))
    df=pd.DataFrame(records)
    df.to_csv(out/'parameter_sweep.csv',index=False,float_format='%.7f')
    plotted=df[(df.status=='ENERGY_SCREEN_ONLY')].copy()
    if not plotted.empty:
        fig,ax=plt.subplots(figsize=(10,6))
        for key,g in plotted.groupby('case'):
            ax.scatter(g.annual_cost_usd,g.annual_self_sufficiency_pct,s=12,alpha=.58,label=key)
        ax.set(xlabel='Annualized equipment and grid purchases, illustrative USD/year',
               ylabel='1 - imported energy / requested demand (%)',
               title='Canonical dispatch sensitivity: energy-screened only (NOT feeder-validated)')
        ax.legend(fontsize=8)
        fig.savefig(out/'cost_vs_self_sufficiency.png',dpi=180,bbox_inches='tight')
        fig.savefig(out/'cost_vs_self_sufficiency.svg',bbox_inches='tight')
        plt.close(fig)
        for key,g in plotted.groupby('case'):
            # Fix battery power and inverter for apples-to-apples heatmap.
            view=g[(g.battery_power_kw==5)&(g.inverter_kva==10)]
            if view.empty:continue
            table=view.groupby(['battery_kwh','pv_kwp']).annual_self_sufficiency_pct.max().unstack()
            fig,ax=plt.subplots(figsize=(8,5))
            img=ax.imshow(table.values,origin='lower',cmap='viridis',vmin=0,vmax=100,aspect='auto')
            ax.set_xticks(range(len(table.columns)),[f'{x:g}' for x in table.columns]);ax.set_yticks(range(len(table.index)),[f'{x:g}' for x in table.index]);
            ax.set(xlabel='PV (kWp)',ylabel='BESS usable (kWh)',title=f'{key}: annual self-sufficiency, screened only')
            fig.colorbar(img,ax=ax,label='%')
            fig.savefig(out/f'{key}_pv_bess_heatmap.png',dpi=180,bbox_inches='tight')
            fig.savefig(out/f'{key}_pv_bess_heatmap.svg',bbox_inches='tight')
            plt.close(fig)
    status_counts={str(k):int(v) for k,v in df.status.value_counts().items()}
    (out/'SWEEP_README.md').write_text(
        '# Canonical energy-only hardware sensitivity\n\n'
        f'Status counts: {status_counts}\n\n'
        '- Energy-screened means zero unserved load, bounded PCC apparent power, and closed annual SOC.\n'
        '- PCC apparent power is controlled INSIDE dispatch; this is not independent feeder validation.\n'
        '- No LV bus voltage, neutral imbalance, line thermal loading, customer mapping or real cable lengths have been validated.\n'
        '- 12-house node 923494 uses a HYPOTHETICAL 5 kVA transformer assumption, not a verified nameplate.\n'
        '- These costs exclude LV reconnection, installation-specific materials, protection, metering, permits and site works.\n'
        '- No full multi-objective joint network optimization has been claimed.\n',encoding='utf-8')
    return df

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--cap-pu',type=float,default=.9)
    p.add_argument('--pf',type=float,default=.98)
    a=p.parse_args()
    d=sweep(locate_repo(a.repo_root),a.outdir,cap_pu=a.cap_pu,pf=a.pf)
    print(json.dumps({'rows':len(d),'status_counts':d.status.value_counts().to_dict()},indent=2))
