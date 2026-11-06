"""Unit checks for plotting/postprocessing phase, not new AC simulation."""
from pathlib import Path
import importlib.util
import pandas as pd
import pytest

MODULE=Path(__file__).resolve().parents[1]/'plot_annual_voltage_sensitivity.py'
spec=importlib.util.spec_from_file_location('plot_annual_voltage_sensitivity',MODULE)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_reject_critical_mode(tmp_path):
    import json
    (tmp_path/'robustness_manifest.json').write_text(json.dumps({'mode':'critical','full_year_each_case':False}))
    (tmp_path/'sensitivity_ac_hours.csv').write_text('dummy\n')
    (tmp_path/'sensitivity_scenarios.csv').write_text('dummy\n')
    with pytest.raises(ValueError,match='full-year'):
        mod.load_review(tmp_path)

def test_voltage_bands_have_explicit_research_status():
    assert len(mod.BANDS)==4
    assert mod.BANDS[-1][1:]==(.97,1.03)
    assert mod.BANDS[-2][1:]==(.95,1.05)

def test_source_checks_full_length(tmp_path):
    import json
    (tmp_path/'robustness_manifest.json').write_text(json.dumps({'mode':'full','full_year_each_case':True,'number_of_sensitivity_cases':1,'hours_per_case':8760}))
    data={'hour_index':[0],'timestamp':['2025-01-01 00:00:00'],'status':['CONVERGED'],
          'min_v_pu':[.98],'max_v_pu':[1.0],'max_trafo_pct':[10.0],
          'max_line_pct':[10.0],'load_pf':[.9],'service_factor':[1.6]}
    pd.DataFrame(data).to_csv(tmp_path/'sensitivity_ac_hours.csv',index=False)
    pd.DataFrame([{'load_pf':.9,'service_factor':1.6,'feasible_hours':1,'min_v_pu':.98}]).to_csv(tmp_path/'sensitivity_scenarios.csv',index=False)
    with pytest.raises(ValueError,match='Incomplete'):
        mod.load_review(tmp_path)
