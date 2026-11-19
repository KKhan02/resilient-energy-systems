# Why imports rise while solar curtailment remains | Study A1 106039

**Date:** 19 November 2026. **Evidence:** two independently inspected signed 8,760-hour 2025 GitLab energy source CSVs, original fixed-equipment PyPSA/Linopy objective and converter/battery constraints; plus a chronological PV-first replay implemented separately for diagnostic research.

## 1. Source-verified 41 versus 33 panels

Same 11 named houses (annual load 20,878.00 kWh), same inverter 12 kVA and eight battery modules (40.96 kWh nominal; model 34.6 kWh usable with 1.832 kWh minimum usable-state floor). Same battery continuous power 12 kW, solar resource and no export/no ENS. Only the PV panel count changes.

| Annual indicator | MC_REF (41 panels) | MC_P33 (33 panels) | Change |
|---|---:|---:|---:|
| Available PV, DC kWh | 21,657.2428 | 17,431.4393 | **−4,225.8035** |
| PV curtailed, DC kWh | 2,443.6043 | 549.2924 | **−1,894.3118** |
| PV used, DC kWh | 19,213.6385 | 16,882.1469 | **−2,331.4917** |
| Battery DC discharge, kWh | 9,648.8346 | 7,742.6287 | **−1,906.2059** |
| Annual grid imports, AC kWh | 3,107.4851 | 5,227.0919 | **+2,119.6068** |
| Self-sufficiency | 85.116% | 74.964% | −10.152 percentage points |
| Curtailed fraction of available PV | 11.283% | 3.151% | −8.132 percentage points |

Energy accounting: reducing panels loses 4,225.80 kWh potential DC PV. Of this, 1,894.31 kWh had been curtailed under the old design; the remaining 2,331.49 kWh was previously used. Reduced PV charging yields 1,906.21 kWh less battery DC discharge. Both effects increase grid imports after efficiency conversion. The curtailment reduction is **77.52%**, not small, but cannot be equated with energy delivered to households.


## Exact annual import decomposition, not just a heuristic explanation

The original signed DC-bus and AC-load balances imply, in kWh/year:

`Grid imports = Household demand − 0.95 × PV available + 0.95 × PV curtailed + 0.95 × (battery DC charging − battery DC discharging)`.

This is an identity for the specified 2025 model with no export or ENS, not an empirical regression. It separates the potential PV energy shortfall, unavoidable curtailed energy at the selected dispatch, and the battery conversion-loss term. It does **not** include independently modelled pandapower feeder losses.

| Term of annual grid imports | MC_REF, 41 panels | MC_P33, 33 panels | Change |
|---|---:|---:|---:|
| Load minus 95%-converted available PV, kWh | 303.619 | 4,318.133 | +4,014.513 |
| 95% of DC PV curtailment, kWh | 2,321.424 | 521.828 | −1,799.596 |
| 95% × (battery DC charge − DC discharge), kWh | 482.442 | 387.131 | −95.310 |
| **Result: grid import AC**, kWh | **3,107.485** | **5,227.092** | **+2,119.607** |

MC_P33's *available* PV at 95% conversion supplies at most **16,559.867 kWh AC** against 20,878 kWh load, even with no curtailment or battery losses. Therefore **at least 4,318.133 kWh of grid imports is unavoidable** under this fixed solar resource and inverter efficiency. The additional 908.959 kWh in the signed dispatch is explained by 521.828 kWh curtailed PV's AC equivalent and 387.131 kWh battery conversion losses. Eliminating the entire 549.292 kWh DC curtailment cannot eliminate imported energy.

The source curves and grid limit constrain timing. The detailed chronological replay separately demonstrates the source optimizer's absence of explicit immediate PV-first charging priority, but the PV-first replay still reaches the same annual import and curtailment totals while changing which hours are curtailed.

## 2. Exact optimization priority from original code

- `case1/studies/ac_aware_redispatch_v1/fixed_hardware.py` uses `fixed_settings(... objective='economic', export_policy='zero', allow_unserved=False)`, then creates an 8,760-hour Linopy LP with fixed PV, BESS energy, BESS power and inverter ratings, minimum battery physical SOC, and cyclic year-end state.
- `case1/studies/pypsa_joint_optimization_v1/model.py` connects PV and battery to SOLAR_DC; solar DC conversion through the PV_INVERTER to AC demand, while `GRID_IMPORT` enters only the AC bus. Battery charging is from SOLAR_DC, not grid. The grid-import marginal cost is assumed USD 0.29/kWh. There is no export generator under export_policy=zero. Battery charge/discharge links carry tiny marginal costs 0.00001 and conversion losses, but **curtailment has no positive economic penalty**.
- At fixed hardware, minimizing annual imports economically does not enforce *charge any available solar surplus immediately*. Perfect-foresight solutions can defer charging until later hours on the same day while producing the same annual import optimum. That makes **hourly curtailment location** non-unique.
- Model's 5 kVA PF=0.98 import proxy and the AC network are distinct: satisfying the proxy is not sufficient for feeder AC feasibility. These source schedules are energy-only and no pandapower AC status is claimed for MC_P33.

## 3. Source-replayed 8,760-hour hourly evidence

