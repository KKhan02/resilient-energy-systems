# Study A1 106039 | Full 12-design hardware frontier review

**18 November 2026, source-grounded.** Research branch `sync/seedexchange-local-2026-11-17`, user result commit `8e180647`. Full frontier receipt: `COMPLETE`; four new 8,760-hour fixed-hardware PyPSA solves, six verified reused pilot solves, zero unresolved. Two signed reference designs are read-only. Total **12 distinct case IDs**, consisting of two references and ten candidate design IDs. The `SS_B9_POWER16` higher-power scenario shares annual energy/cost metrics with `SS_B9` at reported precision, but has a different upper DC battery-power limit and unpriced hardware implications.

**Exact source fingerprints:**
- `StudyA_A1_106039_Utilization_v1/FRONTIER_RECEIPT_FULL.json`, canonical GitLab SHA-256 `a23e6225790585d5145d40f9e012505c2a67cf27df8347326a34b5291ddbfa8c`
- `StudyA_A1_106039_Utilization_v1/FRONTIER_ANNUAL_SUMMARY_FULL.csv`, canonical GitLab SHA-256 `743a0de8721e6a3decd35ed9f22c2dd798a1b6a658b0e617315a474317bf7ebd`.
- `StudyA_A1_106039_B9_Loss_Audit_Local_v2/AUDIT_MANIFEST.json`, canonical GitLab SHA-256 `a208f81e539e0552c83058d84fa06839599b668bc11976b638507b64b3be4f61`. 18/18 paired factor comparisons, 36 design-factor records; 9 direct local historical source summaries, 9 independently indexed GitLab source summaries.
- Source-year 2025, 8,760 hours, the *same* A1 106039 eleven-house cohort, 20,878 kWh gross demand. PV module 435 Wp, battery module 5.12 kWh nameplate, zero export and ENS, physical minimum SOC 20%; unchanged USD model parameters, unverified feeder/hardware installation prices.

## Full frontier economics and solar utilization

| Design | PV panels | BESS modules | Import, kWh/yr | DC PV curtailment, kWh/yr | Self-sufficiency | Modelled annual cost, USD/yr |
|---|---:|---:|---:|---:|---:|---:|
| MC_REF | 41 | 8 | 3107.49 | 2443.60 | 85.116% | 4416.47 |
| MC_B9 | 41 | 9 | 2792.93 | 2095.07 | 86.623% | 4471.70 |
| MC_B10 | 41 | 10 | 2646.99 | 1933.36 | 87.322% | 4575.82 |
| MC_P37 | 37 | 8 | 4027.76 | 1342.74 | 80.708% | 4556.89 |
| MC_P33 | 33 | 8 | 5227.09 | 549.29 | 74.964% | 4778.25 |
| SS_REF | 49 | 8 | 2034.60 | 5492.23 | 90.255% | 5056.59 |
| SS_B9 | 49 | 9 | 1478.23 | 4875.76 | 92.920% | 5041.70 |
| SS_B10 | 49 | 10 | 1184.51 | 4550.31 | 94.327% | 5102.97 |
| SS_B9_POWER16 | 49 | 9 | 1478.23 | 4875.76 | 92.920% | 5041.70 |
| SS_P45 | 45 | 8 | 2483.86 | 3871.80 | 88.103% | 5060.43 |
| SS_P45_B9 | 45 | 9 | 2011.57 | 3348.49 | 90.365% | 5069.91 |
| SS_P41_KEEP20 | 41 | 8 | 3107.49 | 2443.60 | 85.116% | 5114.83 |

The **cost/import-only 2-D Pareto frontier** contains `MC_REF`, `MC_B9`, `MC_B10`, `SS_B9`, `SS_B10`, plus the co-located output `SS_B9_POWER16` if distinct parameter sets are counted separately. Equal outcome does **not** establish a better battery-power design, since greater DC port capacity is unpriced in the original model.

`SS_P45_B9` is dominated by `SS_B9` in annual equipment-plus-import cost and grid imports but has 1527.27 kWh/year less curtailed DC PV. Fewer PV panels also yield 2112.90 kWh/year less available solar energy, so lower absolute curtailment alone is not evidence of better delivered solar output or economic performance. If curtailed PV energy is included as an independent third objective, this design remains relevant for tradeoff sensitivity.

`MC_P33` reduces curtailment by removing eight panels relative to `MC_REF`; it increases both imported grid energy and the modelled annual cost. It does not improve the two-objective economic frontier. If site size/BOS, thermal constraints or curtailment become independent constraints, examine it separately rather than claiming it is categorically worse.

`MC_B10` vs `MC_B9`: 145.94 kWh/year less grid import for USD 104.13/year higher model cost. `SS_B10` vs `SS_B9`: 293.72 kWh/year less grid import for USD 61.27/year higher model cost.

## AC validation priority

The **already verified** eight-module reference corrections and nine-module `SS_B9`/`MC_B9` corrections pass their own 18 annual modelled AC cases each (nine PF/length factors per two-design family), with a narrow modelled transformer margin, but **their dispatch adjustments do not carry over** to the other candidate hardware schedules.

Prepare a new, source-checked AC stress-run for:

1. `SS_P45_B9`, 45 panels, 9 modules, 20 kVA, to quantify whether lower PV curtailment and different energy dispatch remain electrically feasible.
2. `MC_B10`, 41 panels, 10 modules, 12 kVA, as the newly non-dominated cost/import candidate.
3. `SS_B10`, 49 panels, 10 modules, 20 kVA, to complete the high-self-sufficiency margin.

Run PF=0.95 and LV length factor=1.6 first using the original `validate_frontier_ac.py`. The AC output should retain failing-hour records even if not feasible. Do not run the other eight sensitivity factors before reviewing stress events and, if justified, a source-verified SOC-neutral candidate repair. `SS_B9_POWER16` may be set aside until a full 8,760-hour AC-injection equivalence and DC-power hardware-capability/cost check is available. No additional AC solve is needed merely because an unpriced DC power parameter changed while the full injection schedule and inverter rating remain equal.

**Conditionality:** Transformer 106039 is modelled at 5 kVA but unverified in EPM/field. Household assignment, actual transformer nameplate, phase balance, cable routing and impedances, BOS, tariffs, replacement and operating controller causality remain uncertain. This is research modelling, not utility approval or guaranteed field hardware sizing.

**Historical conservation:** No rerun of 6,840 investment optimizations. Study A original 376/432 passing annual AC portfolios remain a different denominator; hypothetical five-edge conductor-resistance overlay 408/432 remains explicitly conditional.
