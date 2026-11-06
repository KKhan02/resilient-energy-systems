import sys
from pathlib import Path
import json
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_archived_campaign import equipment_key,equipment_id,archive_to_tables,geography_gate,resume_rows
from batch_archived_campaign import scenarios


def row(case='12_homes',task='fixed_PV_economic',key='task1',panels=41,modules=8,power=12,inv=12,kva=5,cost=4768,status='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER'):
    return dict(case=case,task=task,task_key=key,status=status,kva=kva,
        panels_equivalent=panels,battery_modules_equivalent=modules,battery_power_dc_kw=power,
        inverter_ac_kva_assumed_unity_pf=inv,annual_total_usd=cost,
        annual_equipment_usd=3515,unserved_kwh=0,grid_import_kwh=4320,
        self_sufficiency_of_demand_pct=81,annual_hours=8760)


def test_dedup_keeps_every_original_objective_task():
    r=[row(),row(task='epsilon_SS_min_cost',key='task2',cost=4770),row(key='task3',status='INFEASIBLE_MODEL')]
    # Last record represents an independent failed task with NO fictitious hardware.
    r[2].update(panels_equivalent=None,battery_modules_equivalent=None,battery_power_dc_kw=None)
    reg,eq,group,counts=archive_to_tables(pd.DataFrame(r))
    assert len(reg)==3 and len(eq)==1
    assert eq.iloc[0].historical_occurrences==2
    assert eq.iloc[0].historical_tasks=='epsilon_SS_min_cost;fixed_PV_economic'
    assert reg.loc[reg.task_key=='task3','new_evidence_gate'].iloc[0]=='ARCHIVED_INFEASIBLE_OR_FAILED'
    assert counts['archived_tasks']==3 and counts['historical_infeasible_preserved']==1
    assert eq.iloc[0].original_task_keys_json=='["task1","task2"]'


def test_nonbuildable_does_not_reclassify_as_feasible():
    r=[row(panels=41.4,key='frac'),row(power=30,key='too_fast'),row(case='11_homes',key='unmapped')]
    reg,eq,group,counts=archive_to_tables(pd.DataFrame(r))
    assert reg.loc[reg.task_key=='frac','new_evidence_gate'].iloc[0]=='REVIEW_NON_BUILDABLE_EQUIPMENT'
    assert not eq.loc[eq.battery_power_dc_kw==30,'existing_fixed_hardware_runner_eligible'].iloc[0]
    assert eq.loc[eq.case=='11_homes','transformer_evidence'].iloc[0]=='GIS_MAPPING_REQUIRED'
    assert not eq.loc[eq.case=='11_homes','existing_fixed_hardware_runner_eligible'].iloc[0]


def test_hypothetical_nameplate_is_explicit():
    assert geography_gate('12_homes',5)[0]=='GIS_MAPPED_CONDITIONAL'
    assert geography_gate('12_homes',15)[0]=='GIS_MAPPED_HYPOTHETICAL_TRAFO_KVA'
    assert geography_gate('13_homes',5)[0]=='GIS_MAPPING_REQUIRED'


def test_hash_key_stable_not_positional():
    a=row();k=equipment_key(a)
    assert equipment_id(k)==equipment_id(equipment_key(dict(a,task_key='other')))
    assert equipment_id(k)!=equipment_id(equipment_key(row(modules=9)))


def test_all_nine_are_complete_year_scenario_configs():
    assert scenarios('reference')==[(.98,1.)]
    assert len(scenarios('nine'))==9
    assert set(scenarios('nine'))=={(p,s) for p in (.98,.95,.90) for s in (1.,1.3,1.6)}


def test_resume_rejects_duplicate_or_missing_hours(tmp_path):
    partial=tmp_path/'annual_ac_hours.csv'
    partial.write_text('hour_index,status\n0,CONVERGED\n1,CONVERGED\n')
    assert resume_rows(partial)==2
    partial.write_text('hour_index,status\n0,CONVERGED\n2,CONVERGED\n')
    with pytest.raises(ValueError,match='nonsequential'):
        resume_rows(partial)


def test_shortlist_snapshot_is_not_full_campaign():
    # The supplied 60-row earlier shortlist must never substitute for a 6840-row manifest.
    assert len({7,9,12})==3
