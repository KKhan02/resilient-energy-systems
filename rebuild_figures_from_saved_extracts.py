from pathlib import Path
import csv, io, json, zipfile, shutil, textwrap
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

OUT=Path(__file__).resolve().parent
STUDIES=OUT/'case1'/'studies'
DATA=OUT/'figure_source_extracts'
DATA.mkdir(parents=True,exist_ok=True)

HOUSE='''id,lat,lon,node,confidence
H01,6.24804546,-75.01088043,,unassigned
H02,6.246173400381,-75.008867333599,,unassigned
H03,6.245735736555,-75.008929643061,931076,probable
H04,6.24492436,-75.00788908,823002,probable
H05,6.24465703,-75.00878304,823002,probable
H06,6.24439032,-75.00971482,931076,probable
H07,6.242856437002,-75.009141986911,823002,probable
H08,6.238544617605,-75.009655882121,241054,possible
H09,6.236739165648,-75.004828762118,900607,possible
H10,6.24169997,-75.0071865,923494|823002,alternative
H11,6.24052442,-75.00403598,923494,possible
H12,6.23828888,-75.00236866,900607,user_definite
H13,6.24041525,-75.0022014,923494,possible
H14,6.240455067323,-74.998742892459,900607,unverifiable
H15,6.24101857,-75.00094582,900607,unverifiable
H16,6.241922531926,-75.002348108136,923494,possible
H17,6.242581054624,-75.004740611835,923494,user_definite
H18,6.2425261,-75.00321339,923494,possible
H19,6.24332425,-75.00515218,923494,possible
H20,6.24325928,-75.00438192,923494,possible
H21,6.243647471521,-75.003318716614,923494,possible
H22,6.244478426223,-75.004079151297,923494,possible
H23,6.243846203288,-75.004723642594,923494,possible
H24,6.24401183,-75.00569515,923494,possible
H25,6.24462939,-75.00523511,923494,possible
H26,6.246362494594,-75.007592448472,931076,possible
H27,6.24766959349,-75.008160816772,931076,probable
H28,6.247490631568,-75.007544224612,931076,possible
H29,6.247587268263,-75.004239123928,931076|923848,alternative
H30,6.246940516261,-75.001083793867,923848,user_definite
H31,6.246872630058,-74.998470712963,923848,possible
H32,6.246946197186,-74.998008326345,923848,possible
H33,6.246301879262,-74.996313925393,923848,possible
H34,6.24862349,-75.00633035,931076,possible
H35,6.2485127,-75.00428209,931076,possible
'''
BASE='''homes,trafo_pct,vmin,voltage_pass,trafo_pass
1,17.657105,0.989774,true,true
2,28.177742,0.983234,true,true
3,40.023215,0.980361,true,true
4,50.966061,0.973599,true,true
5,59.086491,0.971361,true,true
6,70.346546,0.965488,false,true
7,87.329503,0.958962,false,true
8,98.681710,0.951985,false,true
9,104.055847,0.952983,false,false
10,116.978935,0.945063,false,false
11,124.229840,0.943093,false,false
12,136.964066,0.936742,false,false
13,149.908196,0.932594,false,false
14,161.562868,0.924194,false,false
15,170.884939,0.922522,false,false
16,176.494719,0.919108,false,false
17,188.639333,0.915397,false,false
18,200.441678,0.908234,false,false
19,211.351255,0.905348,false,false
20,225.589393,0.896729,false,false
'''
AC='''mode,architecture,pv_kwp,battery_power_kw,policy,min_v,max_v,trafo_pct,pass
storage,central,0,0,none,0.967372,0.974603,86.608655,false
storage,central,0,2,none,0.975011,0.982185,53.061475,true
storage,central,0,4,none,0.981399,0.988526,38.827179,true
storage,shared_two_sites,0,0,none,0.967372,0.974603,86.608655,false
storage,shared_two_sites,0,2,none,0.978396,0.990654,52.95977,true
storage,shared_two_sites,0,4,none,0.98462,1.00975,38.914154,true
pv,central,2.61,0,unrestricted,0.997076,0.998564,22.486548,true
pv,central,5.22,0,unrestricted,1.004823,1.0063,61.698401,true
pv,central,10.44,0,unrestricted,1.006949,1.008423,73.493101,true
pv,shared_two_sites,2.61,0,unrestricted,0.997212,1.013612,22.227415,true
pv,shared_two_sites,5.22,0,unrestricted,1.004661,1.036931,59.970999,false
pv,shared_two_sites,10.44,0,unrestricted,1.006672,1.043257,71.184855,false
pv,central,2.61,0,gross_load_capped,0.994022,0.995515,15.528693,true
pv,central,5.22,0,gross_load_capped,0.994022,0.995515,15.528693,true
pv,central,10.44,0,gross_load_capped,0.994022,0.995515,15.528693,true
pv,shared_two_sites,2.61,0,gross_load_capped,0.994219,1.004295,15.548945,true
pv,shared_two_sites,5.22,0,gross_load_capped,0.994219,1.004295,15.548945,true
pv,shared_two_sites,10.44,0,gross_load_capped,0.994219,1.004295,15.548945,true
'''
SWEEP='''pv_panels,battery_modules,layout,cost_annual_usd,self_sufficiency_pct,peak_import_kw,grid_import_kwh
0,0,C,3852.94,0,3.717,13286.0
0,4,C,5551.6,0.063,3.717,13277.569
0,4,K,5625.27,0.063,3.717,13277.569
0,8,C,6205.35,0.127,3.717,13269.138
0,8,K,6279.02,0.127,3.717,13269.138
12,0,C,4006.55,34.456,3.717,8708.215
12,0,K,4080.22,34.456,3.717,8708.215
12,4,C,4262.48,44.844,3.717,7327.998
12,4,K,4337.05,44.821,3.717,7331.098
12,8,C,4916.24,44.908,3.717,7319.567
12,8,K,4990.81,44.884,3.717,7322.667
24,0,C,4197.6,40.82,3.717,7862.677
24,0,K,4271.27,40.82,3.717,7862.677
24,4,C,3379.53,79.462,3.307,2728.696
24,4,K,3488.79,78.463,2.920,2861.400
24,8,C,3841.28,84.13,3.307,2108.459
24,8,K,3953.02,83.142,2.920,2239.745
32,0,C,4424.13,42.489,3.717,7640.906
32,0,K,4497.8,42.489,3.717,7640.906
32,4,C,3401.35,86.944,2.920,1734.637
32,4,K,3512.75,85.891,2.920,1874.480
32,8,C,3635.34,97.024,2.831,395.445
32,8,K,3784.46,95.066,2.054,655.593
'''
TERRITORY='''node,number,households,archived_kva,portal_kw
923494,106039,12,,5
931076,94022,7,5,
923848,92395,4,5,5
900607,85398,4,,5
823002,113699,3,,3
241054,98380,1,,3
'''
for name,content in [('households_excerpt.csv',HOUSE),('v5_baseline_excerpt.csv',BASE),('ac_rectilinear_excerpt.csv',AC),('annual_7house_excerpt.csv',SWEEP),('territory_register_excerpt.csv',TERRITORY)]:
 (DATA/name).write_text(content, encoding='utf-8')

