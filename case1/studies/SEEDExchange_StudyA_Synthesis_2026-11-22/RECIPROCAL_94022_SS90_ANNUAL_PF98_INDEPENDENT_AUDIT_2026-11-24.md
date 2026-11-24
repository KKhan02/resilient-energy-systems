# Study A | Independent uploaded 94022 SS90 full-year AC PF 0.98 audit

**Audited:** 24 November 2026. **Upload commit:** 32316f790e119283e7a5dbec8ec0b03eb507ec3a. **Source:** StudyA_94022_SS90_MarNov_AnnualAC_PF98_v1. **Status:** completed, **main AC research band still FAILS** because three other evening hours undervolt.

## Archived receipt and source lock

- Completed manifest: \`ANNUAL_94022_SS90_MARCH50_NOV98_PF98_COMPLETE_VIOLATIONS_RECORDED\`, not annual pass; \`annual_AC_verified=false\`.
- Exactly **8760 newly computed original** source AC hour records and **four newly evaluated corrected** hours, per-PF. Corrected 8760 rows reuse 8756 original exact AC results only because the source AC solver rebuilds each hour from flat initialization, per-house loads, independent P and reset Q, and the same model/GIS/hardware. The original source code and signed manifest identify frozen \`A1_94022_ss90_to_A0\`, A0 ten-house cohort, A1 SS90 hardware, six battery modules, assumed 5 kVA transformer and original signed 8760-hour source SHA \`dc3ba1f9f6b3d9b0b750e2212f549ff8e1c351c44258233b8357577850374c93\`.
- Independently reopened original and corrected 8760-row full-year AC CSVs, and four-change CSV. Both 8760 CSVs have 8760 unique ordered 2025 timestamps. Comparing all original/corrected model AC metric inputs shows **exactly four** changed cases: 2025-03-28 17:00, 2025-03-28 20:00, 2025-11-27 17:00, and 2025-11-27 20:00. Other 8756 AC-model metrics equal their original reference values, no additional hidden P injection. These four exactly correspond to previously audited battery transfers and archived March/November AC sample voltages and Q.
- The uploaded RUN_MANIFEST.json, three CSVs and two PNGs are now on the sync GitLab branch. GitLab SHA256 for PNGs matches saved manifest references: annual_min_voltage_comparison.png \`e78e1ff6b619f108c8bd36bdbff77ed5aaf1d3cd79161f2d42c9740ac6c40a09\`, changed_four_hours_voltage.png \`0e968580637d4954f239f518cc07a7420bf12eab16ac595b7aa58ad95fc8b857\`. CSV GitLab blobs are LF-normalized; upload original manifest SHA represents Windows CRLF source form, matching prior documented normalization convention. Do not silently rewrite signed archived CSVs or use their LF blob SHA in place of the original manifest hash.
- All 8760 original and all 8760 reconstructed corrected AC cases converge, zero conductor or transformer overload, zero overvoltage. The main 0.95..1.05 pu screen remains **NOT passed**. All recorded source and corrected model AC hours are at PF .98; PF .95 annual result is not available, and strict .97..1.03 band is a distinct failing sensitivity. No EPM field certification follows.

## Annual model AC results

| 2025 annual PF 0.98 quantity | Original SS90 source dispatch | March50 plus November98 corrected dispatch |
|---|---:|---:|
| Converged AC hours | 8760 | 8760 |
| Main-band infeasible hours | 5 | 3 |
| House V <0.95 pu hours | 5 | 3 |
| Highest house V | .9985165843 pu | .9985165843 pu |
| Lowest house V | .9467702727 pu | .9470063251 pu |
| Max transformer loading | 94.390859% | 94.390859% |
| Max line loading | 11.522439% | 11.522439% |
| Overloads | 0 | 0 |
| Optional strict house V <0.97 pu hours | 354 | 355 |
| Annual AC model network losses | 484.1526461 kWh | 484.1041831 kWh |

**Net AC loss change:** \`-0.0484630399 kWh\`, about a 0.0100% decrease from original annual losses, **not** a new grid-import or tariff optimization. The four individual AC loss deltas sum to this annual change (March donor +.005543519, March target -.030080503, November donor +.023518323, November target -.047444379 kW). Annual energy-only imports are still 4196.6064106846 kWh; we have not reconciled loss-adjusted tariff/PCC energy to the PyPSA economic dispatch.

**Interpretation:** 2 of original 5 voltage failures were fixed (March 28 20:00 and November 27 20:00), while 3 originally unselected failures remain unchanged. Annual AC is now documented, but **the selected hardware+dispatch fails the main model-wide 8760-hour feasibility screen**. Do not generalize the previous 8/8 sampled AC pass into annual pass.

## Remaining exact 2025 model AC failures

| Hour, local 2025 | Gross household P kW | Original/corrected inverter P kW | Min house V pu at PF .98 | Transformer loading % | PCC apparent kVA |
|---|---:|---:|---:|---:|---:|
| Nov 16 20:00 | 3.889757396 | 0 | .9493666354 | 83.606632 | 4.180332 |
| Nov 29 19:00 | 4.239682977 | .495467621 | .9498047086 | 81.138986 | 4.056949 |
| Nov 29 20:00 | 4.385864302 | 0 | .9470063251 | 94.390859 | 4.719543 |

All three fail only the lower voltage, not transformer or conductor limits. The 29 November 19:00 and 20:00 failures are **adjacent** and require jointly SOC-consistent dispatch, not two isolated maxima treated as additive.

## Independent three-event original battery donor screen (source only)

Reopened the exact original frozen SS90 annual energy CSV. The chosen prior same-day donor candidate hours were:
- **16 Nov 19:00 to 20:00**. Original 19:00 battery DC discharge 4.554079 kW, source-only PF.95 scalar maximum isolated deferral **4.094481 kW DC** (target import/no-export bound), up to ~3.889757 kW AC added at 20:00. Original store at both 19/20 is the modeled 1.374 kWh floor, so shifting battery discharge is necessary.
- **29 Nov 17:00 to 19:00**. Original 17:00 discharge 2.939809 kW DC, isolated cap **2.939809 kW DC**, additional AC ~2.792819 kW. Original 19:00 has 0.521545 kW DC discharge, target import 3.744215 kW.
- **29 Nov 18:00 to 20:00**. Original 18:00 discharge 4.057018 kW DC, isolated cap **4.057018 kW DC**, additional AC ~3.854167 kW. Original 20:00 has zero battery discharge and 4.385864 kW grid imports.

These are **individual source-only maxima** at PF .95 scalar kVA bounds, not simultaneous solutions or model AC passes. The 29 November donor-target SOC intervals overlap, so both fractions must be applied to a **single annual candidate frame** and audited together for hourly store, device power, annual energy and cyclic transition closure. Even a candidate that validates source algebra must pass the six selected donor/target hours at PF .98 and .95, with original Q controller, and must retain the previously corrected March/Nov 27 source P unchanged. No 2025-11-16/29 new AC run has been executed.

## Decision and next study

Prepare a bounded 3-event combined AC trial for the existing original A0 ten-house 94022 GIS and unchanged A1 SS90 hardware. The **candidate chronology must include all five shifts simultaneously**: March28 17→20 (50% source donor), Nov16 19→20 (test bounded), Nov27 17→20 (98% source donor), Nov29 17→19 and 18→20 (bounded together). Evaluate 16 Nov donor19/target20 and 29 Nov donors17/18 plus targets19/20 under PF .98/.95 with archived PF.98 baseline at selected hours. Limit new AC evaluations to a small candidate grid only, no repeat 8760 AC and no new LP/PyPSA hardware optimization. If a 3-failure correction passes source and paired-hour AC, one can reconstruct the PF .98 corrected 8760-hour AC from the saved source baseline and at most six freshly corrected AC hours, then independently audit the complete annual scenario. PF .95 annual uncertainty and service x1.3/1.6 afterward. No claim of field-validated EPM nameplate/phase/neutral/routing until evidence obtained.

Main protected, signed frozen runs, original 36/40/20 pilots, local untracked backup files untouched.
