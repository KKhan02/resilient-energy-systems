# SEEDExchange WP1, Study A: nine-house annual AC evidence review

**Date:** 2026-11-07  
**Evidence:** user-uploaded `nine_house_results.zip`, 27 archived files, checked for ZIP integrity, checkpoint hashes, SOC-trajectory hashes and source-pilot hashes. No new PyPSA or pandapower simulations were run for this review.

## Scope and constraints

Existing provisional EPM LV transformer **94022**, modelled at **5 kVA**, nine designated GIS houses **H01, H02, H03, H06, H26, H27, H28, H34, H35**. One 2025 hourly synthetic profile set across all equipment candidates, aggregated household demand **17,082 kWh/year**. Each annual source dispatch is a fixed-hardware PyPSA economic solve with manufacturer minimum **20% physical battery SOC**, **zero grid export**, **no grid-to-battery charging**, perfect foresight, independent PV/BESS/inverter hardware limits; each pandapower run uses head inverter placement, PF 0.98, assumed service factor 1.0, coordinated daytime Q ratio 0.25, nighttime Q disabled and balanced 3-phase proxy. Annual primary feasibility screen: 0.95 to 1.05 pu and 100% thermal loading.

## Source-verified equipment and annual outcomes

| Metric | EC-3cc99d4429a15487a083 | EC-b091c626114a2d74884f | EC-9df8c68834f7c7f6faa3 |
|---|---:|---:|---:|
| PV panels / battery modules / inverter kVA | 34 / 6 / 10 | 40 / 7 / 12 | 41 / 8 / 12 |
| PV kWp | 14.79 | 17.40 | 17.835 |
| Battery DC power limit kW | 10.56 | 11.466544 | 11.749235 |
| Annualized equipment+grid cost USD/year | 3628.4402 | 3735.5284 | 3774.4290 |
| Annual grid import kWh | 2765.2810 | 1373.4444 | 893.5668 |
| Annual grid export kWh | 0 | 0 | 0 |
| Unserved load kWh | 0 | 0 | 0 |
| Self-sufficiency % | 83.81173 | 91.95970 | 94.76896 |
| PV available DC kWh | 17959.6648 | 21129.0174 | 21657.2428 |
| PV curtailed DC kWh | 2488.4727 | 4124.2123 | 4121.9078 |
| PV curtailed while battery at source Store SOC floor kWh | 1898.1063 | 3257.3989 | 3284.5408 |
| AC converged / feasible primary 0.95–1.05 pu hours | 8760/8760 | 8760/8760 | 8760/8760 |
| AC min bus voltage pu | 0.95339189 | 0.95542275 | 0.95339189 |
| AC max transformer loading % | 79.98886 | 76.54783 | 79.98886 |
| AC max line loading % | 10.70966 | 10.70966 | 10.70966 |
| Modelled 8760h AC losses kWh | 458.4287 | 449.3145 | 446.3073 |
| **Original saved strict-band (0.97–1.03 pu) reclassification failure hours** | **203** | **148** | **133** |

The strict research-band reclassification was a check of *fixed* annual P/Q operating points; it did not redispatch the inverter or solve additional power flows. Direct floating-point `min_v_pu < 0.97` counting from hourly CSV returns 204/149/134, one more per case than saved classification because one marginal `0.969999...` hour is excluded by the source's tolerance policy. For consistent model reporting use the saved `voltage_band_comparison.csv` counts and state that a threshold tolerance is involved.

### Derived comparisons

- 41/8 relative to 34/6: grid import is lower by **1,871.7142 kWh/year**, self-sufficiency rises by **10.9572 percentage points**, annualized equipment+grid cost rises **USD145.9888/year**, and annual modelled AC losses fall **12.1213 kWh/year**. This is **not** an isolated battery-size comparison: PV panels, inverter and battery power also change.
- 40/7 relative to 34/6: grid imports fall 1,391.8366 kWh/year, annualized cost increases USD107.0882/year and saved strict-band failures decrease by 55 hours.
- Across all cases the lower 0.95 pu screening margin is small (**0.00339 pu** for two configurations). Length/PF and spatial-load uncertainties matter more for final certification than the low modelled line-loading percentage might suggest.
- The 34/6 and 41/8 cases share the same worst event on **2025-11-27 20:00**, household aggregate load 3.727265 kW and inverter output 0 kW, with nighttime reactive power disabled: 0.95339189 pu and 79.98886% model transformer loading. The 40/7 case's minimum occurs **2025-11-28 21:00**, load 3.570352 kW and inverter output 0 kW, at 0.95542275 pu and 76.54783%. Even larger PV/BESS capacity does not necessarily eliminate a worst evening interval when discharge is unavailable or constrained by its energy schedule.
- Between **76% and 80% of annual curtailed PV** is recorded at the model's minimum Store energy for these cases. This exposes perfect-foresight charge-timing behavior and makes cross-cutting PV-first / causal dispatch comparison worthwhile; it is **not** proof that battery modules are too small or that all curtailed energy can be stored.

