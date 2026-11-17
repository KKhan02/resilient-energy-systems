# SEEDExchange San Rafael | Approved research scope and methodological contract

**Approved by user:** 7 November 2026, following explicit clarification of A, B and C.
**Status:** Research objective and staged methodology approved. Specific hypothetical site choices, cable types, routes, rating modifications, phase assignments, cost inputs and clustering algorithms are not yet validated engineering inputs.
**Project:** `resilient-energy-systems`, branch `main`. This document is intended to be placed in `case1/` in the user's project checkout. Existing GitLab rolling handover `case1/PROJECT_HANDOVER_LIVE.md` is the only remotely writable file without separate authorization.

## 1. Core objective

Study a **shared PV, battery storage and grid-connected community energy system** for 5–15 households in El Arenal / San Rafael, Colombia. Determine (i) economically promising hardware size and dispatch, (ii) AC-network technical feasibility and robustness, (iii) possible corrective active/reactive control, (iv) economically defensible physically feasible alternatives, and (v) benefits and limitations of multiple shared multi-home clusters and possible interconnection.

Preserve the complete pre-existing 6,840-task PyPSA optimization (12 cases: 5, 6, 7, 8_H01, 8_H02, 9, 10, 11, 12, 13, 14, 15 homes). This archive supplies candidate equipment and energy-economic baselines; it is **not full AC validation**. Keep the 1,255 archived distinct hardware designs at the 5 kVA planning reference available. Economic frontier tiers A (50 initial anchors across all household cases), B (other nondominated sampled hardware), C (hardware transition boundaries) and D (remaining archive) are **candidate-selection tiers**, NOT the three physical studies A/B/C. There is no fixed annual AC simulation count or six-design cap.

## 2. A: Existing EPM GIS and actual-network proxy

**First priority and not complete.** Retain EPM transformer points, mapped LV segments and all explicitly *provisional* household service attachments. Existing reference cohorts: 7 houses and 9 houses on transformer **94022**; 12 houses on **106039**. The broader provisional 94022 GIS territory has **10 mapped candidate houses**; its 10-house 40-critical-hour study is not identical to the 7/9-house annual cohorts. Distinguish all three population definitions. Other recorded EPM assets/house memberships may enter A only with compatible evidence, not invented reassignment. Model 106039 as **5 kVA** as explicitly agreed; use archived 5 kVA 94022 model. These are study values, not permission to infer transformer headroom from annual average kWh.

**A workflow:**
1. Maintain each existing cohort and source-specific geometry. Evaluate no-DER/load-only reference and equipment from saved economic PyPSA pool; use manufacturer-SOC-constrained 8,760-hour trajectories where available. Reconstruct missing exact-hardware trajectories only where needed, not the original 6,840-investment sweep.
2. In existing pandapower model check voltage (min/max, hour counts), transformer kVA/%, line current/loading, losses, reverse power, active and reactive operation, demand/ENS and source provenance. Use representative stress hours for rapid diagnosis, then annual AC for informative hardware, extending candidate selection as feasibility or Pareto limits warrant.
3. Apply uncertainty and control analysis to those same cohorts: **assumed service/route length x1.0, x1.3 and x1.6**, household PF 0.95/0.98/1.00, optional 0.90 stress; Q-capability ratio and controls, inverter electrical placement (head/middle/end) and active-power redispatch subject to full-year physical SOC, inverter/transformer limits, energy balance and cost. Retain source mapped LV geometry, and distinguish changed hypothetical service/drop lengths from actual EPM GIS line records.
4. Reuse the existing **40-critical-hour inverter siting and Q-ratio sweep**, 7/12-house annual checks, current 12-house equipment annual AC results, and existing coordinated-Q/AC-redispatch code. A limited matched 8,760-hour siting comparison can be justified after A household/equipment feasibility priority, but is not a separate immediate campaign or replacement for the main A sweep.
5. If equipment fails AC constraints, first diagnose cause, then test existing valid Q and active P redispatch; if still infeasible, revisit hardware or physical constraint, and update its cost. Never mark failed AC as no PV/BESS design possible.

**A is NOT a physical 5–15-house sweep just because the archived economic model covers 5–15 homes.** It is based on supportable EPM candidate cohort assignments. A's observed groups can inform later multi-cluster research.

## 3. B: Proposed community LV configurations for 5–15 homes

**Second principal study, currently not fully modelled.** Use the existing 35 georeferenced candidate houses. Form geographically compact groups of N=5..15 nearby households, allowing multiple defensible groups/configurations per N. Preserve the identity and coordinates of each real mapped house across scenarios; document which houses are in each scenario. Do **not** force all smaller groups to be a single arbitrary nested set of 15 if a more spatially coherent grouping better answers the research question, but keep controlled membership or documented case matching when comparing N and architecture.

Use **different existing stochastic hourly household demand traces**, not one replicated household load profile. Assign reproducible profile IDs/seeds to physical household IDs. Preserve the original archived synthetic 2025 load data as baseline; any new stochastic diversity cases are separately labelled sensitivities and should retain comparable population energy assumptions. The two eight-house economic variants are **load-profile variants**, not GIS house IDs H01/H02.

