"""No PyPSA needed for classification and parameter validation tests."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from model import Settings
from pareto_panel_sweep import summarize_sweep,plot_sweep

def test_exact_panels_bounds():
    assert Settings(max_panels=64,fixed_panels=0).fixed_panels == 0
    assert Settings(max_panels=64,fixed_panels=64).fixed_panels == 64
    for x in (-1,65,10.5):
        with pytest.raises(ValueError):Settings(max_panels=64,fixed_panels=x)

def test_economic_envelope_classification():
    df=pd.DataFrame([dict(panel_count_fixed=p,status='OPTIMAL_ENERGY_ONLY_NO_AC_VALIDATION',
                          annual_total_usd=c,self_sufficiency_of_demand_pct=ss) for p,c,ss in [
                              (0,800,0),(1,700,20),(2,650,20),(3,660,18),(4,900,40)]])
    df.loc[5]=[5,'INFEASIBLE_OR_FAILED',float('nan'),float('nan')]
    out=summarize_sweep(df)
    assert out.nondominated_among_min_cost_at_fixed_pv.tolist() == [False,False,True,False,True,False]

def test_preview_plot_on_synthetic_smoke_data(tmp_path):
    df=pd.DataFrame([dict(panel_count_fixed=p,pv_kwp=p*.435,annual_total_usd=700+p*10,grid_import_kwh=1000-p*50,
        self_sufficiency_of_demand_pct=p*8,battery_usable_kwh=p*2,
        inverter_ac_kva_assumed_unity_pf=5, status='OPTIMAL_ENERGY_ONLY_NO_AC_VALIDATION') for p in range(5)])
    q=summarize_sweep(df)
    plot_sweep(q,tmp_path/'test_preview',case='SYNTHETIC_TEST_ONLY',assumed_kva=5)
    assert len(list(tmp_path.glob('*.png')))==2
