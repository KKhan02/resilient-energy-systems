# WP1 seven, voltage magnitude reinterpretation, v1.4

This additive analysis **does not change the PyPSA schedule, battery SOC, P/Q constraints or pandapower results**. It reclassifies the already solved AC points under four *separate* voltage bands:

| Band | Minimum | Maximum | Purpose |
|---|---:|---:|---|
| National voltage magnitude reference | 0.90 | 1.10 | Regulatory magnitude comparator, not a formal compliance claim |
| Historical EPM NT-13 reference | 0.90 | 1.05 | Historical EPM technical comparator; current applicability not independently reverified here |
| Proposed engineering target | 0.95 | 1.05 | Preferred design margin for research comparisons; subject to engineering review |
| Original stringent sensitivity | 0.97 | 1.03 | Continuity with the original Case 1 model, not a Colombian regulatory limit |

The original robust study uses 77 **selected critical** hours per PF/route scenario. It does **not** establish annual robustness or formal voltage compliance at a customer's service point. National voltage-quality assessments can require different measurement windows, aggregation and technical definitions. This script only applies instantaneous steady-state magnitude thresholds to the *existing sampled model outputs*. Preserve every trace and source hash.

Run after extracting these files alongside `run_robustness.py`:

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests
python case1/studies/ac_aware_redispatch_v1/reassess_voltage_bands.py --robustness-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_robustness_critical_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/seven_voltage_band_review_01
```

Output: 36-row `voltage_band_sample_summary.csv`, 693-row `voltage_band_hourly_screen_flags.csv`, a manifest containing source SHA-256 hashes and two independent heatmaps. Existing folders are not overwritten. The function refuses to run on incomplete or inconsistent sampling grids.

## Engineering consequence

The strict 0.97 pu threshold causes 297 failures across the 693 saved AC observations. All 693 pass the 0.95 to 1.05 pu magnitude screen and the two less stringent reference bands. This **does not** mean the entire year or installed grid is compliant. It shows the voltage criterion is a decisive design assumption. Preserve the 0.97 study as a stringent margin scenario rather than setting it as the default national or EPM requirement.

## Sizing gates

- The earlier shortlisted 60 equipment rows are energy-screened only. They are neither manufacturer-SOC-updated nor AC-validated.
- Use multiple PV/BESS/inverter candidates within each household count. Check real battery/inverter power limits before rerunning their economic objective.
- First test 12-house 106039 at the saved hardware with the existing pilot. Do not transfer a 94022 P corridor or assume EPM-connected houses are physically interchangeable.
- For each shortlisted candidate: manufacturer min SOC, fixed-capacity PyPSA dispatch, critical-hour AC screening, AC-feedback correction if needed, independent annual AC validation, cost and voltage margin, then select diverse designs for full-year sensitivity.
- Test the effect of the 0.95-1.05 engineering target and the original 0.97-1.03 stringent band separately. Do not proclaim grid-code conformity from an hourly balanced-equivalent simulation.
- AC losses are currently measured in pandapower, but not fully included in dispatch and annual costs. Resolve for final economic recommendations.
