#!/usr/bin/env python3
"""Input-only consistency check. This is NOT pandapower AC validation."""
from pathlib import Path
import numpy as np
import pandas as pd
from run_validation import load_dispatch, critical_indices, PCC_ENERGY_LIMIT_KVA
HERE=Path(__file__).resolve().parent
out=HERE/'output_preview';out.mkdir(parents=True,exist_ok=True)
rows=[]
for num in (7,9,12):
    d=load_dispatch(HERE/'input'/'dispatch'/f'{num}_homes_hourly_dispatch.csv')
    ss=100*(1-d.grid_import_kw.sum()/d.demand_kw.sum())
    rows.append({'houses':num,'annual_demand_kwh':d.demand_kw.sum(),
      'annual_grid_import_kwh':d.grid_import_kw.sum(),
      'self_sufficiency_pct':ss,
      'max_gross_household_kw':d.demand_kw.max(),
      'max_inverter_ac_kw':d.inverter_ac_kw.max(),
      'max_scheduled_pcc_kva_proxy':d.pcc_kva_proxy.max(),
      'hours_gross_load_gt_5kw':int((d.demand_kw>5.).sum()),
      'hours_gross_load_gt_4p5kw':int((d.demand_kw>4.5).sum()),
      'hours_schedule_gt_4p5kva':int((d.pcc_kva_proxy>4.5+1e-6).sum()),
      'selected_critical_hours':len(critical_indices(d))})
summary=pd.DataFrame(rows)
summary.to_csv(out/'input_consistency_screen_NOT_AC_VALIDATION.csv',index=False)
print(summary.round(3).to_string(index=False))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axs=plt.subplots(1,3,figsize=(13.2,4.1),sharey=True)
for i,h in enumerate((7,9,12)):
 d=load_dispatch(HERE/'input'/'dispatch'/f'{h}_homes_hourly_dispatch.csv')
 ax=axs[i]
 ax.plot(np.arange(1,8761),np.sort(d.demand_kw.to_numpy())[::-1],label='Gross household demand',lw=1.5)
 ax.plot(np.arange(1,8761),np.sort(d.pcc_kva_proxy.to_numpy())[::-1],label='PyPSA apparent PCC proxy',lw=1.5)
 ax.axhline(5,ls='--',color='grey',lw=.8,label='5 kVA nominal')
 ax.axhline(4.5,ls=':',color='black',lw=.8,label='4.5 kVA dispatch limit')
 ax.set(xlabel='Hours ranked by magnitude',title=f'{h} homes')
 ax.grid(alpha=.15)
axs[0].set_ylabel('kW gross demand or kVA PCC proxy')
handles,labels=axs[-1].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=4,fontsize=8)
fig.tight_layout(rect=[0,0,1,.88]);fig.savefig(out/'energy_dispatch_vs_feeder_gross_load.png',dpi=180)
fig.savefig(out/'energy_dispatch_vs_feeder_gross_load.svg')
plt.close(fig)
