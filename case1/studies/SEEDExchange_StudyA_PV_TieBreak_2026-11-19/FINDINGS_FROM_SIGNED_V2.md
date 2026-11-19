# Signed two-stage PV tie-break, 19 November 2026: completed results and interpretation

## Sources and research status
- Branch `sync/seedexchange-local-2026-11-17`, user push `dd130dde`; full `StudyA_A1_106039_PV_TieBreak_Local_v2/RUN_MANIFEST.json` status `COMPLETE_TWO_STAGE_ENERGY_ONLY_NOT_AC_VALIDATED`, both cases, no errors and four 8,760-hour source-signed CSVs.
- Study A/A1 106039 is the **11-house** geographically reassigned cohort, with provisional 5 kVA transformer, 2025 independent synthetic load profiles. PF=0.98 scalar grid-import planning proxy; this is **not an electrical AC replay, device certification, actual EPM rating, or PV-first causal controller**.
- Both Stage 1 full-year LPs reproduced original source imports within <0.000001 kWh. The Stage 2 optimization preserved annual imports to numerical precision and allowed at most +0.1 DC kWh of annual battery throughput.

## Annual results
| Metric | MC_REF 41 panels Stage 1 | MC_REF Stage 2 | MC_P33 33 panels Stage 1 | MC_P33 Stage 2 |
|---|---:|---:|---:|---:|
| Grid imports AC kWh | 3107.485122634 | 3107.485122634 | 5227.091894141 | 5227.091894141 |
| PV curtailment DC kWh | 2443.604268956 | 2443.601704853 | 549.292445908 | 549.289881806 |
| Weighted early-day curtailment score | 3821.969399398 | 3361.119533051 | 870.613515036 | 741.272587386 |
| Annual DC battery throughput kWh | 19805.502608878 | 19805.602608878 | 15892.764112114 | 15892.864112114 |

Annual curtailment differs by only ~0.00256 DC kWh in each case, while the early-day score decreases by 12.06% and 14.86%. This is a **timing redistribution**, not PV efficiency improvement or reduced purchases.

## Independent hourly comparison of four signed CSV files
For a strict hourly difference >1e-5:
- MC_REF: changed curtailment 1363 hours, changed inverter/grid import 68 hours; sum of absolute hourly PV-curtailment changes 4806.729831 DC kWh; sum of absolute grid-import changes 83.134520 AC kWh; largest import-hour change 2.774903 kW (2025-05-16 21:00); largest battery SOC difference 32.768 kWh (2025-06-20 11:00).
- MC_P33: changed curtailment 495 hours, changed inverter/grid import 95 hours; sum of absolute hourly PV-curtailment changes 1098.582328 DC kWh; sum of absolute grid-import changes 126.891092 AC kWh; largest import-hour change 3.542692 kW (2025-11-13 20:00); largest battery SOC difference 21.383011 kWh (2025-06-20 10:00).
- Example MC_P33, 2025-06-20 09:00: Stage 1 8.425714 DC kWh curtailed, Stage 2 zero; Stage 2 charges 8.425714 DC kWh. At 13:00 Stage 1 zero curtailment vs Stage 2 8.700913 kWh curtailed because SOC=34.6 kWh. Net annual import unchanged.
- The change in **hourly** PCC imports could alter voltage, transformer/line loading, reactive control and losses even without changing annual imports. Do not equate annual grid energy equality with AC equivalence. Total-absolute-difference amounts are temporal redistributions and must not be reported as energy savings.

## Follow-up AC gate
New GitLab source `case1/studies/SEEDExchange_StudyA_PV_TieBreak_AC_Delta_2026-11-19/` reuses v6 source GIS/ac controller to check paired grid-injection change hours (68 MC_REF, 95 MC_P33). Baseline PF .98 length1.0 first; then all 9 PF/length combinations (0.95/0.98/1.00 and 1.0/1.3/1.6), with modeled head-connected inverter and conservative Q-off after daylight. The approved v6 local input manifest and original household profiles are SHA checked; Stage1/Stage2 timebase and hourly demand must match. The proposed source contains regression tests but **has not yet been executed on the user's pandapower workstation**.

Only matched changed-hour AC validation is attempted; no silent substitution of old annual AC baseline. Even if all paired changed-hour checks pass, this alone is not a fresh full-year AC certification and does not erase earlier source AC failures. Follow full source code instructions in the AC delta folder, then push new output independently.

## Research continuity
- No alteration to signed source economic portfolios, archived 6,840 investment jobs, original 376/432 AC configurations or conditional 408/432 overlays.
- AC stress reference SS_P45_B9 / MC_B10 / SS_B10 remains 1/2/1 failed transformer overload hours at PF .95 and 1.6 length.
- Approved prioritization remains Study A complete network/equipment feasibility first, then B compact spatial STAR/MST groups, then C Site A and architecture comparison.
