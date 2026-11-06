# Per-household economic frontier and equipment transitions: original 5 kVA screen

**Source:** [complete archived 6,840-task annual PyPSA study](../pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv). This report uses existing saved costs and 8,760-hour perfect-foresight energy-screen solutions. **No investment solver or new AC calculation was run.**

## How the first candidate pool was derived

The original study already used self-sufficiency targets of **70%, 80%, 90% and 95%**. For each household case, we identify the lowest original cost reaching each target, the absolute minimum-cost design and the highest recorded self-sufficiency design. Identical equipment is merged within each case. All original **nondominated cost/self-sufficiency task points** remain available, plus exact fixed-panel hardware transitions where the optimized battery count or inverter rating changes.

These are three **selection tiers**, not arbitrary counts or claims of network feasibility: 

- **A:** source-defined economic/SS anchors (initial physical validation candidates, pending network definition)
- **B:** all remaining archived sampled cost/SS nondominated hardware
- **C:** exact fixed-PV equipment-switch boundary candidates to expand near feasible/infeasible AC boundaries

The full historical equipment set remains in tier D and stays accessible. We do not automatically run AC for all tier A/B/C members. Annual AC jobs are issued only after choosing a consistent network hypothesis and finding which designs are informative.

## Saved numeric results at the 5 kVA planning reference

| Houses | Optimal task rows | Distinct hardware | Nondominated task points | Nondominated hardware | Defined-target anchors | Min. cost (USD/y) | Min. cost equipment: panels / modules / inverter kVA |
|---|---:|---:|---:|---:|---:|---:|---|
| 5_homes | 114 | 105 | 26 | 18 | 5 | 1991.78 | 17 / 3 / 5.00 |
| 6_homes | 114 | 109 | 31 | 27 | 5 | 2405.62 | 20 / 4 / 6.00 |
| 7_homes | 114 | 107 | 22 | 16 | 4 | 2772.94 | 26 / 5 / 7.60 |
| 8_homes_H01 | 114 | 105 | 47 | 41 | 4 | 3184.49 | 27 / 5 / 8.00 |
| 8_homes_H02 | 114 | 107 | 47 | 43 | 4 | 3186.57 | 27 / 5 / 8.00 |
| 9_homes | 112 | 101 | 53 | 46 | 4 | 3570.99 | 34 / 6 / 10.00 |
| 10_homes | 112 | 107 | 58 | 55 | 5 | 3978.33 | 34 / 6 / 10.00 |
| 11_homes | 112 | 104 | 38 | 33 | 4 | 4362.57 | 41 / 8 / 12.00 |
| 12_homes | 112 | 104 | 41 | 35 | 4 | 4767.83 | 41 / 8 / 12.00 |
| 13_homes | 111 | 102 | 37 | 31 | 4 | 5210.00 | 41 / 8 / 12.00 |
| 14_homes | 110 | 102 | 30 | 25 | 4 | 5684.46 | 41 / 8 / 12.00 |
| 15_homes | 109 | 102 | 22 | 17 | 3 | 6133.19 | 67 / 11 / 20.00 |

Total: **1348** successful archived 5 kVA tasks, **1255** distinct hardware combinations, **452** task-level nondominated records, **387** distinct hardware on the sampled task frontier, and **50** unique target-derived initial anchors. The two eight-house variants are separate *synthetic demand realizations*, not verified transformer-customer assignments.

## Important findings

- Original economic minimum-cost equipment is unchanged when the assumed transformer rating increases from 5 to 25 kVA, **for the examined historical fixed-PV minimum-cost choices**. This does not prove a physical 5 kVA transformer serves all house counts under all hours and PF.
- From nine to ten houses the minimum-cost choice stays at 34 panels, 6 battery modules and 10 kVA inverter, while annual cost rises. From 11 through 14 houses it stays at 41 panels, 8 modules and 12 kVA inverter. These are recorded **energy-economic transitions**, not AC-feasible design conclusions.
- The economic minimum at 15 houses increases to 67 panels, 11 battery modules and 20 kVA inverter. PV rooftop/site and inverter-string compatibility remain source-dependent.
- Nondominated sampled points are **not the complete mathematical Pareto frontier**. Their costs and self-sufficiency are before manufacturer SOC correction, verified feeder losses and site cost corrections. The initial-anchor list is **not yet a feasible equipment shortlist**.

## Figure

[View the 12-panel sampled economic frontier](figures/archived_cost_self_sufficiency_facets_5kva.svg). Gray points are saved equipment choices, black points are task-level sampled Pareto solutions, and outlined circles are the data-driven initial anchors. Each panel has its own annual cost axis and the same 0 to 100% self-sufficiency axis. This is original **energy-only** evidence, not AC feasibility.

## Files

- [Per-household summary](outputs/per_household_5kva_summary.csv)
- [Original nondominated task rows](outputs/sampled_task_pareto_5kva.csv)
- [Every distinct 5 kVA hardware candidate with evidence/selection tier](outputs/archived_hardware_pool_5kva.csv)
- [Exact fixed-PV hardware switching events](outputs/fixedPV_hardware_transition_events_5kva.csv)
- [Minimum-cost equipment changes between household cases](outputs/min_cost_between_household_transitions_5kva.csv)
- [Source and classification manifest](outputs/frontier_source_manifest.json)
- [Proposed LV network design protocol](PROPOSED_LV_NETWORK_PROTOCOL.md)

## Required gate before new annual AC

Existing EPM feeder simulations remain a separate, physically grounded case study. For a **proposed new community LV feeder**, specify one consistent transformer and household/service geometry and realistic voltage/phase/conductor assumptions first. Do not reuse the existing GIS customer topology for arbitrary 5..15 household counts. All selected candidates should ultimately receive **8,760-hour AC** validation at PF 0.95, 0.98 and 1.00 as appropriate, with nine full-year stress combinations only for robust finalists. Preserve every previously completed AC result and every original archived MILP task.
