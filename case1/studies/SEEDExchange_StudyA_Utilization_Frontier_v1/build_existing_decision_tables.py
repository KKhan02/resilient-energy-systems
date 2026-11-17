#!/usr/bin/env python3
"""Reconcile existing signed 22-case energy and 432 AC evidence without a solver."""
from pathlib import Path
import pandas as pd
import json

HERE=Path(__file__).resolve().parent
IN=HERE/'inputs'

def selected_rows(df,scenario,tier):
    result=[]
    for tid in ('94022','106039','113699','85398','92395'):
        if tid=='92395':
            row=df[(df.scenario=='A0')&(df.transformer==92395)&(df.tier==tier)&(df.hardware_family=='four_house_new')]
        else:
            family='four_house_new' if scenario=='A0' and tid in ('113699','85398') else 'archived_reference'
            row=df[(df.scenario==scenario)&(df.transformer==int(tid))&(df.tier==tier)&(df.hardware_family==family)]
        if len(row)!=1:raise ValueError(f'Expected exactly one {scenario} {tier} {tid} {len(row)}')
        result.append(row.iloc[0])
    return pd.DataFrame(result)

def build():
    df=pd.read_csv(IN/'ENERGY_22_RECONCILED_COSTS.csv')
    agg=pd.read_csv(IN/'FIVE_TERRITORY_STAR_AGGREGATE_COMPARISON_36.csv')
    ac=pd.read_csv(IN/'PORTFOLIO_432_ORIGINAL_PLUS_CONDITIONAL_FIVE_EDGE_OVERLAY.csv')
    gross=[]
    for assignment in ('A0','A1'):
        for tier in ('min_cost','ss90'):
            rows=selected_rows(df,assignment,tier)
            rec={'assignment':assignment,'tier':tier,
                 'households':int(rows.households.sum()),
                 'demand_kwh':float(rows.demand_kwh.sum()),
                 'annual_cost_usd_no_LV_network_capex':float(rows.effective_cost_usd.sum()),
                 'grid_import_kwh_no_network_losses':float(rows.imports_kwh.sum()),
                 'curtailment_dc_kwh':float(rows.curtailment_kwh.sum()),
                 'equipment_capex_usd_no_LV_network_capex':float(rows.capex_usd_ex_vat.sum()),
                 'cases_used':';'.join(rows.case.astype(str))}
            a=agg[(agg.scenario==assignment)&(agg.tier==tier)&(agg.pf==.98)&(agg.length_factor==1.)]
            if len(a)!=1:raise ValueError('Gross/energy AC aggregate mismatch')
            row=a.iloc[0]
            rec['network_losses_kwh_pf098_l10_original_dispatch']=float(row.pvbess_losses_kwh)
            rec['gross_demand_network_losses_kwh_pf098_l10']=float(row.gross_losses_kwh)
            rec['annual_cost_including_illustrative_grid_loss_charge_usd']=rec['annual_cost_usd_no_LV_network_capex']+.29*rec['network_losses_kwh_pf098_l10_original_dispatch']
            gross.append(rec)
    summary=pd.DataFrame(gross)
    if set(summary.households)!={34} or max(abs(summary.demand_kwh-64532.))>1e-4:
        raise ValueError('Comparisons not equal 34-home annual load')
    summary.to_csv(HERE/'A0_A1_EQUAL_POPULATION_ENERGY_COST_SCREEN.csv',index=False,float_format='%.8f')
    # Original source full-year AC (pre AC-aware correction) makes valid comparison
    # ONLY for original network and original dispatch. No price on 5-edge research retrofit.
    b=ac[(ac.transformer==92395)&(ac.scenario=='A0')].copy()
    groups=[]
    for (top,tier,dispatch),t in b.groupby(['topology','tier','dispatch']):
        groups.append(dict(topology=top,tier=tier,dispatch=dispatch,annual_cases=len(t),
                           failing_cases=int((t.adjusted_bad_hours>0).sum()),
                           summed_violation_hours=int(t.adjusted_bad_hours.sum()),
                           min_v_pu=float(t.minimum_voltage_pu.min()),
                           mean_annual_loss_kwh_across_sensitivities=float(t.annual_network_losses_kwh.mean()),
                           investment_network_capex='NOT_QUOTED',
                           factual_status='PROPOSED_GEOMETRY_NOT_VERIFIED_EPM_LV_CONNECTIONS'))
    btab=pd.DataFrame(groups).sort_values(['topology','tier','dispatch'])
    assert len(btab)==8 and btab.annual_cases.sum()==72
    btab.to_csv(HERE/'STUDYB_92395_EXISTING_ANNUAL_SCREEN.csv',index=False,float_format='%.8f')
    qa={'equal_population_4_scenarios':True,'studyb_cases':int(btab.annual_cases.sum()),
        'mst_failures':int(btab[btab.topology=='mst'].failing_cases.sum()),
        'star_failures':int(btab[btab.topology=='star'].failing_cases.sum()),
        'loss_cost_proxy_USD_per_kWh':.29,'note':'No physical retrofits or price quotes available'}
    assert qa['mst_failures']==24 and qa['star_failures']==0
    (HERE/'DECISION_TABLE_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    return summary,btab

if __name__=='__main__':
    summary,btab=build()
    print(summary[['assignment','tier','annual_cost_usd_no_LV_network_capex','grid_import_kwh_no_network_losses','network_losses_kwh_pf098_l10_original_dispatch']].to_string(index=False))
    print(btab[['topology','tier','dispatch','failing_cases']].to_string(index=False))
