# Study A consolidation: existing EPM GIS proxy, A0/A1 assignments, equipment and grid outcomes

**Date:** 22 November 2026. **Status:** Evidence inventory and decision gates, not a new AC simulation or final engineering recommendation.

## Why this file exists

The technical investigation recently concentrated on transformer 113699. The approved goal is larger: compare community PV/BESS systems under *original* A0 household associations versus proposed nearest-transformer A1, assess equipment cost, energy imports, storage use and curtailed PV, and validate resulting utility-network limits. Study A must become a coherent result before we claim the overall project completed, then Study B evaluates proposed LV STAR/MST layouts for 5–15 homes, and Study C evaluates Site A central PV+BESS connections.

This matrix aggregates **status**, not mutually interchangeable numerical results. The five main modeled territories cover the same **34 synthetic 2025 household demand traces (64,532 kWh/year)** on either assignment; H08 on 98380 is support-only and excluded from both. Source original A0 territory counts (106039,94022,113699,85398,92395) = **12,10,4,4,4**; proposed nearest A1 = **11,8,6,5,4**. The proposed moves are H03/H06 from 94022 to 113699, and H13 from 106039 to 85398. They are *not* EPM-approved rewiring.

## Which numerical conclusions are supported?

### Whole 34-home population, ENERGY ONLY

The audited 16-case reciprocal matched-hardware PyPSA comparison retains fixed equipment within A0/A1 pairs. Annual costs include modelled equipment and imported electricity, **not** final EPM connection CAPEX or AC losses. Frozen hardware from original A0 min-cost: A1 minus A0 imports **+159.371 kWh** and cost **+$46.217/year**; A0 SS90: **+1,424.628 kWh / +$413.142**. Frozen equipment from proposed A1 min-cost: **-1,070.384 kWh / -$310.411**; A1 SS90: **-2,204.165 kWh / -$639.208**. Consequently there is **no universal geographic winner independent of equipment selection**. All 8 saved whole-population paired portfolios have `AC_verified=False`, and their common 92395 STAR network is proposed.

The *different-equipment* 34-house alternatives are a separate comparison, not a causal hardware-fixed contrast. At modelled min-cost: A0 **$13,783/year, 11,040 kWh imported, 8,757 kWh DC curtailed**; A1 **$13,751/year, 11,666 kWh imported, 7,331 kWh DC curtailed**. At SS90: A0 **$14,530/year, 5,394 kWh imported, 13,098 curtailed**; A1 **$14,647/year, 5,822 kWh imported, 13,572 curtailed**. Both are energy-only annual estimates with different assets; adding a battery need not improve annual cost.

### AC grid evidence: do not conflate levels

- **Full-year conditional main-band AC (0.95–1.05 pu, <=100% assumed equipment loading):** A1 106039 six selected PV/BESS portfolios have nine-factor annual results passing after source-consistent correction, with weakest assumed transformer margin **0.568 percentage points**. The broader corrected original-network 432-case campaign shows **376 passing / 56 failing**. A modified hypothetical A0 94022 five-edge R-halving network separately yields **408 / 432** combined passes; this is not an existing conductor-replacement design.
- **Single-territory 113699 reference annual AC:** For 6 proposed A1 households, two separate fixed-hardware annual SOC-adjusted schedules each pass **8,760/8,760** at PF .98 and service length x1.0 on an assumed 3 kVA transformer, but have **245 and 120** strictly below .97 pu annual hours.
- **113699 bounded robustness, not annual:** 18 factor-hardware groups, **25 common hours each, 450 converged AC case-hours**. All **12** principal band violations occur at PF .95 and stem from undervoltage; no sampled thermal overload. PF .95 main failure case-hour sums: A0-origin hardware **1/3/3** and A1-origin hardware **1/2/2** for length x1.0/x1.3/x1.6. Other PF sampled cases pass. No factors other than PF .98 length1.0 have completed 2025 annual AC on these frozen 113699 schedules.
- **92395:** proposed STAR/MST is not a known EPM LV circuit. Shared STAR outcomes in 34-house accounting must stay labelled hypothetical, and the alternative MST evidence belongs to Study B.

