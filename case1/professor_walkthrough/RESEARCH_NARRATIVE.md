# SEEDExchange Case 1: research progress narrative

**El Arenal, Antioquia, Colombia | Research discussion, 3 November 2026**

This document is written for an intermediate discussion with the professor. It follows the [numbered figure folders](README.md), links to the original evidence and keeps completed findings separate from the next research questions. This is not the final academic poster.

## Research question and starting evidence

The study asks whether a rural electricity community can benefit from a shared solar photovoltaic (PV) and battery energy storage system (BESS), how its capacity should be chosen, and whether economically favourable operation is compatible with the actual constraints of the low-voltage network. The question is especially relevant when several households are supplied by relatively small distribution transformers. Adding a large shared inverter can reduce grid purchases, but it can also change the voltage at different points along the feeder.

We first constructed a reference system from the 2025 NASA POWER solar resource, the previously developed stochastic hourly household demand profiles and the available EPM transformer information. Thirty-five candidate properties were mapped. Six transformer territories contain provisional assignments; a northern 25 kVA transformer remains an alternative rather than an established seventh occupied territory. The household demand is synthetic and normalized using the earlier research dataset, not actual meter readings. The earliest layout used provisional geographic associations. After receiving EPM GIS data, we could reconstruct conductor segments and their node connectivity instead of inventing all feeder branches.

Open [01, community and inputs](01_Community_and_Inputs/) first. The preliminary sketch is a modelled network hypothesis, whereas the later EPM GIS map provides an infrastructure-backed LV backbone. The physical service drops from that backbone to individual homes are still assumed.

## What joint optimization tells us

The initial design problem was economic: how many PV panels and battery modules should be installed, which inverter size is appropriate, how much battery charging and discharging capability is needed, and how many homes might benefit? We therefore implemented a PyPSA/Linopy joint capacity-and-dispatch model with integer equipment decisions in the principal full-study MILP campaign. It accounts for PV production, DC-coupled battery operation, the usable state-of-charge trajectory, grid imports and the aggregate point-of-common-coupling (PCC) constraint. The reported full study comprises 6,840 tasks, of which 6,820 were energy-screen optimal and 20 infeasible under their model settings.

The PV and BESS plots in [02, joint sizing](02_Joint_PV_BESS_Sizing/) show the trade-off among technology size, annualized cost, self-sufficiency and the number of participating houses. Costs are based on historical component prices, a 25-year calculation horizon and assumed tariffs; they exclude verified construction and reinforcement costs. They are therefore **conditional economic estimates**, not an EPM-approved installation quotation. Changing the number of houses can force equipment upgrades, so neither capacity nor the cost per home necessarily follows a smooth curve.

Crucially, the solver knows all 8,760 hours in advance. This is **perfect-foresight optimization**. For the modelled weather and synthetic demand scenario, it supplies a useful idealized planning benchmark, but cannot be described as the performance of a forecasting-free, causal battery controller. Some earlier single-run outputs were continuous LP relaxations with fractional panel or battery-module equivalents; those are not buildable equipment selections and should not be confused with the main discrete campaign.

## The battery was already optimized

A central component of this work is the battery's *chronological operation*. The optimizer selects charging, discharging and SOC hour by hour. The system stores available solar electricity for later consumption when that is economical under the model assumptions. SOC follows the same uninterrupted annual trajectory when day, week and month plots are generated. The files in [03, battery operation](03_Chronological_Battery_Dispatch/) make that schedule visible, instead of presenting the battery as a simple static capacity number.

At this stage, however, the dispatch constraints were aggregate energy and PCC approximations. The optimizer had not solved the actual household voltages, conductor currents and feeder losses simultaneously. That distinction became the next engineering question.

## Why independent power-flow validation was necessary

We replayed the optimized hourly active-power trajectory in pandapower. The first test used a representative 324.5 m radial low-voltage feeder, with 5–15 household scenarios, alternative inverter positions, two load distributions and two household power factors. It showed that an energy design meeting the PCC proxy can still experience undervoltage. Under a full-year representative reference, six houses passed the chosen 0.97–1.03 pu voltage screen; the seven-house case already produced a low-voltage hour. These are results for the **generic test feeder**, not a verified number of houses supportable by any specific EPM transformer.

