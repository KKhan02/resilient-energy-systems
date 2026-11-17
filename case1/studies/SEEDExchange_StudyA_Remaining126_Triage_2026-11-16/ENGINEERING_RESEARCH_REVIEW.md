# Study A, final remaining 126 sensitivity runs: engineering triage

**As of 16 November 2026.** Read-only independent assessment of `StudyA_Remaining_AC_And_PV_Diagnostics.zip`. Historical annual source outputs are unchanged. This review is conditional on synthetic household demand, EPM-mapped backbone where available, modelled service drops and conductor values, a balanced hourly AC proxy, and unverified transformer ratings for some territories. No new dispatch solution or electrical simulation was executed in this review.

## Data completeness and counting rules

`EXTRACTION_QA.json` reports 126/126 remaining AC sensitivity cases read and verified, 1,531 failing case-hour records, 586 distinct events after grouping by `(A0/A1, transformer, hardware tier, hardware family, topology, dispatch, timestamp)`, and 44 annual PV-curtailment summaries (22 equipment configurations × optimized/causal). Its issues list is empty. Our independent CSV checks confirm these counts, the unique event keys, all 1,531 events at local clock 18:00–22:00 with no PV generation, and all case-hour failures involving voltage below 0.95 pu or transformer loading above 100%. These records include repeated PF × length conditions; they are NOT 1,531 unique real-world timestamps, nor 126 unique physical installations.

The 586 grouped events consist of **544 voltage-only, 17 transformer-only, and 25 combined** events. At the original 1,531 case-hour level, **1,276 voltage-only, 179 transformer-only and 76 combined**. The worst line utilization in the remaining event extract is below 100%; the dominant constraints are household voltage and transformer thermal capacity.

| Territory/network | Distinct design-hour events | Failing case-hour records | Worst voltage (pu) | Highest transformer loading | Assessment |
|---|---:|---:|---:|---:|---|
| A0 / 92395 / proposed MST | 411 | 938 | 0.93161 | 41.59% | Route / remote voltage, not transformer |
| A0 / 94022 / mapped | 112 | 310 | 0.93728 | 98.20% | Evening voltage; potential dispatch + feeder improvements |
| A0 / 106039 / mapped | 44 | 234 | 0.94122 | 119.38% | Thermal and low-voltage; dispatch alone not yet proven |
| A1 / 94022 / mapped | 12 | 12 | 0.94799 | 71.28% | Small stressed-hour undervoltage; targeted battery reserve trial |
| A1 / 113699 / mapped | 4 | 16 | 0.94771 | 104.36% | Small number of combined voltage/thermal failures |
| A1 / 106039 / mapped, causal only | 3 | 21 | 0.95424 | 107.43% | Causal dispatch residual; optimized schedule already corrected |

**The 411 grouped 92395 MST events are 70.1% of remaining grouped events.** Among its 938 repeated case-hour records, 787 (83.9%) have *zero net grid import*, yet remote voltage still violates the lower threshold. This is consistent with voltage drops within a long or poorly located distribution route downstream of the shared PV/BESS bus. Moving more power at the head may not cure the remote voltage if behind-the-head household currents remain. The 92395 MST is a **hypothetical routing alternative because EPM LV geometry is missing**, not a documented utility wiring arrangement. The separately tested 92395 STAR case has zero remaining violations in the nine PF/length cases in the signed portfolio. STAR is electrically preferable *under these assumptions*, but its larger modelled cable length must be priced and optimized before a design recommendation.

At the mapped feeders, the operational battery state is relevant. Using the source model's **operational energy floor of approximately 0.229 kWh per module**, 273/310 A0 94022 failing case-hour records, 225/234 A0 106039, 12/12 A1 94022, 16/16 A1 113699 and 21/21 A1 106039 causal are at this floor *at the end of the failing hour*. The state after an hour does **not** alone prove sufficient energy was available earlier to shift, and does not establish that multiple consecutive violations can all be corrected. Preserve intertemporal SOC constraints and full-year chronology. The 106039 18-case optimized dispatch success is a verified narrow demonstration, not proof all other cases can be corrected similarly.

## PV curtailment: energy amount versus operational cause

The 44 annual summary rows are 22 equipment families, each with optimized and causal dispatch. **Never add A0 and A1 curtailment as if both installations operate simultaneously.** For A1 106039: minimum-cost PV 41 ×435 Wp, 8 battery modules, 21,657 kWh available DC, 2,444 kWh DC curtailed (11.28%); higher-SS 49 panels and the same 8 modules, 25,883 kWh available DC, 5,492 kWh curtailed (21.22%). More panels improve annual self-sufficiency but increase absolute and fractional curtailment in this pair.

