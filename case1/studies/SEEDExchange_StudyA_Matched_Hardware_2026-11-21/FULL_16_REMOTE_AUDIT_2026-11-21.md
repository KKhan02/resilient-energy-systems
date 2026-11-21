# SEEDExchange Study A | Full 16-case matched-hardware source audit and external-review disposition

**Date:** 21 November 2026
**Audited source commit:** 120c4e966dfd089eb25116a85c2d5ae027dfd5ca
**Branch:** sync/seedexchange-local-2026-11-17
**Source folder:** StudyA_A0_A1_MatchedHardware_Full_v1
**Audit method:** read-only GitLab source inspection and independent numeric recalculation. No new LP, MILP, pandapower, or network-physics solve.
**External reference:** user-provided "Case 1 consolidated review", from October 24 through Round 7 covering events to November 8, 2026. This is a historical reviewer snapshot, not a live 21-November audit.

## 1. Confirmed current result and scope

- Final manifest: ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING; scope full; completed 16/16; error dictionary empty; new AC cases 0; expected new annual PyPSA fixed-hardware LP solves 12.
- Reuse: two original 106039 opposite-target exact-equipment schedules, A1-hardware-to-A0 113699 initial signed pilot, and independently audited A0-hardware-to-A1 113699 reverse signed pilot.
- Four changed transformer territories: 106039, 94022, 113699, 85398. Equipment origin A0 or A1, each min_cost or ss90. At each transformer, freeze PV panel count, battery module count, battery DC continuous power, inverter kVA and assumed transformer nameplate across A0/A1 load assignment.
- Existing proposed 92395 STAR four-house energy cohort H30/H31/H32/H33 is shared on both sides and counted once per portfolio. H08 on support-only unmapped transformer 98380 is excluded on BOTH sides.
- Both A0 and A1 contain the same 34 distinct synthetic profiles, annual gross demand 64532 kWh. PV/meteorology is the same original NASA source, perfect-foresight 2025 PyPSA energy chronology. No export or unserved energy; no actual EPM tariff or feeder costs established.

## 2. Independent 2025 energy and provenance checks

- Opened and compared 16 saved per-case CASE_RECEIPT.json files against their top-level RUN_MANIFEST.json entries: 16/16 exact matching serialized fields, four reused method flags and twelve new method flags consistent with manifest.
- Independently opened all **12 new 8,760-row hourly CSVs**, 105,120 annual target-hour records. Every CSV source signature reproduced exactly when restoring original Windows CRLF from GitLab-normalized LF; every series has 8,760 unique consecutive local timestamps for calendar 2025.
- For all 12 new files, recomputed demand/import/PV availability/curtailment/charge/discharge sums and compared to case receipts at within 0.0002 kWh. All 12 passed finite value, zero grid export, zero ENS, no simultaneous battery modes, 20% physical SOC floor (using original Store coordinates), model Store ceiling, battery DC power, inverter active-power rating and assumed PCC apparent-power proxy bounds.
- Independently recomputed hourly inverter-side active power closure (grid import + inverter - demand - grid export - unserved), PV availability closure, cyclic Store SOC balance with sqrt(0.95) battery charging/discharging, and sqrt(P²+Q²) apparent power proxy. Max cyclic SOC residual across 12 new cases approximately 1.48e-10 kWh; active-power and PV closure residuals approximately 1e-10 kW.
- Exact reused two 113699 pilots were separately audited before full result. Two 106039 original same-hardware schedules were source-signature/dispatch checked before the run. This audit did not independently re-solve source optima; optimizer success is a saved user-run result, not a proof of global solver integrity.
- Reconstructed all **eight 34-house portfolio rows** from all four territory case receipts + separate signed shared 92395 energy/source entries. Eleven numeric portfolio fields in each row matched at tolerance 1e-5. Independently recomputed A1-minus-A0 imports, annual costs and curtailment for each of four matched pairs, matching saved pair CSV at 1e-5.

### Controlled matched-equipment comparisons (A1 minus A0)

| Frozen hardware origin | Tier | Fixed PV panels / batteries / total inverter kVA | Delta imports (kWh/year) | Delta annual equipment+import USD/year | Direction |
| --- | --- | --- | ---: | ---: | --- |
| A0 | minimum cost | 126 / 23 / 37.0 | +159.371 | +46.217 | A0 lower imports/cost |
| A0 | SS90 | 146 / 29 / 47.0 | +1424.628 | +413.142 | A0 lower imports/cost |
| A1 | minimum cost | 122 / 23 / 36.0 | -1070.384 | -310.411 | A1 lower imports/cost |
| A1 | SS90 | 146 / 28 / 48.6 | -2204.165 | -639.208 | A1 lower imports/cost |

**Interpretation:** Same annual gross demand and fixed equipment within each pair isolate a *modelled household-assignment and aggregation effect on the perfect-foresight energy-only optimizer*. The outcome changes sign with equipment origin. No assignment is a demonstrated universal energy winner. This does not isolate real geographic electrical merits: feeder distances, drops, phase imbalance, losses, protection, installation cost and true transformer connections are not included in these results. Avoid comparing percentages across tiers as a physical superiority test.