| Source diagnostic | MC_REF | MC_P33 |
|---|---:|---:|
| Hours with solar curtailment | 704 | 246 |
| Hours importing grid electricity | 1,778 | 2,809 |
| Hours with both curtailment and grid import | **0** | **0** |
| Annual curtailed PV when source battery is at minimum SOC | 1,859.33 kWh | **376.35 kWh** |
| Annual curtailed PV while battery charging is zero | 1,916.39 kWh | **385.83 kWh** |
| Curtailment recorded with full battery at hour end | 0 kWh | 0 kWh |

Therefore a substantial share of curtailment cannot be attributed to a full battery. The source schedule leaves the battery empty early in some daylight hours, because the perfect-foresight optimum charges later.

**Exact example: MC_P33, 13 January 2025 at 09:00.** Available PV 6.79755 kW DC, used 2.13615 kW DC, curtailed 4.66140 kW DC, battery charging 0, usable-state SOC at 1.832 kWh floor, grid import 0. At 14:00 the source uses PV to charge 5.02962 kW DC, but chronological PV-first would have charged earlier and curtailed an equivalent amount later.

**Seasonality is material:** MC_P33 has approximately 371.9 kWh (67.7%) of its 549.3 kWh curtailment in June–August, whereas about 2,629.4 kWh (50.3%) of its 5,227.1 kWh imported energy falls in February, March, October and November. This monthly separation cannot be erased with an eight-battery bank holding only tens of kWh, and there are diurnal supply-demand mismatches as well.

## 4. Independent chronological PV-first counterfactual

A simple PV-first chronological replay starts from each signed source's cyclic year-end battery state and, each hour, supplies AC loads with PV, then charges the battery with remaining PV, then discharges for unmet load and imports the residual grid deficit. It observes 0 grid charging, zero export, 12 kW battery power, 12 kVA inverter, 20% physical minimum SOC, efficiencies `ETA_INV=0.95`, `ETA_BAT=sqrt(0.95)`. It is **not** a new optimum nor a guaranteed feasible controller.

First independent calculations from exact signed CSVs:

| Metric | MC_REF | MC_P33 |
|---|---:|---:|
| Source grid imports kWh | 3,107.4851 | 5,227.0919 |
| PV-first grid imports kWh | 3,107.4851 | 5,227.0919 |
| Source PV curtailment kWh | 2,443.6043 | 549.2924 |
| PV-first PV curtailment kWh | 2,443.6043 | 549.2924 |
| Hours changing hourly curtailment schedule | 1,348 | 491 |
| Battery end-of-year SOC from source/greedy replay | 14.38215/14.38215 kWh | 14.19450/14.19450 kWh |

**Critical limit:** The MC_P33 pure PV-first rule raises AC grid import above the modelled PF=0.98 5 kVA grid proxy in **two hours**:
- 13 October 2025 19:00, import 5.32668 kW versus proxy 4.88161 kW (excess 0.44507 kW).
- 20 November 2025 20:00, import 4.91970 kW versus proxy 4.89919 kW (excess 0.02051 kW).

This does not mean the signed source LP itself violates its transformer proxy; it does not. The signed optimization anticipates constrained future hours and schedules battery energy accordingly. A purely greedy rule cannot replace that forward-looking operational requirement. The PV-first counterfactual is **not AC-feasible or grid-proxy-feasible** as-is, so never treat it as a recommended dispatch.

## 5. What to do next

The correct technical architecture should preserve the existing signed energy optimum and add a separately evaluated **operational policy**:
1. Primary constraints: solar serves current demand; no grid-to-battery charging, no export, minimum battery SOC, inverter/BMS limits and hourly 5 kVA grid-import proxy. Independent pandapower feeder AC remains a separate, stronger screen.
2. Primary goal: minimize annual grid imports or serve the agreed target without violating the transformer. Do not assume unlimited grid capacity in the causal policy.
3. Secondary goal: where annual import and battery throughput are equivalent, prefer **charging earlier from solar**, reducing early curtailment and respecting battery energy/power limits. This is a tie-breaker or operational dispatch preference, not an independent proof of more annual energy availability. Simple curtailment minimization alone can spur needless cycling or shift curtailment rather than eliminate it.
4. Use rolling-horizon forecast or conservative reserve to satisfy future evening transformer constraints. Analyze critical hours, forecast error, annual losses, cost sensitivity, curtailment, throughput, and source-verified SOC before suggesting controller or equipment changes.
5. Prioritize Study A real-network electrical evidence and margin on assumed **5 kVA transformer 106039**, not an unbounded AC-independent PV-first policy.

The contemporaneous user-run **new hardware AC stress receipt** on GitLab commit `c249f603` confirms all 8,760 hours converged for SS_P45_B9, MC_B10 and SS_B10 at PF=.95/length 1.6, but each design has **one or two transformer-overload hours**, peak 107.431% and min voltage 0.954236 pu. They remain uncorrected source schedules, not annual AC passing designs. No historical 432-case denominator is changed.

## Reproduction

The companion source-only `audit_pv_first_priority.py` verifies byte-level CSV hashes, exact cohort and hardware, annual source balances and manufacturer SOC, then independently generates two full-year PV-first counterfactuals, a 24-row monthly comparison, and source-to-causal diagnostic manifest. It never overwrites historical results, never launches PyPSA/pandapower, and records proxy failures rather than claiming AC feasibility.
