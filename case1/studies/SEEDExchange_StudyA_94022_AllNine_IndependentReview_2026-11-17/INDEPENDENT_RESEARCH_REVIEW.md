# SEEDExchange Study A: five-branch A0 94022 all-nine annual network validation

**Independent review date:** 2026-11-17  
**Supplied source:** `StudyA_A0_94022_Annual_five_allnine_Results_v1.zip`  
**SHA-256 of original source ZIP:** `28712658b465d55d6879f8118acf5ebda936748d5ed7f11175ec12649ddfb229`  
**Research status:** Verified **conditional annual balanced-AC feasibility**. Physical conductor construction, customer connections, real costs and distribution-operator approval unverified.

## What was checked

- All 73 ZIP members checked, including 36 complete hourly CSVs, 36 corresponding per-case JSON summaries and the cumulative receipt. No corrupt members.
- Exactly four hardware/dispatch alternatives (minimum-cost and higher self-sufficiency, each optimized and causal), three load power factors (0.95, 0.98, 1.00) and three service-length multipliers (1.0, 1.3, 1.6). No duplicates or omissions.
- Every annual CSV has **8,760 consecutive, unique 2025 hourly timestamps**. All **315,360** power-flow status rows converged and independently recalculate as compliant with the research 0.95–1.05 pu household-voltage and 100% transformer/line-loading screens.
- All 36 CSV hashes match the corresponding summary. Per-case minimum/maximum, annual loss sums and violation counts match both the detailed summaries and cumulative receipt. All reported nine selected-hour numerical controls are smaller than the tolerance.
- **Four pilot annual CSVs and summaries match byte for byte** against `StudyA_A0_94022_Annual_five_pilot_Results_v1.zip`. This confirms correct reuse of earlier output, not merely identical rounded metrics.
- All audit checks passed, with no known discrepancies. This independent check did **not** run pandapower or reproduce physical circuit equations from scratch. It verified the locally executed results and their internal/source consistency.

## Verified AC outcomes

| Measure | Across 36 all-nine annual runs |
|---|---:|
| Completed/passing runs | 36/36 |
| Converged annual case-hours | 315,360/315,360 |
| AC violating case-hours | **0** |
| Lowest household voltage | **0.953223659 pu** |
| Highest household voltage | 0.999639972 pu |
| Highest modelled transformer loading | **97.395823%** |
| Highest line loading | 11.887281% |
| Worst minimum-voltage margin against 0.95 pu | **0.003223659 pu** |

The corrected five-branch network was tested with the same four existing annual battery schedules. It does not reoptimize PV/BESS investment or annual dispatch. It has a narrow voltage margin, particularly given uncertain actual conductors, phases, service attachments and transformer impedances.

Annual total modelled AC (line plus transformer) losses across the nine stress factors range from roughly **408.18 to 468.87 kWh** in the minimum-cost cases, and **391.70 to 452.12 kWh** in the higher-self-sufficiency cases. These losses are **not integrated into the original energy-model operating cost** and must be handled carefully in future economic comparisons.

## Exactly what the five-branch variant means

| Model edge | Source | Modelled length (m) | Treatment |
|---|---|---:|---|
| 007 | Assumed service to H01 | 326.553 | Resistance ×0.5 |
| 004 | Assumed service to H06 | 315.267 | Resistance ×0.5 |
| 014 | EPM GIS FID 47053086 split edge | 83.173 | Resistance ×0.5 |
| 011 | EPM GIS FID 47053070 split edge | 67.000 | Resistance ×0.5 |
| 016 | EPM GIS FID 47053100 split edge | 34.656 | Resistance ×0.5 |
| **Total** | Three GIS-derived model edges, two assumed service edges | **826.648** | **Not a physical quotation** |

The GIS branches are split model representations of mapped source line sections, not necessarily independent installable cable runs. Both long service connections are provisional. A reduction in line resistance alone does not establish the correct alternative conductor's reactance, ampacity, protection, voltage unbalance, phase/neutral arrangements, installation feasibility or price. This is a **conditional research network** only.

## Correct interpretation of the 432-case research portfolio