For each group, propose and evaluate feasible transformer supply positions near the group, not automatically the geometric centroid. Compare objective(s) such as connection length/cost, worst-voltage and transformer/feeder loading and physical route constraints. **Initial transformer 5 kVA is a planning hypothesis**, with rating reconsideration when calculated constraints require. Evaluate two physical feeder geometries:
- **Star:** separate service/branch route from common supply point to each household.
- **MST:** a connected minimum-spanning-tree candidate that reduces geometric total cable length; shared branches carry downstream load. The MST is also radial, so distinguish *star versus branched MST*, not 'radial versus MST' as mutually exclusive categories. Survey, access, line-route and protection constraints take priority over Euclidean shortest edges.

Apply A's *same modelling methodology* to the B topology: baseline demand flow, manufacturer-SOC 8760-hour energy/AC, PV+BESS sizing candidate checks, Q-ratio and P/Q control, inverter placement when it matters, x1.0/x1.3/x1.6 service/route sensitivities, PF and voltage limits, losses, thermal limits, cost. Reuse the network-building, time-series, control and economic engines. The new work is scenario/topology/attachment parameterization, NOT another simulator.

## 4. C: Site A shared central installation and grid-connection alternatives

**Third study.** Candidate Site A clearing coordinates: **6.248376671296207, -75.00932156861505**. Existing gross polygon ~1,759 m² is user-digitized, not a surveyed usable PV area. Reuse existing NASA/pvlib and site shading sensitivities with explicit uncertainty.

**C1 first:** place shared PV+BESS at Site A and propose a connection to **existing 94022 LV infrastructure**. Check route/line length (existing closest mapped 94022 segment GIS FID 47053144, geometric shortest distance ~192 m, not routed connection), bus voltage min/max, transformer kVA, line thermal ratings, losses, reverse flow, controlled inverter P/Q, electrical and site-specific costs, and EPM permission. Do NOT assume new physical service wires already exist.

**C2 fallback:** if C1 is unsuitable after technical/economic comparison, analyze **new transformer at Site A** and physically proposed connections to suitably nearby households. User previously explicitly selected **5 kVA initial new-transformer scenario**; latest spoken description also mentions '5–15 transformer', which may indicate a sensitivity range. **Do not silently select a final 10/15 kVA nameplate**; keep 5 kVA baseline and treat 10/15 kVA as possible sizing sensitivities if demonstrated necessary. Compare STAR versus MST feeder geometries and route/thermal/voltage/connection costs, including how a new transformer itself gets a valid upstream supply. Do not automatically presume 5 kVA supports 15 houses.

**EXCLUDE the northern transformer entirely.** The mapped northern 25 kVA transformer and any suggested connections to it are outside this project, irrespective of previously discovered GIS identifiers.

## 5. Cross-cutting architecture / clustering question

This is an **additional comparison dimension**, not a fourth disconnected study:
- **Centralized shared PV+BESS:** one multi-house energy installation at one electrically valid point.
- **Multiple shared multi-home clusters:** two or more PV+BESS installations, each serving a group of households. A's separate existing EPM customer territories provide meaningful cluster reference examples.
- **Hybrid:** central installation plus selected satellite shared PV and/or battery nodes where justified.
- **Individual PV+BESS per house:** secondary benchmark only, not the default research objective.

Two controlled comparisons are useful: (1) **matched total hardware, common household demand, PF and network assumptions** to isolate clustering/placement effects; (2) **architecture-specific feasible equipment**, allowing different inverter/battery numbers and costs, to compare best implementable lifecycle economics. The second is not an instruction to redo every archived investment task. It means use stored candidates and only perform new constrained equipment/dispatch optimization where architecture or AC limits genuinely change the answer.

**Interconnecting separate transformer territories is not a free electrical switch.** Treat three different hypotheses separately: (a) independent physically separate clusters; (b) common commercial/energy accounting without direct LV tie, under the rules of the utility; (c) actual proposed electrical interconnection requiring compatible LV circuits, new cables, protection/metering, utility permissions, and possibly a different network architecture. Do not simply parallel existing transformer secondaries or double-count the same household.

## 6. Core modelling/evidence assumptions and caveats

