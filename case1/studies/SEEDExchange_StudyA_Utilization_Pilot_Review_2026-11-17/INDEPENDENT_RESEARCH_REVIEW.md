# SEEDExchange, Study A: A1 106039 PV/BESS utilization frontier

**Independent audit date:** 17 November 2026. **Source:** `StudyA_A1_106039_Utilization_Pilot_v1.zip`, SHA-256 `bae74218fd0b0ca60da26cfb3625e28638820ef588498df7d7afa36132a3282d`.

## Provenance, completeness, and scope

All six new 8,760-hour fixed-hardware PyPSA results completed without solver errors. The ZIP contains six signed energy manifests, six full hourly CSVs, one eight-design annual table, 96 monthly rows, and one batch receipt. Exact 2025 chronology, manifest-output SHA-256 matching, original v6.2 input/model/NASA SHA identity, individual equipment values, zero export/ENS, DC/AC power balance, cyclic SOC recurrence, 20% physical SOC floor and battery/inverter power ratings passed independent numerical checks. New hourly rows audited: **52,560**. Monthly totals reconcile to hourly totals for every energy column. The two original equipment references remain signed, read-only comparison rows, not new solver runs.

This is a **fixed-hardware annual energy-dispatch experiment**, not a new joint integer investment optimization. The baseline may have previously completed AC-aware corrections, but those corrections **do not transfer** to changed hardware or newly solved schedules. No new AC feeder power flows have been performed on the six new designs.

## Annual results

| Case | Panels ×435 W | Battery modules ×5.12 kWh nominal | Inverter kVA | Grid import kWh | PV curtailed DC kWh | Self-sufficiency % | Modelled USD/year |
|---|---:|---:|---:|---:|---:|---:|---:|
| MC_REF | 41 | 8 | 12 | 3,107.49 | 2,443.60 | 85.116 | 4,416.47 |
| MC_B9 | 41 | 9 | 12 | 2,792.93 | 2,095.07 | 86.623 | 4,471.70 |
| MC_P37 | 37 | 8 | 12 | 4,027.76 | 1,342.74 | 80.708 | 4,556.89 |
| SS_REF | 49 | 8 | 20 | 2,034.60 | 5,492.23 | 90.255 | 5,056.59 |
| SS_B9 | 49 | 9 | 20 | 1,478.23 | 4,875.76 | 92.920 | 5,041.70 |
| SS_B10 | 49 | 10 | 20 | 1,184.51 | 4,550.31 | 94.327 | 5,102.97 |
| SS_P45 | 45 | 8 | 20 | 2,483.86 | 3,871.80 | 88.103 | 5,060.43 |
| SS_P41_KEEP20 | 41 | 8 | 20 | 3,107.49 | 2,443.60 | 85.116 | 5,114.83 |

All rows use the same 11 A1 households, 20,878 kWh demand/year, 2025 normalized solar profile, zero export, zero unserved demand, fixed PV/BESS hardware and separate 8,760-hour cyclic SOC optimization. Historical financial assumptions are quoted in USD; they exclude real LV network investment, protection/metering, actual Colombian grid tariffs, AC losses in the objective and sourced battery-side power CAPEX.

## Marginal battery economics and diminishing benefits

- **SS_REF to SS_B9:** one additional battery module adds **USD 146.45/year** of annualized equipment costs, saves **556.37 kWh/year** of grid imports (USD 161.35/year at 0.29 USD/kWh), and cuts DC curtailment **616.47 kWh/year**. Net modelled cost decreases by **USD 14.89/year**, while self-sufficiency improves **2.665 percentage points**. This is the first candidate for AC validation, not a final global optimum.
- **SS_B9 to SS_B10:** second additional module saves only **293.72 kWh/year** of imports, cuts curtailment **325.45 kWh/year**, and costs **USD 61.27/year more net**. The imported-electricity price needed to offset its extra annualized equipment cost is ~**USD 0.499/kWh**, given unchanged modelling assumptions. Retain as a higher-autarky option, not the lowest-cost choice.
- **MC_REF to MC_B9:** extra module saves **314.56 kWh/year** imports and **348.54 kWh/year** curtailment, at **USD 55.23/year** higher net cost. Retain as a moderate-investment trade-off.

