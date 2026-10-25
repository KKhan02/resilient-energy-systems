from pathlib import Path
import numpy as np
import pytest
from studies.site_a_solar.solar_access_pvlib import tree_angle,load_weather,poa,run
WEATHER=Path(__file__).resolve().parents[3]/"data"/"NASA_POWER_SanRafael_hourly_2025.csv"

def test_assumed_geometry_is_monotone():
    assert tree_angle(12,5)>tree_angle(12,20)
    assert tree_angle(18,10)>tree_angle(8,10)
    assert tree_angle(1,10)==0
    assert tree_angle(11.5,10)==pytest.approx(45)
    with pytest.raises(ValueError):tree_angle(12,0)

def test_power_weather_and_solar_position():
    d,s=load_weather(WEATHER)
    assert len(d)==len(s)==8760
    assert d.ALLSKY_SFC_SW_DWN.sum()/1000==pytest.approx(1773.01,abs=.01)
    assert s.apparent_elevation.max()>70

def test_direct_screen_is_monotone():
    d,s=load_weather(WEATHER)
    normal,_=poa(d,s,10,180)
    blocked,_=poa(d,s,10,180,25)
    east,_=poa(d,s,10,180,25,"east")
    assert blocked.sum()<normal.sum()
    assert np.all(blocked<=normal+1e-7)
    assert east.sum()>=blocked.sum()-1e-7

def test_run_outputs(tmp_path):
    metadata=run(WEATHER,tmp_path)
    assert metadata["screened_tree_cases"]==54
    assert metadata["observed_tree_heights_m"] is None
    assert metadata["hours_dhi_exceeds_ghi"]==329
    assert (tmp_path/"tree_height_setback_sensitivity.csv").exists()
