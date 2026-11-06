# Reusing the full annual PyPSA campaign for network-feasible equipment screening

**Purpose:** Evaluate the existing investment and equipment sweep against manufacturer battery constraints and an independently modelled EPM AC feeder, **without repeating completed investment optimizations**.

## Existing model results

The committed [full-study optimization archive](../../studies/pypsa_joint_optimization_v1/outputs/full_study/) contains **6,840 annual PyPSA MILP tasks**: 6,820 energy-screen optima and 20 infeasible tasks. It covers **12 synthetic household configurations**, **five assumed transformer-rating scenarios** (5, 10, 15, 20, 25 kVA), fixed-PV and fixed-BESS variations and multiobjective constraint points. Each original energy solve used an 8,760-hour perfect-foresight trajectory.

The [campaign reuse index](../../studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01/campaign_reuse_manifest.json) identifies **6,339 distinct archived hardware configurations** across the whole study. Of those, **1,214** were placed in the present mapped/hardware-screen-ready queue. Unmapped, hypothetical-nameplate and component-current-review cases remain recorded, rather than being incorrectly called infeasible.

Only **three original reference designs** had full hourly dispatch files archived with the investment campaign. For other hardware, a **new fixed-hardware annual redispatch** is necessary to obtain manufacturer-SOC-compatible hourly injections. It must not be described as rerunning the original investment sizing optimization.

## Feasibility workflow

1. Keep every original task and objective in the index, including failed optimizations.
2. Merge exact duplicated hardware solutions for execution while preserving task provenance.
3. Reuse matching completed manufacturer-SOC trajectories and annual AC runs through validated provenance checks.
4. For each other eligible design, run a **new** full 8,760-hour fixed-hardware energy/SOC solve using the existing PyPSA model and manufacturer's 20% minimum physical SOC.
5. Replay all 8,760 hours in the EPM GIS pandapower model at a documented reference PF and service assumption, then at nine full-year PF/route combinations. Record voltage, transformer/line loading, modelled losses and unserved energy.
6. Preserve failures and blocked hardware for distinct follow-up. When needed, apply SOC-consistent AC-aware feedback and revalidate the **complete year**.

## Status and limits

This section describes a campaign **in progress**. Neither the 1,214 queued configurations nor the 6,339 historical hardware choices are automatically AC-feasible. Avoid counting partial AC checkpoints as completed annual results. No new network-feasible economic Pareto curve is claimed.

The 12-house reference with 41 PV panels, eight batteries and a 12 kVA inverter has a completed manufacturer-SOC and annual 0.95–1.05 pu AC screen as documented in [08](../08_Annual_AC_and_Uncertainty/). Its **5 kVA transformer is a hypothetical sensitivity**, not a field-confirmed nameplate for 106039.

Once complete-year AC results are collated and hardware ratings reviewed, this section can add the genuine **cost/self-sufficiency/voltage/hosting** comparison without recomputing the archived investment sweep.

## Sources

- [Archived full MILP table](../../studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv)
- [Original study manifest](../../studies/pypsa_joint_optimization_v1/outputs/full_study/study_manifest.json)
- [Reuse campaign manifest](../../studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01/campaign_reuse_manifest.json)
- [Equipment candidate register](../../studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01/all_distinct_equipment_candidates.csv)
