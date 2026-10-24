# Case Study 1 v3.1 — Static Pareto Plot Correction

This update changes **plots only** and reuses `results/ALL_designs_including_extended_battery_power.csv` (11,515 screened rows). It does not recalculate demand, PV, BESS dispatch, economics, or electrical feasibility.

## Figures

- `results/figures/01_pareto_all_designs_self_consumption.png`: six-panel overview, zero export remuneration.
- `results/figures/01_pareto_all_designs_homer_sellback.png`: six-panel overview, HOMER 0.275 USD/kWh sellback.
- `results/figures/pareto_per_household/`: 34 individual PNGs, one for each of 4–20 households in each compensation regime.

**Every dataset row** is plotted with a color drawn from the *usable battery capacity (kWh)* colorbar at the right. Four marker shapes indicate PV panel-count groups. The continuous colorbar is used consistently across all figures, with no separate arbitrary colors per household or economic scenario. The same physical dispatch is used under both tariffs.

Solid colored marker = hardware-prescreened configuration with zero unserved grid-connected demand under the **algebraic PCC apparent-power model** (not confirmed LV network feasibility).

Faint colored x = hardware-prescreened scenario **excluded from the PCC zero-ENS frontier** due to unserved grid-connected demand. These points are included, not hidden, and use the same BESS color scale.

Black line connects **only** nondominated PCC-passing configurations, computed separately for every fixed household population and export-credit regime. Colored black-outlined frontier points retain the battery-size color. Black-outlined hollow star marks the lowest annualized-total-cost scenario among PCC-passing solutions.

**X:** annual grid-demand self-sufficiency (%). **Y:** annualized equipment plus purchased minus credited electricity (USD/year). Y is not upfront capital expenditure; hardware cost is an extrapolation of the HOMER split scaled to the quoted 12P/4B/5kVA subtotal.

Some distinct designs have exactly or nearly identical self-sufficiency and cost, so their markers naturally overlap. Values have not been artificially jittered.

## Run without redoing 11,515 simulations

From the `consolidated` folder:

```powershell
python -m pip install pandas numpy matplotlib
python render_pareto_static.py
```

To rerun the full simulation and all figures after installing dependencies: `python run_case1_v3.py --require-pvlib`.

## Limits

- Inputs in the existing 11,515-row result were screened using the earlier *independent approximate NASA GHI/Erbs* PV method. A pvlib source-aligned rerun is pending.
- PCC power balance and `max_trafo_kva` do not validate LV voltage, conductor loading, protection, split-phase balancing, or parallel-inverter approval. Full pandapower checks remain pending.
- A 90% continuous utilization factor for the 5 kVA transformer and household PF 0.98 are assumed, not verified EPM limits.
- HOMER export remuneration of 0.275 USD/kWh is a hypothetical scenario, not an approved Colombian tariff.
