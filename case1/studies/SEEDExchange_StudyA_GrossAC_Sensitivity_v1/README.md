# SEEDExchange Study A: annual gross PF × service-length sensitivity v1

The earlier **eight** full-year AC runs are the baseline `PF=0.98`, `service length ×1.0` for both A0 and A1 on `94022`, `106039`, `113699`, `85398`. Do **not** overwrite or rerun those baseline files.

This local-only package uses the existing, unchanged `SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py` and the SHA-verified `input_manifest_v6_2.json`. It does **not** run the 6,840 historical investment optimizations, edit repository source files, push to GitLab or create provisional connections for transformer 92395.

## Matrix

For each of the eight baseline case cohorts, the complete planned grid is:

| Load power factor | Length ×1.0 | Length ×1.3 | Length ×1.6 |
|---|---|---|---|
| 0.95 | Main phase | Interaction phase | Interaction phase |
| 0.98 | **Existing annual baseline** | Main phase | Main phase |
| 1.00 | Main phase | Interaction phase | Interaction phase |

The main phase adds **32 annual cases** and the interaction phase adds **32 annual cases**. Together with the existing eight, that is **72 distinct annual configurations** or 630,720 hourly power flows for the four mapped transformers and both hypotheses. Each new combination starts with its own 24-hour smoke test. Only physically uncertain assumed **household service drops** change under the length multiplier, not source GIS LV segment geometry. Check actual source behavior in `epm_topology.build_territory`.

## Execute on your own machine

Extract this ZIP into your repository's `case1\studies\` folder. From your repository root, inside **Miniforge Prompt or Anaconda Prompt**, run these commands:

First inspect the planned main cases (does not run simulations):

```bat
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase main --dry-run
```

Then run the main-effect phase:

```bat
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase main --run
```

After review, inspect and run the PF-by-length interaction corners:

```bat
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase interactions --dry-run
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase interactions --run
```

For a smaller pilot before the full main phase, run one transformer under both hypotheses:

```bat
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase main --transformer 113699 --dry-run
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase main --transformer 113699 --run
```

Results are created only under the **new** `case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\sensitivity_gross_v1\` folder, one uniquely named subdirectory per parameter case and run length. Existing complete files are checksum-checked and skipped on restart. Existing partial files are never overwritten. Violations of 0.95 pu or 100% loading **are valid research findings**, not a reason to delete a completed run. Nonconvergence is preserved and flagged separately.

The unchanged runner's name `--service-factor` is deliberate. PF and physical length are scenario dimensions, not source-certified true values. Gross runs have no inverter P or nighttime reactive power. Do not report manufacturer battery limits or PV curtailment from these runs.

## What remains

A full AC run for the 4-house `92395` cohort in both A0 and A1 is **pending explicitly approved hypothetical LV geometry or additional EPM service evidence**. Its absence of GIS LV geometry is NOT proof of absent service. `98380` is a one-house support-only transformer, outside the approved `N>=4` cohort sweep. Separate 113306 connections remain an unapproved scenario sensitivity.

After the gross annual sensitivity runs, move to the source-selected **minimum-cost** and **≥90% self-sufficiency** PV+BESS equipment references, four-house designs, manufacturer physical-SOC and kW checks, PV curtailment, causal versus perfect-foresight dispatch, and annual AC replay for *each* study cohort. No equipment optimisation results are implied here.
