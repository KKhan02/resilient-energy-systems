# Study A | A0 transformer 94022 | paired H01/H06 service study

**Evidence date:** 16 November 2026  
**Source:** User-run `StudyA_94022_DualService_Trial_v1_Results.zip`, SHA-256 `c0985268efa29d621273812ccefca23f24a3b57ad619359d476fc6d6bf670879`.

## What has been established

The uploaded ZIP contains 1,152 **converged** 60-Hz balanced-proxy AC solves: 16 resistance options × 9 selected 2025 timestamps × 4 fixed equipment/dispatch schedules × 2 PF/feeder-length cases. Exactly six options overlap the earlier sparse-bundle local experiment. The 432 overlapping AC records, including voltage and thermal values, match the previous uploads **exactly (maximum error 0)**. All 1,152 feasibility flags were independently recomputed from raw limits: min voltage >=0.95 pu, max voltage <=1.05 pu, transformer and line <=100%.

The *smallest passing bundle among the 16 tested options* is four electrical-model edges, each assigned **R × 0.5**:

| Model edge | Source identity | Original modelled distance |
|---|---|---:|
| 007 | Assumed service `T_47053144_0` to `HOUSE_H01` | 326.55 m |
| 004 | Assumed service `T_47053100_0` to `HOUSE_H06` | 315.27 m |
| 014 | Mapped EPM section 47053086, tapped graph piece | 83.17 m |
| 011 | Mapped EPM section 47053070, tapped graph piece | 67.00 m |
| **Total** | Modelled affected reference lengths | **791.99 m** |

This bundle passes **72/72** selected AC snapshots (original head reference **28/72**), with minimum household voltage **0.951267925 pu** (27 November at 20:00, PF 0.95, length ×1.6, H01 limiting), peak transformer loading **97.5130%**, maximum voltage 0.995011 pu, and maximum line loading ~11.70%. The 0.001268 pu voltage margin is exceptionally narrow. It must not be presented as robust field compliance.

Adding mapped edge 016 produces a 5-edge solution with **0.953224 pu** lowest voltage (72/72); adding 018 produces a 6-edge solution with **0.954500 pu** lowest voltage (72/72). These are larger bundles but have somewhat greater selected-hour voltage margins. No battery or PV equipment changed. Modelled annual energy imports and PV curtailment are not improved by this network-only resistance screen.

## Physical and methodological limitations

1. **Only nine selected hours and two sensitivity pairs:** This result does not validate the other seven PF/length combinations or all 8,760 annual hours. Reducing line resistance can change PV-injection overvoltage, losses and thermal conditions elsewhere in the year.
2. **No actual cable specification:** Halving resistance alone leaves reactance, ampacity, equipment and topology unchanged. The output is an electrical sensitivity, not a manufacturer cable selection or installed-cost estimate.
3. **Service routing is provisional:** The H01 and H06 326.6 and 315.3 m service-drop assumptions are particularly influential. H06 is one of the households reassigned out of A0 94022 under A1. Whether either long individual service is physically connected as modelled requires EPM/field evidence.
4. **Mapped EPM segments are split into modelled tap edges:** Edge indices 014 and 011 are not independent purchasable cables; upgrade boundaries and total installed lengths require GIS/source reconciliation.
5. **No new portfolio-wide AC pass claim:** The 432-case original and validated-dispatch portfolio is still 376 passing / 56 failing, including 32 A0 94022 and 24 proposed 92395 MST cases. The selected-hour network proxy does not overwrite that status.
6. **Comparison objective:** The A0 retrofit is a counterfactual. We should compare its cost and plausibility with A1 reassignment and check that A1's own feeder additions remain feasible, not assume A0 must be retrofitted.

## Next verification gate

The accompanying `studya_94022_allnine_targeted.py` tests five network options at **all nine PF/length settings** for the same nine timestamps, 4 schedules, 1,620 AC calculations in total. Options: head reference, four-edge R×0.5, five-edge R×0.5, six-edge R×0.5, and full-LV R×0.5 control. It reproduces all 360 overlapping source rows (five options × 72). It refuses any mismatched signed candidate annual schedule or original AC provenance, any incomplete factor grid, duplicate records, nonconvergence, or unaccounted source change.

**Not yet executed:** The new 1,620 targeted AC calculations require the user's local Miniforge/pandapower checkout. Seven source/logic regression tests and the module's local preflight passed in the assistant container. If the nine-factor targeted checks pass, the next engineering stage is a physically specified *grouped cable* sensitivity with the actual transformer/service evidence, followed by a genuine full-year AC replay and a cost comparison with A1.

Do not use the four-edge passing result to claim 8,760-hour reliability, field cable requirements, energy-cost optimality or the benefits of a new battery size. PV curtailment and PV/BESS hardware redesign remain a separate research problem.
