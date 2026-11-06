# WP1: verified reuse decision, 2026-11-04

**Source audited live:** Private GitLab `KKhan02/resilient-energy-systems`, canonical path `case1/studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv`, read alongside `run_plan.json`, `study_manifest.json`, `full_study.py`, `model.py` and the 7/9/12 shortlisted reference manifests. The earlier validated source commit was `e377e21d26db4bffd7a164d1257d5860bb01f325`; the new local audit script verifies content via SHA256 rather than relying on a branch name.

## Saved full annual campaign, do not rerun

| Evidence | Count |
|---|---:|
| Archived full-year MILP tasks | 6,840 |
| Reported energy-screen optima | 6,820 |
| Archived infeasible tasks | 20 |
| Household scenarios | 12 |
| Assumed transformer rating scenarios per household case | 5 |
| Distinct equipment tuples, including every household/rating case, using 6-decimal battery kW grouping | 6,339 |
| Exact PV-panel economic tasks | 4,980 |
| Fixed BESS-module economic tasks | 1,020 |
| Min-cost with self-sufficiency constraint tasks | 480 |
| Max self-sufficiency with budget constraint tasks | 360 |
| Optimal task records exceeding the conservative SE-G5.1 2.24 kW/module continuous DC-current proxy | 1,480 |
| Optimal task records with no PV/inverter | 53 |

**Definition of duplicate:** same household variant, assumed transformer kVA, installed PV panels, battery modules, optimized DC battery power to 1e-6 kW, and inverter kVA. An identical buildable design that satisfies different *historical objective tasks* appears once in the new AC job queue, but all task records and original cost/SS outputs remain preserved. This is **not a complete exhaustive combinatorial PV × BESS × inverter sweep**: it is the complete set of outcomes of the already executed historical task campaign.

## Currently provisionally GIS-mapped 5 kVA reference cases

| Archived case | Energy-screen optimal tasks | Distinct equipment tuples | Passing *conservative current proxy* and existing fixed-hardware-runner inputs | Requires hardware/grid-only review |
|---|---:|---:|---:|---:|
| 7 houses, transformer 94022 | 114 | 107 | 66 | 41 |
| 9 houses, transformer 94022 | 112 | 101 | 84 | 17 |
| 12 houses, transformer 106039 | 112 | 104 | 84 | 20 |
| **Total** | **338** | **312** | **234** | **78** |

The 106039 5 kVA rating is a modelling assumption, not an independently verified EPM kVA nameplate. All customer association evidence is provisional. Entries requiring hardware review are not declared electrically infeasible merely because a conservative DC-current proxy flags them.

## Work already completed beyond the archived campaign

- Seven-house, 94022: manufacturer-SOC fixed-hardware baseline and AC-aware P redispatch. The full-year new baseline passes 0.95–1.05 pu; the AC-feedback version also satisfies the stricter 0.97–1.03 pu band under reference assumptions.
- Twelve-house, 106039: reference **41 × 435 W panels, 8 × Deye SE-G5.1, 12 kW battery DC, 12 kVA inverter**. Already completed new manufacturer-SOC full-year run and 8,760-hour pandapower **0.95–1.05 pu** validation with 0 violations. Reuse these source files by hash; do not rerun the same case.
- Twelve-house Q/PF/service-length *critical 96-hour* sensitivity is useful engineering evidence but **not** a replacement for nine separate 8,760-hour AC scenarios.

## v1.8 work that is actually new

1. Build the complete original-task registry and deduplicated hardware catalogue without any optimization.
2. Reuse any existing manufacturer-SOC trajectories that can be checked, especially the 12-house reference.
3. For other mapped and hardware-screen-compatible archived equipment, run exactly **one** necessary fixed-hardware annual SOC correction using the original `solve_fixed()` and original chronological model, not a new PV/BESS capacity-sizing MILP.
4. For each candidate, reuse matching AC evidence when possible, otherwise run full 8,760-hour AC for each required PF × service-factor combination. Save all failures.
5. Compare all fully checked candidates on manufacturer-adjusted annual economics and self-sufficiency, conditional on available network evidence. Do not call unvalidated configurations feasible or convert synthetic housing counts into physical EPM connections.

**Not executed in this deliverable:** the complete new PyPSA fixed-hardware candidate queue, new pandapower AC queue, AC-feedback repairs, additional household GIS mapping, and AC-loss-aware economic feedback. Those require the user's local full repository and power-system Python environment.
