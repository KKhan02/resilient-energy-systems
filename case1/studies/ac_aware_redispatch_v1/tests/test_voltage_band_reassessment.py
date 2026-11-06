from pathlib import Path
import importlib.util
import json
import pandas as pd
import pytest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('voltage_band_reassessment',HERE/'reassess_voltage_bands.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def fixture():
    d=pd.DataFrame({'load_pf':[.98,.98,.95,.95], 'service_factor':[1.,1.,1.3,1.3],
        'hour_index':[1,2,1,2],'status':['CONVERGED']*4,
        'ac_feasible':[True,False,False,True],
        'min_v_pu':[.980,.968,.962,.978],
        'max_v_pu':[1.0,1.0,1.0,1.0],
        'max_trafo_pct':[40.,45.,55.,40.], 'max_line_pct':[5.,5.,6.,6.]})
    return d


def test_strict_and_engineering_are_distinct():
    d=fixture()
    assert list(v.pass_flags(d,.97,1.03))==[True,False,False,True]
    assert v.pass_flags(d,.95,1.05).all()
    out,flags=v.summarize(d)
    assert out[out.band=='original_strict_research'].hours_failing.sum()==2
    assert out[out.band=='engineering_target'].hours_failing.sum()==0


def test_thermal_constraint_not_dropped():
    d=fixture();d.loc[0,'max_trafo_pct']=101
    assert not v.pass_flags(d,.95,1.05).iloc[0]


def test_incomplete_hour_group_rejected():
    d=fixture().iloc[:3].copy()
    reference=pd.DataFrame([dict(load_pf=.98,service_factor=1.,feasible_hours=1,violating_or_failed_hours=1,min_v_pu=.968,max_v_pu=1.),
                            dict(load_pf=.95,service_factor=1.3,feasible_hours=0,violating_or_failed_hours=1,min_v_pu=.962,max_v_pu=1.)])
    with pytest.raises(ValueError):
        v.inspect_source(d,dict(mode='critical',hours_per_case=2,number_of_sensitivity_cases=2),reference)


def test_original_summary_crosscheck():
    d=fixture();reference=[]
    for (pf,sf),g in d.groupby(['load_pf','service_factor']):
        f=v.pass_flags(g,.97,1.03)
        reference.append(dict(load_pf=pf,service_factor=sf,feasible_hours=int(f.sum()),
              violating_or_failed_hours=int((~f).sum()),min_v_pu=g.min_v_pu.min(),max_v_pu=g.max_v_pu.max()))
    v.inspect_source(d,dict(mode='critical',hours_per_case=2,number_of_sensitivity_cases=2),pd.DataFrame(reference))
    reference[0]['feasible_hours']=7
    with pytest.raises(ValueError):
        v.inspect_source(d,dict(mode='critical',hours_per_case=2,number_of_sensitivity_cases=2),pd.DataFrame(reference))
