from pathlib import Path
import zipfile, shutil
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, FixedLocator
from PIL import Image,ImageOps,ImageDraw,ImageFont

zp=Path('/mnt/data/geographic_sensitivity_results.zip')
out=Path('/mnt/data/SEEDExchange_Geographic_Sensitivity_Review_2026-11-01')
fig=out/'figures';data=out/'data';fig.mkdir(parents=True,exist_ok=True);data.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(zp) as z:
    s=pd.read_csv(z.open('ac_scenario_summary.csv'))
    h=pd.read_csv(z.open('ac_hourly_or_critical.csv'))
    geo=pd.read_csv(z.open('candidate_territory_summary.csv'))
    manifest=z.read('validation_manifest.json')
(data/'validation_manifest.json').write_bytes(manifest)
s['strict_screen_pass']=(s.hours_below_097.eq(0)&s.hours_above_103.eq(0)&s.hours_trafo_over_100.eq(0)&s.hours_line_over_100.eq(0))
s['wide_screen_pass']=(s.hours_below_095.eq(0)&s.hours_above_105.eq(0)&s.hours_trafo_over_100.eq(0)&s.hours_line_over_100.eq(0))
s.to_csv(data/'scenario_summary_reviewed.csv',index=False)
geo.to_csv(data/'candidate_territory_summary.csv',index=False)
base=s[(s.allocation=='equal') & (s.pf==.98)&(s.route_factor==1.3)].copy()
base.to_csv(data/'reference_comparison.csv',index=False)
stress=s[(s.allocation=='far_end_heavy') & (s.pf==.9)&(s.route_factor==1.3)].copy()
stress.to_csv(data/'stress_comparison.csv',index=False)
# Route length data for figure 3
p=geo[geo.transformer.astype(str).isin(['94022','106039'])].copy()
p['trafo']=p['transformer'].astype(int)
# reference plotting
plt.rcParams.update({'font.size':11,'axes.titlesize':14,'axes.labelsize':12,'figure.dpi':125,'savefig.dpi':220})
POSITIONS=['head','middle','end']; LABELS=['Trafo LV head','Midpoint','Feeder end']; offsets={'mst':-.10,'star':.10}
# separate plots per trafo? Combined plot two transformers with shape + route color, but only 12 points and 6 x categories. Most legible 1 image 2 lines of subgroups? use scatter x siting and trafo separated x groups.

