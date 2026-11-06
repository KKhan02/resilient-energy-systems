"""No numerical simulation required: protect validation gates and shortlist semantics."""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from run_robustness import critical_hour_indices,summarize_variation,verify_reference_evidence
from shortlist_equipment import dominated_frontier,eligible_rows,choose_shortlist
from validate_annual_ac import sha256


def test_critical_all_weak_hours_retained():
    ac=pd.DataFrame({'min_v_pu':np.ones(8760)*.99,
                     'max_v_pu':np.ones(8760)*1.00,
                     'max_trafo_pct':np.ones(8760)*20,
                     'max_line_pct':np.ones(8760)*10,
                     'ac_feasible':np.ones(8760,dtype=bool),
                     'hour_index':np.arange(8760)})
    ac.loc[123,'min_v_pu']=.9701;ac.loc[2500,'min_v_pu']=.9740
    ac.loc[5500,'max_line_pct']=99.
    h=pd.DataFrame({'timestamp_lst':pd.date_range('2025-01-01',periods=8760,freq='h'),
                    'demand_kw':np.ones(8760),
                    'inverter_ac_kw':np.ones(8760),
                    'grid_import_kw':np.ones(8760)})
    ix=critical_hour_indices(ac,h,.975,10)
    assert 123 in ix and 2500 in ix and 5500 in ix
    assert 0 in ix and 8759 in ix
    assert ix==sorted(set(ix))


def test_sensitivity_summary_never_claims_annual_pass_from_critical():
    g=pd.DataFrame([{'status':'CONVERGED','ac_feasible':True,'min_v_pu':.971,
                     'max_v_pu':1.01,'max_trafo_pct':50.,'max_line_pct':30.}])
    d=summarize_variation(g,1,'critical')
    assert d['conclusion']=='CRITICAL_SAMPLE_PASS_ONLY'
    d2=summarize_variation(g,8760,'full')
    assert d2['conclusion']!='CONDITIONAL_FULL_YEAR_PASS'


def test_failure_never_hidden():
    g=pd.DataFrame([{'status':'CONVERGED','ac_feasible':True,'min_v_pu':.971,
                     'max_v_pu':1.01,'max_trafo_pct':50.,'max_line_pct':30.},
                    {'status':'AC_FAILURE','ac_feasible':False,'min_v_pu':None,
                     'max_v_pu':None,'max_trafo_pct':None,'max_line_pct':None}])
    r=summarize_variation(g,2,'critical')
    assert r['converged_hours']==1 and r['violating_or_failed_hours']==1


def test_reference_requires_exact_source_hash(tmp_path):
    f=tmp_path/'new.csv';f.write_text('reference data')
    m={'scenario':'seven','transformer':'94022','nighttime_q_policy':'off'}
    s={'scenario':'seven','transformer':'94022','trajectory':'redispatched',
       'all_8760_evaluated':True,'ac_feasible_full_year':True,
       'source_trajectory_sha256':'bad','nighttime_q':'off'}
    a=pd.DataFrame({'hour_index':np.arange(8760),
                    'status':['CONVERGED']*8760,'ac_feasible':[True]*8760})
    with pytest.raises(ValueError,match='hash'):
        verify_reference_evidence(m,s,a,f,tmp_path/'annual.csv')
    s['source_trajectory_sha256']=sha256(f)
    verify_reference_evidence(m,s,a,f,tmp_path/'annual.csv')
    a.loc[100,'ac_feasible']=False
    with pytest.raises(ValueError,match='conflict'):
        verify_reference_evidence(m,s,a,f,tmp_path/'annual.csv')


def _saved_campaign():
    return pd.DataFrame([
      ('7_homes',5.,'OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER','zero',8760.,0.,3200.,80.,24.,4.,7.,7.6),
      ('7_homes',5.,'OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER','zero',8760.,0.,3500.,87.,32.,5.,8.,10.),
      ('7_homes',5.,'OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER','zero',8760.,0.,3800.,88.,36.,6.,9.,10.),
      ('7_homes',5.,'OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER','zero',8760.,0.,4200.,85.,40.,8.,10.,12.),
      ('7_homes',5.,'INFEASIBLE_MODEL','zero',8760.,0.,1000.,99.,16.,3.,3.,5.)],
      columns=['case','kva','status','export_policy','annual_hours','unserved_kwh',
       'annual_total_usd','self_sufficiency_of_demand_pct','panels_equivalent',
       'battery_modules_equivalent','battery_power_dc_kw','inverter_ac_kva_assumed_unity_pf'])


def test_saved_shortlist_is_only_energy_screened():
    a=eligible_rows(_saved_campaign(),('7_homes',),5.)
    assert len(a)==4
    assert a.validation_status.str.contains('NOT_AC_VALIDATED',regex=False).all()
    f=dominated_frontier(a)
    assert len(f)==3
    b=choose_shortlist(a,10)
    assert not b.empty
    assert b['validation_status'].str.contains('ENERGY_SCREEN_ONLY').all()


def test_fractional_hardware_is_rejected():
    a=_saved_campaign()
    a.loc[0,'panels_equivalent']=24.5
    with pytest.raises(ValueError,match='fractional'):
        eligible_rows(a,('7_homes',),5.)
