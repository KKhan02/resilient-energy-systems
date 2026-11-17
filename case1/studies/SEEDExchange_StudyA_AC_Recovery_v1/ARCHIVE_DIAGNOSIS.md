# Study A PV+BESS annual portfolio: collection audit, 10 November 2026

## Coverage confirmed by uploaded compact archive

- 22/22 full-year signed energy cases, including six four-house equipment candidates.
- 22/22 full-year signed causal PV-first cases.
- 42/48 fully signed baseline 8760-hour AC replays. All 42 report 8,760 converged hours.
- Six additional AC folders each contain an 8,760-row `ac_hourly.csv` but **no `ac_summary.json`**. They cannot yet be considered verified.
- **No PF/length sensitivity AC runs were located** in the collected folder. The two receipts for energy/causal were complete; the single baseline AC receipt recorded 6 blocks and return code 2 caused the all-in-one CMD to stop before the 384-case stage.

## Incomplete annual AC cases

| Assignment | Transformer | Equipment | Dispatch | Existing hourly rows | Current status |
|---|---|---|---|---:|---|
| A0 | 106039 | archived minimum-cost reference | optimized | 8,760 | Missing summary, unverified CSV |
| A0 | 113699 | new four-house minimum-cost | optimized | 8,760 | Missing summary, unverified CSV |
| A0 | 113699 | archived minimum-cost reference | optimized | 8,760 | Missing summary, unverified CSV |
| A0 | 85398 | new four-house minimum-cost | optimized | 8,760 | Missing summary, unverified CSV |
| A1 | 106039 | archived minimum-cost reference | optimized | 8,760 | Missing summary, unverified CSV |
| A1 | 113699 | archived minimum-cost reference | optimized | 8,760 | Missing summary, unverified CSV |

The collector marks these as `HOURLY_HASH_MISMATCH` because the missing summary has no expected checksum. This is **not evidence of an actual byte mismatch**. The original exception before the summary was saved is not present in the uploaded receipts.

## Preliminary validated AC summary evidence

- 42 signed baseline AC cases are present.
- 367,920 signed converged hourly AC results.
- 11 of the signed AC cases have at least one modelled 0.95–1.05 pu / 100% violation.
- Cumulative AC-infeasible case-hours among these 42: 32. Not unique system-wide hours.
- These are summary-based interim observations only. Do not publish a full gross-vs-DER comparison until all 48 baseline cases and the 384 sensitivity cases are resolved.

## Recovery procedure

1. Extract `SEEDExchange_StudyA_AC_Recovery_v1.zip` to `case1/studies/`. It does not replace any original model or runner.
2. Run `studya_recover_ac_summaries.py` without `--repair` and review `StudyA_AC_Recovery_Check.json`. It verifies the 8,760-hour chronology, convergence, numeric data, recorded voltage/thermal flags, dispatch identity, input and source hashes, and source household groups.
3. Only if the check reports six `RECOVERABLE_CHECKED_NO_WRITE`, rerun with `--repair` and a new report name. This creates only the missing `ac_summary.json`, clearly marked `recovery_provenance` and then uses the original portfolio verifier to validate the restored signed cases. No AC numerical rerun.
4. If any case is rejected, do not force recovery. Preserve that folder and share the rejection report and corresponding raw `ac_hourly.csv` for diagnosis; determine if a true AC rerun is needed.
5. Re-run `run_all_2025_AC_baseline.cmd` to get a clean 48-case receipt; it skips already verified cases.
6. Run `run_all_2025_AC_sensitivities.cmd` for the 384 outstanding annual AC cases.
7. Collect a new ZIP with `python collect_studya_pvbess_results.py --repo-root . --out StudyA_PVBESS_Annual_Result_Summary_v2.zip`.

## Constraints

- No GitLab mutations, original optimization reruns or historical result deletions.
- No valid AC source result should be overwritten or fabricated.
- Reconstructed summaries are explicitly labelled as post-processing of preserved hourly data.
- The new recovery script has only synthetic regression tests in this environment; actual user CSVs were not present in the compact ZIP.
