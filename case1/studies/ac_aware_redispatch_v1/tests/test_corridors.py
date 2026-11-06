import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from corridors import grid_points,choose_corridor,q_ratio_at_hour
from fixed_hardware import Hardware


def test_grid_includes_reference_without_exceeding_nameplate():
    pts=grid_points(7.6,3.91,7)
    assert pts[0]==0 and pts[-1]==7.6 and any(abs(x-3.91)<1e-8 for x in pts)
    assert pts==sorted(set(pts))


def test_multiple_feasible_islands_pick_near_reference():
    data=[(0,True),(1,True),(2,False),(3,False),(4,True),(5,True)]
    band=choose_corridor(data,4.1)
    assert (band.p_min_kw,band.p_max_kw)==(4,5)


def test_no_fake_feasible_if_all_fail():
    assert choose_corridor([(0,False),(1,False),(3,False)],1) is None


def test_no_extrapolation_for_single_feasible_point():
    band=choose_corridor([(0,False),(1,True),(2,False)],1)
    assert band.p_min_kw == band.p_max_kw == 1


def test_bad_samples_rejected():
    with pytest.raises(ValueError):choose_corridor([(1,True),(1,False)],1)
    with pytest.raises(ValueError):grid_points(5.,-1.,7)
    with pytest.raises(ValueError):grid_points(5.,2.,3)


def test_night_q_is_off_even_if_battery_discharge_is_possible():
    assert q_ratio_at_hour(0.,.25,False)==0.
    assert q_ratio_at_hour(0.,.25,True)==.25
    assert q_ratio_at_hour(2.,.25,False)==.25


def test_extract_exact_reference_hardware():
    m={'settings':{'transformer_kva':5,'loading_pu':.9,'load_pf':.98,'export_policy':'zero'},
       'summary':{'panels_equivalent':41,'battery_modules_equivalent':8,
                  'battery_power_dc_kw':12,'inverter_ac_kva_assumed_unity_pf':12,
                  'unserved_kwh':0,'annual_equipment_usd':3515.,'annual_total_usd':4767.}}
    x=Hardware.from_manifest(m)
    assert (x.panels,x.battery_modules,x.battery_power_dc_kw,x.inverter_kva)==(41,8,12,12)
