# San Rafael Case 1: corrected modelling scope and delivery gates

27 October 2026. This is a planning note, **not evidence of completed optimisation or verified electrical topology**.

## Objective

First determine whether each current *provisional* transformer customer territory can serve all of its existing candidate households under baseline loading and optimally sized PV+BESS. Only after that, test how much additional load can be hosted, including physical reassignment of houses from neighboring transformer territories where feasible, while maintaining an explicit self-sufficiency target, equipment limits and lifecycle cost.

## Stage 0: evidence-quality electrical register

- Keep all 35 H01–H35 property IDs. Verify actual residential customers, meters, transformer-service links, transformer nameplate kVA, LV phase and conductor routes.
- Existing provisional counts: 923494 (12), 931076 (7), 923848 (4), 900607 (4), 823002 (3), 241054 (1); H01/H02/H10/H29 remain unresolved or alternative.
- Only 931076/94022 and 923848/92395 have archived 5 kVA evidence. Other portal values are in **kW, not independently verified kVA**.
- Do not display hypothetical radial drops as physical service wires; produce a schematic or evidence matrix labelled provisional, and a separately verified topology diagram when source evidence arrives.

## Stage 1: all current candidate customers, no DER

- Keep current candidate territory membership intact. Do not split seven into five/two or twelve into five/seven as the principal analysis.
- Run pandapower representative hours and ideally annual scenarios with demand diversity, voltage and transformer/feeder thermal limits.
- Report min/max per-bus voltage, transformer kVA and duration over limit, loss and worst-case household, plus feasible/infeasible status conditional on known topology.
- For 12-candidate territory 106039, include explicit nameplate sensitivities (for example hypothetical 5, 10, 15 kVA) until actual transformer rating can be verified. Do **not** claim its rating is 5 kVA.

## Stage 2: sustain the SAME customers with PV+BESS

- For each transformer territory independently, sweep PV DC kWp, inverter AC kVA, BESS usable kWh, BESS power kW, dispatch policy, export control and demand uncertainty.
- Then perform joint sizing/dispatch optimization (economic, self-sufficiency and network hosting objectives), with the same scenario inputs and explicit matched technology bounds.
- Do not conflate the 386 scenario heuristic annual screen with full PyPSA capacity expansion or with full-year AC verification.
- Couple optimized hourly nodal load, PV and storage injections to pandapower. Feed constraint violations back into optimization, first via critical hours, later broader time series. Preserve SOC chronology and charging losses.
- Track self-sufficiency separately from outage survival, particularly under extended low-PV intervals and battery depletion.

## Stage 3: additional housing and neighboring-transformer transfer

- After existing customers pass both performance and self-sufficiency requirements, increment additional household loads at each existing transformer until a limit is reached.
- Test houses currently assigned to an alternative transformer only under explicit reassignment scenarios, with a proposed LV connection length/impedance, capacity and protection compatibility and estimated connection cost.
- Never count the same house twice. A geographical neighbor cannot be switched to another transformer just through accounting or battery sharing: actual physical reconnection and EPM approval may be necessary.
- Keep the original assignment as baseline, and label reassignment proposals as alternatives rather than current electrical reality.

## Stage 4: integrated community portfolio

- Compare per-territory feasible designs under a common 25-year accounting basis and community target. Optimize total present cost, operational self-sufficiency and number of covered households.
- Report capex, replacements, O&M, actual LV cable, meter, protection, civil installation and permitting where sourcing is possible. Keep unidentified costs as ranges, not zero.
- Do not require or invent new utility transformers. Only present reinforcement as a separate explicitly costed option if the client requests it.

## Non-negotiable presentation outputs

Each study must include a `figures/` folder, PNG/SVG, captions with units, source/ref and evidence flags, numerical summary tables, and a reproducible local plot script. At minimum: association/verified topology diagrams, time series of demand/PV/BESS/SOC, transformer loading/voltage violations, PV×BESS parameter sensitivity, optimized Pareto frontier, household hosting curve, transformer reassignment comparisons and lifecycle-cost breakdown. Existing figures in this pack are **historical results only**. No new hosting, annual AC coupling or optimization has been run here.