**Preserved original-network signed/validated evidence, after battery redispatch:** 376 passing, 56 failing annual sensitivity cases. The remaining 56 failures consist of 32 A0 94022 original-network cases and 24 A0 92395 proposed MST cases.

**Alternative-network decision overlay**, replacing the original-network A0 94022 rows with this independently validated five-branch *hypothetical* network: **408 passing, 24 failing** out of 432. The five-branch network changes 32 originally failing sensitivity cases to passing; the other four of its 36 cases had already passed. This is not an update or overwrite of the original signed 432 campaign. Its mixed-network comparison must be explicitly labelled as conditional.

At the A0 94022 location, the previously validated sequential battery shifts reduced residual violation case-hours (summed across 36 annual factor/dispatch cases) from 310 to **126**. The five-branch network eliminates those 126 remaining *modelled* case-hours; this is a different intervention and the original network history stays preserved. The single Study A baseline 34-home comparison must not confuse the number of violation case-hours with annual electrical demand.

The remaining 24 failing annual scenarios are the **92395 proposed MST topology**. Its proposed STAR alternative passed the modelled scenarios earlier but uses more assumed cable length. The actual 92395 GIS LV backbone, service routing, connection status, conductor costs and technical design remain unverified. Compare STAR and MST as **alternatives in Study B**, rather than reporting the MST as an established real-world network failure.

## Decision gates: no more speculative network sweeps by default

1. **Verify physical feasibility** at A0 94022. Obtain the actual service points and phases for H01/H06, conductor material/size, EPM line lengths, transformer/protection details and quotations. Check whether 826.648m of simulated model edges corresponds to any practical field works. A 50% resistance assumption is not a cable specification.
2. **Compare geographic reassignment and upgrading A0 at a common study boundary.** A0 and A1 assign different numbers of houses to individual transformers. Compare investment plus AC losses and energy economics **over the same 34 households**, not cost per transformer without cohort normalization. Price site works, service cables, metering, protection, inverter interconnection and operating losses. Preserve the original USD source costs until currency conversion is documented.
3. **Move the 92395 STAR/MST problem to Study B.** Optimize route/cable/inverter location and annual AC voltage under physically plausible scenarios, then compare construction costs; do not assume the GIS absence means no existing wires.
4. **Resume the PV/BESS utilization study.** The 22 validated energy designs, 44 dispatch curtailment diagnostics and their original dispatch records provide the starting point. Size batteries, PV and inverter rating jointly or in targeted increments, while reporting energy curtailment, grid import, battery utilization, annualized cost and the already established AC constraints. Historical 6,840 MILPs remain preserved; new design runs are versioned research experiments.
5. **Later test resilience**, with explicit outage/service definitions and islanding constraints. Annual autarky is not outage resilience.

## Source files in this review package

- `INDEPENDENT_QA.json`: full audit and case counts.
- `FIVE_BRANCH_36_ANNUAL_INDEPENDENT_AC_AUDIT.csv`: each complete case, extrema, dates, hashes, losses and pilot reuse flag.
- `PORTFOLIO_432_ORIGINAL_PLUS_CONDITIONAL_FIVE_EDGE_OVERLAY.csv`: original signed/validated status preserved alongside a clearly separate conditional variant.
- `A0_94022_SEQUENCED_VS_FIVE_EDGE_BY_NINE_FACTORS.csv`: factor-specific annual violation counts, before/after hypothetical retrofit.
- `FIVE_MODEL_EDGES_PHYSICAL_VERIFICATION_REGISTER.csv`: GIS vs service evidence gap and required field data.
- `PV_BESS_22_DESIGN_UTILIZATION_PRIORITIES.csv`: existing verified alternatives ranked by curtailment, not an added-storage optimization.
- `A0_94022_annual_violation_recovery_by_stress.png` and `.svg`: candidate figure for the walkthrough, with explicit hypothetical label.
- `audit_uploaded_allnine.py`, `build_decision_evidence.py`: code to regenerate independent analysis from the already available source ZIPs. No solver invoked.

**No GitLab writes and no original saved numerical cases modified.**
