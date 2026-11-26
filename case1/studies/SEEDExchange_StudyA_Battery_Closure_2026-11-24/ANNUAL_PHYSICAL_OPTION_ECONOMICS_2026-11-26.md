# 94022 physical option and battery economics | 26 November 2026

## Scope and source
Trace-derived remote report job18386901176 (pipeline3117458310, execution65178970) and signed `StudyA_94022_FullNight_Reserve_v1/RUN_MANIFEST.json`. All 12 reference/stress records matched corrected-energy SHA identities exactly, 8760 converged each, sample error zero. No new AC/LP. Full remote binary CSV/figure bytes not independently retrieved. All calculated costs are conditional on the historical model, not current verified Colombian tariffs.

## Matched economics
For each case, add `0.29 USD/kWh * annual AC network losses` to saved annual equipment+grid import cost as the existing all-losses-purchased sensitivity. No reoptimization of imports or losses. 25 years and 6% discount from `pypsa_joint_optimization_v1/model.py` give CRF 0.0782267182. Loss-only present value = annual modeled saving / CRF, assuming repeated annual savings, no escalation, no differential O&M or replacements. This is a maximum incremental upfront spend attributable solely to modeled loss savings under those assumptions, not an installed cable estimate. Middle and R050 combine different inverter locations and conductor resistance; the difference cannot isolate the causal contribution of either.

| PF / length | modules | middle annual cost incl. losses USD | R050 annual cost incl. losses USD before physical cost | loss saving kWh/a | saving USD/a | 25y PV USD | middle / R050 strict failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.98 / 1 | 5 | 4305.97 | 4292.01 | 48.13 | 13.96 | 178.44 | 0 / 0 |
| 0.98 / 1 | 6 | 4344.14 | 4330.14 | 48.27 | 14.00 | 178.93 | 0 / 0 |
| 0.98 / 1 | 7 | 4429.95 | 4415.84 | 48.65 | 14.11 | 180.34 | 0 / 0 |
| 0.95 / 1.6 | 5 | 4363.99 | 4305.79 | 200.71 | 58.21 | 744.08 | 76 / 0 |
| 0.95 / 1.6 | 6 | 4402.92 | 4343.92 | 203.47 | 59.01 | 754.31 | 78 / 0 |
| 0.95 / 1.6 | 7 | 4489.29 | 4429.61 | 205.78 | 59.68 | 762.86 | 76 / 0 |

Five modules minimize modeled annual cost among these three designs at both placements and factors before physical costs; six and seven improve energy autonomy and curtailment, but neither removes middle-placement stress violations on the frozen dispatch. On R050 stress, B6 costs $38.13/a extra vs B5; B7 costs $85.70/a extra vs B6. The import/spill reductions (371.34/411.46 and 208.27/230.77 kWh/a respectively) are separate AC import and DC curtailed quantities. No final equipment choice.

R050 modifies five model edges, nominal lengths 826.648086 m total (641.819516 m two assumed services and 184.828570 m three GIS pieces). It is not a surveyed route, installed cable quantity, selected conductor or certified upgrade. Both options have unpriced siting, connection, protection and construction costs. Loss-only value is modest ($178–180 reference; $744–763 stress). Do not compare a stress-infeasible schedule as an equivalent feasible investment; voltage compliance is the principal value of the hypothetical improvement. No probability weight assigned to stress.

## Next decision gate
Middle placement had tested feasible ceiling points at all nine prior adverse events, but frozen annual schedules fail 76/78/76 night hours. Before recommending an unpriced network modification, use the already approved stateless AC method to screen all 4353 night hours at zero and zero-export active-power ceiling on middle placement, PF .95 length1.6, with signed matched samples and endpoint regressions. Screen bounded intermediate P for endpoint failures, preserve unresolved cases. Only if a credible common support corridor exists should a source-matched SOC-constrained reserve LP be considered; full annual AC replay is required for any new schedule. No night Q, no new conductor, tariff, inverter or battery assumptions. No claims of global feasible interval or causal controller from static screening. Do not rerun the completed R050 case or close Study A prematurely.
