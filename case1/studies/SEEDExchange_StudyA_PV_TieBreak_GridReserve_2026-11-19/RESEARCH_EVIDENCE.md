# 19 November 2026 | Source-reconciled PV-priority / AC outcome and evening reserve gate

## Verified user results

The sync branch user commit `c1518e83` contains `StudyA_A1_106039_PV_TieBreak_AC_Delta_Baseline_v1` and `StudyA_A1_106039_PV_TieBreak_AC_Delta_Full_v1`, both with `COMPLETE_MATCHED_DELTA_AC_WITHOUT_ANNUAL_CERTIFICATION` and empty errors.

- 18 matched AC factor/case scenarios. PF 0.95/0.98/1.00 × length multiplier 1.0/1.3/1.6 for MC_REF and MC_P33.
- 68 MC_REF and 95 MC_P33 distinct changed inverter hours each at every factor. Stage1 and Stage2 => (68+95)×9×2 = 2,934 AC changed-hour solutions. All converged, zero new or resolved AC violations **among changed hours**. This does NOT establish annual AC feasibility.
- At stress PF .95 / 1.6, MC_REF changed-hour max trafo 89.377% Stage1 vs 87.801% Stage2; MC_P33 94.143% Stage1 vs 93.309% Stage2. These are the maximums **within the changed-hour sets only**, not 2025 annual peaks.
- The stress changed-hour loss delta (Stage2 minus Stage1) is -0.0095909 kWh for MC_REF and -0.0595612 kWh for MC_P33. Not a material economic benefit. At individual hours transformer loading may increase by >40 percentage points and decrease elsewhere, so maxima and annual totals alone conceal operational redistribution.

## Cross-check against historical 8,760-hour reference AC

Reopened all nine historical archived **MC_REF A1 106039 optimized** `ac_summary.json` and `ac_hourly.csv` under `case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01/annual_ac_replays_v1/A1_106039_min_cost_ref_mapped_optimized_pf*_length*_annual8760/`.

Historical 8760h stage1 original source and new signed Stage1 match every tested timestamp, demand and inverter AC output to numerical rounding (max inverter diff 5e-10 kW in independent full-year cross-checks). All nine sources share signed energy manifest SHA `29f136fbc1d1adf0968ef7222406fdd67c2eeaa7df4fd727995c40b9ec6ab125`. Independent matched 68-hour Stage1 AC output versus historical annual AC output across **all nine factors**: max loading difference ~6e-9 percentage points; other AC quantities within 1e-10. Exact changed-hour dates line up. This supports a source-stitched annual Stage2 AC comparison that reuses immutable unchanged-hour baseline rows, not a newly simulated full year.

Historical MC_REF annual overloads are **unchanged by Stage2 PV-priority preference**, because the decisive hours 2025-10-13 20:00 and 2025-11-27 20:00 are NOT among its 68 changed inverter hours. Stress PF .95 x1.6: two historical overloads, max trafo 107.431169%; PF .98 x1.6: one, max 103.603747%; PF 1.00 x1.6: one, max 100.582341%. Counts are 2/1/1 for all three length factors. No claim of new physical electrical feasibility is allowed. 106039 5 kVA is still a planning assumption.

On 2025-10-13 20:00, Stage2 MC_REF BESS is at 1.832 kWh 20%-SOC usable floor, 0.269556 DC kWh discharged, grid import 4.633279 kWh. On 2025-11-27 20:00, BESS is at same floor, discharge zero, grid import 4.843887 kWh. Early-use PV preference alone did not reserve battery for these evening thermal peaks.

## Existing correction reused conceptually, never overwritten

Already completed `StudyA_A1_106039_Redispatch_Trial_v1/trial_manifest.json` (status `ALL_NINE_PF_LENGTH_CASES_FEASIBLE`) documents original MC_REF active-P/SOC-consistent evening corrections, 0.60 DC kWh Oct 13 and 0.80 DC kWh Nov 27, eliminating 1/2 original AC failures across all nine factors, changed hours independently AC solved and unchanged original annual AC reused. This is **existing evidence for the original economic Stage1 schedule**, not a proof for the new Stage2 charge timing. The earlier November candidate moved discharge through 18:00, whereas the Stage2 source discharges from 17:00; direct copying is invalid.

**New experimental plan from Stage2 itself:** 0.60 DC kWh discharge from Oct 13 17:00→20:00, and 0.80 DC kWh from Nov 27 17:00→20:00, same 41-panel / 8-module / 12 kW / 12 kVA equipment. New isolated source `case1/studies/SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19/`, committed in `0c3aff13`. Local user must first run synthetic tests, signed-source preflight, stress AC, then nine-factor source-stitched AC with four extra changed hours.

**Independent preflight energy check in GitLab source data:** applying those two precise shifts to the already signed MC_REF Stage2 8,760 CSV preserves grid imports 3107.4851226344 kWh, annual battery discharge 9648.883322274 DC kWh, terminal SOC 14.3821543546 kWh, SOC range 1.832–34.6 kWh, maximum grid proxy PCC 4.590036 kVA; maximum cyclic SOC equation error 1.43e-10 kWh; max AC/DC nodal mismatch ~1e-10 kW. Source hours 8,760, grid import never negative. This **does not substitute for new pandapower AC run**, which remains user-local.

The new runner will read-only verify historic annual nine-factor AC and existing matched Stage2 delta source hashes; test the four new hours with original v6 pandapower; construct 8,760 hour source-stitched AC status, peak loading, voltage, line/trafo and annual modeled losses, separating one-stress gate from full nine-factor results. It must not call these new full annual AC simulations or utility certifications.

## Remaining research
- MC_P33 still lacks source-matched full-year nine-factor AC reference; its zero new changed-hour failures cannot become an annual pass claim.
- Three new hardware SS_P45_B9 / MC_B10 / SS_B10 stress cases still have 1/2/1 annual transformer-overload hours; none automatically corrected here.
- Prior full-workflow approved A/B/C objectives and historical 376/432 + conditional 408/432 campaigns remain unchanged. Work on A AC-feasible/cost tradeoff before B STAR/MST and C Site A. No main merge.