house=pd.read_csv(io.StringIO(HOUSE),dtype={'node':'string'})
base=pd.read_csv(io.StringIO(BASE))
ac=pd.read_csv(io.StringIO(AC))
sweep=pd.read_csv(io.StringIO(SWEEP))
ter=pd.read_csv(io.StringIO(TERRITORY),dtype={'node':'string'})

styles={
 'geo':'community_georef/field_review_2026_10_27/figures',
 'reference':'reference_v5_baseline/figures',
 'ac':'conditional_94022_pv_bess/figures',
 'annual':'annual_shared_pvbess/figures'
}
for folder in styles.values(): (STUDIES/folder).mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'figure.figsize':(10,6.2), 'font.size':10, 'axes.titlesize':14, 'axes.labelsize':11,'savefig.dpi':170})

def emit(fig,sub,name):
 fig.tight_layout(pad=1.7)
 folder=STUDIES/styles[sub]
 for ext in ['png','svg']:
  fig.savefig(folder/f'{name}.{ext}',bbox_inches='tight',dpi=190)
 plt.close(fig)

def new(title, subtitle):
 fig,ax=plt.subplots()
 ax.set_title(title,loc='left',weight='bold',pad=30)
 ax.text(0,1.022,subtitle,transform=ax.transAxes,fontsize=9,alpha=.75)
 ax.grid(alpha=.22,axis='y')
 ax.set_axisbelow(True)
 return fig,ax

