# SEEDExchange: Curated optimization figures and plot review

Date: 31 October 2026

## Scope

This package is a **post-processing-only** review of the completed 6,840-task PyPSA/HiGHS energy screening study. No solver tasks or pandapower AC power flows were run to prepare these new plots.

**Source files:** `complete_study_results.csv`, `study_manifest.json`, `conditional_hosting_envelope.csv`, and `SEEDExchange_All_Plots.zip` supplied by the project. The original 34 MB plot archive is not duplicated in this ZIP.

## Recommended presentation selection

1. **Main body: 6 figures.** For each of 7, 9 and 12 households under assumed 5 kVA, show (a) PV panel count vs annual self-sufficiency and (b) usable battery capacity vs annual self-sufficiency. Colour represents annual total USD/year. These are in `figures/main/`.
2. **Optional: 4 figures.** PV and battery sizing for 15 homes, 12-house transformer-rating sensitivity, and 12-house monthly self-sufficiency coloured by grid imports. These are in `figures/optional/`.
3. **Operational appendix:** the original day, week, month and annual output PNGs for all three shortlisted configurations are preserved unmodified in `appendix_hourly_original/`. Those are time-series plots, where connected lines have a temporal meaning.

For a short presentation, use the two 12-house figures plus one 12-house monthly operation figure. Add the 7- and 9-house paired figures in a longer report or appendix.

## Interpreting the technology plots

- **PV plot:** one point for each `fixed_PV_economic` solver configuration. PV count is fixed, while the MILP optimizes BESS quantity, battery power, inverter family/rating and 8,760-hour dispatch. It is a conditioned economic sizing sweep, not pure PV-only physics.
- **BESS plot:** one point for each `fixed_BESS_economic` configuration. BESS modules are fixed, but PV count, battery power, inverter and dispatch may change. It is not a single-variable experiment with PV held constant.
- **Colour scale:** annual total cost in USD/year, not upfront CAPEX. Each PV/BESS pair for the same household count has the same colourbar bounds for direct visual comparison. Different household counts have different cost bounds.
- **Black ring:** minimum annual-cost result within that specific fixed-technology sweep. The ring does not indicate verified feeder feasibility.
- **No connecting lines:** each point is a distinct MILP solution. Lines across unrelated discrete designs imply continuity that was not optimized.
- **Not a full Pareto frontier:** the original sampled epsilon-constrained and budget objectives have not been proved to span the continuous cost/self-sufficiency efficient set.

## Original archive audit

The uploaded archive contained **513 files**, including **252 PNG** and **252 SVG** files, 6 CSV files and 3 JSON files. All 252 PNG images passed basic image-decode validation and all 252 SVG files passed XML parsing. The 240 main PNGs are exactly **12 demand-profile cases × 5 assumed transformer ratings × 4 plot families**. The 12 additional PNGs are **3 shortlisted hourly scenarios × 4 plot families**.

There are 12 demand cases rather than 11 because the eight-house scenario has separate H01 and H02 demand realizations. The original four main families are:

| Original family | PNG count | Recommended use |
|---|---:|---|
| `all_objectives_pareto` | 60 | Archive only. Dense symbols and connected nondominated subsets make interpretation difficult. Sampled, not complete Pareto frontier. |
| `cost_self_sufficiency` | 60 | Remove from main report. Primarily repeats fixed-PV information with axes reversed and uses connected sequences. |
| `pv_sizing_curve` | 60 | Replace in the main report with unconnected scatter and cost colourbar. Original 3-panel plot remains available in source archive for detailed engineering review. |
| `battery_sweep` | 60 | Replace with unconnected battery-capacity scatter and cost colourbar. Original curves remain available in source archive. |

The detailed `audit/original_plot_inventory.csv` gives every one of the 240 file names and its disposition.

## Numerical findings relevant to the figure selection

| Households | Cost-minimizing PV panels | PV kWp | BESS usable kWh | Annual total cost USD/year | Self-sufficiency |
|---:|---:|---:|---:|---:|---:|
| 7 | 26 | 11.31 | 21.625 | 2,772.94 | 85.59% |
| 9 | 34 | 14.79 | 25.950 | 3,570.99 | 84.97% |
| 12 | 41 | 17.835 | 34.600 | 4,767.83 | 81.04% |
| 15 | 67 | 29.145 | 47.575 | 6,133.19 | 92.03% |

These are the energy-screen economic minima under the assumed 5 kVA case, not validated transformer-hosting capacities. Panel rating is 435 Wp and each usable battery module is 4.325 kWh.

### Repeated transformer-rating plots

The best annual cost for 7, 9, 12 and 15 households is **identical at the reported precision** across assumed 5, 10, 15, 20 and 25 kVA ratings. For the 12-house cost-minimizing configuration, the **PCC apparent-power proxy changes from 4.50 kVA at 5 kVA rating to approximately 5.22 kVA at higher assumed ratings**, even while annual cost remains $4,767.83. Therefore, reproducing near-identical technology plots for every rating is of little value. The optional rating figure instead reports cost against rating and colours the peak PCC proxy.

This is not a statement that transformer rating is electrically irrelevant. The model includes aggregate connection-power screening without as-built LV feeder voltage, phase balance, losses, or thermal limits.

### Monthly operation

For the 12-house shortlisted annual dispatch, monthly self-sufficiency ranges from about **69.6% in November** to **99.6% in July**, with the maximum monthly grid import in November at about **653.9 kWh**. The new optional monthly chart makes this visible in one unconnected scatter. The time-series figures in the original archive remain useful as detailed diagnostics.

### Results requiring follow-up

- Of 6,840 task records, 6,820 have an optimal energy-screening status and 20 are infeasible. All 20 infeasible cases occur in the assumed 5 kVA cases for 9 to 15 households and low or zero fixed DER sizing.
- No pandapower AC feeder validation exists in this run. Do not treat 15-house energy feasibility as an existing transformer capacity assessment.
- One stochastic household-demand realization and a 2025 solar-resource profile were used. The 8-house H01 and H02 cases must remain distinguishable.
- No confirmed utility customer-to-transformer electrical topology, measured service-drop impedances or validated voltage profiles are included.

## Reproduce the clean figures locally

From the repository root, put the scripts in a local working directory or run them from the unpacked ZIP:

```powershell
python scripts/build_final_figures.py `
  --results "case1/studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv" `
  --out "figures_curated"
```

To reproduce the simplified 12-house monthly figure, use the original archive:

```powershell
python scripts/build_monthly.py `
  --archive "SEEDExchange_All_Plots.zip" `
  --houses 12 `
  --out "figures_curated"
```

These scripts only read existing results. They do not invoke PyPSA, HiGHS, pandapower or GitLab CI.
