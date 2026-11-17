# Study A, transformer 94022: branch-specific follow-up

The source network probe tests inverter siting versus uniform line resistance. It does **not** show which cables matter. This package gives the audited interpretation and a read-only local AC script to isolate EPM GIS LV lines versus assumed service drops, and individual lines, with the same signed A0 annual schedules.

## Installation

Extract the **folder** `SEEDExchange_StudyA_94022_Branch_Isolation_v1/` from this ZIP into `case1\studies\` in your existing local GitLab repository. Keep the earlier `SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16` and `SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1` folders in `case1\studies\` and the unmodified `StudyA_A0_94022_Sequenced_Trial_v1` folder in repository root.

The source `StudyA_A0_94022_Network_Probe_v1.zip` is bundled under `inputs/` and checked against its signed trial provenance. No copying or downloading that original ZIP is necessary.

From repository root in **Miniforge/Anaconda Prompt**:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_94022_Branch_Isolation_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_94022_Branch_Isolation_v1\probe_94022_branch_isolation.py" --repo-root . --preflight
python "case1\studies\SEEDExchange_StudyA_94022_Branch_Isolation_v1\probe_94022_branch_isolation.py" --repo-root . --trial-dir "StudyA_A0_94022_Sequenced_Trial_v1" --out "StudyA_94022_Branch_Isolation_v1_Results.zip"
```

Upload the resulting `StudyA_94022_Branch_Isolation_v1_Results.zip` **even if no option completely removes the violations**. The input fingerprints are verified, and the script refuses to overwrite any result ZIP.

## Output

- `94022_LV_BRANCH_REGISTER.csv`: the precise modelled LV sections and assumed service drops, line R/X/ampacity and lengths at ×1.0.
- `BRANCH_SCREEN_AC_HOURLY.csv`: independent AC results at the nine events × four groups × two factor pairs, for head baseline, all LV R×0.5, GIS-only R×0.5, service-only R×0.5, and each individual branch R×0.5.
- `BRANCH_SCREEN_OPTION_SUMMARY.csv`: success counts, voltage and loading extremes by option.
- `BRANCH_SCREEN_MANIFEST.json`: input provenance, row count, model assumptions, explicit nonannual status.

**Limits:** This isolates electrical sensitivity, not physically available cables, cable prices or certified site upgrades. It uses the original 0.95–1.05 pu research voltage target and 100% modelled thermal screens. No original annual results, source ZIPs or GitLab files are changed.