# 01 map: point locations grouped by candidate transformer node, not literal physical line routes
fig,ax=new('El Arenal: provisional transformer territories','35 numbered properties | 31 uniquely nominated, 4 unresolved | not surveyed electrical connections')
groups=[('923494','106039, 12 candidates'),('931076','94022, 7 candidates'),('923848','92395, 4 candidates'),('900607','85398, 4 candidates'),('823002','113699, 3 candidates'),('241054','98380, 1 candidate')]
for node,label in groups:
 d=house[house.node==node]
 ax.scatter(d.lon,d.lat,s=76,label=label,edgecolor='black',lw=.5,alpha=.9)
for _,r in house.iterrows():
 ax.annotate(r.id,(r.lon,r.lat),xytext=(4,4),textcoords='offset points',fontsize=7.5)
unres=house[(house.node.isna())|(house.node.str.contains('|',regex=False,na=False))]
ax.scatter(unres.lon,unres.lat,marker='x',s=75,label='Unassigned / alternative',c='black')
ax.scatter([-75.006208238],[6.246949759],marker='*',s=210,label='94022 asset: archived position',edgecolor='black')
ax.scatter([-75.011914005],[6.249940251],marker='P',s=145,label='Northern 25 kVA: supplied candidate',edgecolor='black')
ax.set(xlabel='Longitude (degrees east; negative values are west)',ylabel='Latitude (° N)')
ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(1.015,1),frameon=False)
ax.grid(alpha=.2)
ax.text(.01,-.17,'No LV conductors or service connections plotted; transformer coordinates unknown except the two marked assets.',transform=ax.transAxes,fontsize=8)
emit(fig,'geo','01_provisional_household_transformer_map')

# 02 register: count, not actual verified customers
fig,ax=new('Candidate households per existing transformer','Provisional EPM viewer interpretation, not utility-verified service records')
t=ter.iloc[::-1].copy()
bars=ax.barh(t['number'].astype(str)+' / '+t['node'].astype(str),t['households'])
for bar,(idx,r) in zip(bars,t.iterrows()):
 rating=(f"{r.archived_kva:g} kVA archived" if pd.notna(r.archived_kva) else f"{r.portal_kw:g} kW portal (not kVA)")
 ax.text(bar.get_width()+.18,bar.get_y()+bar.get_height()/2,f"{int(r.households)} houses | {rating}",va='center',fontsize=9)
ax.set_xlim(0,20)
ax.set(xlabel='Number of uniquely nominated properties',ylabel='Transformer no. / electrical node')
ax.text(.0,-.16,'H01, H02, H10, H29 excluded; assignments and most transformer coordinates still unverified.',transform=ax.transAxes,fontsize=8)
emit(fig,'geo','02_existing_territory_association_counts')