def placement_plot(col, filename, ylabel, ylim, bounds, title):
    f,ax=plt.subplots(figsize=(11.3,5.7))
    for trafo,group_shift,marker in [(94022,0,'o'),(106039,4,'D')]:
      for route,c in [('mst','C0'),('star','C1')]:
        sub=base[(base.trafo==trafo)&(base.routing==route)]
        x=[group_shift+POSITIONS.index(v)+offsets[route] for v in sub.siting]
        ax.scatter(x,sub[col],marker=marker,s=115,c=c,edgecolor='white',linewidth=.9,zorder=4,label=(f'{route.upper()}  |  {trafo}' if False else None))
        for ix,val in zip(x,sub[col]):
            ax.annotate(f'{val:.3f}' if 'voltage' in col else f'{val:.1f}',(ix,val),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
    for val,label,ls in bounds:
        ax.axhline(val,linestyle=ls,color='gray',alpha=.6,lw=1)
        ax.text(6.95,val,label,fontsize=9,ha='right',va='bottom',color='dimgray')
    ax.axvline(3.0,color='0.8',lw=1)
    ax.set_xticks([0,1,2,4,5,6],LABELS+LABELS)
    ax.set_xlim(-.55,6.65);ax.set_ylim(*ylim)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.text(1.0,ylim[0]+.015*(ylim[1]-ylim[0]),'94022: 10 houses',ha='center',fontsize=11,weight='bold')
    ax.text(5.0,ylim[0]+.015*(ylim[1]-ylim[0]),'106039: 12 houses',ha='center',fontsize=11,weight='bold')
    from matplotlib.lines import Line2D
    handles=[Line2D([0],[0],marker='o',linestyle='none',markerfacecolor='C0',markeredgecolor='white',markersize=10,label='MST feeder'),Line2D([0],[0],marker='o',linestyle='none',markerfacecolor='C1',markeredgecolor='white',markersize=10,label='Star feeder'),Line2D([0],[0],marker='o',linestyle='none',color='0.4',markersize=9,label='94022'),Line2D([0],[0],marker='D',linestyle='none',color='0.4',markersize=9,label='106039')]
    ax.legend(handles=handles,loc='best',ncol=2,fontsize=9,frameon=False)
    ax.grid(axis='y',alpha=.18)
    f.tight_layout()
    f.savefig(fig/(filename+'.png'))
    f.savefig(fig/(filename+'.svg'))
    plt.close(f)

placement_plot('min_voltage_pu','01_min_voltage_by_inverter_position','Minimum LV voltage (pu)',(.91,1.01),[(.97,'0.97 screening limit','--'),(.95,'0.95 reference','--')],'Minimum voltage: siting versus feeder routing')
placement_plot('max_voltage_pu','02_max_voltage_by_inverter_position','Maximum LV voltage (pu)',(.985,1.108),[(1.03,'1.03 screening limit','--'),(1.05,'1.05 reference','--')],'Maximum voltage: remote PV/BESS injection')

# Longest path and minimum voltage, midpoint PF0.98 equal
mer=s[(s.allocation=='equal') & (s.pf==.98) & (s.siting=='middle')].merge(
  p[['trafo','route','detour','longest_candidate_path_m','total_candidate_lv_m']],left_on=['trafo','routing','route_factor'],right_on=['trafo','route','detour'],how='left',validate='one_to_one')
f,ax=plt.subplots(figsize=(9.7,6))
for trafo,mark in [(94022,'o'),(106039,'D')]:
 for route,c in [('mst','C0'),('star','C1')]:
    d=mer[(mer.trafo==trafo)&(mer.routing==route)]
    ax.scatter(d.longest_candidate_path_m,d.min_voltage_pu,marker=mark,s=120,c=c,edgecolor='white',linewidth=.8,label=f'{trafo} | {route.upper()}')
    for _,r in d.iterrows():
       ax.annotate(f'{r.route_factor:g}×',(r.longest_candidate_path_m,r.min_voltage_pu),xytext=(6,3),textcoords='offset points',fontsize=8)
ax.axhline(.97,color='gray',lw=1,linestyle='--',alpha=.8)
ax.axhline(.95,color='gray',lw=1,linestyle=':',alpha=.7)
ax.set_xlabel('Longest assumed transformer-to-house path (m)')
ax.set_ylabel('Minimum LV voltage (pu)')
ax.set_title('Feeder-path length versus voltage: midpoint inverter')
ax.grid(alpha=.15)
ax.legend(loc='lower left',ncol=2,fontsize=9,frameon=False)
f.tight_layout(); f.savefig(fig/'03_feeder_path_length_vs_minimum_voltage.png');f.savefig(fig/'03_feeder_path_length_vs_minimum_voltage.svg');plt.close(f)
# Power factor comparison: categorical two PF groups, 1.3, far_end_heavy, midpoint
pfs=s[(s.allocation=='far_end_heavy')&(s.route_factor==1.3)&(s.siting=='middle')]
f,ax=plt.subplots(figsize=(10,5.7))
for trafo,marker in [(94022,'o'),(106039,'D')]:
 for route,c in [('mst','C0'),('star','C1')]:
   d=pfs[(pfs.trafo==trafo)&(pfs.routing==route)].sort_values('pf')
   shift = { (94022,'mst'):-.25,(94022,'star'):-.08,(106039,'mst'):.08,(106039,'star'):.25}[(trafo,route)]
   x=[0 if abs(pf-.9)<1e-6 else 1 for pf in d.pf]
   x=[xx+shift for xx in x]
   ax.scatter(x,d.max_trafo_pct,marker=marker,s=135,color=c,edgecolor='white',linewidth=.7,label=f'{trafo} | {route.upper()}')
   for xx,val in zip(x,d.max_trafo_pct): ax.annotate(f'{val:.1f}%',(xx,val),xytext=(0,8),textcoords='offset points',fontsize=8,ha='center')
ax.axhline(100,color='gray',linestyle='--',lw=1.2,label='100% nameplate')
ax.set_xticks([0,1],['PF 0.90','PF 0.98'])
ax.set_xlim(-.55,1.55);ax.set_ylim(87,116)
ax.set_ylabel('Maximum transformer loading (%)')
ax.set_title('Reactive demand drives transformer overload')
ax.grid(axis='y',alpha=.17)
ax.legend(loc='upper right',ncol=2,fontsize=9,frameon=False)
f.tight_layout(); f.savefig(fig/'04_transformer_loading_vs_power_factor.png');f.savefig(fig/'04_transformer_loading_vs_power_factor.svg');plt.close(f)
# lengths
f,ax=plt.subplots(figsize=(9.4,5.8))
d=p[p.detour.eq(1.3)].copy()
xs={('94022','mst'):0,('94022','star'):1,('106039','mst'):3,('106039','star'):4}
for _,r in d.iterrows():
  x=xs[(str(r.transformer),r.route)]; ax.bar(x,r.total_candidate_lv_m/1000,width=.57,color=('C0' if r.route=='mst' else 'C1'),alpha=.85)
  ax.text(x,r.total_candidate_lv_m/1000+.06,f'{r.total_candidate_lv_m/1000:.2f} km',ha='center',fontsize=10)
ax.set_xticks([0,1,3,4],['MST','Star','MST','Star']);ax.set_ylim(0,4.5)
ax.set_ylabel('Total assumed LV conductor route length (km)')
ax.set_title('Trade-off: star feeder needs longer total cable routes')
ax.text(.5,.1,'94022',ha='center',transform=ax.get_xaxis_transform(),fontsize=12,weight='bold')
ax.text(3.5,.1,'106039',ha='center',transform=ax.get_xaxis_transform(),fontsize=12,weight='bold')
ax.axvline(2,color='gray',alpha=.2,lw=1)
ax.grid(axis='y',alpha=.17); f.tight_layout();f.savefig(fig/'05_assumed_lv_route_length.png');f.savefig(fig/'05_assumed_lv_route_length.svg');plt.close(f)

# review files
strict_ct=s.groupby(['trafo','routing','pf','allocation']).strict_screen_pass.agg(['sum','count']).reset_index()
strict_ct.to_csv(data/'screening_pass_counts.csv',index=False)
round3=lambda x:round(x,3)
md='''# El Arenal | Geographic AC sensitivity review

**Scope:** 144 conditional pandapower scenarios, 40 selected hours each (5,760 converged AC calculations). Transformer 94022 serves 10 candidate houses; transformer 106039 serves 12 candidate houses. These are model allocations, not verified meter connections.

## Screening results

- All 144 scenarios converged for their selected 40 hours. Convergence is not proof of engineering compliance.
- 12/144 scenarios passed the joint project screen: all tested house voltages in 0.97–1.03 pu and peak transformer/line loading no greater than 100%.
- 47/144 scenarios passed the wider 0.95–1.05 pu screen with no transformer/line overloading.
- All 12 strict-screen passes occur in star-feeder configurations with assumed PF 0.98. The MST hypotheses have no strict passes across the 72 MST cases; none of the 72 PF 0.90 cases pass.
- Across all scenarios, the worst calculated voltage is 0.8437 pu and the greatest maximum voltage is 1.1121 pu. They occur in different scenarios and should not be combined as one network condition.
- The highest transformer loading is 112.2%. No modelled LV conductor exceeds its synthetic 0.15 kA limit (highest loading about 18.3%).

## Controlled comparison (PF 0.98, equal allocation, 1.3 route factor)

| Transformer | Feeder | Inverter | Min V (pu) | Max V (pu) | Peak transformer (%) | Strict screen |
| --- | --- | --- | ---: | ---: | ---: | --- |
'''
for _,r in base.sort_values(['trafo','routing','siting']).iterrows():
 md+=f"| {r.trafo} | {r.routing.upper()} | {r.siting} | {r.min_voltage_pu:.4f} | {r.max_voltage_pu:.4f} | {r.max_trafo_pct:.1f} | {'Pass' if r.strict_screen_pass else 'Fail'} |\n"
md+='''
## Main interpretation

1. **Routing dominates some voltage outcomes.** At midpoint inverter placement, PF 0.98, equal load distribution and factor 1.3, the minimum voltage for 94022 is 0.9409 pu (MST) versus 0.9725 pu (star). For 106039 it is 0.9334 (MST) versus 0.9743 (star). These comparisons reflect *alternative hypothetical radial topologies*, not a choice that has already been surveyed or built.
2. **End-of-feeder injection risks overvoltage.** Under the same reference case, maxima for the far-end inverter are 1.0477 (MST) and 1.0594 (star) for 94022; 1.0921 (MST) and 1.0512 (star) for 106039. No far-end-siting scenario satisfies the strict full screen over all tested hours.
3. **Lower power factor matters.** None of the 72 PF 0.90 scenarios meets all joint strict criteria. At the 1.3 factor with far-end-heavy allocation and a midpoint inverter, 106039 transformer peak loading is 109.5% (MST) and 104.1% (star), despite voltage improvements in the star design.
4. **Star routings use more installed conductor length in the hypotheses.** At multiplier 1.3, 94022 has 2.00 km MST versus 3.77 km star; 106039 has 1.64 km MST versus 2.82 km star. This additional line cost has not been included in the PyPSA economic optimum; therefore a passing star layout should not be called economically preferable without reinforcement costing.
5. **Shorter feeder paths help voltage.** As the assumed detour factor increases from 1.0 to 1.6, the modeled MST midpoint minimum voltage for 106039 falls from 0.9442 to 0.9223 pu in the PF 0.98/equal case.

## Important limitations and next decision

- Only 40 critical hours per scenario were evaluated; do not interpret the counts as full-year violation hours or annual loss figures.
- The routing is MST or star with geometric detour factors of 1.0/1.3/1.6, not verified cable geography. The terminal voltage findings are sensitive to this distinction.
- The electrical model uses a balanced three-phase equivalent of a 240 V single-phase feeder, fixed loop resistance/reactance assumptions, an ideal upstream MV source, and unverified conductor ratings and transformer impedance. Phase/neutral effects, real conductor layout and actual voltage regulator settings remain outside scope.
- The inverter is a combined PV+BESS AC injector at unity power factor using fixed prior PyPSA active-power dispatch. The model does not AC-optimize inverter reactive support or resolve PV/BESS sizes after line losses and voltage constraints.
- Association alternatives H01/H02, H10 and H29 were not swept in this run. Transformer-to-house assignments remain provisional.
- **Recommended next work:** targeted annual AC simulation for a small matched subset of contrasting MST and star cases, followed by an explicitly costed and AC-feasible redesign. Prioritize obtaining conductor and route evidence before selecting star as an engineering solution. Then proceed to resilience/adaptability on accepted configurations.

## Figures

- `01_min_voltage_by_inverter_position`: reference minimum voltage, two transformer groups, both routing hypotheses.
- `02_max_voltage_by_inverter_position`: remote inverter voltage rise.
- `03_feeder_path_length_vs_minimum_voltage`: longest assumed electrical path versus worst voltage for midpoint inverter, three distance factors.
- `04_transformer_loading_vs_power_factor`: reactive demand impacts under far-end-heavy loading.
- `05_assumed_lv_route_length`: cost-relevant total routed length comparison.

All optimization and electrical comparisons are conditional simulations. They do not verify the EPM as-built supply network or utility permissible voltage range.
'''
(out/'TECHNICAL_REVIEW.md').write_text(md,encoding='utf-8')
# simple poster 2x2 assembly from four independent plots with no additional text
panels=['01_min_voltage_by_inverter_position.png','02_max_voltage_by_inverter_position.png','03_feeder_path_length_vs_minimum_voltage.png','04_transformer_loading_vs_power_factor.png']
imgs=[]
for pn in panels:
 im=Image.open(fig/pn).convert('RGB');im.thumbnail((1120,720))
 tile=Image.new('RGB',(1140,730),'white');tile.paste(im,((1140-im.width)//2,(730-im.height)//2));imgs.append(tile)
canvas=Image.new('RGB',(2280,1460),'white')
for i,im in enumerate(imgs):canvas.paste(im,((i%2)*1140,(i//2)*730))
canvas.save(fig/'00_four_panel_poster_summary.png',quality=95)
# original review zip includes data and plots and script
shutil.copy2(__file__,out/'reproduce_figures.py')
archive=Path('/mnt/data/SEEDExchange_Geographic_Sensitivity_Review_2026-11-01.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for pth in out.rglob('*'):
  if pth.is_file():z.write(pth,pth.relative_to(out.parent))
print('output',archive, archive.stat().st_size,'figures',len(list(fig.glob('*'))))
