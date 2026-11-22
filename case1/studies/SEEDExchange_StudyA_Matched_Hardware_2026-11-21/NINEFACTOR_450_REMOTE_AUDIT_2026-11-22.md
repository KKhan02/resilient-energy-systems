# Study A 113699 | Independent 450-row nine-factor sensitivity source audit

**Date:** 22 November 2026
**User result commit:** `ce8301b6339d34b7125e0e2f7a27da1bdb8620bb`
**Source folder:** `StudyA_A0_A1_MatchedHardware_113699_NineFactorStress_v1/`
**Method:** Read-only inspection and numerical recomputation from complete GitLab CSVs. No new AC, LP, MILP, GIS or hardware optimization solves.

## Verification

- Parsed original 450-row `factor_ac_hourly.csv`, all 18 rows `factor_summary.csv`, `RUN_MANIFEST.json`, plus both original 8,760-row AC reference CSVs. All required files exist in GitLab.
- **450 distinct** hardware-origin × PF × length × timestamp case-hours, exactly 25 common distinct source timestamps for each of the 18 factor groups, with no duplicate factor combinations or missing timestamps.
- **450/450 converged**, no AC failure, 0 model thermal-overload cases. Recomputed principal 0.95–1.05pu/100% flags and optional 0.97–1.03pu flags directly from numeric data for all 450 rows. Every source feasibility flag agrees.
- **50/50 sampled PF=.98, service length=1.0 reference AC rows**, 25 for each equipment origin, match **exactly** against the original complete 8,760h saved AC sources on nine separate numerical fields: gross demand, inverter AC power, min/max bus voltage, max transformer/line %, loss kW, PCC kVA and Q selected. Maximum absolute discrepancy at saved precision: **0**.
- Independently recomputed all 18 group minima/maxima, sampled loss sums, strict-voltage hour counts and main failure counts. All match `factor_summary.csv` to float precision. Manifest `new_AC_solves=planned_AC_solves=450`, `factor_groups=18`, `reference_pf098_length1_reproduced=true`, `annual_AC_verified_for_nine_factors=false`. Source result status correctly **SAMPLED_NINEFACTOR_MAIN_BAND_VIOLATIONS_RECORDED**.
- 12 main-band voltage failures across repeated factor-case hours, **all PF=.95**, none from transformer/line loading. Main failures by unique timestamp: November 30 20:00 appears in six factor-origin combinations, March 30 19:00 in four, March 14 19:00 in two. Only three distinct timestamps. Recomputed **241 strict under-.97 sampled case-hours** across 18 different groups, **not 241 distinct annual hours**. No above 1.03 pu.
- A0-origin hardware sample under PF=.95: **1,3,3** main failures at length x1.0,1.3,1.6; A1-origin **1,2,2**. PF=.98 and1.00: **0** main failures in all 12 factor-origin groups.
- PF=.95/length1.6 worst modelled minimum voltage **0.948734337 pu**, maximum transformer loading **99.373870%**, maximum line loading **11.061548%**, identical sampled extremes for both hardware origins. This is near the assumed 3kVA transformer thermal bound despite no recorded overload.

## Interpretation and bounds

The two previously audited 8,760-hour baseline replays remain reference AC passes at PF .98 length1.0 for BOTH fixed battery schedules. The nine-factor experiment evaluates 25 *selected* common hours per factor and cannot establish new annual PF .95 or PF1.0 certificates. The stricter old .97pu research band still fails and must remain separate from the chosen .95pu principal research magnitude screen. The available result supports **conditional low-PF voltage vulnerability**, not unbalanced phase-neutral calculations, field transformer/nameplate confirmation, true service wire routing, utility permission, or installation resilience.

**Poster curation:** Two new source-traceable vector diagrams under `case1/professor_walkthrough/15_Matched_Hardware_and_AC_Robustness/`, covering (a) 34-house matched-hardware *energy-only* geographic-control outcome from independently audited full 16-case source, and (b) this 113699 sample sensitivity. The latter should not be presented as a full-population AC result.

**Decision:** Stop further ad hoc 113699 test expansion. Request actual EPM PF, circuit phases, transformer rating and service-wire observations. A decision-critical PF.95 full annual replay may be commissioned later, but prioritize consolidated Study A multi-territory PV/BESS cost, curtailment, operation and grid results; then Study B and C. No new solver work or source changes in this audit.