- Existing NASA POWER 2025 source: 8760 hourly values, not site measurements; existing seed-controlled synthetic household load profiles, not meter readings.
- Reference household PF **0.98**; principal sensitivities **0.95, 0.98, 1.00**; PF **0.90** optional stress. User reports Colombian practice may approximate apparent power with PF1; **this is not independent proof that residential loads have measured PF1**. Nameplate chosen for 106039 = 5 kVA.
- Principal study voltage screen **0.95 to 1.05 pu**, old strict **0.97 to 1.03 pu** retained as sensitivity, not legal certification; transformer and conductor thermal limits explicitly evaluated each hour.
- Battery minimum physical SOC **20%** per archived manufacturer-DoD interpretation, with power, energy, inverter and chronology constraints retained. Default nighttime inverter reactive power **off** until documented device capability. Manufacturer configurations provisional.
- Historic 25-year, 6% discount economic framework used as source reference, with original quote/HOMER-derived equipment costs and uncertain Colombian tariffs, capex replacements/O&M and installation/feeder/switchgear/site/protection/meter/utility costs explicitly separated or sensitivity priced. Do not assume unpriced costs are zero.
- Inverter-location and Q-controllers already exist: reuse. Original archived optimization ignored AC feeder losses in the energy objective; report this separately and correct/refine when necessary.
- Critical/deferrable loads remain **parked**. Islanding/outage claims require additional inverter/control/protection evidence; no unverified blackout survival certification.
- No assumed EPM service-map, phase, conductor thermal/nameplate, routing, land ownership or grid interconnection is field-certified. Preserve source records, status and exact model inputs.

## 7. Execution priority / research gates

**Phase A FIRST:** review 7/9/12 cohort matrix and the provisional 10-house GIS population; consolidate existing 8,760h checks and current two candidate annual jobs; make sure manufacturer SOC and provenance match. Run required unresolved hardware-vs-network/PF/line-length/control cases in targeted batches. Select extra 5kVA archived equipment from Pareto/transition boundaries where network constraints dictate. Report conditional feasible hardware versus household-cohort and cost/self sufficiency, plus robustness intervals. Do not jump straight to inverter siting annual reruns or Site A as the primary output.

**Phase B SECOND:** spatial clusters N 5..15 from known coordinates and independent stochastic profiles, optimize feasible transformer locations, star/MST electrical models and uncertainties. Reuse A's solver and evaluation pipeline. Compare same-hardware and re-sized alternatives and identify limits per N. Additional clusters/alternatives allowed if important.

**Phase C THIRD:** Site A PV+BESS to existing 94022 LV, then optional new transformer star/MST fallback, with site land/solar and actual new connection costs. Only perform new 8,760-hour AC after geometry and load-only/critical-hour checks.

**After comparable A/B/C evidence:** assess centralized versus several shared clusters and possible physical or economic interconnection. Use old cluster energy study as reference; do not reinvent it. Report electricity cost, self-sufficiency, voltages, losses, thermal stress, house count, equipment dimensions and spatial/connection caveats on matched inputs. Re-run investment solver only for new real constraints or justified alternatives, never just because results are missing from an old folder.

## 8. Non-negotiable workflow

1. **Read existing work first.** Reuse source models/data, saved 6,840 optimization cases, 40-hour placement/Q studies, existing 7/12 annual checks, manufacturer-SOC results, and Site A resource analysis. Distinguish unchanged source evidence, new proposed inputs and completed AC runs.
2. **Local-first execution.** The assistant supplies focused project-contained scripts/tests or exact reproducible commands; the user runs on Windows and returns results. Use new versioned paths **inside the existing `resilient-energy-systems` repository**. Each study has its own outputs. Do not scatter output to drive-level sibling directories, silently overwrite existing results or conflate hardware candidates with geographic network scenarios.
3. **Main only for authorized GitLab changes.** No project code, data, result or other repo commits without explicit user instruction. One standing exception: assistant updates **only** `case1/PROJECT_HANDOVER_LIVE.md` on `main` after each reply, with `[ci skip]`.
4. **Scope change control.** Any proposal that changes the research question, A/B/C membership, network topology, transformer rating, routing, meaningful control assumption or economic basis must identify the proposal, reason and expected scientific benefit. Do not silently treat model suggestion as a user-approved assumption. This document is an approved scope and methodological intent; implementation-specific physical choices require documented review.
5. **Known working results are reusable, not fixed constraints.** Existing annual candidate outputs are immutable scientific evidence, not mandatory destinations for all future work. New studies need their own manifest with source hashes, exact customer IDs, power profiles, model and scenario version.

## 9. Status as approved on 7 November 2026

- **Approved:** objective, A/B/C scope and order, B grouping by proximity, optimized feasible transformer position, star/MST alternatives, line-length/ PF / reactive and active controls, distinct stochastic demand, C 94022 first and Site A transformer fallback, centralized-versus-clustered follow-up, all source reuse and local-first workflow.
- **Completed historical:** investment archive; partial EPM GIS and PV/BESS validations; 40-critical-hour inverter and Q-ratio sensitivity; selected 7/12 annual results; prior central-vs-two-cluster annual energy screen; preliminary Site A resource sensitivity.
- **Reported by user but not yet numerically inspected here:** one of two recently started 12-house annual AC candidate runs is completed, the other intended/planned.
- **Implementation choices still open:** exact algorithm and spatial participation sets per N for B; transformer siting feasibility/cost and conductor sizes; actual service routing and phase representation; prospective Site A connection route and utility permission; which specific hardware/control finalists justify new annual run; whether any new 10/15 kVA transformer sensitivity is necessary; physical feasibility/cost of any inter-cluster LV tie.
