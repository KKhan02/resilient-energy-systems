# 20 November 2026 | Source equivalence audit for new hardware annual AC

**Status: A read-only comparison of existing GitLab source data, not a numerical AC validation.** The new `StudyA_A1_106039_NewHardware_Reserve_NineFactor_v1` case has been completed locally per user console receipt (`NINE_FACTOR_CHANGED_HOURS_PASS_ONLY`, 144 calls and 27 factor cases) but **has not yet been pushed to the GitLab branch at audit time**. Upload and independently audit its `SCREEN_MANIFEST.json`, all 144 AC rows, and figures before making annual claims.

## Research question

Can original 2025 balanced pandapower annual AC solutions for **MC_B9 and SS_B9** be reused exactly for separate fixed-hardware schedules **MC_B10, SS_B10, SS_P45_B9** where their complete per-hour electrical inputs match? This avoids automatically repeating 24 x 8,760 annual AC solves and preserves the existing signed evidence.

## Grounded solver equivalence

Reviewed `case1/studies/SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py`, `solve_ac_hour` lines 626–688 and `case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17/validate_frontier_ac.py`.

The solver applies the same independently verified 11-house load trace and per-factor PF / line geometry. It sets inverter `p_mw` from `inverter_ac_kw` with a fixed three-phase root scale. Under `pvbess` mode the hourly reactive control uses the original inverter kVA rating, AC inverter power, `q_ratio=.25`, a 9-point Q candidate search, and **whether** PV is available (`pv_dc_available_kw > 1e-9`), not the actual PV kW magnitude. The hour is initialized with a flat power flow; there is no carry-over of network electrical state between hours. Therefore reuse is justified **only for an individual hour** when all effective electrical inputs, model code, mapped network, PF, line length, Q-control settings and inverter rating are identical. Reuse of other hours is prohibited. The source AC results must carry valid original signatures and the new schedule must carry valid separate annual signatures.

MC_B10 and MC_B9 both use **12 kVA** inverter settings, whereas SS_B10, SS_P45_B9 and SS_B9 all use **20 kVA**. These are not physical field-installed inverter certifications.

## Source CSV equality audit

Compared the 2025 signed 8,760-hour `energy_hourly_2025.csv` columns `timestamp_lst`, `inverter_ac_kw` and the PV daylight-control Boolean for each new hardware design against its matching B9 reference. Comparisons used the exact recorded 10-decimal inverter AC values, **not a power tolerance**. No PV daylight-control Boolean mismatch was observed.

| New design | Signed reference | Exactly equal hour count | Distinct inverter hours | Reuse fraction |
|---|---|---:|---:|---:|
| MC_B10 | MC_B9 | 8601 | 159 | 98.1849% |
| SS_B10 | SS_B9 | 8493 | 267 | 96.9521% |
| SS_P45_B9 | SS_B9 | 8029 | 731 | 91.6553% |
| **Per-factor total** | | **25123** | **1157** | **95.5974%** |

All original B9 reference AC directories for 9 PF/line combinations are available in `StudyA_A1_106039_Frontier_AC_v1/`, and each must pass `frontier.check_saved` and its source provenance checks before use.

The **three new designs already have their own exact full-year PF=.95 / length=1.6 original AC source** in `StudyA_A1_106039_NewHardware_AC_Stress_v1/`. Therefore no new original-source solves are required for that factor.

For the other eight factors, a naive procedure would request `3 designs * 8 factors * 8760 = 210240` new per-hour AC solves. A verified exact-source-hour reuse scheme requires at most `8 * (159 + 267 + 731) = 9256` distinct original schedule AC solves across those missing cases, provided no extra source mismatch arises. This is **95.6% fewer original AC solves**; it is a planning estimate, not executed results. The changed-hour reserve candidates are independently tested in the user's 144-call nine-factor screen and must be source-hash matched when integrating annual corrected AC.

## Required annual-source-stitch implementation

1. First **upload and independently audit** the user-local new hardware nine-factor changed-hour screen. Require precisely 27 case-factor results, 144 phase/hour AC evaluations, all required source hashes, 0 changed-hour failures, and the explicit `may_claim_annual_ac_feasibility=False`.
2. Implement a read-only baseline-source gate. For each missing factor and candidate, validate original B9 annual AC file digest, 8,760 timestamps, signed B9 reference energy, household demand trace, inverter kVA equality, PV Q-enable state and exact 10-decimal P equality. If any comparison cannot be established, fail closed and solve that hour separately. Do **not** rely on the earlier numerical counts without rechecking current local source files.
3. Use the original v6.2 pandapower solver to evaluate only every unmatchable original candidate-hour. Retain original AC rows for matching hours. For the PF=.95/length=1.6 factor, preferentially use each new design's **own** complete original AC stress file rather than reconstructing it.
4. Verify that the reconstructed 8,760-hour baseline matches **all** of the original AC-source hour inputs and has no missing/duplicate timestamps. The resulting original annual AC is reconstructed from signed identical-source-hour records and newly computed mismatches, not a new complete 8,760-hour power-flow campaign.
5. Overlay corrected reserve-hour AC values from independently verified nine-factor results for the **same candidate, timestamp and PF/length factor**, with exact corrected inverter schedule identity. This creates 27 corrected original-plus-overlay 2025 annual AC cases. Recompute full-year 0.95–1.05 pu, transformer, line, strict 0.97/1.03 pu sensitivity, and losses; record source/recomputed hour counts, signed hashes and figure/CSV provenance.
6. Compare the final AC-feasible portfolios on annualized equipment + imports, curtailment, equivalent battery cycles, and clearly labelled conditional network loss charges. Do not transfer a B9 AC correction or an AC loss quantity to different hardware unless its AC input equivalence is separately shown.
7. Commit code/tests to the **sync branch only**; numerical work stays user-local. Stage and push only verified signed new results. Maintain rolling `PROJECT_HANDOVER_LIVE.md` after each substantive reply. Keep `main` unchanged.

## Caveats

The network is a **provisional balanced EPM 11-house A1 106039** representation with assumed 5 kVA transformer. It excludes actual service conductor details, phase imbalance, complete EPM customers, utility approvals and protection checks. The previously reported narrow worst-case 99.4318% transformer loading margin is an assumption-limited result. Do not use an energy-only match to imply real-world network equivalence outside the tested solver. A mismatched or missing source hash must block AC reuse rather than silently reusing another portfolio's results.
