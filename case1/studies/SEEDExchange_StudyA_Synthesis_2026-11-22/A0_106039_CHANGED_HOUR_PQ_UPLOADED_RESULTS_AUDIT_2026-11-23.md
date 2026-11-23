# A0 106039 source Q proof | uploaded full-year changed-hour response audit

**Independent saved-results review:** 23 November 2026, after commits `2e225de8` and `aeb22c8a`. **Method:** GitLab source-file and manifest validation. No new AC solver or optimization run by the reviewer.

## Local uploaded receipts and signatures

- Four-family source input gate: `StudyA_Matched16_FourFamily_InputGate_v1`, status `FOUR_FAMILY_SOURCE_AND_SAVED_SHIFT_INPUT_AUDIT`, four original matched 2025 AC equipment/source families, 35,040 archived source-case hours, zero solved AC power flows, zero corrected source reuse certified.
- A0 106039 min-cost optimized P/Q daylight pilot: `StudyA_A0_106039_ChangedHour_PQ_Audit_v1`, status `A0_CHANGED_HOUR_PQ_REPLAY_PASS`, two altered solar-daylight-capable hourly positions × nine PF/length factors × original/corrected, total **36** AC solver records, zero discrepancies.
- A0 106039 min-cost optimized P/Q complete changed-hour audit: `StudyA_A0_106039_ChangedHour_PQ_Audit_v2`, same `PASS` status, **39** modified hourly positions × nine factors × original/corrected, total **702** recorded AC solutions, zero discrepancies.

All three local receipt manifests cryptographically match their respective uploaded GitLab CSVs after reconstructing the original **Windows CRLF** line endings from GitLab-normalized LF:

| Receipt | Original Windows/manifest SHA-256 | Git-normalized LF SHA-256 |
|---|---|---|
| Four-family gate | `771f523dfc266cd22def4c5eea7af01f2799630dc7ce74bbc7f509e82f875960` | `77280ef4c0b36ea1f09ed8f5a18ba39c36f2e5713339b6aa6e495b5eb21b9a18` |
| Daylight 36-call | `189b12da86a324c4a892ad0f16104d5751d0c035d5732ea4e32b5a9b0fe7d208` | `687ba12f08de1d0c4e64cfac9be641855879bd29946b4b38ba2f80550bc7a7d0` |
| Full 702-call | `bc1fec7944e0b9b412b4209d99622f06c2250ab67ed33e065300c0427961c120` | `120a76eab7c6c13ceff0e228281f7ac7b259c54bb1aece094e38bfc4bfe4c46e` |

The 702-row CSV was independently parsed: **351 original** baseline and **351 corrected** AC responses, across **39** distinct changed hours and **nine** approved PF/service-length settings. Each comparison row reports `comparison_pass=True`, `status=CONVERGED`. All corrected rows report `ac_feasible=True`. The original rows include 103 *factor-hour* infeasibility records; these are stress-factor repeats, not 103 unique 2025 hours. At the reference PF .98/length x1.0, the original A0 optimized 106039 source had 10 failed distinct annual hours, all included in these 39 changed hours.

## P/Q and electrical findings

- All **351 corrected** power-flow records report **zero selected reactive power** (`q_selected_kvar=0`). This closes the *saved model* Q logging gap, including the 15 November and 27 November 2025 daytime-capable changed hours. Both daytime points report `q_controller_status=AC_FEASIBLE_Q`, so Q=0 is a result of the modeled controller choice, not the absence of daytime Q control.
- The corrected modelled network's **minimum voltage** across the 351 changed factor-hour points is **0.9500077895224552 pu**, a margin of only `0.0000077895224552 pu` above the project's 0.95 pu research threshold.
- The corresponding **maximum modeled transformer loading** is **99.74373801004316%**, just `0.25626198995684 percentage points` below the assumed 100% limit.
- Maximum saved-versus-new compact corrected result difference: transformer loading about `3.84e-13 percentage points`, minimum voltage exactly equal in stored values. These checks concern the **same frozen AC solver and assumed GIS model**, not an independent physical feeder measurement.

## Regression test correction

A subsequent user-local unit-test run returned **8 tests passed and 1 test error**. The test `test_annual_source_comparison` created a simulated `CONVERGED` AC dictionary without `ac_feasible`; the comparison function requires it and the real v6 solver provides it. The appropriate fix is to add `"ac_feasible": True` to that synthetic fixture. No production code, solver, source integrity, AC output, numerical tolerance or saved results should be changed. The repaired nine-test suite **still requires a user-local run** before its tests can be called passing.

## Scientific conclusion and next work

The uploaded v2 evidence independently reproduces the **39 changed-hour fixed-schedule AC model responses** and their original annual-source baselines across all nine factor scenarios. Combined with saved untouched-hour original AC, this supports the earlier **provisional model** zero-violation SOC-correction conclusion for the A0 106039 optimized minimum-cost case. It does not certify physical EPM LV customer connections, the transformer actual nameplate/rating, phase balancing, unbalanced flows, inverter control and reactive Q permission, field resilience or economic optimality. The extremely small modeled minimum-voltage margin makes the result fragile to unmodeled uncertainty. Do not describe a modeled 100% screening boundary as real-world engineering reserve.

The next workstream is targeted materiality and safety screening for the **remaining 12 of the 16 reciprocal hardware families without an exact original 2025 source-family match**. Existing A0 94022 problem evidence and the 113699 cohort differences should guide which new AC calculations merit running. There is no rationale to automatically run 12 × nine × 8,760 new AC cases before resolving actual EPM GIS/phase/rating evidence.
