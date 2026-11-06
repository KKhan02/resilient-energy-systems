"""Pure-data regression tests, no pandapower or PyPSA solver required."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_12house_robustness import chosen_indices, classify_records


def baseline_fixture():
    ac=pd.DataFrame({'hour_index':np.arange(8760),
        'min_v_pu':np.full(8760,.98), 'max_v_pu':np.full(8760,1.),
        'max_trafo_pct':np.full(8760,20.),'max_line_pct':np.full(8760,2.)})
    ac.loc[100,'min_v_pu']=.958
    ac.loc[200,'max_trafo_pct']=96.
    hourly=pd.DataFrame({'timestamp_lst':pd.date_range('2025-01-01',periods=8760,freq='h'),
        'demand_kw':np.full(8760,2.),'inverter_ac_kw':np.zeros(8760),
        'grid_import_kw':np.full(8760,2.)})
    return ac,hourly


def test_selection_keeps_known_weak_and_thermal_peaks():
    ac,hourly=baseline_fixture()
    selected=chosen_indices(ac,hourly,.965,5)
    assert 100 in selected and 200 in selected and 0 in selected and 8759 in selected
    assert sorted(selected)==selected


def test_selection_does_not_accept_partial_year():
    ac,hourly=baseline_fixture()
    with pytest.raises(ValueError):chosen_indices(ac.head(10),hourly)


def test_strict_label_independent_from_engineering_pass():
    rows=pd.DataFrame([dict(status='CONVERGED',min_v_pu=.956,max_v_pu=1.01,
         max_trafo_pct=94.,max_line_pct=10.)])
    result=classify_records(rows,.95,1.05)
    assert result['failure_hours']==0 and result['below_097_count']==1
    assert result['below_095_count']==0


def test_thermal_failure_cannot_be_relabelled_as_voltage_pass():
    rows=pd.DataFrame([dict(status='CONVERGED',min_v_pu=.98,max_v_pu=1.01,
         max_trafo_pct=101.,max_line_pct=10.)])
    result=classify_records(rows,.95,1.05)
    assert result['failure_hours']==1


def test_unconverged_never_passes():
    rows=pd.DataFrame([dict(status='AC_FAILURE',min_v_pu=np.nan,max_v_pu=np.nan,
         max_trafo_pct=np.nan,max_line_pct=np.nan)])
    result=classify_records(rows)
    assert result['feasible_hours']==0


def test_invalid_limits_rejected():
    rows=pd.DataFrame([dict(status='CONVERGED',min_v_pu=.97,max_v_pu=1.,
         max_trafo_pct=1.,max_line_pct=1.)])
    with pytest.raises(ValueError):classify_records(rows,1.01,1.05)
