# Study A1 106039 | PV/BESS sizing decision checkpoint

**Evidence date:** 19 November 2026. **Network:** A1 106039 11-house provisional EPM balanced LV model, assumed 5 kVA transformer, 2025 hourly synthetic household demand. Cost model is annualized historical equipment and USD 0.29/kWh purchases, excluding installation, verified feeder works and full network-loss settlement. This is research modelling, not utility approval.

## What is already verified

- The complete `StudyA_A1_106039_Utilization_v1/FRONTIER_RECEIPT_FULL.json` reports 10 fixed-hardware annual PyPSA solved/reused cases plus two signed references. All 8,760-hour schedules passed energy-only checks; energy-only is not an AC certificate.
- `StudyA_A1_106039_PV_TieBreak_GridReserve_Full_v3/RUN_MANIFEST.json` and `Stress_v3` document the **MC_REF** Stage2 and evening reserve 8,760-hour source-stitched AC result: all nine PF/length scenarios converge and satisfy the main 0.95–1.05 pu, transformer and line constraints. Two original PF .95 evening transformer overload hours reduce to zero with unchanged annual imported energy and terminal battery SOC. Worst peak 99.431815% at PF .95, length x1.6; worst min voltage 0.957240 pu. This does NOT pass the stricter 0.97 pu sensitivity criterion.
- `StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1/ANNUAL_AC_MANIFEST.json` independently reports **MC_B9** and **SS_B9** corrected 9/9 annual AC factor cases, using their own corrected schedules, signed original 8,760-hour AC and precisely replayed changed hours. Both have zero corrected main-band failures, worst peak 99.431815%.
- The original signed `StudyA_A1_106039_NewHardware_AC_Stress_v1/PORTFOLIO_AC_NEW_HARDWARE_STRESS.json` shows uncorrected **MC_B10**, **SS_B10** and **SS_P45_B9** all converge for 8,760 hours at PF .95/length x1.6, but respectively have two, one and one AC violations. No corrected AC result yet exists for these hardware cases.

## Annual hardware and dispatch tradeoffs

| Portfolio | PV panels | Battery modules | Imports kWh/year | Curtailment kWh DC/year | Battery cycles/year | Equipment + import USD/year | Current network evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| MC_REF | 41 | 8 | 3107.49 | 2443.60 | 294.46 | 4416.47 | **Stage2 reserve corrected 9/9 main-band pass** |
| MC_B9 | 41 | 9 | 2792.93 | 2095.07 | 270.72 | 4471.70 | **Own B9 correction 9/9 main-band pass** |
| MC_B10 | 41 | 10 | 2646.99 | 1933.36 | 247.40 | 4575.82 | Original stress 2 AC failures; correction pending |
| SS_REF | 49 | 8 | 2034.60 | 5492.23 | 322.19 | 5056.59 | Older separate reference correction, not this new pilot |
| SS_B9 | 49 | 9 | 1478.23 | 4875.76 | 302.27 | 5041.70 | **Own B9 correction 9/9 main-band pass** |
| SS_B10 | 49 | 10 | 1184.51 | 4550.31 | 279.60 | 5102.97 | Original stress 1 AC failure; correction pending |
| SS_P45_B9 | 45 | 9 | 2011.57 | 3348.49 | 289.79 | 5069.91 | Original stress 1 AC failure; correction pending |

These figures come from `FRONTIER_ANNUAL_SUMMARY_FULL.csv`. A changed battery schedule that preserves imports and hardware leaves the base annual equipment-plus-import cost unchanged, but any new operational cost, replacement wear, loss charge or real CAPEX has not been priced.

## Exact questions answered and still open

**Cost versus self-sufficiency:** Relative to MC_REF, MC_B9 imports 314.56 fewer kWh/year at USD 55.23/year higher equipment-plus-import cost. MC_B10 could reduce imports another 145.94 kWh/year relative to MC_B9 but costs USD 104.13/year more. SS_B10 imports 293.72 kWh/year less than SS_B9 but costs USD 61.27/year more. These comparisons are conditional on existing equipment tariffs and do not establish a final installable choice.

**PV curtailment:** SS_P45_B9 has 1527.27 fewer curtailed DC kWh/year than SS_B9, but 533.34 more grid-import kWh/year and USD 28.22/year greater combined annual cost. Thus curtailment, import reliance and cost must be shown on separate axes, not reduced to one ungrounded efficiency score.

**Battery utilization:** Adding modules can reduce import reliance while increasing effective battery capacity and reducing equivalent full-discharge cycles per year. The trial must retain manufacturer physical SOC floors, battery DC limits and annual cyclic dispatch.

**AC limitations:** Neither the source AC stress failures nor a prospective reserve shift proves all-nine failure or success. The proposed pilot first tests each new hardware case's *own* 2025 schedule at PF .95/length x1.6 using the original pandapower solver. Only if that passes should the other eight factors be generated and overlaid with each case's own signed annual AC. Existing MC_REF and B9 corrected results cannot be copied.

**Geographical uncertainty:** Real 106039 transformer nameplate, phase allocation, H11 and H16–H25 physical service attachments, cable lengths and conductor types remain provisional. The 0.5682 percentage-point worst remaining transformer headroom must be treated as limited margin, not field-certified robustness.

## Next reproducible gate and GitLab workflow

The new runner `new_hardware_reserve.py` and its 5 synthetic regression tests are committed at `case1/studies/SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19/`.

1. User pulls the active sync branch and runs the five tests. Run `--preflight-only` to verify all three signed energy and AC originals and the proposed annual energy-neutral shifts, with no output folder creation.
2. User executes the stress pilot locally. The runner produces versioned `StudyA_A1_106039_NewHardware_Reserve_Stress_vN/` hourly schedules, changed-hour AC CSVs, manifest and audit figures. Inspect any failures without disguising them.
3. If validated, user selectively `git add` only the successful result folder, commit `[ci skip]`, rebase and push to `sync/seedexchange-local-2026-11-17`.
4. Assistant independently reviews the pushed source hashes, annual SOC/PV/energy, changed AC hours, failures and plots, updates `PROJECT_HANDOVER_LIVE.md`, then prepares the original nine-factor network replay only for justified finalists.
5. Return to the approved broader **Study A** cohort and A0/A1 geography comparison, then **Study B** STAR/MST and **Study C** Site A against existing 94022 or the explicitly hypothetical new transformer. Do not silently substitute one network for another.

The current package does not rerun the archived 6,840 investment optimization, change saved input data or merge `main`.