There is no demonstrated EPM-certified house wiring, conductor, phase/neutral loading, actual transformer nameplate, downstream utility approval, protection or islanded outage-reserve proof. Do not transform research-screen voltage compliance into a legal Colombian interconnection statement.

## Decision priorities before expanding studies

1. **Report a common Study A comparison** with the 34-home same-population hardware-fixed and architecture-specific annual economics in separate tables. Include battery modules, PV panels, battery power, inverter rating, imports, DC PV curtailment, discharge/cycles and modelled annual cost.
2. **Attach an evidence grade to every electrical claim:** prior source-architecture 8,760h, newly source-matched 8,760h, bounded 25-hour study, conditional physical network alternative, or missing field topology. Do not infer whole-population AC from a passing 113699 or 106039 subcase.
3. **Do not quote a final corrected network-loss cost differential** until the same two assignments, hardware and AC dispatch schedules have matched annual AC loss series. Archived LP purchase cost does not internally price the independent pandapower losses, and hypothetical rerouting must have separate installed cost.
4. **Request field evidence with high expected value:** actual 106039 and 113699 transformer ratings/phase connections, H03/H06/H13 actual EPM membership and service routes, H01/H06 94022 service paths, 92395 mapped LV conductors, wire type/ampacity, meter/settlement arrangements and selected installation costs.
5. **Control new simulations:** no more 113699-only exploratory sweeps without an identified Study A decision change. A PF .95 targeted 8,760-hour sensitivity may be required if the physical household PF is credible and the proposed 113699 assignment survives phase/connection evidence review. Preserve original signed results. Focus remaining effort on A-wide evidence closure, then the approved B and C geometry/energy/economic comparisons.
6. **Keep resilience separate:** current 2025 grid-connected perfect-foresight self-consumption is not measured outage survival, black start, islanding or critical-load continuity. Define outage and reserve requirements before such claims.

## Source and walkthrough crosswalk

- Approved scope: `case1/RESEARCH_SCOPE_APPROVED_2026-11-07.md`.
- Historical 34-home source-architecture cohort reconciliation: `case1/studies/SEEDExchange_StudyA_Matched_Cohort_2026-11-21/A0_A1_MATCHED_34H_SOURCE_AUDIT.md`.
- Full source signed 16-case reciprocal annual energy controls: `StudyA_A0_A1_MatchedHardware_Full_v1/` and `case1/studies/SEEDExchange_StudyA_Matched_Hardware_2026-11-21/FULL_16_REMOTE_AUDIT_2026-11-21.md`.
- A1 106039 economic/annual AC frontier: `case1/studies/SEEDExchange_StudyA_Validated_Frontier_2026-11-21/` and validated 27-case independent review.
- 94022 conditional five-edge study and its physical verification register: `case1/studies/SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17/`.
- 113699 full 2025 annual AC and new 25-hour PF/length: `case1/studies/SEEDExchange_StudyA_Matched_Hardware_2026-11-21/AC113699_TWO_8760H_AC_REMOTE_AUDIT_2026-11-22.md` and `NINEFACTOR_450_REMOTE_AUDIT_2026-11-22.md`.
- Walkthrough: [Stage 12 mapped geography](../../professor_walkthrough/12_Geographic_Assignment_and_Routing/), [Stage 13 AC corrections](../../professor_walkthrough/13_Annual_AC_Corrections_and_Conditional_Retrofit/), [Stage 14 PV/BESS utilization](../../professor_walkthrough/14_PVBESS_Sizing_and_Utilization/), [Stage 15 same-hardware versus PF robustness](../../professor_walkthrough/15_Matched_Hardware_and_AC_Robustness/).

This is a **read-only synthesis of saved evidence**. No original simulation, grid or equipment data was altered. No new solver was executed.
