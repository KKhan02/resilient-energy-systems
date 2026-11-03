# SEEDExchange | Coordinated voltage and transformer thermal control + Q sweep

**Package v1.2 | EPM GIS candidate feeders | 2 November 2026**

This release *extends* the previous `case1/studies/epm_gis_pandapower_v1` model. It preserves all prior files, including HIL Volt–Var, the standalone transformer Q guard, EPM LV network geometry and tests. It adds:

- `coordinated_q_control.py`: an AC-feedback search over permissible inverter reactive power **in either direction**. Candidate solutions are tested against both LV voltage limits (default 0.97–1.03 pu), transformer rating (100%) and conductor loading (100%). A physically feasible solution is preferred over any infeasible solution.
- `run_coordinated_q.py`: tests unity PF, settled HIL Q(V), and the coordinated AC Q controller using identical *fixed PyPSA hourly P schedules*. Q capability obeys `min(q_ratio * P_inst, sqrt(S_inv^2 - P_inv^2))`.
- `plot_coordinated_q.py`: four-panel scatter plots by EPM transformer and placement, with NO connecting lines: Q ratio against Vmin, Vmax, transformer loading, and fraction of tested hours passing all limits.
- `tests/test_coordinated_q.py`: six independent numerical logic tests. Together with the original suite, **28 tests pass locally**.

## Run on your Miniforge environment

1. Extract the ZIP into the **repository root**, retaining `case1/studies/epm_gis_pandapower_v1` and existing dispatch files. Open Miniforge Prompt in `case1/studies/epm_gis_pandapower_v1`.
2. Confirm the tests:

```bat
python -m unittest discover -s tests -v
```

3. Run the planned **critical-hour Q capability sweep**, initially with the more likely head and midpoint placements, PF 0.98 and unmodified EPM backbone. This uses 0.00, 0.05, ..., 0.60, and also 0.48, automatically. The 0.25 setting is already in the 0.05 grid:

```bat
python run_coordinated_q.py --mode critical --trafos 94022 106039 --siting head middle --power-factors 0.98 --service-factors 1.0 --q-start 0.0 --q-max 0.60 --q-step 0.05 --q-extra 0.48 --policies unity hil coordinated --output outputs/coordinated_q_sweep_pf098
```

**Performance:** Each coordinated hour samples 21 or more pandapower Q operating points. This is more computationally expensive than the old single-Q solve. It saves `ac_hours.csv` **after every scenario**, rather than only at the end. Run a small smoke test first if preferred:

```bat
python run_coordinated_q.py --mode critical --trafos 94022 --siting middle --power-factors 0.98 --q-ratios 0 0.25 0.48 --max-hours 4 --q-grid-points 13 --q-refine 1 --output outputs/coordinated_smoke
```

4. Plot results and identify successful configurations:

```bat
python plot_coordinated_q.py --input outputs/coordinated_q_sweep_pf098/ac_scenario_summary.csv --output outputs/coordinated_q_sweep_pf098/figures
```

5. Run stress PF 0.90 **after examining** the PF 0.98 result. Use a separate output directory:

```bat
python run_coordinated_q.py --mode critical --trafos 94022 106039 --siting head middle --power-factors 0.90 --service-factors 1.0 --q-start 0 --q-max 0.60 --q-step 0.10 --q-extra 0.25 0.48 --policies unity hil coordinated --output outputs/coordinated_q_sweep_pf090
```

6. For cable-length sensitivity, add `--service-factors 1.0 1.3 1.6` to a *shortlisted* set of Q ratios to avoid unnecessary duplicate full sweeps.

7. **Full-year verification, only after choosing an admissible controller** (illustrative choice of q=0.30 to be updated after examining your results):

```bat
python run_coordinated_q.py --mode full --trafos 106039 --siting middle --power-factors 0.98 --q-ratios 0.30 --policies unity hil coordinated --q-grid-points 13 --q-refine 1 --output outputs/epm_full_year_selected
```

A 25-year economic update based on resulting AC feeder losses will require separately valuing those losses, and a full-year SOC-consistent rerun if active P dispatch changes.

8. ZIP the critical results for review:

```bat
python -c "import shutil; shutil.make_archive('coordinated_q_results','zip','outputs/coordinated_q_sweep_pf098')"
```

## Output

`ac_hours.csv`, `ac_scenario_summary.csv`, `validation_manifest.json`, `house_assignments.csv`, `network_edges.csv`, `house_service_assumptions.csv`, `territory_topology.csv`, `skipped_cases.csv`. After the plotting step, `figures/*.png`, `figures/*.svg`, and `figures/all_sampled_hours_feasible.csv`.

Summary columns include Q ratio, selected Q (kvar), minimum and maximum voltage, peak transformer and line loading, losses, failure counts, number of hours in which controller Q differs from HIL Q, and the number of hours where **no sampled Q** can satisfy the constraints at the fixed active-power dispatch.

## Modelling boundaries and interpretation

- **Q ratio** is the maximum reactive capability relative to installed AC P rating, not the actual reactive output. The actual `q_selected_kvar` varies by hour and is limited by `sqrt(S_inv^2 - P_inv^2)`.
- The HIL U1=.96, U2=.99, U3=1.01, U4=1.04 rule is retained as the **reference**. The coordinated search may override its Q command to satisfy network limits, including changing the sign if that offers an electrically feasible point.
- The controls use steady-state hourly AC feedback. HIL T95=10s transients, inverter current dynamics, control oscillation, phase imbalance, neutral current and protection are **not** simulated.
- The controller **does not alter P, battery SOC, PV curtailment or loads**. If no sampled Q is feasible, the CSV says so. It does not fake feasibility. More finely sampled Q or a different controller may reveal a narrow feasible interval, so the phrase is *no sampled feasible Q*, not a mathematical proof of impossibility.
- EPM GIS LV sections and their lengths are used. Household service drops are still **assumed**, transformer 92395 has no linked LV feeder in the export, conductor electrical properties include **screening proxies**, and the base house allocations are modelling assumptions.
- 5 kVA/3 kVA one-phase equipment is approximated using the existing balanced equivalent and ROOT_FACTOR=3. Actual split-phase voltages and neutral currents are **not** verified. Do not treat these numerical tests as confirmed utility compliance.
- `all_sampled_hours_feasible.csv` proves only passing the selected conditions and selected simulation hours. It is not an annual certificate or an optimization of system equipment cost.
- Inverter nameplates currently assumed 10 kVA and 12 kVA for transformers 94022 and 106039, and P_inst defaults to S if not specified. Explicit `--p-installed 94022:<kW> 106039:<kW>` can override based on validated equipment specifications.
- Q > 0.48 extends beyond the earlier nominal HIL Q ratio **for sensitivity analysis only**, and is constrained by inverter capability, not certified EPM grid-code support.

**Implementation verification here:** 28 unit checks and syntax compilation. pandapower itself was unavailable in the creation environment; AC solve results must come from your Miniforge run.
