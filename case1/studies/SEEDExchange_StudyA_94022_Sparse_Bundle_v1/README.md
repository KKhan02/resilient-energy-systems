# SEEDExchange Study A A0 94022 sparse resistance-bundle pilot

**Scope:** 15 source-derived, read-only resistance configurations, nine timestamps, four dispatch/equipment combinations, two PF/length settings. The 1,080 targeted pandapower solves are a **what-if** screen only. They neither change signed source results nor establish annual feeder feasibility or cable quotes.

## Setup

Extract this folder to:

`case1\studies\SEEDExchange_StudyA_94022_Sparse_Bundle_v1\`

The previous `SEEDExchange_StudyA_94022_Branch_Isolation_v1`, `SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16`, `SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1` packages must remain installed under `case1\studies\`. Keep the original `StudyA_A0_94022_Sequenced_Trial_v1` folder at the repo root. The included `inputs/StudyA_94022_Branch_Isolation_v1_Results.zip` is an exact checksum-verified copy of the uploaded 2,160-row results.

Use **Miniforge/Anaconda Prompt**, from the repository root, not PowerShell:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_94022_Sparse_Bundle_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_94022_Sparse_Bundle_v1\studya_94022_sparse_bundle_trial.py" --repo-root . --preflight
python "case1\studies\SEEDExchange_StudyA_94022_Sparse_Bundle_v1\studya_94022_sparse_bundle_trial.py" --repo-root . --trial-dir "StudyA_A0_94022_Sequenced_Trial_v1" --out "StudyA_94022_Sparse_Bundle_Trial_v1_Results.zip"
```

Upload the resulting `StudyA_94022_Sparse_Bundle_Trial_v1_Results.zip` for independent audit.

## Source check and result details

- Verifies the source branch-screen ZIP SHA-256 and expected 2,160 records.
- Confirms 26 model graph edges and all bundle membership indices before power flow.
- Imports the existing original A0 network model and source-signed annual schedules.
- Solves both stress factors for every bundle and hour, checking output identity, convergence, voltage, line, transformer loading.
- Reproduces the original baseline, GIS-only, service-only and all-LV reference sensitivities within a numerical tolerance.
- Records `BUNDLE_OPTION_SUMMARY.csv`, `BUNDLE_BRANCH_MEMBERSHIP.csv`, `MODEL_BRANCH_ENDPOINTS.csv`, all targeted AC values, and `BUNDLE_MANIFEST.json`. The model endpoint file identifies the household bus for each assumed service connection, including line 007.
- Writes only a new ZIP. Refuses overwriting existing destination ZIP. No annual PyPSA or 432-AC campaign reruns.

Do **not** interpret half-resistance as a physically selected conductor, a field-verified cable or a priced upgrade. Grouping of split GIS graph edges is illustrative, not an installation scope. The modelled affected length is not an installed cable bill of materials.