At USD 0.29/kWh grid price, the break-even price for SS_REF to SS_B9 is approximately **USD 0.263/kWh**. However its USD 14.89 annual cost advantage is smaller than plausible unpriced equipment/BOS/loss variation, so the cost ranking should not be presented as economically robust or applicable to a utility quote.

**Cost-versus-import Pareto candidates within these eight tested choices:** MC_REF, MC_B9, SS_B9 and SS_B10. MC_P37 reduces curtailment but increases both cost and imports, so it remains a distinct curtailment trade-off rather than a preferred energy/economic alternative. SS_P41_KEEP20 is strictly inferior to MC_REF under this model: same annual imports/curtailment with an extra USD 698.36/year, reflecting the larger inverter rating. SS_P45 has lower DC curtailment than SS_REF but higher imports and cost.

## What PV curtailment diagnostics mean

During the six new optimal schedules, curtailment almost never coincides with battery charging **at its DC power limit**. For SS_B9, just **2 of 1,076** curtailed hours are at the 14.110 kW battery charge-power cap. **813** of those curtailed hours finish at the modelled operational SOC floor; no curtailed hours finish near the modelled upper storage bound. These are consequences of an all-year perfect-foresight cost-minimizing schedule, often choosing to use or recharge storage later. They do **not** imply a charge-power bottleneck or justify indiscriminately increasing battery power. They also do not demonstrate that no extra energy could ever be utilized by a causal controller. Check actual seasonal/daily energy and an operating policy before inferring practical storage dispatch.

The peak observed AC inverter delivery in SS_B9 is **5.33 kW**, far less than its selected 20 kVA AC equipment rating, but this alone does not justify replacing it with a 5–6 kVA inverter: the original model also requires a DC PV/input ratio <= 1.5 and a specified battery-port rating. With 49 × 435 W panels, 12 kVA would violate the assumed DC/AC input ratio. Inverter right-sizing and real manufacturer input-port limits require their own sourced hardware comparison.

## Immediate AC-validation gate

The lowest-cost meaningful new frontier improvement is **SS_B9**; the useful smaller-energy alternative is **MC_B9**. Validate both as *new dispatches* through the same A1 106039 balanced pandapower model, first under **PF 0.95 × feeder length 1.6**, before running nine full-year factors. Existing successful A1 106039 AC corrections are from **other hourly schedules** and must not be reused as a proof of success.

The included `validate_frontier_ac.py` does exactly that. It checks the locally stored new energy manifests against the signed original v6.2 source, PV source and exact 11-house demand. It runs the full year with identical source `v6.solve_ac_hour`, head-inverter placement and daylight Q=.25/ nighttime Q off, writes per-case signed AC CSV/JSON to a separate output folder, records violations explicitly and does not overwrite existing results. Its first `--mode stress` run covers two new candidates × 8,760 hours = **17,520 AC hourly evaluations**. Once independently verified, `--mode all-nine` expands those two candidates to all nine PF/length factors with checkpoint reuse; do not infer success if new overloads/undervoltages appear.

The other four new designs remain energy-only. Follow-up after new AC evaluation: bounded SOC-aware redispatch for any residual hours (checking donor and target hours, annual SOC and current limits), then prioritize a **combined 45-panel/9-battery** test (SS_P45_B9) and realistic inverter/installation cost sensitivity. Do not run the full original 6,840-case MILP again.

## Other workstreams

The original signed 432 annual AC cases after corrected dispatch: **376 pass, 56 fail**. The explicitly hypothetical five-edge A0 94022 overlay: **408 pass, 24 fail**, the latter all the **proposed A0 92395 MST** configurations. This does not imply actual EPM cables fail. Study B should investigate STAR vs MST physical cable specification, routing and cost as a distinct follow-up. For A0 vs A1, do not name a clear annual-cost winner until actual interconnection/upgrade CAPEX, modelled electrical-loss changes and like-for-like household/hardware bases are included.

**No GitLab changes, no numerical PyPSA or pandapower runs were performed for this independent review.**
