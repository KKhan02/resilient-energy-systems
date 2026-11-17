# SEEDExchange walkthrough, proposed continuation after historical stages 01–11

**Source status:** Editorial draft and summary-only scientific results, 16 November 2026. Does not modify historical GitLab files or claim completion of Studies B, C or resilience.

## Preserve the existing evidence progression

The original 24 PNGs in `case1/professor_walkthrough/01_...` through `08_...` show how the research evolved, including hypothetical household grouping, discrete PV/BESS investment screening, daily/monthly operation, representative feeder AC, GIS interpretation, inverter siting, Q-control and early uncertainty tests. Stages `09_...` to `11_...` document further AC-aware feedback and campaign reuse and need not be filled with uninformative figures.

## New Stage 12. Geography changes the engineering problem

**G4. A0 versus A1 EPM-mapped LV topology.** The membership comparison includes 35 candidate locations, of which 34 fall in the five multi-house groups of >=4 households. H03 and H06 move from 94022 to 113699; H13 moves from 106039 to 85398. The single 98380 household is shown for geographic completeness but is not a PV+BESS cohort. The figure does not show a confirmed service cable, and no 25 kVA northern alternative is added. 92395 has no extracted mapped LV segments, so STAR/MST remains explicit proposed routing. Source is the signed v6.2 35-house mapping and EPM GIS records, with a rounded-coordinate snapshot used for the packaged preview; `--repo-root .` re-renders against the exact original checkout GIS sources.

**P3. STAR versus MST at 92395.** Same four houses and hardware, PF0.95. At length factor 1.6 the MST configuration has 277 gross-load violating hours, reduced to 110 with minimum-cost PV+BESS or 105 with higher-SS hardware. Proposed STAR has no main violations in these cases. Cable length differs materially (about 1,153m STAR vs 550m MST at 1.0), so voltage alone is insufficient for economic network choice. No claims of actual wire routes, conductor cost or field protection.

## New Stage 13. PV+BESS improves AC feasibility, but leaves a specific design problem

**P1. Five-territory annual AC improvement.** Matching PF0.98 ×1.0 and STAR 92395 across 34 in-scope houses: A0 gross 110 → minimum-cost PV+BESS 15 → higher-SS 3 violating territory-hours. A1 gross 25 → minimum-cost 2 → higher-SS 1. This is a sum of individual transformer-territory hourly violation counts, not a unique set of community clock hours. Zero solver nonconvergence does not imply no voltage/thermal violations.

**P2. Residual PF/length robustness.** Two matching 3×3 heatmaps show the PV+BESS higher-SS residual violation hours under A0/A1, PF 0.95/0.98/1.00 and service factors 1.0/1.3/1.6. Even in the A1 nominal condition, the one remaining transformer overload at 106039 must be addressed. Under PF0.95×1.6, A1 has two residual violation territory-hours.

**P4. Annual economic-energy trade-off.** Four selected 34-house architectures: A0/A1 assignment and min-cost/higher-SS hardware. Aggregated costs and energy availability sum *five separate shared local installations*, four historical reference hardware configurations plus the separately new four-house 92395 design. It is not a central 34-house optimization, fully priced mini-grid, network-constrained cost optimum or a continuous Pareto frontier. Annual USD costs omit cable installation, field protection, verified network loss valuation and site work. The achieved higher-SS level is not uniformly exactly 90% in every individual cohort.

### Figure editorial selection

- Main research walkthrough: G4 → P1 → P3, in that order, with P2 after P1 as the stress-test evidence when discussion needs uncertainty.
- P4 economic interpretation is an appendix or a dedicated trade-off paragraph, not automatically a mandatory extra slide.
- Preserve existing historical `01_representative_feeder_validation`, `02_hypothetical_routing_sensitivity` and `02_12_houses_monthly_energy` as source-era evidence rather than rewriting them using the new geographic results.
- Extend the old monthly-energy approach *only after* reading the source-signed geographic hourly dispatch files. Use one selected cohort in the main body and the 22-cohort monthly table to prepare optional appendix panels, rather than flooding the narrative.

## Next engineering milestone, 106039 residual

At PF0.98 and length ×1.0, A1 106039 still registers one transformer overload hour under both min-cost and higher-SS equipment. Both have the same 103.49% maximum transformer loading. This supports targeted hourly diagnosis rather than automatic hardware upsizing. The root cause, exact timestamp, initial/available SOC and whether a chronologically feasible alternate dispatch can remove the overload **cannot be concluded from the compact summaries alone**. The included local hourly postprocessor extracts the relevant 106039 AC events and all-cohort monthly energy from checked original signed files, without rerunning optimization or powerflow.

## Planned research beyond Stage 13

- **Study A refinement:** validate daylight Q capability, inspect 106039 hour, evaluate AC-aware fixed-hardware dispatch and annual revalidation, review two causal SOC endpoint drifts. Distinguish actual network feasible performance from conditional magnitude screens.
- **Stage 14, Study B:** design new community networks for 5–15 houses and compare STAR, MST and feasible branched alternatives using identical members, matched equipment, conductor sizing, transformer choice, costs, voltage/losses and protection constraints.
- **Stage 15, Study C:** solar site A, interconnection route to 94022 versus alternative hypothetical transformer and placement, including right-of-way, cable cost and interconnection limitations.
- **Cross-study architecture:** centralized shared PV+BESS versus multiple multi-house clusters, matching total installed size and energy service before claiming economic superiority.
- **Stage 16, resilience:** outage studies only after defining critical loads, islanding/grid-forming capability, reconnection and protection, initial SOC, forecast/no-forecast controllers, outage start and duration, unserved critical energy and incremental resilience cost.

No Stage 14–16 numerical outcomes are claimed here.