# 02b: matrix of evidence associations, emphatically not physical wire map
fig,ax=plt.subplots(figsize=(14.3,5.8))
ax.set_title('Candidate transformer-to-property association register',loc='left',weight='bold',pad=32)
ax.text(0,1.028,'Evidence matrix, NOT an electrical single-line diagram or confirmed LV connections',transform=ax.transAxes,fontsize=10,alpha=.75)
node_order=['931076','923494','923848','900607','823002','241054']
ylabels=['94022 / 931076 (5 kVA archived)','106039 / 923494 (portal 5 kW)','92395 / 923848 (5 kVA archived)','85398 / 900607 (portal 5 kW)','113699 / 823002 (portal 3 kW)','98380 / 241054 (portal 3 kW)']
shapes={'user_definite':'s','probable':'o','possible':'.','unverifiable':'o','alternative':'D'}
for _,r in house.iterrows():
 x=int(r.id[1:]); nodes=[] if pd.isna(r.node) else r.node.split('|')
 if not nodes:
  ax.scatter([x],[-1],marker='x',s=82,c='black',zorder=3)
 for node in nodes:
  yi=node_order.index(node)
  if r.confidence=='unverifiable':
   ax.scatter([x],[yi],marker='o',s=66,facecolors='none',edgecolors='black',linewidths=1.5,zorder=3)
  else:
   ax.scatter([x],[yi],marker=shapes.get(r.confidence,'o'),s=100 if r.confidence=='user_definite' else 60,c=('C1' if r.confidence=='user_definite' else 'C2' if r.confidence=='alternative' else 'C0'),alpha=.92,zorder=3)
ax.set_yticks([-1,0,1,2,3,4,5],['Unassigned (H01, H02)']+ylabels)
ax.set_xticks(np.arange(1,36),[f'H{i:02d}' for i in range(1,36)],rotation=90,fontsize=7)
ax.set_xlim(.3,35.7);ax.set_ylim(5.65,-1.65)
ax.set(xlabel='Original numbered properties (35 positions, not confirmed households)',ylabel='Candidate EPM transformer asset / electrical node')
ax.grid(axis='x',alpha=.17)
from matplotlib.lines import Line2D
handles=[Line2D([0],[0],marker='s',linestyle='None',label='User-described definite (not meter-confirmed)',markerfacecolor='C1',markersize=9),Line2D([0],[0],marker='o',linestyle='None',label='Probable / possible',markerfacecolor='C0',markersize=8),Line2D([0],[0],marker='o',linestyle='None',label='Unverifiable',markerfacecolor='none',markeredgecolor='black',markersize=8),Line2D([0],[0],marker='D',linestyle='None',label='Alternative transformer candidates',markerfacecolor='C2',markersize=8),Line2D([0],[0],marker='x',linestyle='None',label='Unassigned',markersize=8)]
ax.legend(handles=handles,ncol=3,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.18),frameon=False)
emit(fig,'geo','02b_household_to_transformer_evidence_matrix')


# 03 transformer limit reference only
fig,ax=new('Archived v5 reference: transformer loading','Representative 5 kVA feeder; synthetic peak-hour loads, NOT actual EPM hosting capacity')
ax.plot(base.homes,base.trafo_pct,'o-',label='Transformer loading')
ax.axhline(100,ls='--',label='100% nameplate screen')
ax.axvline(9,ls=':',label='First over 100% at 9 houses')
ax.set(xlabel='Households modelled',ylabel='Transformer loading (%)',xlim=(1,20))
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.legend(fontsize=9)
emit(fig,'reference','03_v5_transformer_loading_vs_households')

# 04 voltage reference
fig,ax=new('Archived v5 reference: LV voltage limit','Representative LV feeder; each household count evaluated at its synthetic peak snapshot')
ax.plot(base.homes,base.vmin,'o-',label='Minimum LV voltage')
ax.axhline(.97,ls='--',label='0.97 pu study screen')
ax.axvline(6,ls=':',label='First below 0.97 pu at 6 houses')
ax.set(xlabel='Households modelled',ylabel='Minimum LV voltage (pu)',xlim=(1,20))
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.legend(fontsize=9)
emit(fig,'reference','04_v5_min_lv_voltage_vs_households')

