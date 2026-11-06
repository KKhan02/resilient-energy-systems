"""Test annual failure extraction without running pandapower or the PyPSA solver."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_annual_feedback import extract_bad_hours


def ref():
    dates=pd.date_range('2025-01-01',periods=8760,freq='h')
    return pd.DataFrame({'timestamp_lst':dates,'demand_kw':np.ones(8760)*2.,
                         'inverter_ac_kw':np.zeros(8760)})


def ac(r):
    return pd.DataFrame({'hour_index':np.arange(8760),
        'timestamp':r.timestamp_lst.copy(), 'status':['CONVERGED']*8760,
        'ac_feasible':[True]*8760,'p_inverter_kw':np.zeros(8760),
        'load_kw':np.ones(8760)*2})


def test_exact_bad_hours():
    r=ref();a=ac(r)
    bad=[7940,7964,7965,7987]
    a.loc[bad,'ac_feasible']=False
    assert extract_bad_hours(a,r).hour_index.tolist()==bad


def test_bad_alignment_fails():
    r=ref();a=ac(r)
    a.loc[120,'timestamp']=pd.Timestamp('2025-01-06 02:00')
    with pytest.raises(ValueError,match='timestamps'):
        extract_bad_hours(a,r)


def test_modified_p_fails():
    r=ref();a=ac(r)
    a.loc[7940,'p_inverter_kw']=.75
    with pytest.raises(ValueError,match='p_inverter_kw'):
        extract_bad_hours(a,r)


def test_incomplete_year_fails():
    r=ref();a=ac(r).iloc[:8759]
    with pytest.raises(ValueError,match='8,760'):
        extract_bad_hours(a,r)


def test_failure_from_convergence_status():
    r=ref();a=ac(r)
    a.loc[7940,'status']='AC_FAILURE'
    assert extract_bad_hours(a,r).hour_index.tolist()==[7940]
