#!/usr/bin/env python3
"""Publication-ready labels for archived parameter_sweep.csv, not PyPSA optima."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
x=pd.read_csv(root/'reference/previous_parameter_sweep.csv')
figs=root/'figures';figs.mkdir(parents=True,exist_ok=True)
# Compare leading DISTINCT configurations, dropping duplicates with identical economics
names={'seven':'7 houses','eight_H01':'8, +H01','eight_H02':'8, +H02','nine':'9 houses','twelve_assumed5kva':'12 houses, hypothetic 5kVA'}
fig,axs=plt.subplots(2,1,figsize=(14,10),constrained_layout=True)
for j,case in enumerate(['seven','nine']):
 d=x[(x.case==case)&(x.status=='ENERGY_SCREEN_ONLY')].copy()
 d=d.sort_values('annual_cost_usd').drop_duplicates(subset=['panels','battery_modules','battery_power_kw','inverter_kva'])
 # lowest cost 8, and highest SS 4, unique
 low=d.head(8)
 high=d.sort_values('annual_self_sufficiency_pct',ascending=False).head(4)
 d=pd.concat([low,high]).drop_duplicates(subset=['panels','battery_modules','battery_power_kw','inverter_kva']).sort_values('annual_cost_usd')
 labels=[f'{int(r.panels)}P | {int(r.battery_modules)}B | {r.battery_power_kw:g}kW | {r.inverter_kva:g}kVA' for _,r in d.iterrows()]
 bar=axs[j].barh(np.arange(len(d)),d.annual_cost_usd)
 axs[j].set_yticks(np.arange(len(d)),labels,fontsize=9)
 axs[j].invert_yaxis();axs[j].set_xlabel('Annualized total cost incl. grid purchases / assumed export credit (USD/year)')
 axs[j].set_title(f'{names[case]} | current 290-row sweep, energy-screened only, NO AC validation')
 for yy,(_,r) in enumerate(d.iterrows()):
  axs[j].text(r.annual_cost_usd+12,yy,f' SS {r.annual_self_sufficiency_pct:.1f}% | grid {r.grid_import_kwh:.0f} kWh',va='center',fontsize=8)
 axs[j].set_xlim(0,max(d.annual_cost_usd)*1.45);axs[j].grid(axis='x',alpha=.2)
fig.suptitle('Explicit alternatives: P = 435 W PV panels; B = 4.325 kWh usable modules; kW = battery power',fontsize=13)
for ext in ['png','svg']:fig.savefig(figs/f'01_labeled_equipment_cost_comparison.{ext}',dpi=190)
plt.close(fig)
# Heatmap best screened SS by panel count & battery modules (over battery-power and inverter variants)
fig,axs=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
for ax,case in zip(axs,['seven','nine']):
 d=x[(x.case==case)&(x.status=='ENERGY_SCREEN_ONLY')]
 panels=sorted(x.panels.unique()); batts=sorted(x.battery_modules.unique())
 grid=np.full((len(batts),len(panels)),np.nan)
 for _,r in d.iterrows():
  iy=batts.index(r.battery_modules);ix=panels.index(r.panels)
  grid[iy,ix]=max(grid[iy,ix],r.annual_self_sufficiency_pct) if not np.isnan(grid[iy,ix]) else r.annual_self_sufficiency_pct
 m=ax.imshow(grid,vmin=0,vmax=100,aspect='auto',cmap='YlGnBu')
 ax.set_xticks(range(len(panels)),[f'{p*0.435:.2f}' for p in panels]);ax.set_yticks(range(len(batts)),[f'{b*4.325:.1f}' for b in batts])
 ax.set_xlabel('PV nameplate (kWp)');ax.set_ylabel('Battery usable energy (kWh)')
 ax.set_title(f'{names[case]}: maximum self-sufficiency\namong screened inverter/power variants')
 for yy in range(len(batts)):
  for xx in range(len(panels)):
   val=grid[yy,xx]
   ax.text(xx,yy,'No pass' if np.isnan(val) else f'{val:.1f}%',ha='center',va='center',fontsize=9,color='white' if not np.isnan(val) and val>65 else 'black')
fig.colorbar(m,ax=axs,shrink=.8,label='Operational self-sufficiency (%)')
for ext in ['png','svg']:fig.savefig(figs/f'02_pv_bess_heatmap_7_vs_9.{ext}',dpi=190)
plt.close(fig)
# Feasibility count, emphasizes hypothetical 12 case
cats=['seven','eight_H01','eight_H02','nine','twelve_assumed5kva']
agg=(x.groupby(['case','status']).size().unstack(fill_value=0).reindex(cats))
fig,ax=plt.subplots(figsize=(11,5),constrained_layout=True)
bottom=np.zeros(len(cats))
for k,col in [('ENERGY_SCREEN_ONLY','#448e70'),('UNSERVED_OR_SOC_UNCLOSED','#dbab49'),('HARDWARE_REJECTED','#ba6565')]:
 vals=agg.get(k,pd.Series(0,index=cats)).to_numpy()
 bars=ax.bar(range(len(cats)),vals,bottom=bottom,label=k.replace('_',' ').title(),color=col)
 for rect,v,b in zip(bars,vals,bottom):
  if v:ax.text(rect.get_x()+rect.get_width()/2,b+v/2,str(v),ha='center',va='center',fontsize=9)
 bottom+=vals
ax.set_xticks(range(len(cats)),[names[z] for z in cats],rotation=10)
ax.set_ylabel('Number of attempted configurations');ax.set_title('Energy-only screen, not transformer/feeder AC validated')
ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.14))
for ext in ('png','svg'):fig.savefig(figs/f'03_5_case_screening_counts.{ext}',dpi=190)
plt.close(fig)
print('Saved clearer source-sweep figures to',figs)
