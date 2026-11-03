# SEEDExchange | 5 kVA poster and presentation figure kit

## Intended output
This kit is for a **scientific poster and its accompanying presentation**, not a report. It only post-processes the completed PyPSA/HiGHS dataset. No solver rerun, GitLab CI job, or pandapower AC validation was performed.

### Poster-ready image

`poster/5kva_four_figure_scaling_panel.png` and `.svg`: a consistent 2×2 arrangement of:

1. Number of households vs optimal PV panel count; colour = annual total cost (USD/year).
2. Number of households vs optimal usable BESS size (kWh); colour = annual total cost (USD/year).
3. Number of households vs upfront CAPEX (USD, excluding VAT); colour = self-sufficiency (%).
4. Number of households vs annual cost **per house** (USD/year per house); colour = self-sufficiency (%).

The chart is deliberately just axes, points, titles and colourbars. No connecting lines.

### Individual presentation images

The `presentation/` folder contains all **five** cross-household scatterplots as PNG and vector SVG. The additional one is number of houses vs **total annual cost**, with self-sufficiency as colour. The SVG is best for changing scale in PowerPoint or printing.

The `existing_scenario_views/` folder contains previous selected **5 kVA** within-scenario figures for 7, 9 and 12 households: (a) PV panels vs self-sufficiency, cost-coloured and (b) BESS kWh vs self-sufficiency, cost-coloured. It also contains the selected 12-house monthly energy figure. These source figures are included for presentation convenience; no transformer-rating plots are included.

### Method: selection and comparability

- Filter `complete_study_results.csv` to `kva == 5.0`, task `fixed_PV_economic`, and `OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER`.
- For each of 12 distinct demand cases, select the row with minimum `annual_total_usd` from the fixed-PV sweep. The sweep fixes the PV panel count and jointly optimizes BESS modules, battery power, inverter selection and hourly dispatch.
- There are **11 unique household numbers (5 to 15)** but **12 demand cases**, because the eight-house scenarios `8_homes_H01` and `8_homes_H02` are distinct. Both are retained as separate points. Their x locations are offset by ±0.10 households only to avoid overlap; both represent eight actual modelled households.
- `annual cost per house` is the selected total annual cost divided by household count. `CAPEX` is modelled upfront cost, excluding VAT.
- All technologies are those in one **jointly** cost-optimized design per scenario. The two technology-versus-houses charts are not independent PV-only/BESS-only sweeps.
- The chosen designs have *different self-sufficiency percentages*, roughly 72% to 92%. Differences therefore do not represent identical service-quality targets.

### Results worth discussing on the poster

| Quantity | 14 households | 15 households | Change |
|---|---:|---:|---:|
| PV panels (435 Wp) | 41 | 67 | +26 |
| Usable BESS (kWh) | 34.600 | 47.575 | +12.975 |
| Upfront CAPEX (USD, ex. VAT) | 30,754.93 | 48,042.22 | +17,287.29 (56.2%) |
| Annual cost (USD/year) | 5,684.46 | 6,133.19 | +448.73 (7.9%) |
| Annual cost/house (USD/year) | 406.03 | 408.88 | +2.85 |
| Self-sufficiency | 71.85% | 92.03% | +20.18 percentage points |

- **Lowest modelled annual cost per house:** 7 households, ~$396.13/year/house. Most other cases lie within a few dollars of this, so do **not** present seven households as an unambiguous economic optimum.
- **Visible equipment/CAPEX step:** 14 to 15 households. This is a step between discrete 5 kVA MILP outcomes under the chosen model and synthetic profiles; it is **not** evidence that an existing 5 kVA transformer can actually serve fourteen households or that a physical connection must be upgraded at fifteen.
- **Cost-per-house chart:** annualized cost/house increases slightly from roughly $396 at seven households to $409 at fifteen. The plotted y range is deliberately 385–420 USD/year, so read that narrow absolute difference correctly.
- **What the transformer assumption means:** These are aggregate energy/PCC screening results. Voltage, cable loading, phase imbalance, losses, topology, transformer thermal operation, and verified customer connections were not analysed using pandapower in this dataset.
- Do not title this a complete Pareto frontier. It is a consistent technology scaling comparison of optimized selected designs.

### Poster placement suggestion

Use the four-plot composite as the **community-scaling** panel. Use one 12-house PV-vs-self-sufficiency chart for a separate **detailed sizing** panel if space permits. Put the four other individual charts plus monthly operation in the presentation, where there is room to discuss assumptions and trade-offs.

### Reproduce locally

```powershell
python scripts/generate_figures.py `
  --results "case1/studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv" `
  --out "SEEDExchange_5kVA_Poster_Presentation_Figures"
```

Requires `pandas`, `numpy` and `matplotlib`. The script makes all cross-household figures and a selected-design CSV. It does not need PyPSA.
