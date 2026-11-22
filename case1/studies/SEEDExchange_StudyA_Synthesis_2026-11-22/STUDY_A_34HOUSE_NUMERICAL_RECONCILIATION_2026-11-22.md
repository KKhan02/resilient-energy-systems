# Study A | independent 34-house energy/AC evidence reconciliation

**Date:** 22 November 2026. **Analysis:** read-only numerical audit of saved GitLab CSVs. **No PyPSA or pandapower solver execution.**

## 1. Checks performed directly from immutable source files

- Read all **432 distinct** source 2025 annual-AC overlay rows, plus the derived 72-row original/proposed A0/A1 five-territory scenario-factor roster.
- For each of all **72** 34-home case selections, resolved exactly **five unique source AC cases** by their *full case ID*, 360 case references across 72 source combinations, with correct scenario (except the explicitly shared A0 92395 STAR), hardware tier, optimized/causal dispatcher, PF and cable length multiplier, full 8,760-hour source convergence and 34-home sum. Checked 92395 was the common proposed STAR, not an assumed EPM mapped feeder.
- Recomputed original AC violation territory-hour totals from each case's `infeasible_hours`, corrected original-network totals from `adjusted_bad_hours`, and optional alternative-network totals by substituting **only** A0 94022's stored `conditional_five_edge_violation_hours`. **72/72 three-way aggregates reproduced exactly.**
- Source corrected AC: **40/72** derived whole-population factor selections have zero modelled main-band violation territory-hours on the original proxy network, comprising **36 A1** and **4 A0**. All **32** still-infeasible A0 selections' residual violations occur **only in 94022**, not in other selected EPM territory proxies. All **72/72** hypothetical five-edge overlay combinations have zero saved model violations, but that overlay depends on the unbuilt A0 94022 resistance-change scenario plus proposed 92395 STAR and is not a physically demonstrated feasible network.
- Read **four** original architecture-specific annual energy aggregates. Independently cross-matched each numeric capacity, demand, modelled annual imports, self-sufficiency, DC curtailment, and equipment-plus-import cost to the corresponding same-origin/same-load member of the independently audited **eight** 34-home matched-hardware portfolio rows. All 32 comparisons within 1e-6 source units.
- Independently recomputed all **four** matched-hardware A1-minus-A0 contrasts from the eight underlying portfolio rows: original reported yearly cost, imports and curtailment differences agree within 1e-6. The match must **not** be mistaken for a common 34-house AC comparison.

This audit validates cross-file accounting and case selection, not 432 rerun power flows or actual distribution-system physics. All source inputs and outputs remain untouched.

## 2. Architecture-specific source-grid comparisons

Each count below is the **sum of violated territory-hours across five separate 8,760h source AC models**, not unique household outages. These are source-architecture-sized devices, not matched equipment across A0 and A1. The data reuse a hypothetical common 92395 STAR.

### PF 0.98, length factor 1.0, optimized dispatch

| Assignment | Equipment tier | Original network | After SOC-aware correction, original network | After hypothetical A0 94022 five-edge replacement |
|---|---|---:|---:|---:|
| A0 | min_cost | 15 | 4 | 0 |
| A0 | ss90 | 3 | 2 | 0 |
| A1 | min_cost | 2 | 0 | 0 |
| A1 | ss90 | 1 | 0 | 0 |

### PF 0.95, length factor 1.6, optimized dispatch

| Assignment | Equipment tier | Original network | After SOC-aware correction, original network | After hypothetical A0 94022 five-edge replacement |
|---|---|---:|---:|---:|
| A0 | min_cost | 62 | 9 | 0 |
| A0 | ss90 | 16 | 7 | 0 |
| A1 | min_cost | 9 | 0 | 0 |
| A1 | ss90 | 2 | 0 | 0 |

Across all 72 entries, use the committed `A0_A1_34H_AC_72_FACTOR_DISPATCH.csv` for each exact PF, length and dispatch variation. The reference and stress tables above are only two concise slices.

## 3. Hardware and curtailment in the community comparison

