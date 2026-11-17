# SEEDExchange Study A: safe annual AC summary recovery

This package is a **post-processing recovery tool**, not a solver. It never edits the historical GitLab results, the v6.2 runner, original PyPSA results, or existing hourly CSVs. Default mode is read-only except for a new JSON audit report outside results. `--repair` writes ONLY missing `ac_summary.json` files after comprehensive checks.

## Install

Extract the ZIP so the folder is:

`case1\studies\SEEDExchange_StudyA_AC_Recovery_v1\`

From your repository root, use **Miniforge Prompt or Anaconda Prompt**.

## Step 1: synthetic regression tests

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_AC_Recovery_v1\tests" -v
```

Expected: `Ran 7 tests`, `OK`.

## Step 2: read-only diagnosis

```bat
python "case1\studies\SEEDExchange_StudyA_AC_Recovery_v1\studya_recover_ac_summaries.py" --repo-root . --report "StudyA_AC_Recovery_Check.json"
```

The diagnostic output identifies 42 signed baseline AC results, and checks the six cases that have a complete `ac_hourly.csv` but no `ac_summary.json`. **Do not proceed with repair if any case reports `NOT_RECOVERABLE_NEEDS_INSPECTION` or `EXISTING_SIGNED_OUTPUT_INCONSISTENT`.** Send that report and affected hourly CSV instead.

## Step 3: only if all six pass source and CSV checks

```bat
python "case1\studies\SEEDExchange_StudyA_AC_Recovery_v1\studya_recover_ac_summaries.py" --repo-root . --repair --report "StudyA_AC_Recovery_Applied.json"
```

This reconstructs signed summary values from the existing complete 8,760-hour outputs, adding an explicit `recovery_provenance` field. Every restored summary is immediately rechecked by the original controller. Original CSVs are not changed. Results with failed hours, invalid values, bad chronology, differing dispatch or wrong source signatures are rejected.

## Step 4: finish baseline and then sensitivities

```bat
call "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_2025_AC_baseline.cmd"
```

Expected 48 verified case outcomes and no blocks (if every case could be recovered). Then:

```bat
call "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_2025_AC_sensitivities.cmd"
```

This last command is the **384-case annual AC sensitivity stage**. The original all-in-one CMD did not start it because the baseline stage returned failure status. All runs use 8,760 hours and preserve completed case folders.

## Step 5: collect final evidence

```bat
python collect_studya_pvbess_results.py --repo-root . --out "StudyA_PVBESS_Annual_Result_Summary_v2.zip"
```

Share the final ZIP and both recovery reports. Existing `StudyA_PVBESS_Annual_Result_Summary.zip` is preserved.

## Important source limitations

The uploaded compact ZIP contains only metadata and checksum inventories, not the six original hourly CSVs or first-run traceback. Therefore, neither the CSV validity nor the exact cause of the six missing summary files can be independently established here. The local diagnosis is specifically designed to resolve that uncertainty before creating recovered summaries. Original annual power-flow numerics are **not recomputed**.