# 05 snapshot PV voltages
fig,ax=new('Transformer 94022: midday PV voltage rise','Seven candidate properties | rectilinear assumed drops | distinct PV-only AC snapshots')
for a,label in [('central','At transformer LV bus'),('shared_two_sites','Two existing-house injection sites')]:
 for policy,sty in [('unrestricted','-'),('gross_load_capped','--')]:
  q=ac[(ac['mode']=='pv')&(ac.architecture==a)&(ac.policy==policy)].sort_values('pv_kwp')
  ax.plot(q.pv_kwp,q.max_v,marker='o',linestyle=sty,label=f'{label}, {policy.replace("_"," ")}')
ax.axhline(1.03,ls=':',label='1.03 pu study upper screen')
ax.set(xlabel='Installed PV capacity (kWp DC)',ylabel='Maximum LV voltage (pu)',ylim=(.99,1.052))
ax.legend(fontsize=8)
emit(fig,'ac','05_94022_pv_voltage_rise_snapshot')

# 06 battery voltage support
fig,ax=new('Transformer 94022: battery injection and voltage','Seven candidates | rectilinear assumed drops | evening snapshots, conditional charged battery')
for a,label in [('central','Central injection'),('shared_two_sites','Two shared injection sites')]:
 q=ac[(ac['mode']=='storage')&(ac.architecture==a)].sort_values('battery_power_kw')
 ax.plot(q.battery_power_kw,q.min_v,marker='o',label=label)
ax.axhline(.97,ls='--',label='0.97 pu lower screen')
ax.set(xlabel='Instantaneous battery discharge (kW)',ylabel='Minimum LV voltage (pu)')
ax.legend(fontsize=9)
emit(fig,'ac','06_94022_evening_battery_voltage_snapshot')

# 07 annual sweep SS contours from original selected verified rows
fig,ax=new('Seven-house annual sweep: self-sufficiency','2025 NASA-based hourly screen | central shared system, no export, selected 5 kW battery power')
q=sweep[sweep.layout=='C'].copy()
q['pv_kwp']=q.pv_panels*.435
for mods in [0,4,8]:
 d=q[q.battery_modules==mods].sort_values('pv_kwp')
 ax.plot(d.pv_kwp,d.self_sufficiency_pct,marker='o',label=f'{mods} battery modules')
ax.set(xlabel='PV capacity (kWp DC)',ylabel='Operational self-sufficiency (%)',ylim=(0,102))
ax.legend(fontsize=9)
emit(fig,'annual','07_7house_annual_pv_bess_sweep_self_sufficiency')

# 08 annual cost screen same slice
fig,ax=new('Seven-house annual sweep: indicative annualized cost','Central shared system, zero export | historical hardware and illustrative BOS, not full lifecycle costing')
for mods in [0,4,8]:
 d=q[q.battery_modules==mods].sort_values('pv_kwp')
 ax.plot(d.pv_kwp,d.cost_annual_usd,marker='o',label=f'{mods} battery modules')
ax.set(xlabel='PV capacity (kWp DC)',ylabel='Illustrative annualized cost (USD/year)')
ax.legend(fontsize=9)
emit(fig,'annual','08_7house_annual_pv_bess_sweep_annualized_cost')

# 09 avoid claiming community optima; compare illustrative saved cases
fig,ax=new('Seven-house case: annual energy imports','Matched total PV and storage | 24 panels, 4 batteries, 5 kW battery power, no export')
labels=['No DER','One shared site','Two shared sites']
vals=[13286,2728.696,2861.4]
bars=ax.bar(labels,vals)
for bar,v in zip(bars,vals): ax.text(bar.get_x()+bar.get_width()/2,v+140,f'{v:,.0f} kWh',ha='center')
ax.set(ylabel='Grid imports (kWh/year)',ylim=(0,15000))
emit(fig,'annual','09_7house_grid_import_comparison')


