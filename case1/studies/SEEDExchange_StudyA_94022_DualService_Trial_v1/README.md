# SEEDExchange Study A: A0 94022 paired assumed-service sensitivity (v1)

This package continues the 15-option sparse branch test using the **actual uploaded output**. H01's model line 007 and H06's model line 004 are long, *assumed* service-drop branches. The next study tests whether adding both to selected mapped-LV improvements passes the nine selected critical timestamps. No new full-year optimization or annual AC rerun is performed.

**Existing local requirements** (previously run/installed):

- `case1/studies/SEEDExchange_StudyA_94022_Sparse_Bundle_v1/studya_94022_sparse_bundle_trial.py`, with its exact `inputs/StudyA_94022_Branch_Isolation_v1_Results.zip`.
- `case1/studies/SEEDExchange_StudyA_94022_Branch_Isolation_v1/probe_94022_branch_isolation.py`.
- `StudyA_A0_94022_Sequenced_Trial_v1/` at repository root, with four completed candidate annual schedules.
- Existing pandapower, numpy, pandas, scipy, shapely, pyproj etc. Miniforge environment used for the prior screens.

Extract the folder `SEEDExchange_StudyA_94022_DualService_Trial_v1` directly into `case1/studies/`. From the **repository root** in **Miniforge Prompt / Anaconda Prompt**, run:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_94022_DualService_Trial_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_94022_DualService_Trial_v1\studya_94022_dual_service_trial.py" --repo-root . --preflight
python "case1\studies\SEEDExchange_StudyA_94022_DualService_Trial_v1\studya_94022_dual_service_trial.py" --repo-root . --trial-dir "StudyA_A0_94022_Sequenced_Trial_v1" --out "StudyA_94022_DualService_Trial_v1_Results.zip"
```

Upload `StudyA_94022_DualService_Trial_v1_Results.zip`. This is **16 × 72 = 1,152** targeted pandapower AC evaluations, with six independent historical control combinations re-solved. All source result checksums, output keys, power-flow thresholds and line model endpoints must pass; incomplete or mismatched data causes an error instead of a success report. The output is written as a new ZIP, refusing overwrite. Original source files are not modified.

Output files: `DUAL_SERVICE_AC_72_CASES_EACH.csv`, `DUAL_SERVICE_OPTIONS_RANKED.csv`, `DUAL_SERVICE_BRANCH_MEMBERSHIP.csv`, `DUAL_SERVICE_MODEL_BRANCH_ENDPOINTS.csv`, `DUAL_SERVICE_MANIFEST.json`.

**Do not infer physical installed cable lengths, prices, voltage compliance or annual feasibility from this sensitivity.** Resistance alone is halved; source EPM mapped lines and modelled service taps require real-world verification.

Audit and scientific interpretation: [RESEARCH_REVIEW.md](RESEARCH_REVIEW.md).
