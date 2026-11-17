# Study A walkthrough Stages 12 and 13, curated figure and hourly evidence package

Created 16 November 2026, read-only. This package is *not* a GitLab commit and does not modify the v6.2 runner, historical investment outputs, or the old professor walkthrough.

## Contents

- Five curated, approved comparison figures in `figures/`, each **280 dpi PNG and editable vector SVG**.
- `plot_studya_walkthrough.py`: independent post-processing script, no PyPSA, pandapower, network calls or simulations.
- `evidence/`: the signed input mapping and exact analyzed **90 gross cases, 432 AC cases, 36 34-house matched sensitivity totals and 22 energy designs** from the 16-Nov independent review.
- `source_geometry/`: figure-preview-only local extract from private GitLab `main` (commit `9aaca5473838b69de442cb238ba40a0e97405844`) retaining all 35 house coordinates, six relevant transformers and 30 relevant EPM LV line sections rounded to eight decimal places. **The local `--repo-root` path is preferred for final G4 publication, as that reads the original GIS sources directly.** A0/A1 assignments come from signed input manifest.
- `FIGURE_INDEX_APPEND_PROPOSAL.csv`, `WALKTHROUGH_NARRATIVE_EXTENSION.md`: proposed GitLab stages 12/13; do not overwrite stages 01–11.
- `extract_monthly_and_residual.py`: separate **read-only** postprocessor to collect all 22 optimized + 22 causal monthly-energy case tables and precise A1 106039 violating hours from your local source-signed annual CSVs.
- `tests/`: seven unit tests.

## Figure interpretation and stage placement

| Figure | One question | Suggested place |
|---|---|---|
| G4 A0 vs A1 LV map | Which houses were assigned to which transformer after obtaining EPM? | Stage 12, main |
| P3 92395 STAR/MST | Does the shortest proposed routing guarantee lower electrical risk? | Stage 12 / Study B bridge, main |
| P1 gross to PV+BESS | How many territory-hour violations remain after shared PV+BESS? | Stage 13, main |
| P2 higher-SS PF/length | Does the improvement survive uncertainty? | Stage 13, optional main/appendix |
| P4 cost and SS | What is the cost/autarky/AC constraint trade-off among 4 discrete architectures? | Stage 13, appendix |

P1 and P2 use the 34 houses on five multi-house transformers, not the one support-only household at 98380. G4 shows all 35 for geographic completeness. A violation territory-hour is one hour at one transformer, so multiple territories could violate in the same clock hour. All PV+BESS AC figures inherit the model's **daylight Q=0.25 and Q=0 at night** assumptions. No proof of inverter Q capability or true Colombian service phases has been obtained.

## Reproduce figures from your exact local EPM GIS files

Extract package under `case1\studies\` in the repository checkout, then from **Miniforge/Anaconda Prompt** at repository root:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Walkthrough_Stage12_13_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_Walkthrough_Stage12_13_v1\plot_studya_walkthrough.py" --repo-root . --out "case1\studies\SEEDExchange_StudyA_Walkthrough_Stage12_13_v1\figures_local"
```

The original `epm_network_relevant_sanitized.geojson` and `houses_candidate_associations.csv` are loaded when present in `case1/studies/epm_gis_pandapower_v1/data`. **G4 is a schematic of mapped EPM LV and assumed house service links, not measured cable routes.** The nearest **transformer** rather than nearest GIS line is used to define A1 membership.

## Obtain operational evidence without rerunning 432 AC cases

```bat
python "case1\studies\SEEDExchange_StudyA_Walkthrough_Stage12_13_v1\extract_monthly_and_residual.py" --repo-root . --out "StudyA_Monthly_And_Residual_Evidence.zip"
```

Upload `StudyA_Monthly_And_Residual_Evidence.zip`. It should contain 528 month rows (44 annual optimized/causal runs × 12 months), the exact source-signed 106039 A1 residual-hour records from five chosen annual AC scenarios, and an explicit exception register. If a mismatch exists, **do not rerun or delete anything**. The ZIP reports the error for investigation. This extraction does not change any model files, results, folders or GitLab.

After those hourly summaries arrive, the selected 106039 monthly operation and multi-cohort appendix figures can be made, and the 106039 AC-aware fixed-hardware correction can be scoped using real violation hours.

## Source gates

- The summary ZIP's signed hourly CSVs were **verified by the user's collector locally**, but the raw 432×8,760 hourly values are not in the compact ZIP; this figure package does not claim an independent AC physics re-simulation.
- The two borrowed A0 four-house higher-SS causal cases have nonzero terminal SOC drift, so equal-endpoint annual comparisons remain conditional.
- The 92395 STAR/MST source is proposed topology, not documented cable installation or cost.
- The higher-SS equipment choices do not uniformly attain 90% for every cohort.
- No GitLab changes made; provenance and final figure selection should be reviewed before merging or publishing.