A significant **optimization-vs-causal temporal diagnostic**:

- Across all 22 causal profiles, **18,964 of 18,988** hours with curtailment coincide with a battery **near its modelled maximum at the end of the hour**.
- Across all 22 optimized profiles, just **23 of 19,629** hours with curtailment coincide with near-full end-of-hour SOC, despite almost the same total annual DC curtailment. Total curtailment across all 22 A0+A1 alternatives differs by only about 8.65 kWh between dispatch methods (this sum is a diagnostic of distinct alternative scenarios, not community production).
- Across all 44 profiles, reported curtailment hours coincident with the model's charge-power cap are rare, and **none coincides with an inverter near its reported AC nameplate** under the extractor's specific condition.

These are **coincidence flags**, not an attribution model. The perfect-foresight optimizer can schedule curtailment and SOC very differently from PV-first causal operation while achieving similar aggregate import. A battery that is not full *at the end of a curtailed hour* does not establish that the optimizer could have used more PV without affecting later imports, SOC or its objective. Equally, a full battery in causal operation does not demonstrate that buying an additional module will produce a positive net benefit. **It would be premature to claim that more batteries are necessary or that inverters are oversized based on these flags alone.**

All the AC violations in the diagnostic package occur with PV=0 and curtailed PV=0. This is expected for evening events. Increasing solar utilization can help *indirectly* by saving usable midday energy for later, but only if it changes storage dispatch/capacity and remains AC-feasible; it will not directly supply the evening hour.

## Design-stage decisions

1. **Freeze validated history.** Keep the completed 432 annual AC base results, 22 energy/22 causal outputs and 18 successful A1 106039 optimized trial overlays unchanged. The 126 remaining failed sensitivity cases are an active **research backlog**, not a claim that 126 grid connections are intrinsically infeasible.
2. **Prioritize operational corrections by network.** First A1 94022 (five unique evening timestamps across hardware and dispatch), A1 113699 (two timestamps in minimum-cost tier), and A1 106039 causal (two timestamps). Next A0 94022 and A0 106039, which have multi-hour and multi-day violations and may need proper annually constrained optimization. Verify SOC earlier in the day, net AC injection, overnight constraints and feasibility against every affected PF/length setting. Do not force a correction when an energy corridor is infeasible.
3. **Treat 92395 MST as Study B network design.** Investigate real conductor evidence, conductor cross-section, cable route, alternative inverter siting / clustered systems, and cable length plus losses and cost. Do not repair 411 grouped voltage events with blind 1–2-hour discharge shifts.
4. **Run a separate PV/BESS utilization and hardware sensitivity frontier.** At least per actual Study A territory and both A0/A1 assumptions, start with current panels/modules/power/inverters, then controlled local variations in 435 Wp panels, 5.12 kWh nominal / 4.325 kWh modelled usable battery modules, DC battery kW and inverter kVA. Keep no export, the existing manufacturer SOC convention and device current limits. Examine marginal avoided import **per extra module, per extra PV panel, and per kW of DC charge power**, rather than promising zero curtailment. Compare minimum annualized cost, achieved self-sufficiency, PV curtailed DC, battery throughput, network-loss-inclusive cost, AC voltage/loading feasibility and a later reserve-for-outage constraint. Retain all failures and stop at defensible Pareto choices.
5. **Keep distinct interventions and validations.** A forced source→target discharge shift is not a reoptimized full-year PyPSA optimum, and AC screen is not a real-time or field-certification test. A revised hardware investment requires a new 8,760-hour energy solve, an AC replay for its selected stress sensitivities and new provenance. No need to rerun the historical 6,840-task investment campaign or 432 already signed AC sources.

## Walkthrough and GitLab

Retain the figure chronology through Stages 12 and 13. Add a *proposed* diagnostic decomposition chart only after editorial review: 92395 MST routing voltage versus mapped 94022 evening voltage versus 106039/113699 thermal failures; maintain the numeric 586-event definition in the caption. Revise prior figure P1 to overlay the successful 106039 optimized correction; do not rewrite original saved case values. The PV-utilization figure should show annual curtailed DC kWh/%, achieved self-sufficiency and battery utilization for actual independently sized candidate designs, not a fictitious smooth Pareto curve through discrete hardware options. No GitLab actions are authorized in this step.

**Data lineage**: ZIP SHA-256 and independent integrity checks in `INDEPENDENT_QA.json`. Original 4 diagnostic files retained alongside aggregated CSVs. No solver executed.
