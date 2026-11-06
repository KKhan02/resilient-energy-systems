# Repository review after reorganization

**Repository:** `KKhan02/resilient-energy-systems` (GitLab main), 3 November 2026. All curation commits carry `[ci skip]`, so no pipeline validation is claimed.

## Narrative recommendation

Present the study through the **18 ordered figures** in [the walkthrough](README.md). The story starts with energy and geography, moves through discrete joint sizing and perfect-foresight 8,760-hour battery dispatch, then demonstrates that the energy optimum needs independent AC voltage and thermal validation. The study advances from a synthetic representative feeder to EPM GIS-backed line topology, from HIL Volt–Var to coordinated Q, and finally to conditional annual feasibility with limited robustness.

The current comparison is for **professor feedback**, not a final poster. Retain the numerical outputs and alternative studies in GitLab for detailed questions without opening every historical figure.

## Preserve as active source and results

- `case1/studies/pypsa_joint_optimization_v1/` including `full_study.py`, `model.py`, tests, `outputs/full_study/complete_study_results.csv`, `study_manifest.json` and hourly shortlist dispatch.
- `case1/studies/epm_gis_pandapower_v1/` including EPM line/node inputs, controller code, tests, coordinated Q and 106039 annual AC numerical outputs.
- `case1/data/`, `case1/studies/community_georef/`, `case1/studies/spatial_electrical_reconciliation/` for source/provenance data.
- `case1/wp1_v3/`, `case1/legacy/` and historical output tables as reproducibility evidence; **do not merge their independent dispatch results** into the main MILP without reconciling their models.

## Supporting but not primary

- `case1/studies/pandapower_dispatch_validation_v1/` representative feeder, which showed why energy-only feasibility was insufficient.
- `case1/studies/geographic_pandapower_v1/` earlier MST/star network geometry assumptions, superseded as the primary topology by EPM GIS.
- `case1/studies/site_a_solar/` illustrative site area, irradiance and hypothetical shading scenarios.
- `case1/studies/annual_shared_pvbess/`, `case1/studies/integrated_dispatch_v1/`, `case1/studies/conditional_94022_pv_bess/` and `case1/studies/reference_v5_baseline/` exploratory, historical or independent comparative approaches.

## Files moved, not deleted

- **480 original all-case PyPSA PNG/SVG plots** to `case1/research_archive/legacy_joint_optimization_figures/`.
- **41 prior v3 plots** to `case1/research_archive/legacy_v3_figures/`.
- **190 standalone review-package files** to `case1/research_archive/past_review_packages/`, including their technical review tables and figures.
- **10 old result-transfer ZIP files** to `case1/research_archive/transfer_zips/`.
- Previous root upload notes, obsolete preview exports and two original hackathon notebooks to explicit archive subfolders.

The archive contains a [relocation index](../research_archive/RELOCATION_INDEX.csv) so that every moved original path can be traced. No core simulation Python module, data input, model test or numerical validation CSV was moved.

## The substantive independent audit

The consolidated review from October remains useful as a review of the *older v3 engine*. Its fixes for PCC energy conservation, local-hour backlog, SOC boundary, pvlib selection, cost replacement and plot eligibility should be preserved. But the legacy `RUN_MANIFEST.json` still labels the saved solar resource as an unverified approximation and reports 3,909 screened rows where the audit computed 3,599. Keep these output tables frozen and clearly labelled; do not cite them as the source of the new MILP findings. The old algebraic 4.5 kVA PCC post-filter is not an independent AC validation.

The newer **6,840-task PyPSA MILP** is a distinct model with discrete choices and full-year **perfect foresight**. An earlier saved `discrete:false` run is a continuous relaxation and does not give integer commercial equipment counts. Treat PyPSA's battery SOC schedule as an optimized planning benchmark, not a tested controller. The later GIS pandapower stage adjusts Q with **active battery dispatch held fixed**. This distinction is an important research contribution and also the next research gap.

The 106039 full-year pass occurs at minimum voltage **0.970005 pu** under assumed PF 0.98/service length 1.0/Q=0.25; it is **not robust utility validation**. Stress conditions and 94022 remain unresolved. Check nighttime inverter Q specifications and actual cable/phase details.

## CI integrity and next quality gates

The user required **no CI/CD run** for this reorganization, and the commits were made with `[ci skip]`. The last previously green CI run predates the large new study drop. Local test and solver convergence evidence exists, but the new sources are not independently GitLab-CI verified. Do not create a GitHub Actions job just because GitLab has `.gitlab-ci.yml`: this project already uses GitLab.

Next, implement SOC-consistent AC-aware battery active-power redispatch, verify that revised schedules remain physically and economically credible, and then test resilience and adaptability. Prefer a separate CI-gated verification stage only when the researcher explicitly authorizes it.


## Update after local WP1 sync, 6 November 2026

The pre-existing repository review above describes the **3 November** figure selection. It remains as an audit of that earlier state. The current walkthrough now includes **24 source-copied figures** and revised sections for manufacturer-SOC correction, the completed seven-house full-year AC-aware active-power feedback, the twelve-house manufacturer-SOC annual AC result and the full-campaign reuse plan. Sections 06 and 07 gained original source-figure copies for maximum voltage, losses and the Q-ratio voltage/transformer trade-off. Section 08 now separates old Q-only annual evidence from later conservative nighttime-Q-off annual results and separates engineering from historical regulatory-magnitude references.

The new annual campaign is still in progress. No campaign-wide validated equipment frontier, unbalanced physical feeder certification or vendor-verified nighttime Q capability is claimed. Source study code, numerical outputs and original figure files were not modified by this walkthrough-only update.