# 10 / 11: identical named equipment cases, two separate candidate transformer territories
fig,ax=new('Same PV+BESS equipment, different household counts','Central 10.44 kWp + 17.3 kWh usable BESS, 5 kW battery power, 10 kW inverter, no export')
name=['7 candidates\n94022','12 candidates\n106039']
values=[79.462,51.152]
bars=ax.bar(name,values)
for bar,v in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,v+1.4,f'{v:.1f}%',ha='center')
ax.set(ylabel='Simulated operational self-sufficiency (%)',ylim=(0,100))
emit(fig,'annual','10_7_vs_12house_matched_capacity_self_sufficiency')
fig,ax=new('Same PV+BESS equipment: peak import screening','7-house and 12-house provisional territories | annual energy screen, not AC transformer validation')
values=[3.307,5.373]
bars=ax.bar(name,values)
for bar,v in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,v+.12,f'{v:.3f} kW',ha='center')
ax.set(ylabel='Peak simulated grid import (kW)',ylim=(0,6.5))
emit(fig,'annual','11_7_vs_12house_matched_capacity_peak_import')

readme='''# El Arenal / San Rafael: evidence-based figure pack (27 October 2026)\n\nThese figures were generated **locally** from values read from the current GitLab `main` repository at commit `1fdf097a`. No GitLab commits or pipelines were triggered. The simplified CSV extracts included under `figure_source_extracts/` reproduce the selected plotted values; the complete authoritative CSVs remain in GitLab.\n\n## Included figures\n\n| Figure prefix | Repository destination | Meaning |\n|---|---|---|\n| 01, 02, 02b | `case1/studies/community_georef/field_review_2026_10_27/figures/` | Provisional house locations and transformer assignment counts |\n| 03, 04 | `case1/studies/reference_v5_baseline/figures/` | Archived representative feeder transformer and voltage screens |\n| 05, 06 | `case1/studies/conditional_94022_pv_bess/figures/` | Actual AC snapshot PV and BESS placement sensitivities |\n| 07, 08, 09, 10, 11 | `case1/studies/annual_shared_pvbess/figures/` | Saved 8760h energy screening results, not PyPSA optimization |\n\n## Evidence limitations\n\n1. **Do not present dotted/colored candidate associations as existing wires.** Only transformer 94022 and a separate northern 25 kVA candidate have supplied coordinates. The other transformer poles are unlocated. The 35 properties are not verified service meters.\n2. Transformer 106039 / node 923494 has 12 *provisionally nominated* properties and a portal value of **5 kW**, not a verified 5 kVA nameplate.\n3. The archived v5 household limits belong to a representative synthetic feeder, not to a verified EPM asset.\n4. The seven-property AC plots use separate PV-only and storage-only rectilinear snapshot assumptions, not combined annual power flow.\n5. The annual plots use the **myopic 8760h sizing screen**. They are not an optimal capacity expansion result, not network-compliant designs, and their cost results omit installation-specific cables, protection, utility works and various lifecycle expenses.\n6. C / K architecture comparison is from the historical study and does not establish preferred neighborhood grouping. The corrected next-phase priority is existing transformer + all current candidate customers, then PV/BESS feasibility, then additional hosting capacity and physical cross-transformer reassignment screening.\n\n## How to use\n\nExtract the archive into the **root of your local GitLab checkout**, preserving `case1/studies/.../figures/` paths. The images are static drafts for group/professor review and can be used in presentations with the above disclaimers. Keep the existing modelling scripts and outputs intact. Do not stage the standalone convenience folder `figure_source_extracts/` if you prefer to rely on the original source CSVs in the repo.\n\nFigure 10 and 11 juxtapose matched equipment assumptions for 7 versus 12 candidate properties; source profiles, true electrical connectivity, and 106039 nameplate remain unverified.\n\nNo optimization or new simulations were carried out to make these plots. Recreate plots from the authoritative complete CSVs for each future run, including a timestamp and scenario metadata.\n'''
(OUT/'README_FIGURE_PACKAGE.md').write_text(readme)
# central index of newly created outputs
listing=[]
for p in sorted(STUDIES.rglob('*.png')):
 listing.append(str(p.relative_to(OUT)))
(OUT/'figure_index.txt').write_text('\n'.join(listing)+'\n')
print(f'Rebuilt {len(listing)} PNG and matching SVG figures from saved source extracts.')
