# WP1, seven-house sensitivity and voltage-band decision audit

**Evidence date:** 4 November 2026. Source: user-uploaded v1.3 robustness and equipment shortlist, and v1.1/v1.2 annual AC replays. No new pandapower, PyPSA or Linopy optimization was performed for this audit.

## Finding 1: strict-band sensitivity

All nine scenarios reused the same 77 selected critical hours and unchanged 7-house/94022 AC redispatch. All 693 AC solves converged. All 693 points remain within the proposed **0.95 to 1.05 pu magnitude band**; **297/693** violate the historical research **0.97 to 1.03 pu** band. Overall lowest simulated voltage: **0.960979 pu** at PF=0.90 and service-length factor=1.6. Maximum reported transformer loading **64.60%** and line loading **9.84%**; no thermal overloads among sampled points.

| Load PF | Service factor | Worst Vmin (pu) | Strict failures / 77 |
|---:|---:|---:|---:|
| 0.98 | 1.0 | 0.970099 | 0 |
| 0.98 | 1.3 | 0.967841 | 19 |
| 0.98 | 1.6 | 0.965572 | 36 |
| 0.95 | 1.0 | 0.968190 | 17 |
| 0.95 | 1.3 | 0.965912 | 33 |
| 0.95 | 1.6 | 0.963564 | 50 |
| 0.90 | 1.0 | 0.965803 | 35 |
| 0.90 | 1.3 | 0.963432 | 50 |
| 0.90 | 1.6 | 0.960979 | 57 |

These are *critical samples*. The 77 hours were selected from the original reference conditions, so they are **not a proof of all-year robustness** under changed PF and service-route assumptions. Q selection was zero throughout all 693 saved samples; no VAR benefit was observed in this sample. As before, electrical connections, feeder impedance and balanced three-phase equivalent are provisional.

## Finding 2: whole-year reinterpretation of the existing scenario

Both *previously simulated* 8,760-hour trajectories pass the 0.95 to 1.05 magnitude and thermal screen, without rerunning the models:

| Historical AC replay | Annual 0.95–1.05 + thermal | Annual 0.97–1.03 + thermal | Worst Vmin |
|---|---:|---:|---:|
| Manufacturer-SOC baseline | 8,760/8,760 | 8,756/8,760 | 0.968184 pu |
| AC-redispatched | 8,760/8,760 | 8,760/8,760 | 0.970099 pu |

Therefore, **the strict 0.97 pu research threshold created the four baseline violations that drove this particular AC redispatch**. At 0.95 pu, this fixed-hardware scenario had no voltage-magnitude failures in its modelled year. This is useful for the scientific comparison of the cost of stronger voltage-margin targets, but it is not national or EPM certification. The model is hourly, balanced-equivalent and uses provisional customer and conductor data.

## Finding 3: energy-only equipment shortlist

The uploaded 6,840-task campaign contains 338 eligible energy-only rows for the screened 7-, 9- and 12-house cases at the assumed 5 kVA rating; 60 candidates were shortlisted (20 per case). Selection intentionally preserves hardware diversity. Of these, 52/60 pass a **proxy** battery-current filter; this is not equipment certification. None has a new manufacturer SOC dispatch, AC-feeder validation or robust lifetime cost calculation.

| Scenario | Selected rows | PV panel range | Battery module range | Inverter range, kVA |
|---|---:|---:|---:|---:|
| 12_homes | 20 | 20–82 | 2–13 | 6.0–24.0 |
| 7_homes | 20 | 14–38 | 0–10 | 5.0–12.0 |
| 9_homes | 20 | 17–82 | 1–12 | 5.0–24.0 |

## Updated research and engineering decisions

1. Preserve **0.90–1.10 pu** as the previously researched national voltage-magnitude reference and **0.90–1.05 pu** as the historical EPM technical comparator, with applicability and voltage-quality measurement criteria checked in the official standards before any compliance claim. These are not a substitute for the actual connection agreement and site measurements.
2. Use **0.95–1.05 pu** as the *proposed WP1 engineering design target*, and **0.97–1.03 pu** as an intentionally more stringent scenario. Neither should be labelled as the regulatory limit.
3. Continue to enforce SOC >= the manufacturer-recommended 20% physical SOC, device active/reactive limits, zero-export if that case was chosen, zero normal-operation ENS and feeder thermal screening. Do not use the retired, unsourced adaptive SOC heuristic.
4. For model robustness, run **one full-year worst-end sensitivity, PF=0.90 and service multiplier=1.6**, while maintaining the original dispatch. Then reclassify the sampled AC magnitudes without rerunning identical power flows. A single stress scenario does not prove all combinations robust.
5. Revisit the 12-house 106039 reference, and advance the PV/BESS/inverter/household sweeps with *parameterized* voltage-limit settings. The v1.1–v1.3 scripts still instantiate a hard-coded 0.97–1.03 `ACLimits()`; a future AC-corridor solve must expose the voltage band consistently in its CLI, constraints and provenance manifests.
6. When ranking equipment, rerun selected candidates with 20% SOC, device power limits and AC validation. Do not treat the 60 energy-only shortlist rows as final optima; do not immediately run the full historical 6,840-task campaign under AC constraints.
7. AC losses remain a separate pandapower output; they are not yet included in PyPSA energy/cost. Do not add all modelled losses directly to imports without reconciling when and where they are supplied.

## Reproducibility

- The add-on `reassess_voltage_bands.py` validates the original 77-hour scenario counts and flags before postprocessing. It performs no power-flow solve.
- The original v1.3 robustness manifest labels each scenario *critical only* and source dispatch *unchanged*. The saved equipment manifest labels all rows *energy only*. Preserve both.
- Numeric outputs are included in `voltage_band_sample_summary.csv`, `voltage_band_hourly_screen_flags.csv`, and `annual_reference_voltage_band_reclassification.csv`.
