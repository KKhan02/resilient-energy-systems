"""Pure tests; no PyPSA or pandapower runtime required."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from voltage_band_protocol import reclassify_ac_hours,validate_limits
from run_12house_manufacturer_baseline import verify_source_manifest
from validate_annual_ac_target import validate_manifest_against_hardware
from fixed_hardware import Hardware,physical_soc_floor_usable_kwh
from scenario_membership import CASE_HOUSE_IDS


def sample_data(n=2):
    return pd.DataFrame(dict(status=['CONVERGED']*n,
        min_v_pu=[.96,.968][:n],max_v_pu=[1.,1.01][:n],
        max_trafo_pct=[60.,50.][:n],max_line_pct=[8.,8.][:n]))


def test_reference_bands_not_strict():
    out=reclassify_ac_hours(sample_data())
    assert out.set_index('band').loc['engineering_target','failure_or_unconverged_hours']==0
    assert out.set_index('band').loc['original_strict_research','failure_or_unconverged_hours']==2
    assert not out.full_year_verified.any()


def test_thermal_not_overridden_by_wide_voltage_band():
    df=sample_data();df.loc[0,'max_trafo_pct']=101.
    out=reclassify_ac_hours(df).set_index('band')
    assert out.loc['national_magnitude_reference','failure_or_unconverged_hours']==1


def test_nonconvergence_always_fails():
    df=sample_data();df.loc[1,'status']='AC_FAILURE'
    out=reclassify_ac_hours(df).set_index('band')
    assert out.loc['engineering_target','feasible_hours']==1


def test_strict_year_requires_8760():
    with pytest.raises(ValueError,match='8760'):reclassify_ac_hours(sample_data(),True)


def test_limits_validation():
    assert validate_limits(.95,1.05)==(.95,1.05)
    with pytest.raises(ValueError):validate_limits(.97,.98)


def test_manufacturer_floor_12_houses():
    assert physical_soc_floor_usable_kwh(8,.2)==pytest.approx(1.832)


def sample_manifest():
    return {'settings':{'transformer_kva':5,'loading_pu':.9,'load_pf':.98,'export_policy':'zero'},
        'summary':{'candidate_epm_node':'923494','profile_indices':list(range(1,13)),
        'panels_equivalent':41,'battery_modules_equivalent':8,
        'inverter_ac_kva_assumed_unity_pf':12,'battery_power_dc_kw':12,
        'annual_equipment_usd':3515,'annual_total_usd':4767,'unserved_kwh':0}}


def test_12house_hardware_from_saved_manifest():
    hw=verify_source_manifest(sample_manifest())
    assert (hw.panels,hw.battery_modules,hw.inverter_kva)==(41,8,12)
    assert len(CASE_HOUSE_IDS['twelve'])==12


def test_reject_changed_transformer_and_house_set():
    m=sample_manifest()
    hw=verify_source_manifest(m)
    meta={'scenario':'twelve','transformer':'106039',
        'selected_candidate_houses':list(CASE_HOUSE_IDS['twelve']),
        'nighttime_q_policy':'off', 'assumed_nameplate_kva':5,'hardware':vars(hw)}
    assert validate_manifest_against_hardware(meta,hw)==('twelve','106039')
    meta['selected_candidate_houses'].append('H29')
    with pytest.raises(ValueError,match='membership'):validate_manifest_against_hardware(meta,hw)


def test_reject_wrong_nameplate():
    m=sample_manifest();m['settings']['transformer_kva']=10
    with pytest.raises(ValueError,match='5 kVA'):verify_source_manifest(m)


def test_q_ratio_api_night_disabled_kwarg_matches_validator():
    from corridors import q_ratio_at_hour
    assert q_ratio_at_hour(0.0, 0.25, night_q_allowed=False) == 0.0
    assert q_ratio_at_hour(1.0, 0.25, night_q_allowed=False) == 0.25


def test_annual_validator_q_keyword_regression():
    import ast
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / 'validate_annual_ac_target.py'
    tree = ast.parse(src.read_text(encoding='utf8'))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == 'q_ratio_at_hour']
    assert calls, 'The validator must call q_ratio_at_hour'
    assert all('night_q_allowed' in {k.arg for k in call.keywords} for call in calls)
    assert all('allow_night' not in {k.arg for k in call.keywords} for call in calls)
