# Study A1 106039 | Completed AC-validated PV/BESS economic frontier
**Date:** 21 November 2026. **Status:** Derived from independently reviewed, signed source results in GitLab. This is a provisional research outcome, not field certification or complete installed-project economics.

## Scope and interpretation

The six designs below have distinct signed 2025 hourly PV/BESS schedules and independently validated 9-case main AC sensitivity outcomes (PF 0.95/0.98/1.00 × service-length multipliers 1.0/1.3/1.6). Four underlying AC study branches are combined, without rewriting their archives: MC_REF corrected PV-priority schedule; MC_B9 and SS_B9 own signed B9 reserve overlays; and newly completed MC_B10, SS_B10, SS_P45_B9 source-equivalent annual AC campaigns. The cohort is 11 households H11,H16–H25 attached provisionally to EPM transformer 106039, **assumed 5 kVA**, with 2025 stochastic demand **20,878 kWh**. Same balanced electrical model, provisional GIS/service attachments, zero export, and default nighttime inverter reactive Q off apply. Only actual modelled input equivalence allows AC reuse; an 8,760-hour stitched annual result is distinct from an independent fresh 8,760-hour pandapower campaign.

## The six comparable validated hardware choices

| Portfolio | PV panels | Battery modules | Annual imported kWh | Annual PV curtailed DC kWh | Equivalent battery cycles | Equipment + grid USD/year | PF .95 ×1.6 losses kWh/year |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MC_REF | 41 | 8 | 3107.5 | 2443.6 | 294.46 | 4416.47 | 440.35 |
| MC_B9 | 41 | 9 | 2792.9 | 2095.1 | 270.72 | 4471.70 | 438.06 |
| MC_B10 | 41 | 10 | 2647.0 | 1933.4 | 247.40 | 4575.82 | 436.95 |
| SS_B9 | 49 | 9 | 1478.2 | 4875.8 | 302.27 | 5041.70 | 427.13 |
| SS_B10 | 49 | 10 | 1184.5 | 4550.3 | 279.60 | 5102.97 | 425.08 |
| SS_P45_B9 | 45 | 9 | 2011.6 | 3348.5 | 289.79 | 5069.91 | 431.50 |

Every entry has 9/9 reconstructed annual main-limit AC case-passes. For the PF .95, length x1.6 stress condition, all six share **maximum transformer loading 99.4318148586%** and **minimum voltage 0.957239659 pu**. This means only 0.568185 percentage points of headroom relative to the assumed 5 kVA limit, with unverified physical nameplate and topology. The 0.97–1.03 pu strict sensitivity fails for each new-hardware option, even though the accepted 0.95–1.05 pu main research screen passes. The equivalent battery-cycle measure is a modelled discharge/usable-capacity indicator, not verified battery lifetime.

The source annual cost equals `annual_equipment_usd + annual_grid_import_usd` with an implied USD 0.29/kWh electricity purchase assumption. It is the archived 25-year 6% discount model's annualized equipment assumption, not a site quotation. The future cost of real cables, transformer retrofit, protection, taxes, installation, metering, battery replacement/degradation, grid-use charges and any network AC-loss settlement is outside this base cost. Existing modelled AC losses are reported separately and must not be silently double-counted with a retail bill.

## Incremental storage tradeoffs, same PV and inverter sizes

| Design change | Reduction in annual imports kWh | Extra annual equipment cost USD | Change in total annual cost USD at $0.29/kWh | Break-even import tariff USD/kWh for extra equipment |
| --- | ---: | ---: | ---: | ---: |
| MC_REF to MC_B9 | 314.6 | 146.45 | +55.23 | 0.466 |
| MC_B9 to MC_B10 | 145.9 | 146.45 | +104.13 | 1.003 |
| SS_B9 to SS_B10 | 293.7 | 146.45 | +61.27 | 0.499 |

Adding a ninth battery module to MC_REF improves 2025 imports by **314.6 kWh** but increases the modelled annual equipment-plus-import cost by **$55.23** at the base tariff. Adding a tenth MC module saves another **145.9 kWh** but costs **$104.13** more per year. Adding the tenth SS module saves **293.7 kWh** for an extra **$61.27** per year. The results are robust energy accounting but tariff/price sensitive investment judgments.

### Curtailment is a separate objective

At the current cost and grid-import objectives only, **SS_P45_B9 is dominated by SS_B9**: it costs **$28.22** more and purchases **533.3 kWh/year** more. However, removing four PV panels cuts its annual PV curtailment by **1527.3 kWh DC**. It is still a meaningful candidate for a **three-objective** cost/import/curtailment comparison and possible physical PV-area constraint. Less curtailment by itself does not prove better economics.

### Illustrative electricity-tariff decision sensitivity

