# A0 94022 annual network bundle validation v1

This package follows the **verified nine-factor, nine-hour** source results for the four-, five- and six-branch R×0.5 research assumptions. It does **not** supply annual validation results, select real cables or change previously signed files.

## Local installation and dependencies

Extract the folder `SEEDExchange_StudyA_94022_Annual_Bundle_Validation_v1/` into `case1/studies/` of your existing Windows GitLab checkout. Retain the previously extracted packages:

- `case1/studies/SEEDExchange_StudyA_94022_AllNine_Bundle_v1/`
- `case1/studies/SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16/`
- `case1/studies/SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1/`
- `case1/studies/SEEDExchange_StudyA_PVBESS_v1/` and the original signed local-runner outputs.
- `StudyA_A0_94022_Sequenced_Trial_v1/` in the repository root with all four accepted candidate 8,760-hour schedules and its manifest.

Use **Miniforge Prompt or Anaconda Prompt** from the repository root, not PowerShell. No new PyPSA hardware or energy optimization is performed. Only pandapower AC replay with a fixed bundle network is new numerical work.

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_94022_Annual_Bundle_Validation_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_94022_Annual_Bundle_Validation_v1\validate_94022_annual_bundle.py" --repo-root . --preflight
python "case1\studies\SEEDExchange_StudyA_94022_Annual_Bundle_Validation_v1\validate_94022_annual_bundle.py" --repo-root . --bundle five --mode pilot --out-dir "StudyA_A0_94022_Annual_Bundle_Results_v1" --zip-out "StudyA_A0_94022_Annual_five_pilot_Results_v1.zip"
```

**Upload `StudyA_A0_94022_Annual_five_pilot_Results_v1.zip`** even if some hours fail electrical limits. This pilot is 4 corrected schedules × 1 stress pair (PF .95, factor 1.6) × 8,760 hours = 35,040 AC evaluations. All non-solver tests passed locally, and an isolated preflight using the original previously uploaded trial source passed. The assistant did not run the full annual solver.

## Subsequent optional modes

After independent review of the pilot, the same runner can use `--bundle five --mode all-nine` to validate the 5-edge assumption under all nine pairs: **36 annual runs**, 315,360 hours in total, with the previously completed 4 pilot jobs **checksum-verified and reused**, not rerun. The same `--out-dir` must be used. Use an explicit new `--zip-out` name, e.g. `StudyA_A0_94022_Annual_five_allnine_Results_v1.zip`.

Alternatives `--bundle four` and `--bundle six` are available for comparative tests if needed. `--mode reference` uses PF .98 and length ×1.0. Avoid launching all three bundles across all nine pairs before examining the pilot. The annual job boundaries are resumable. Within a job, a failed computation must be rerun; sources are never overwritten.

## Outputs and safeguards

Each completed annual job produces one hourly CSV and signed JSON summary under its own case directory. The script checks source manifests and checksums, 8,760 chronological hours, SOC/energy constraints, device ratings and the baseline AC evidence, then reproduces the **nine matching uploaded selected-hour AC controls** to tolerance 2e-4. It records voltage/thermal violations and annual line/transformer losses in the original energy scale. The output ZIP holds all completed jobs for the selected run; no source files or original 432-case results are altered.

The research model uses balanced AC, conditional transformer and service connections, hypothetical R×0.5 on selected branches, unchanged line reactance and ampacity. Physical wiring, procurement cost, protection, phase imbalance, short-circuit and dynamic protection compliance are still out of scope. Electrical passing results must not be called utility authorization or physical design approval.
