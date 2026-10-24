"""Regenerate static PNG Pareto figures from the existing saved v3 sweep.

Run in the consolidated folder: python render_pareto_static.py
Requires pandas, numpy and matplotlib. Does not rerun the simulation.
"""
from pathlib import Path
import pandas as pd
from wp1_v3.plots import pareto_panels
ROOT=Path(__file__).resolve().parent
csv=ROOT/'results/ALL_designs_including_extended_battery_power.csv'
if not csv.exists():
    raise FileNotFoundError(f'Missing scenario data: {csv}')
table=pd.read_csv(csv)
pareto_panels(table,ROOT/'results/figures')
print(f'Rendered static Pareto charts from {len(table):,} cases.')