With annualized equipment costs and import quantities held fixed, `modelled annual cost(t) = equipment annuity + t × imported kWh`. For just these six AC-validated choices, the minimum-cost hardware changes from **MC_REF** to **MC_B9** near **$0.4656/kWh**, then to **SS_B10** near **$0.6825/kWh**. At the archived $0.29/kWh, **MC_REF** has the lowest annual model cost; **SS_B10** has the lowest imports and highest modelled self-sufficiency (**94.33%**). These are analytic break-even tariffs, **not Colombian tariff forecasts**. Other option dimensions, actual works, aging and capacity costs may shift these crossings.

### Network-loss sensitivity

The PF .95 ×1.6 annual AC losses range from 425.08 to 440.35 kWh/year across the six candidates. Valuing losses at the source retail tariff, strictly as an *illustrative additional charge if those losses are not already paid*, gives $123.27 to $127.70 per year. This cannot be added to the base objective without establishing settlement and avoiding double counting. Compared with equipment-cost differences the pairwise loss-cost variations are small.

## Audited full new-hardware annual AC implementation

The user-pushed GitLab commit `b2fdfe6b13c5077b3ac6d2131042b8697e1c5ace` contains `StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Full_v1/`. Independently opened its complete `RUN_MANIFEST.json`, `ANNUAL_AC_PAIRED_SUMMARY.csv`, all **27** individual `CASE_RECEIPT.json` files, and all **27** `AC_NEW_SOLVED_HOURS.csv` ledgers. All individual receipts match their manifest cases. Each delta file has exactly the recorded number of original and reserve rows, with unique timestamp/phase identities; all new records converge; all **72** corrected AC replay records match the independently saved `NewHardware_Reserve_NineFactor_v1` for inverter P, household voltage, transformer/line loading, losses and PCC kVA within the 2e-7 recorded CSV-value comparison. This is an independent **file and numerical consistency audit**, not a new AC solver execution.

Full campaign: **27 × 8,760 = 236,520** annual case-hours converged and no main-limit failures; **9,256** original nonidentical hours newly solved, **227,264** original annual case-hours reused from source-equivalent B9 or case-owned stress AC, **72** reserve corrections re-solved and matched, with **72** independent same-input source control replays. The source-stitch process avoids repeating 210,240 original missing-factor AC solves; it does not certify field conductors or unbalanced phases. All 27 hardware/factor cases fail the stricter 0.97–1.03 pu voltage sensitivity for some hours, and their individual exact strict-band counts remain saved in the source manifest. The source original nine-factor AC is validated only for this mapped 11-house cohort.

Source pointers:
- Energy and source equipment economics: `StudyA_A1_106039_Utilization_v1/FRONTIER_ANNUAL_SUMMARY_FULL.csv`.
- MC_REF full annual corrected: `StudyA_A1_106039_PV_TieBreak_GridReserve_Full_v3/RUN_MANIFEST.json`.
- MC_B9 / SS_B9 full nine-factor: `StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1/ANNUAL_AC_MANIFEST.json`.
- MC_B10 / SS_B10 / SS_P45_B9 27-case: `StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Full_v1/RUN_MANIFEST.json`.
- Strict source-stitch source code: `case1/studies/SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19/new_hardware_annual_ac_stitch.py`.

## Next work, respecting the approved research contract

**Complete Study A's common-household A0 versus A1 comparison before starting a new hypothetical Study B/C physical network.** The approved `case1/RESEARCH_SCOPE_APPROVED_2026-11-07.md` explicitly requires the original EPM assignment cohorts and a matched 34-house electricity, cost, loss and AC feasibility comparison rather than comparing dissimilar 10-house A0 94022 to 8-house A1 94022 as equal-demand systems. The A0 106039 12-house sequential redispatch has already passed 36 annual factor/dispatch cases with near-zero voltage and transformer margins. The A0 94022 hypothetical five-edge improvement passed 36 cases but its proposed segments and 50% resistance reduction are not field-verified. Preserve the original non-retrofit A0 94022 failures and separate conditional variant; do not turn cable hypotheses into a costed engineering solution. The proposed 92395 STAR/MST belongs under Study B, with unavailable mapped EPM LV backbone and separate physical evidence requirements. Site A and 94022 interconnection remain Study C questions. Northern 25 kVA transformer excluded.

**Next immediate, read-only task:** inventory the saved A0/A1 34-house, per-cohort 2025 cost/import/PV/BESS and AC summaries; define one matched population/dispatch/network scenario contract and source provenance for a non-double-counted A0-vs-A1 comparison. Only then design a focused missing-input or local simulation gate. Do not rerun the archived 6,840 optimizations by default.

This report is source-derived. No new physical data, economic quote, simulations or unapproved optimizer inputs were invented.