See [04, representative feeder](04_Representative_Feeder_AC_Screen/). This result motivated a more specific network model rather than an immediate conclusion that larger communities are impossible.

## From hypothetical feeder routes to EPM GIS

An intermediate geographic model used minimum-spanning-tree and star feeder assumptions with 1.0, 1.3 and 1.6 length factors. The results changed substantially with the routing method. Straight-line cable estimates are therefore inadequate as final evidence. The subsequently received EPM GIS archive contains recorded LV conductor segments, transformer locations, attributes and node connectivity. We reconstructed the mapped LV backbone and connected each candidate home to a nearby eligible conductor using an explicit service-drop assumption.

The figure in [05, geographic EPM evidence](05_Geographic_EPM_Feeder_Evidence/) shows the important distinction. Recorded segments are a stronger basis for the electrical graph than invented cable paths, but the service drops, cable impedances, phase allocation and household-to-transformer supply assignments are not field-verified. The model remains a balanced equivalent rather than a detailed split-phase customer connection representation.

## Inverter position and reactive-power control

The next question was whether the shared PV/BESS inverter should connect at the transformer head, around the electrical midpoint or near the remote end of the feeder. Remote injection can improve low-voltage operation, but can also create overvoltage in sunny hours. We reused the piecewise HIL Volt–Var logic, with a deadband and adjustable Q capability. Reactive support improved some low-voltage cases, while large Q flows sometimes overloaded a small transformer and increased losses.

A transformer-aware safeguard could reduce inverter Q when the transformer was overloaded, but that adjustment sometimes removed the reactive absorption that had been suppressing overvoltage. [06, siting and Volt–Var](06_Inverter_Siting_and_VoltVar/) documents this conflict. It explains why simply increasing the Q range is not necessarily a sound solution.

We therefore implemented coordinated AC Q selection, searching both reactive directions while evaluating minimum and maximum household voltage, transformer loading and conductor loading in pandapower. We swept the capability ratio rather than comparing only 0.25 and 0.48. In the 40-hour reference critical sample for transformer 106039, a Q ratio of 0.20 at the midpoint or 0.25 at the transformer head was enough to pass all tested voltage and thermal screens. The 94022 territory retained unresolved hours. Those outcomes are visible in [07, coordinated Q](07_Coordinated_AC_Q_Optimization/).

## Full-year success, but little robustness margin

To test whether a promising critical-hour result was merely selective, we ran all 8,760 hours of the 106039 twelve-house reference configuration in the EPM GIS-based pandapower model. The head-connected inverter with coordinated Q control, ratio 0.25, household PF 0.98 and a 1.0 assumed service-length factor passed every hourly AC screening check. The minimum voltage was **0.970005 pu**, essentially on the selected lower limit, while transformer loading remained below 100%.

The conclusion is therefore **conditional feasibility**, not network certification. When household PF was reduced to 0.90 and assumed service lengths increased to 1.3 or 1.6, not all configurations remained feasible. The 106039 operating point also used reactive support during hours with negligible inverter active power. Whether the chosen hardware can produce that nighttime reactive power must be established from the actual inverter capabilities. [08, annual validation and uncertainty](08_Annual_AC_and_Uncertainty/) separates this positive annual result from the sensitivity failures.

## Scientific contribution and next research decision

The completed work has two linked contributions. First, it compares economic PV/BESS/inverter capacities while optimizing the battery's chronological charge, discharge and SOC. Second, it demonstrates why the resulting power injections need feeder-specific AC validation and how coordinated reactive-power control can restore conditional feasibility in some cases.

The remaining link is **SOC-consistent AC-aware active-power redispatch**. For transformer 94022, some difficult evening hours had zero scheduled inverter active injection. Extra BESS discharge might improve voltage and transformer loading, but the model must first verify stored energy, inverter kVA, charging and discharging limits and the consequences for later hours. It must then measure the cost difference relative to the original perfect-foresight optimum. Simply adding power in pandapower without rebalancing SOC would not be a credible contribution.

That next stage, followed by resilience during outages and adaptability to additional households, is proposed work rather than a completed result. [09, research decisions](09_Next_Research_Decisions/) records the discussion points. The complete simulation source and original output tables are linked in the [research status audit](../RESEARCH_STATUS_AND_AUDIT.md), while the non-core historical plots and old transfer packages remain available through the [research archive](../research_archive/).
