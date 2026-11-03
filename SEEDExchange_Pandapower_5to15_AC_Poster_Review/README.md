# San Rafael: 5–15-house pandapower AC review

## Scope and reproducibility

- Original uploaded simulation archive: `pandapower_5_to_15_review.zip`.
- Representative 5 kVA transformer and approximately 324.5 m radial LV feeder derived from existing study model. It is **not** a spatially reconstructed EPM distribution network.
- Critical-hour suite: 132 combinations (11 house counts × 3 inverter positions × 2 load allocations × 2 power factors); 6,324 scenario-hour solves. All converged.
- Annual suite: 11 combinations (5–15 homes × LV-head inverter × equal allocation × load PF 0.98), 96,360 scenario-hour solves. All converged.
- Operating schedules are the selected optimized energy-model designs, and **change with household count**. Comparisons do not isolate household demand from equipment sizing or dispatch differences.

## Findings

- **Strict 0.97–1.03 pu screen:** The largest tested fully compliant annual reference configuration is **6 households**. A first low-voltage violation occurs at 7 houses (one hour of 2025). Under the broader critical-hour stress conditions, **only the 5-house case** passes across all tested assumptions.
- **0.95 pu reference:** Only the 14-house annual reference case falls below 0.95 pu (one hour). The 15-house model has a minimum of 0.9500065 pu, narrowly above that threshold. This is **not** a formal claim of EN 50160 compliance, which has different definitions/observation conventions.
- **Thermal loading:** All annual PF 0.98 reference cases have transformer and LV conductor loading below their nominal thermal limits. In PF 0.90 remote-heavy critical-hour scenarios, transformer loading exceeds 100% starting at 10 houses, up to ~114.68% at 14 houses. No LV conductor loading above 100% in any tested scenario.
- **Siting:** In the 14-house PF 0.90, remote-heavy critical case, minimum voltage is 0.92994 pu at LV head, 0.93885 at midpoint, 0.94539 at far end. Moving to the far end improves the worst voltage by 0.01546 pu but does not meet the 0.97 criterion or eliminate transformer overload.
- **Connection apparent power:** The annual reference observes 283 scenario-hours above the energy optimizer’s 4.5 kVA proxy but zero scenario-hours above the transformer’s 5 kVA rating. These are across multiple independently modelled household cases, not distinct real-world calendar hours.
- **Non-monotonic outcomes:** The 14-house reference has 663 hours below 0.97 pu, versus 238 for 15 houses; the optimized device sizes and dispatch differ between cases. Do not interpolate a continuous 'maximum households' without holding technology and load structure fixed.
- **Network losses:** Sum of each hourly simulated real loss estimate ranges from roughly 313 kWh (5 homes) to 638 kWh (14 homes) per modeled year. Approximate totals presume hourly timesteps.

## Important modelling limitations

The 0.97 pu lower bound is a project screening criterion, not equivalent to a guaranteed legal grid-code limit. The 324.5 m feeder is representative. There are no verified individual LV cable routes, pole connections or conductor data for the real house groups. The model uses a balanced equivalent for single-phase 120/240 V service and does not test leg imbalance, neutral voltage, phase allocation or protection. The annual runs test one PV/BESS siting, one load allocation, and one PF only. Critical-hour sweeps are not annual failure probabilities. No resilience or islanding is simulated in this dataset.

## Correct next engineering step

Construct a geographically informed conditional pandapower model using the precise transformer points and candidate H01–H35 territory associations. Explicitly compare several defensible network route alternatives and cable sizes, and if future PV/BESS equipment is chosen, map PV/BESS locations onto the candidate feeders. Then use a targeted AC-feasible redispatch/resize study, followed by resilience and adaptability scenarios.

## Figure set

- `00_poster_composite_5_to_15`: the four key scatterplots in a single poster visual, without connecting data lines.
- `01_annual_minimum_voltage`: yearly worst LV voltage, with two reference thresholds.
- `02_annual_violation_hours`: annual count of hours below each chosen reference threshold.
- `03_pv_bess_connection_position`: inverter placement in critical PF 0.90, far-end-heavy demand scenario.
- `04_transformer_loading`: reference and critical-stress transformer loading versus houses.
- `05_annual_feeder_losses`: optional modelling detail.

## Data files

- `annual_reference_summary.csv`
- `critical_stress_summary.csv`
- `placement_sensitivity_pf090_far_end_heavy.csv`

Plot data are read directly from supplied simulation CSVs. See `recreate_figures.py` for the reproducible figure routine.
