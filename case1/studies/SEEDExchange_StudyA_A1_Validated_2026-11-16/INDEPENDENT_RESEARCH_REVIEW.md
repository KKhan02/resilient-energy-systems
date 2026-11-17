# SEEDExchange Study A: independent A1 AC-aware redispatch validation

**Date:** 16 November 2026  
**Scope:** `StudyA_A1_Mapped_Redispatch_Trial_v1.zip`, eight annual A1 schedules, 19 discharge shifts, all nine PF/service-length configurations per schedule.  
**Method:** inspect and reconcile uploaded results and candidate schedule files against the preceding independently audited 432-case Study A annual AC table. Original 2025 full-year pandapower network solver was not rerun in this environment. The local source/AC signatures and changed-hour recomputations are part of the uploaded runner receipt, not independently reproduced here.

## 1. Audit decision

**PASS for the bounded 2025 A1 research trial, subject to the underlying conditional network model.**

- Archive integrity: CRC and all eight candidate SHA-256 hashes match the uploaded manifest.
- 19 adopted schedule shifts across eight equipment/dispatch combinations; no unresolved events.
- Each of eight candidate dispatch series has exactly 8,760 ordered, unique 2025 hourly timestamps.
- All schedules satisfy the DC battery SOC recurrence, AC demand balance and PV accounting at recorded floating-point precision; no grid export or unserved load.
- PV curtailed and imported energy, minimum/maximum SOC and year-end SOC are unchanged from each candidate's recorded original source values.
- 72/72 PF/length full-year AC reuse comparisons report zero violation-hours. All 342 changed-hour PF/length snapshots independently recomputed by the Windows trial runner report converged and passed the AC thresholds.
- All 72 original violation-hour counts match the preserved independent 432-case table for the exact transformer, hardware tier, topology, dispatch and PF/length dimensions. In particular, **34** of these 72 rows previously had violations; the other 38 were already passing and remain passing. Summed original violated territory-hours across 72 sensitivity rows = **49**.
- The earlier **18** A1 106039 optimized-dispatch sensitivity runs were also validated as passing by the separate trial. These two trials operate on disjoint source schedule/dispatch identities.

## 2. Reconciled 432-scenario portfolio status

| State | Passing scenario runs | Failing scenario runs |
|---|---:|---:|
| Original 432 audited annual AC cases | 288 | 144 |
| After the prior A1 106039 optimized correction | 306 | 126 |
| **After this 19-event A1 trial** | **340** | **92** |

All **216 A1** annual sensitivity cases pass under the specified 2025 model and nine PF/length settings. All remaining **92** failing cases are A0, corresponding to **12** distinct hardware/dispatch/topology groups:

- A0 106039 existing mapped LV: 36 PF/length cases across four reference designs/dispatch combinations.
- A0 94022 existing mapped LV: 32 PF/length cases across four combinations.
- A0 92395 proposed MST: 24 PF/length cases across four combinations, retaining the unconfirmed-network limitation. Proposed STAR is already passing in the original model.

These scenario counts must not be described as independent outage hours or unique time instants. A1/A0 changes household allocation but does not change total 34-home annual demand.

## 3. Evidence of physical schedule consistency

At each accepted shift, earlier-day DC discharge was withheld and used at the evening target hour. The runner checked original signed AC at both modified hours, then solved changed feeder AC at all nine PF/length factors. All unchanged hours in each year's 8,760-hour annual AC record are inherited from the unchanged signed source results. That is valid for this snapshot-by-snapshot, memoryless balanced-AC replay, not a substitute for dynamic or three-phase voltage/protection validation.

All eight uploaded annual candidate files pass independent battery SOC and hourly demand-balance reconstruction with numeric errors near 1e-10, using one-way battery efficiency sqrt(0.95). No claim of optimality is made: these are greedy fixed-hardware schedule changes, not new PyPSA MILP solutions, and they preserve the historical synthetic demand, investment and curtailment data.

### Low-margin result

At 94022 A1 minimum-cost **causal** dispatch, 25 March 2025 20:00, PF 0.95 and service length x1.6, the changed-hour minimum voltage is **0.9500613354 pu**. This is only **0.0000613354 pu above the 0.95 pu research threshold**. It passes the discrete tested scenarios, but the margin is too small to claim robust field feasibility under uncertainties in household phase, conductor, EPM service association or solar/load realizations. No probabilistic reliability or voltage quality certification follows.

### Energy and cost boundary

The 19 fixed-discharge transfers do **not** reduce annual DC curtailment or imports. They conserve the adopted source's total storage discharge and end-of-year SOC, so do not claim additional PV utilization, lower annual cost, or outage backup. Feeder AC losses were not reintegrated into the annual energy objective.

## 4. Walkthrough figure revisions

- `P1_updated_A0_A1_gross_PVBESS_ACaware` now explicitly shows gross demand versus original PV+BESS versus A1 corrected. At PF0.98, length x1.0, using optimized dispatch and 92395 proposed STAR: A0 gross 110 / minimum-cost15 / higher SS3 annual summed territory-hours; A1 gross25 / original minimum-cost2 / original higher SS1 / both corrected 0.
- `P2_updated_A0_A1_ACaware_robustness` shows the matched PF x service-length heatmap for A0 higher SS, A1 higher SS original, and A1 higher SS corrected (all zero). For PF0.95/length x1.6: A0 higher SS 16; A1 original 2; A1 corrected 0.

The original Stage12/13 plots and raw evidence should remain in the project as dated snapshots. Add these as **new progress figures** rather than erasing historical figures or overwriting curated provenance. The project walkthrough aims to tell the entire research progression, not only professor slides.

## 5. Next engineering experiment

A0 maps to 156 distinct design-hour events across eight annual schedules, corresponding to 109 schedule-specific day blocks. **43 of those blocks contain two or three event hours**, so a naïve independent discharge correction can exhaust the same earlier-hour energy several times or break previous corrections.

A separate conservative A0 pilot has been prepared for **106039 only**: 44 events over 33 design/dispatch day blocks, 11 multi-event blocks. It verifies signed sources and both source/target AC for every accepted shift, tests all nine PF/length combinations, and rechecks all changed timestamps in each corrected annual schedule. It is an exploratory sequential test that may leave failures unresolved. If it does, proceed to genuine daily/annual SOC-constrained AC-aware optimization rather than forcing a pass.

For **94022 A0**, 112 events over 76 blocks, 32 multi-event blocks, represent a larger stage. For **92395 MST**, conductor sizing, transformer/siting, and physically viable route design belong in Study B.

## 6. Provenance and repository policy

Source archive: `StudyA_A1_Mapped_Redispatch_Trial_v1.zip`, SHA-256 recorded in `INDEPENDENT_QA.json`. The pre-existing original 432-case review and prior 106039 18-row trial are used only for read-only reconciliation. New files here are derived overlays and figure proposals; signed original numeric results are untouched. **Do not push any changes to GitLab without explicit user approval**, local repository diff inspection, source privacy review, and completed relevant evidence checks.
