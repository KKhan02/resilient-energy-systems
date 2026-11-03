"""Regression checks: full_study task field 'panels' is accepted by the plotting routine."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pareto_panel_sweep import plot_sweep, summarize_sweep


def _records():
    return pd.DataFrame([
        {"status":"OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER", "panels":10,
         "pv_kwp":4.35, "annual_total_usd":2100, "grid_import_kwh":2200,
         "self_sufficiency_of_demand_pct":75.0, "battery_usable_kwh":8.65,
         "inverter_ac_kva_assumed_unity_pf":5},
        {"status":"OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER", "panels":2,
         "pv_kwp":.87, "annual_total_usd":3000, "grid_import_kwh":5000,
         "self_sufficiency_of_demand_pct":50.0, "battery_usable_kwh":4.325,
         "inverter_ac_kva_assumed_unity_pf":5},
        {"status":"INFEASIBLE_MODEL", "panels":1}
    ])


def test_full_study_checkpoint_uses_panels_field(tmp_path):
    q=summarize_sweep(_records())
    plot_sweep(q, tmp_path/'figures'/'7_homes_5kva', case='7_homes', assumed_kva=5)
    for suf in ['_cost_self_sufficiency.png', '_pv_sizing_curve.png',
                '_cost_self_sufficiency.svg', '_pv_sizing_curve.svg']:
        assert (tmp_path/'figures'/('7_homes_5kva'+suf)).is_file()


def test_original_column_still_supported(tmp_path):
    q=_records().rename(columns={'panels':'panel_count_fixed'})
    q=summarize_sweep(q)
    plot_sweep(q, tmp_path/'standalone', case='7_homes', assumed_kva=5)
    assert (tmp_path/'standalone_pv_sizing_curve.png').is_file()


def test_incomplete_checkpoint_does_not_trigger_plot(tmp_path):
    q=summarize_sweep(pd.DataFrame([{'status':'INFEASIBLE_MODEL', 'panels':0}]))
    plot_sweep(q,tmp_path/'no_figures',case='7_homes',assumed_kva=5)
    assert not (tmp_path/'no_figures_pv_sizing_curve.png').exists()
