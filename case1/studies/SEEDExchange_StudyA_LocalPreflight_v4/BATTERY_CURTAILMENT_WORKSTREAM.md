# Cross-study battery sizing, utilization and PV curtailment analysis

Status: **Approved research dimension, not yet completed in the newly paired EPM scenarios.** Source: canonical GitLab handover, 7 Nov battery cross-study decision, 8 Nov A/B/C scope. Preserve the already-completed original fixed-BESS economic 0–16 module sweep (5–15-house cases), archived investment frontier, 7/9/12 annual reference AC and SOC manifests.

## Required comparisons for all suitable A, B, C cases

1. **Unchanged-hardware reference:** reproduce historical 2025 PV-first manufacturer-SOC-constrained economic dispatch and its real PV available profile. Require at least the full 8,760 hours; historic vs new Excel-load sensitivity remain separately tagged.
2. **Curtailed-energy and binding-constraint attribution:** report PV available, demand served directly, battery charging and discharge, inverter clipping/AC power limits, battery-energy headroom, charge-power headroom, grid purchases, battery full or partially charged when PV curtails, and SOC floor when unmet load would otherwise require the grid. Battery-full is not automatically the sole reason for curtailment.
3. **Controlled dispatch comparison:** with *fixed identical physical hardware and household profiles*, compare original perfect-foresight optimal schedule against causal PV-first charging and, if appropriate, a lexicographic or explicitly justified low-curtailment dispatch tie-breaker. Keep **zero grid export**, **no grid charging**, source-checked manufacturer battery minimum physical SOC **20%**, inverter AC kVA and battery DC current/power limits; no unjustified night Q.
4. **Targeted hardware marginal changes:** independently vary battery energy capacity (count/modules), battery charge/discharge power, and inverter kVA; optionally PV panel count when curtailment/insufficient solar makes it informative. First reuse archived fixed-BESS 0–16 sweep and economic equipment transitions. Do not rerun all 6,840 original investment tasks or add an arbitrary AC candidate cap.
5. **Electrical feasibility and economics:** for promising designs, AC-check 8,760 hourly power flows and, where needed, legitimate P/Q feedback with chronological SOC-respecting redispatch and revalidation. Apply primary PF 0.95/.98/1.00 and service route x1.0/x1.3/x1.6 with strict voltage 0.97–1.03 as a separate sensitivity from primary 0.95–1.05. Report AC losses/thermal/voltage violation hours and annualized installed, replacement, cycling, cable and connection costs when known. Unknown costs remain unknown, never treated as zero.
6. **Architectural comparison:** for A existing utility territories, B purpose-built coherent STAR/MST networks, C Site A 94022 tie or conditional new transformer, compare matched total equipment across central versus multiple shared multi-home PV+BESS clusters first. Then allow architecture-specific equipment selection for cost and performance. Preserve feeder ownership, connection, protection and metering boundaries.

## Example causal research questions

- At a given PV module size, is observed curtailment driven by BESS **energy** saturation, charge **power** constraints, inverter AC limits, network export cap, or a perfect-foresight economic schedule that chooses not to charge despite headroom?
- What is the *marginal* decrease in curtailed PV and grid imports for one extra feasible battery module, compared with its annualized capital cost and cycling wear?
- Can better charging control outperform battery expansion using the same equipment, without violating network voltage, transformer or line limits?
- Are two smaller multi-home storage clusters technically or economically preferable to one central shared bank after including additional inverter, controls, cables, maintenance, losses and protection?

## Measurement ledger, per case

`study, scenario_id, household_membership_sha256, demand_source, stochastic_seed, pv_source, transformer_id/rating_evidence, network_model_sha256, hardware_candidate_id, panel_count, installed_pv_kwp, bess_modules, nominal_battery_kwh, usable_battery_kwh, batt_charge_kw, batt_discharge_kw, inverter_kva, control_policy, min_soc_fraction, annual_pv_available_kwh, annual_pv_curtail_kwh, curtail_fraction, curtail_hours, curtail_when_bess_full_kwh, curtail_with_unused_charge_power_kwh, annual_battery_charge_kwh, discharge_kwh, throughput_kwh, equivalent_full_cycles, energy_loss_kwh, grid_import_kwh, grid_export_kwh, self_sufficiency_percent, annualized_total_usd, incremental_annualized_usd, incremental_kwh_curtail_saved, min_voltage_pu, max_voltage_pu, voltage_violation_hours, max_line_loading_percent, max_trafo_loading_percent, thermal_violation_hours, annual_ac_loss_kwh, source_status`.

**Do not compute savings from a proposed control or a more expensive battery before running the actual user-executed 8,760-hour dispatch and AC validation.**
