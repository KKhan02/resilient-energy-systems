"""Source-only tests; the solve requires user's pinned PyPSA environment."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import Settings
from site_capacity import SolarAreaCase,site_cases
from full_study import house_variants,design_tasks,task_key,main
import pytest


def test_site_fractions_geometric_and_hardware_bounds():
    cases=site_cases()
    assert [c['geometric_panel_bound'] for c in cases]==[73,146,219]
    assert [c['hardware_panel_bound'] for c in cases]==[82,82,82]
    assert [c['model_panel_bound'] for c in cases]==[73,82,82]
    assert round(cases[2]['geometric_pv_kwp'],3)==95.265


def test_invalid_land_or_panel_area():
    with pytest.raises(ValueError):SolarAreaCase(0)
    with pytest.raises(ValueError):SolarAreaCase(.25,1.5)


def test_all_households_and_eight_alternatives():
    cases=house_variants(5,15)
    assert len(cases)==12
    assert [x['case'] for x in cases if x['houses']==8]==['8_homes_H01','8_homes_H02']
    assert len(set(cases[8]['profiles']))==cases[8]['houses']


def test_independent_battery_sweep_and_study_count():
    tasks=list(design_tasks(house_variants(5,15),[5.,10.,15.,20.,25.],82,[73,82,82],16,[.7,.8,.9,.95],[12000.,20000.,30000.]))
    assert len(tasks)==6840
    assert len(set(task_key(t) for t in tasks))==len(tasks)
    pv=[t for t in tasks if t['task']=='fixed_PV_economic' and t['kva']==5 and t['case']=='7_homes']
    assert [x['panels'] for x in pv]==list(range(83))
    battery=[t for t in tasks if t['task']=='fixed_BESS_economic' and t['kva']==5 and t['case']=='7_homes']
    assert [t['battery_modules'] for t in battery]==list(range(17))


def test_fixed_battery_modules_validation():
    assert Settings(max_battery_modules=16,fixed_battery_modules=16).fixed_battery_modules==16
    with pytest.raises(ValueError):Settings(max_battery_modules=16,fixed_battery_modules=17)


def test_preview_does_not_require_repository_or_solver():
    result=main(['--preview'])
    assert result['total_distinct_solver_tasks']==6840
    assert result['solver']=='MILP'
