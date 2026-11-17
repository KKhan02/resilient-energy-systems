# SEEDExchange Study A: Local Demand Source and EPM GIS Preflight v4

**Local-first handoff. You execute the scripts. No PV+BESS optimization or pandapower AC is claimed.**

## Why this package

The original `Demand_curve.xlsx` seasonal curves and the HOMER XML match within XML three-decimal precision. This package explicitly retains two distinct 2025 stochastic profile sets:

1. **`excel`**: season/hour values derived from `Demand_curve.xlsx` `Tabelle1!F5:I28` at workbook precision, mapped Sep–Nov/Dec–Feb/Mar–May/Jun–Aug. Normalized to **1,898 kWh per household per year**, then independently varied as described in the historical v18 notebook. This is the new proposed source-sensitive baseline, not a replacement for the saved original simulations.
2. **`homer`**: identical notebook-v18 method and original three-decimal monthly HOMER shape; the fixed 2025 seed and first 20 unique profiles should match `nasa_hourly_pv_and_load_inputs.csv` across all 8,760 hours if that source is present and unchanged. This is a *historical reproducibility control*.

The two modes differ slightly in individual hourly load. **Do not claim archived AC, optimization, or battery trajectories are verified against a newly defined Excel-mode profile.** All original results remain intact and historically valid for their own inputs.

`Curva_típica_Regional_Antioquia.xlsx` is included, unchanged, for regional context. Its note refers to a typical PF of **0.94**, whereas the explicitly approved electrical sensitivities are **PF 0.95, 0.98 and 1.00** with PF 0.90 as an optional stress assumption. No claim is made that these model PFs are universal grid-code or actual measured PF.

## Installation and use, Windows PowerShell

Run these commands **from your existing local `resilient-energy-systems` Git checkout root**, without ongoing simulations and after examining your local changes. Extract the ZIP under `case1\studies\`, so it becomes `case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\`.

```powershell
# Once extracted, from repository root:
python -m pip install -r "case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\requirements.txt"
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\tests" -v

python "case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\scripts\prepare_study_a.py" `
  --repo-root . `
  --outdir "case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\outputs\run_01"
```

The output folder must not exist before execution. If `run_01` already exists, use `run_02`. All outputs stay under your project. Historical files and GitLab are read-only. The analysis uses source SHA-256 guards for original mapped homes, transformer evidence, GIS GeoJSON and original workbook/XML. This intentionally stops if a source differs from the verified GitLab inputs; inspect any changes instead of suppressing source checking.

For a demand/household-geography check without the optional GIS package dependencies, add `--skip-gis`. This does **not** establish full feeder compatibility.

## Important outputs

- `preflight_summary.json`: source hashes, confirmed historical reference check, paired population counts, GIS graph findings and reasons for blockers.
- `source_12_month_summary.csv`: Excel versus HOMER numeric source comparison.
- `fixed_house_to_profile_map.csv`: 35 unique fixed house-to-stochastic-profile assignments; each house retains its profile in both mapping cases.
- `paired_house_transformer_assignments.csv`: A0 original versus A1 geographic-nearest; changes only H03, H06 and H13; 35/35 homes in both, no northern 25 kVA asset.
- `household_profiles_2025_excel_35.csv` and `household_profiles_2025_homer_35.csv`: separately identified complete 8,760-hour household time series.
- `gross_load_pf_sensitivity.csv`: P/PF transformer capacity screen (36 entries per source), **not AC results**.
- `annual_pvbess_ac_run_matrix.csv`: explicit local-followup hardware/dispatch/AC queue for all ten eligible original/nearest transformer-cohort combinations, each labelled NOT_RUN and with unresolved GIS/hardware gates.
- `hourly_transformer_gross_kw_excel.csv` / `homer.csv`: hourly gross demand by transformer and assignment.
- `gis_source_connection_audit.csv`: nearest LV section of the *selected* transformer, straight-line distance to it, connection-status caveats; generated if GIS dependencies are available.
- `gis_graph_preflight_cases.csv`: whether source EPM GIS can form a candidate feeder graph. Passing this preflight is NOT passing pandapower AC.

### What to share next

Send **`preflight_summary.json`, `source_12_month_summary.csv`, `gross_load_pf_sensitivity.csv`, `gis_graph_preflight_cases.csv`**, and, if created, **`gis_source_connection_audit.csv`**, and **`annual_pvbess_ac_run_matrix.csv`**. The original 20-profile check will explicitly report full equality, a mismatch, or missing data. Keep the large 8,760-hour CSVs locally for the next stage.

## Physical/evidence gates for next annual runs

| Territory | Original → nearest homes | Main gate |
|---|---:|---|
| 94022 | 10 → 8 | H03/H06 reassignment path, loads and transformer/line capacity |
| 106039 | 12 → 11 | 5 kVA is user-selected modelling assumption, not nameplate certification |
| 113699 | 4 → 6 | 3 kVA evidence, potential capacity and long service drops |
| 85398 | 4 → 5 | Only one exported GIS LV segment; H14/H15 original association unverifiable |
| 92395 | 4 → 4 | **No exported LV sections**; no invented physical wiring; retain H30–H33 |
| 98380 | 1 → 1 | Below N>=4 main analysis inclusion, monitor population accounting |

Original 7/9-house cases on 94022 and 12-house case on 106039 stay independent historical evidence. The 4-house cohorts are outside the old 5–15 house investment sweep and will need targeted equipment selection. No old optimizations or simulations are overwritten. No rejections based only on critical hours.

## Following verified preflight

We will review the actual saved connection graph results, then prepare the **two parallel** fixed-hardware 8,760-hour manufacturer-SOC annual dispatch campaigns with the correct household membership, followed by pandapower annual AC. This stage must reuse existing code modules and archived economic hardware anchors, with targeted new 4-home hardware where needed. Running the current existing `run_archived_energy.py` on a new 8/10/11-house physical grouping without adapting its source cohort would give the **wrong household trajectories**, so it must not be presented as the new scenario's result.

For each approved cohort and chosen hardware, compare PV-first versus alternative feasible no-grid-charge/zero-export scheduling, Q/P controls, batteries and inverter limits, 20% physical SOC, energy/power sizing, battery utilization, curtailed PV, self-sufficiency, lifetime costs, feeder voltage/loading/losses and PF/service-length uncertainty. This **battery optimization and curtailment analysis applies in Studies A, B and C** as networks become source-supported; it is not a single 12-home demonstration. See `BATTERY_CURTAILMENT_WORKSTREAM.md`.

**Study B**: separately engineered compact 5–15-home proposed LV STAR vs branched MST; do not claim this package defines its transformer location, conductors, or routes. **Study C**: Site A-to-94022 proposed cable first, followed by new transformer only if warranted, never use northern 25 kVA transformer. Do not assume physical connections or installation costs exist without evidence.
