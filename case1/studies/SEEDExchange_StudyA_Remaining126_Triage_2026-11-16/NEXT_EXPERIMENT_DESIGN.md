# Next experiment: narrow AC-aware repair and PV/BESS utilization frontier

## Gate 1. Feasible evening repair windows, not hypothetical capacity

Use the existing signed 2025 annual schedules. For each distinct failing model architecture and dispatch family, select each unique failing timestamp and its neighboring 12–24 hours. Confirm on the same date the PV power, demand, grid import, battery charging and discharge, operational SOC floor, maximum SOC, energy throughput, DC charge/discharge limits and inverter AC power. Identify candidate source hours whose foregone discharge does not create a new AC violation and whose reserved SOC stays valid at the target hour. For multi-hour violations, optimize a complete day or preferably the entire 8,760-hour trajectory with SOC continuity. Revalidate modified hours for all original PF/length combinations, retaining signed unchanged AC hours only if the electrical model remains a stateless hourly replay.

**First dispatch subset:** A1 94022, A1 113699 and A1 106039 causal. **Second:** A0 94022 and A0 106039, with many distinct violating timestamps. Reject unphysical transfers or schedules that introduce new violations. The A1 106039 optimized trial is already validated and is not part of the remaining correction backlog.

## Gate 2. Cable topology before battery sizing at 92395

Use the 92395 proposed STAR and MST source geometry, distinguish missing EPM LV evidence from assumed geometries, sweep conductor section size and possible PV/BESS connection location, and include cable length, connection cost, conductor ampacity, voltage drop and annual losses. Only after topology passes AC can PV/BESS size/cost be compared fairly. Never assert utility confirmation of either route.

## Gate 3. PV curtailment mechanism and marginal battery sizing

Select the current 22 hardware configurations and both optimized/causal schedules; analyze hour-by-hour DC balance, PV availability, DC charging, battery SOC, AC conversion, AC injection, grid imports and curtailed PV. The existing 44-row summary establishes patterns but **cannot tell how many curtailed kWh could be shifted to a later import hour**. For selected likely candidate territories, re-solve fixed hardware under progressively restricted PV-curtailment conditions or an epsilon objective, retaining 8,760-hour SOC, same annual ending SOC and realistic inverter/BMS constraints. Then test equipment variants: PV panels ±small integer steps, battery modules +0/+1/+2/+4, independent DC battery kW, inverter kVA options. This is a **proposed candidate grid**, not a completed numerical study.

Report **marginal recovered curtailed PV**, **marginal avoided grid import**, annualized equipment and O&M cost, effective new battery cycling, peak converter utilization, AC losses and stress-case feasibility. Price additional modules and PV in source USD before any currency conversion; use consistent battery usable versus nameplate units. Avoid rewarding excessive PV generation when it is subsequently curtailed. Evaluate future outage reserve separately.

## Gate 4. End-of-study ranking

Keep multiple defensible designs: minimum life-cycle cost subject to AC constraints, ≥90% *achieved* self-sufficiency subject to AC constraints, lower PV curtailment at justified marginal cost, and an eventual outage-reserve design. The share of unmet load during grid outages is **not** equivalent to annual grid autonomy. Validate requirements with the community and EPM before real-world recommendations.
