#!/usr/bin/env python3
"""Source-specific decision registers and figure. No solver, no changes to model data."""
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path('/mnt/data')
OUT=ROOT/'SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17'
assert (OUT/'INDEPENDENT_QA.json').exists()
raw=ROOT/'SEEDExchange_StudyA_94022_AllNine_Bundle_v1/CANDIDATE_BRANCH_REGISTER.csv'
d=pd.read_csv(raw)
sel=d[d.option=='svc007_004_gis014_011_016_R050'].copy()
assert len(sel)==5
sel['model_only_reduced_r_ohm_per_km']=sel.original_r_ohm_per_km*0.5
sel['field_connection_confirmed']='NO'
sel['physical_conductor_selected']='NO'
sel['required_site_evidence']=np.where(sel.kind=='ASSUMED_SERVICE','Confirm household service route, length, connection, phase, cable and permissions','Confirm EPM conductor, length, phase, tap point, neutral and electrical parameters')
sel['installed_cost_eur']='NOT_PRICED'
sel['source']='SEEDExchange_StudyA_94022_AllNine_Bundle_v1/CANDIDATE_BRANCH_REGISTER.csv'
sel.to_csv(OUT/'FIVE_MODEL_EDGES_PHYSICAL_VERIFICATION_REGISTER.csv',index=False)
energy=pd.read_csv(ROOT/'SEEDExchange_StudyA_FinalIndependentReview_2026-11-16/ENERGY_22_RECONCILED_COSTS.csv')
curt=pd.read_csv(ROOT/'SEEDExchange_StudyA_Remaining126_Triage_2026-11-16/PV_BESS_CURTAILMENT_SCREENING_44.csv')
curt=curt[curt.dispatch=='optimized'].copy()
energy['case_family']=energy.case.str.removeprefix('energy_')
merged=energy.merge(curt, on='case_family',suffixes=('_energy','_screen'),validate='one_to_one')
assert len(merged)==22
cols=['case_family','scenario_energy','transformer','tier_energy','hardware_family','households','panels','battery_modules_energy','battery_power_dc_kw_energy','inverter_kva_energy','demand_kwh','pv_available_dc_kwh','curtailment_kwh','pv_curtailment_pct','imports_kwh','self_sufficiency_pct','equivalent_battery_cycles','effective_cost_usd']
priority=merged[cols].copy().rename(columns={'scenario_energy':'scenario','tier_energy':'tier','battery_modules_energy':'battery_modules','battery_power_dc_kw_energy':'battery_power_dc_kw','inverter_kva_energy':'inverter_kva','effective_cost_usd':'annualized_equipment_plus_energy_cost_usd'})
priority['priority_reason']='Review curtailment reduction and storage utilization with battery/AC constraints; no resizing run completed'
priority['source_status']='Validated archived energy + curtailment diagnostics; alternative scenarios not additive'
priority=priority.sort_values('curtailment_kwh',ascending=False).reset_index(drop=True)
priority.to_csv(OUT/'PV_BESS_22_DESIGN_UTILIZATION_PRIORITIES.csv',index=False)
p=OUT/'PORTFOLIO_432_ORIGINAL_PLUS_CONDITIONAL_FIVE_EDGE_OVERLAY.csv'
portfolio=pd.read_csv(p)
sub=portfolio[(portfolio.scenario=='A0')&(portfolio.transformer==94022)&(portfolio.hypothetical_five_edge_overlay)].copy()
assert len(sub)==36
summary=sub.groupby(['pf','length_factor']).agg(before_after_sequenced_violations=('adjusted_bad_hours','sum'),after_hypothetical_five_edge_violations=('conditional_five_edge_violation_hours','sum'),annual_cases=('case','size'),minimum_hypothetical_voltage_pu=('conditional_five_edge_min_voltage_pu','min'),max_hypothetical_transformer_loading_pct=('conditional_five_edge_trafo_max_pct','max')).reset_index()
assert int(summary.before_after_sequenced_violations.sum())==126
assert int(summary.after_hypothetical_five_edge_violations.sum())==0
summary.to_csv(OUT/'A0_94022_SEQUENCED_VS_FIVE_EDGE_BY_NINE_FACTORS.csv',index=False)
fig, ax = plt.subplots(figsize=(9.2,4.6),layout='constrained')
# Side-by-side grouped bars keep baseline vs hypothetical transparent.
x=np.arange(len(summary)); width=.4
ax.bar(x-width/2, summary.before_after_sequenced_violations, width, label='Original LV network, after battery redispatch',color='#597a9b')
ax.bar(x+width/2, summary.after_hypothetical_five_edge_violations,width,label='Hypothetical five-edge R × 0.5 network',color='#499b8d')
for i,v in enumerate(summary.before_after_sequenced_violations):ax.text(i-width/2,v+.45,str(int(v)),ha='center',va='bottom',fontsize=9)
for i in range(len(summary)):ax.text(i+width/2,.5,'0',ha='center',va='bottom',fontsize=9,color='#2c6960')
ax.set_xticks(x,[f'PF {r.pf:.2f}\nL×{r.length_factor:.1f}' for r in summary.itertuples()],fontsize=8)
ax.set_ylabel('Annual violation-hours across four A0 94022 schedules')
ax.set_ylim(0,max(summary.before_after_sequenced_violations)*1.19)
ax.grid(axis='y',alpha=.2)
ax.set_axisbelow(True)
ax.spines[['top','right']].set_visible(False)
ax.set_title('A0 94022: annual electrical violations before and after hypothetical network change',fontsize=12)
ax.legend(loc='upper left',fontsize=8.5,frameon=False)
fig.savefig(OUT/'A0_94022_annual_violation_recovery_by_stress.png',dpi=230,bbox_inches='tight')
fig.savefig(OUT/'A0_94022_annual_violation_recovery_by_stress.svg',bbox_inches='tight')
plt.close(fig)
print('five edge length',sel.original_length_m.sum())
print('A1 top candidates:')
print(priority[priority.scenario=='A1'][['case_family','panels','battery_modules','pv_curtailment_pct','curtailment_kwh','imports_kwh','annualized_equipment_plus_energy_cost_usd']].head(8).to_string(index=False))