| Assignment | Tier | PV panels | BESS modules | Inverter kVA total | Grid imports kWh/year | DC curtailment kWh/year | Equipment + grid USD/year |
|---|---|---:|---:|---:|---:|---:|---:|
| A0 | min_cost | 126 | 23 | 37.0 | 11039.9 | 8756.7 | 13783.15 |
| A0 | ss90 | 146 | 29 | 47.0 | 5394.2 | 13098.0 | 14529.81 |
| A1 | min_cost | 122 | 23 | 36.0 | 11665.8 | 7330.8 | 13750.91 |
| A1 | ss90 | 146 | 28 | 48.6 | 5821.7 | 13571.7 | 14647.02 |

The higher-SS equipment tiers were simultaneously resized: they are not an isolated BESS marginal experiment. More installed PV and changes to batteries/inverter can drive more curtailment in absolute kWh, even if grid imports drop. These are 2025 planning-model costs, not quotations, and independent AC losses are not fed into the optimizer.

## 4. Incompatible-but-complementary evidence sets

**Source architecture AC status** comes from annual factor cases with *their own* hardware and SOC-redispatched schedules. **Matched-hardware 16-case status** controls PV/BESS/inverter quantities across A0/A1 target memberships, and its 34-home portfolios still have `AC_verified=False`. This is why the 72 original proxy selections' full-year corrected A1 pass does **not** resolve the later 113699 PF .95 sampled failures under the frozen hardware of a distinct test. These are separate equipment, charging and inverter-P source trajectories. Avoid incorrectly substituting schedules between them.

**Potential decision:** A1 is source-AC preferable to A0 before considering the hypothetical 94022 replacement in the architecture-specific portfolio, but there is no unambiguous energy-cost winner under frozen hardware. Moreover, real EPM service moves, phase distribution, 3/5kVA transformer nameplates, installed LV upgrade costs and 92395 feeder existence are unverified. Therefore do **not** publish a recommendation for a physically constructed A1 network from these comparisons alone.

## 5. Next executable gate before costly AC solving

Prepare a **read-only exact-source annual AC reuse and missing-case audit** for all 16 reciprocal frozen-hardware cases. For every target schedule, compare full 2025 timebase, source demand and PV availability, annual inverter active power, inverter rating, Q policy, customer-to-transformer assignment and network topology/phase assumptions with archived matching cases. A matching case can reuse a saved power flow only if **all electrical inputs** are identical at the hour and the previous AC source is signed. Do not infer AC source identity from equivalent annual cost, matching equipment counts or the source hardware name alone.

For mismatched hours/cases, classify source-supported feasible feeder scenarios and plan targeted bounded AC diagnostics, correcting power flow with chronological physical battery SOC. Only then choose the informative full 8,760-hour AC campaign, rather than blindly solving 16×9×8,760 hours. Reassess actual EPM phase/transformer/service records before any final physical recommendation. Preserve previously signed originals and both isolated experimental network hypotheses.

## Sources
- `case1/studies/SEEDExchange_StudyA_Matched_Cohort_2026-11-21/A0_A1_34H_AC_72_FACTOR_DISPATCH.csv` (72 selected sources)
- `case1/studies/SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17/PORTFOLIO_432_ORIGINAL_PLUS_CONDITIONAL_FIVE_EDGE_OVERLAY.csv` (432 annual AC source cases)
- `case1/studies/SEEDExchange_StudyA_Matched_Cohort_2026-11-21/A0_A1_34H_MATCHED_SOURCE_ENERGY.csv` (4 architecture source energy)
- `StudyA_A0_A1_MatchedHardware_Full_v1/MATCHED_34HOUSE_ENERGY_PORTFOLIOS.csv` (8 controlled source cases)
- `StudyA_A0_A1_MatchedHardware_Full_v1/MATCHED_A0_VS_A1_SAME_HARDWARE_PAIRS.csv` (4 controls)
- `case1/professor_walkthrough/14_PVBESS_Sizing_and_Utilization/01_34house_architecture_cost_import_curtailment.svg` (figure source from 4 original-architecture annual energy points)