## Verification

- ZIP container passed CRC test; expected 27 files present for 3 source equipment candidates.
- Each source manufacturer dispatch and each AC replay has exactly 8,760 hourly rows, from `2025-01-01 00:00:00` through `2025-12-31 23:00:00`.
- All 3 `fixed_hardware_manufacturer_soc_baseline.csv` SHA-256 hashes match `pilot_manifest.json.source_trajectory_sha256`.
- All 3 `annual_ac_hours.csv` SHA-256 hashes match `ac_checkpoint.json.annual_ac_hours_sha256`.
- All 3 `pilot_manifest.json` SHA-256 hashes match `annual_ac_summary.json.source_pilot_manifest_sha256`.
- All source results state 8,760 AC converged/feasible at 0.95–1.05 pu, 0 recorded export, and no unserved energy.

## Evidence boundaries

1. **The 9-house baseline AC feasibility reference is complete** under the above assumptions. It is *not yet robustly feasible* at PF 0.95, service factor 1.3/1.6, altered Q control/placement, household-specific nodal loads or measured service topology.
2. Existing historical 7- and 9-house scenarios both belong to **94022**; they are *different customer populations on the same mapped transformer*. The 40-hour, 10-house provisional GIS territory is a distinct population and should never be mistaken for the 9-house group.
3. The source annual AC replay uses `run_hour(..., allocation='equal', siting='head')`, **even though the upstream PyPSA demand is a sum of distinct synthetic individual house profiles**. This equal spatial allocation does not preserve household-level hourly coincidence or unbalanced phase loading. Revisit with mapped distinct profiles as an explicit follow-up sensitivity, not as if these full-year runs already supplied it.
4. 5 kVA 94022 nameplate and GIS customer attachments remain provisional; service drops and line impedances are uncertain. `service_factor` scales **assumed house service drops**, rather than all mapped EPM feeder backbone segment lengths. Do not call x1.3/x1.6 a blanket feeder-length multiplier.
5. Annualized costs do not price modelled AC losses, conductor upgrades, permits, metering, new service drops or site-specific connection costs. A simple `$0.29 × modelled line-loss kWh` is illustrative only and is **not** an AC-aware optimized electricity bill.
6. Results describe steady-state voltage and thermal screening, not field compliance, islanding, GFM/GFL dynamics or resilience under blackout.

## Efficient research continuation

1. Freeze these **three AC-reference passes** in the evolving Study A candidate-evidence ledger, together with the saved 7-house feedback and three 12-house reference AC passes. Preserve `NOT_RUN` for unchecked economic candidates.
2. Reuse critical-hour indices and near-0.95-pu intervals to screen **service factors 1.0, 1.3, 1.6** and **load PF 0.95, 0.98, 1.00**, plus night-Q-off and allowed day Q controls. Escalate to full 8,760-hour verification for representative feasible-boundary cases only. Do not blindly run all selected equipment across all 9 sensitivity combinations.
3. Cross-check distinct source household time series against their explicit GIS attachments, then compare the equal-load proxy against one defensible nodal stochastic allocation; phase data are not certified.
4. For all retained candidates across A, later B and C, perform controlled PV-first battery dispatch comparison, quantifying curtailment at battery floor/full/intermediate SOC, causal vs perfect-foresight savings, battery power constraints, equipment and lifetime costs, and steady-state AC effects. Reuse the original 0–16-module fixed-BESS economic sweep first, do not rerun the 6,840 historical optimization tasks.
5. Keep the approved zero-grid-export, PV-only battery-charging baseline unchanged.

Source reviewed locally; the uploaded ZIP was not modified and no new simulation was run.
