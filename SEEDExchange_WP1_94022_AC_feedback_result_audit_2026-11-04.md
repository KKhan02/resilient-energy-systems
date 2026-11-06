# SEEDExchange WP1 | 94022 seven-house AC-feedback full-year audit

Date: 4 November 2026. Evidence: uploaded baseline, feedback manifests, sampled AC corridors, hourly dispatch, and independent annual pandapower replay. **Research screening only, not verified as-built utility compliance.**

## Result

The fixed-hardware seven-house design passes **8,760/8,760** converged AC hours after a new 8,760-hour PyPSA dispatch. Before feedback, the same manufacturer-SOC baseline had **4** voltage failures, 8,756 pass hours and Vmin **0.968183955 pu**. After feedback, Vmin is **0.970098728 pu**, Vmax **0.998157028 pu**, maximum transformer loading **58.585%**, maximum line loading **8.953%**. The threshold 0.97–1.03 pu and <=100% thermal ratings are research assumptions.

Only **9 hours** changed inverter active power (threshold 1e-6 kW). PV generation, battery charging, total battery discharge, total grid imports, ENS, equipment sizes, and flat-tariff modelled annual cost remained unchanged. Battery discharge shifted between hours, rather than increasing total discharged energy.

| Previously failing time, 2025 | Old minimum voltage (pu) | Revised voltage (pu) | Revised P inverter (kW) |
|---|---:|---:|---:|
| 27 Nov 20:00 | 0.968184 | 0.970968 | 0.730 |
| 28 Nov 20:00 | 0.969163 | 0.970514 | 0.354 |
| 28 Nov 21:00 | 0.969196 | 0.970546 | 0.354 |
| 29 Nov 19:00 | 0.969935 | 0.971250 | 0.345 |

The narrowest revised margin is **0.000098728 pu** (about 0.0099% of nominal), at **28 Nov 2025 18:00**. There are **41 hours below 0.975 pu**. This result is numerically feasible under the chosen thresholds but **not robustly separated from the boundary**.

## SOC and dispatch checks

- Uninterrupted 8,760-hour trajectory, with `e_cyclic=True` in the existing PyPSA model. Source script `run_annual_feedback.py` calls `solve_fixed()` to reoptimize every hour with fixed equipment, AC P corridor constraints, and manufacturer SOC floor.
- **Maximum SOC equation residual:** 8.882e-15 kWh, using `E_t - E_(t-1) - sqrt(0.95)*P_charge,t + P_discharge,t/sqrt(0.95)` and cyclic wrap-around.
- **Maximum AC-bus energy balance residual in the PyPSA energy model:** 8.882e-16 kW.
- **Simultaneous battery charging/discharging hours:** 0.
- Minimum reported Store energy: **1.145 kWh**, matching the added 20% physical SOC floor in the original Store coordinates. This is distinct from stored energy being zero at physical 0% SOC.

## Equipment and economics

Fixed equipment: **26 panels = 11.31 kWp PV, 5 Deye SE-G5.1 battery modules = 25.6 kWh nominal, 21.625 kWh original model Store maximum, 8.499 kW battery DC power, and 7.6 kVA inverter.** EPM transformer 94022 is screened at an assumed 5 kVA; seven candidate houses are H03, H06, H26, H27, H28, H34, H35.

- Annual imported energy: **2,042.636 kWh** in both manufacturer-SOC and revised dispatch.
- Normal-operation ENS: **0 kWh** in both.
- Annualized equipment and purchased-energy cost: **USD 2,810.008/year** in both. Thus **incremental cost for AC feedback is USD 0.00/year under the current flat-tariff, energy-only cost model**.
- Modelled AC feeder losses: **367.180 kWh before**, **367.150 kWh after**, delta **-0.0302 kWh**. These are separate pandapower estimates, not yet in the PyPSA dispatch balance or cost objective. Do not simply add all losses to billed import without establishing the metering boundary and supply of losses.

## Reactive-power control observation

`daylight_q_ratio=0.25` is enabled in the manifest, but **Q was actually zero in all 8,760 modelled hours** (`q_selected_kvar` == 0 in the validation CSV). Nighttime Q was disabled. The annual pass is therefore attributable to P redispatch, not to realized reactive support in this particular trajectory. This does not validate the inverter's ability to provide nighttime Q.

## Caveats and implementation details

1. EPM GIS LV backbone is used, but customer drops, phase allocation, line impedances/ampacities and rating interpretation are assumed. This is a balanced equivalent, not an unbalanced 120/240 V verification.
2. The P corridors are sampled at **9 P points** and Q at **9 points**, with `q_refine=0`; each CSV explicitly states that between-point AC feasibility was **not** proven. The independent full-year AC replay nevertheless verifies the *actual chosen* operating points.
3. The saved `annual_ac_summary(1).json` contains `full_year_pypsa_energy_and_soc_reoptimized: false`. That flag is assigned unconditionally by the **AC validator** (which does no optimization), not by the preceding `run_annual_feedback.py`. The feedback script did perform the full-year PyPSA reoptimization according to its source and the changed 8,760-hour outputs. To avoid confusion, update validation provenance to explicitly distinguish **dispatch recomputed upstream** from **validator itself recomputing dispatch**.
4. Losses, real inverter battery consumption, manufacturer inverter Q operation and Colombian tariff/connection rules remain outstanding.
5. GitLab source was unchanged in this audit. Original reference manifest states commit `e377e21d26db4bffd7a164d1257d5860bb01f325`.

## Recommended next gates before a broad equipment sweep

**Gate 1: small engineering robustness tests** using the identical redispatched hourly series, with service-drop length factors 1.0, 1.3, 1.6 and household PF 0.98, 0.95, 0.90. Preserve results separately. Even a small deterioration may violate the tiny voltage margin. Do not label variants field-realistic without evidence.

**Gate 2: numerical sample refinement** around the four originally failing P thresholds and the new weakest hours. Establish whether the 9-point P grid changes the solution materially, then choose a resolution based on demonstrated errors/runtime, not a nominal precision claim.

**Gate 3: economics and losses**. Define an appropriate loss-aware grid balance, metering boundary and inverter losses before claiming fully network-constrained least-cost sizing. Keep the current result as the original screening baseline.

**Gate 4: network-aware hardware shortlist**. Reuse the prior PV, battery-module, battery-power and inverter sweeps, shortlist candidates with low-cost/high-self-sufficiency tradeoffs, and run the AC-aware method on each. This fixed five-module case remains a **method validation case**, not the final design. The household-hosting sweep and 106039 territory remain on the roadmap.

## Reference hashes of uploaded outcomes

- `feedback_manifest.json`: `b12cdd08b04cb57dbcd1d0cd58db58b73146fe13ba5f4328a2691be054e4beb2`
- `redispatched_hourly(1).csv`: `6bdf93cba08e80db0614aff54263de7b6ec7d21373c187303a5e785bcf570b09`
- `annual_ac_summary(1).json`: `76958885bd4819ac7e7a6d1b7885d7bbb9244dae92c1e3af4e2076f64d7405e7`
- `annual_ac_hours(1).csv`: `3414f4cc60fcd9809e34bad2d7502e3bbed4261cddd787d7cf69661639bcd95e`

## Supporting plots

- [AC-feedback inverter dispatch comparison](WP1_AC_feedback_inverter_dispatch_comparison.png)
- [AC voltage comparison](WP1_AC_feedback_voltage_comparison.png)
