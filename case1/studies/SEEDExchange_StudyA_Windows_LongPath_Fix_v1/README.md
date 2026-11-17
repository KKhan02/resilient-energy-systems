# Study A v1 Windows MAX_PATH correction and safeguarded AC recovery

## Confirmed from the reported traceback

The reported failing output directory is **244 characters**. The case's `ac_hourly.csv` path is **258 characters** and its `ac_summary.json` path is **260 characters**. On systems that still enforce the legacy Win32 MAX_PATH limit, the CSV can be written before the JSON fails, even after all 8,760 AC solves finish. **No AC divergence is established by this traceback.** The operating-system condition is strongly indicated by the exact boundary, but the Windows configuration was not independently read.

## What the patch does

The ZIP contains three *replacement* Python modules at their existing `case1/studies` relative paths:

1. `SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py`
   - Adds Windows extended-length filesystem handling (`\\\\?\\D:\\...`) for result-folder creation and both CSV/JSON writes. No changes to the electrical model, dispatch, selected cohorts, PF/length values, or the frozen v6.2 runner.
2. `SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1/run_annual_replays.py`
   - Uses the same long-path handling to verify and reuse existing finished 8,760-hour results.
3. `SEEDExchange_StudyA_AC_Recovery_v1/studya_recover_ac_summaries.py`
   - Uses the same long-path handling to validate existing hourly files and write missing summaries only with `--repair`. Existing case IDs, filenames and output directory locations are unchanged.

The original `SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py` and `input_manifest_v6_2.json` **MUST NOT** be changed. Do not rename existing output folders or clear them.

## Install and use in Miniforge Prompt or Anaconda Prompt

**If the 384-case sensitivity batch is still running**, stop it using `Ctrl+C` before copying Python files. Preserve all results, including incomplete case folders. Don't run the old code again.

Extract this ZIP into your repository's `case1\\studies\\` directory, preserving the three existing package folder names and replacing the named Python scripts. The ZIP contains those three replacement package folders plus `SEEDExchange_StudyA_Windows_LongPath_Fix_v1/` containing this README and the regression tests.

From your repository root, run regression tests for all existing components:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\tests" -v
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_AC_Recovery_v1\tests" -v
```

Run the patch-specific tests as well. On Windows, the test suite includes an actual long-filename write/read test:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Windows_LongPath_Fix_v1\tests" -v
```

On a non-Windows host that one filesystem test is skipped.

### 1. Read-only audit of complete and partial cases

```bat
python "case1\studies\SEEDExchange_StudyA_AC_Recovery_v1\studya_recover_ac_summaries.py" --repo-root . --scope full --report "StudyA_LongPath_Recovery_Check.json"
```

The report should list existing signed runs, recoverable missing-summary cases, cases not started and any cases that cannot be safely recovered. **Do not repair** if the report contains `NOT_RECOVERABLE_NEEDS_INSPECTION`, `EXISTING_SIGNED_OUTPUT_INCONSISTENT` or `SUMMARY_PRESENT_UNVERIFIED`; upload the report and the affected CSV for diagnosis.

### 2. Recover only fully checked missing-summary cases

If the audit reports only `EXISTING_VERIFIED_COMPLETE`, `RECOVERABLE_CHECKED_NO_WRITE` and `NOT_STARTED`, apply recovery:

```bat
python "case1\studies\SEEDExchange_StudyA_AC_Recovery_v1\studya_recover_ac_summaries.py" --repo-root . --scope full --repair --report "StudyA_LongPath_Recovery_Applied.json"
```

The recovery:
- Reads and independently checks 8,760 timestamps, convergence, numerical validity, limit flags and energy-source consistency.
- Writes **only** a missing `ac_summary.json` using exclusive creation, with explicit `recovery_provenance`.
- Rechecks the reconstructed result against the original annual verifier.
- Never edits an `ac_hourly.csv` or an already present summary. It cannot salvage an incomplete hourly CSV.

**Note:** `--scope full` may scan all 432 planned annual AC cases. `NOT_STARTED` is expected for cases not yet run.

### 3. Restart the unfinished sensitivities

```bat
call "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_2025_AC_sensitivities.cmd"
```

The controller checks and reuses previously complete results, including recovered summaries, then processes remaining 8,760-hour cases. It does not rerun signed cases. If any partial case is not recoverable, leave it untouched for review instead of deleting evidence.

### 4. Share small evidence after first rerun

Please upload `StudyA_LongPath_Recovery_Check.json`, `StudyA_LongPath_Recovery_Applied.json` (if created) and the latest `annual_AC_replay_receipt_*.json`. The recovery report should tell us how many cases were rescued and whether any require a numerical rerun.

## Tested here

- 6 dedicated nonnumerical Windows-path and case-plan regression tests passed; 1 additional Windows-only long-path filesystem test is provided for local execution.
- 12 existing annual portfolio tests passed against patched modules.
- 7 existing recovery tests passed against patched modules.
- 12 existing PV+BESS planning tests passed.

**Windows end-to-end filesystem behaviour needs confirmation on your local computer.** No 8,760-hour numerical simulations were run while preparing this patch.

## Scientific provenance

This is a file-I/O correction only. It does not alter the 35-house assignment, 2025 profiles, transformer ratings, PV/BESS dispatch constraints, AC equations, signed manifest or historical results. No GitLab commit is made.