## 3. External review: current relevance and status checked against live branch

**Verified safe in this specific matched-hardware set:** Manufacturer Deye SE-G5.1 evidence register (case1/studies/ac_aware_redispatch_v1/HARDWARE_EVIDENCE_2026-11-04.md) requires conservative 50A * 44.8V = 2.24kW maximum continuous battery DC power per module; fixed_hardware.py explicitly checks this before calling PyPSA. Across all four frozen hardware origins and shared 92395 tiers, highest saved nameplate battery power ratio is **1.92 kW per module**, under 2.24. Independent 12-new-hourly power checks passed. This is a screening statement, NOT verified BMS, installation or three-phase compatibility.

**Still open in historical WP1 v3:** case1/run_case1_v3.py still forces power_limit=5.0 kW for every nonzero battery in headline sweep. Source case1/results/PCC_screened_designs.csv has **3,599** rows, 330 of which have two batteries at 5 kW total (2.50 kW per module), beyond the 2.24 kW/module screen. The older saved case1/results/RUN_MANIFEST.json still reports screened_no_grid_ens=3909, inconsistent with those 3,599 saved screened rows. Review's old denominator "330 of 3,304" refers to another historical snapshot. Do not silently relabel these old rows valid, alter old files, or conflate their legacy causal-dispatch sweep with the new source-verified PyPSA experiments.

**Still open as historical documentation:** Ten saved pypsa_joint_optimization_v1/outputs/*/model_manifest.json files checked, and **0/10** has an explicit perfect_foresight flag or comparable local wording. Newer higher-level narrative does label perfect-foresight planning benchmarks, but the old per-case artifacts remain unlabeled. Recommended fix is an index/sidecar provenance register, not mutable edits to signed historical results, unless regeneration with new versioning is approved.

**CI gap persists:** Latest GitLab pipeline on 120c4e96 is **skipped**, ID 3097652012, and the previous recent sync-branch pipelines were also skipped. Current .gitlab-ci.yml does not have a dedicated new matched-hardware reciprocal suite job. The local user's tests and signed runs are not equivalent to current GitLab CI passing. The attached review correctly corrected its earlier mistaken GitHub-vs-GitLab assertion: GitLab CI exists and has run historically. CI execution and scope for the current research branch remain open. Do not trigger new jobs or alter CI configuration without considering runner budget.

**Historical findings reported as already resolved in the attached review:** G1a/G1b conservation/backlog, pvlib branch, DatetimeIndex guard, SOC boundary diagnostics, core test/requirement pinning, selected plotting fields and replacement rules. Those do not invalidate the new independent energy-only checks. Older annual_shared_pvbess annual_screen battery-coupling and duplicate dispatch implementations remain possible comparability risks for historical architecture screens, not directly tested in this audit.

## 4. Next engineering gate: AC feasibility of matched-hardware assignments

1. **Strict source preflight, no solver:** identify signed GIS customer IDs/coordinates, transformer names and assumed kVA, A0 and A1 feeder attachment maps for four named territories. Prove that each moved H03/H06/H13 has a specific *provisional* electrical attachment in the target territory. Confirm phase/base-kV and existing source pandapower model assumptions; reject accidental 94022 five-edge retrofit or proposed 92395 STAR/MST mixing in Study A base case. Carry source hashes.
2. **Bounded AC pilot:** perform original and cross-assigned minimum-cost 113699 source checks with source-appropriate A0/A1 feeder geometries, default PF=0.98 and service-length x1.0, starting with load-only and stress-hour checks. Validate that the fixed-hardware energy PCC proxy agrees on injection sign convention; record voltage extremes, nonconvergence, transformer % kVA, line ampacity, P/Q, and losses. Classify failed hours, not only pass/fail totals.
3. **Corrected dispatch only after source AC evidence:** if AC violates, perform feasible Q/P redispatch with the exact frozen PV/BESS/inverter hardware and 8760-hour physical SOC; never copy old SOC-aware trajectories to the new load case. Recheck AC after correction.
4. **Expand conditional annual testing:** after pilot source and routing QA, use existing signed original AC where exact inputs match; otherwise independently model mismatched source hours. Evaluate PF .95/.98/1.00 and lengths 1.0/1.3/1.6 (nine factors) on the matched cohorts, with the 0.95-1.05 pu principal research band and 0.97-1.03 pu strict sensitivity. Keep assumptions and conditional 94022 five-edge results separate.
5. **Economics after AC:** correct annual losses on exact same-hour signed old/new power flows; include required hypothetical cable/utility equipment, actual metering and EPM approval as open variables, not zero cost. Keep balanced proxy and manufacturer compatibility caveats in any decision.

**Final status:** INDEPENDENTLY VERIFIED ENERGY-ONLY FULL 16 RECIPROCAL CASES. AC PENDING. Historic WP1 v3 artifact corrections/CI remain separate workstreams. No field or installation approval. No numerical solver run by assistant in this review.
