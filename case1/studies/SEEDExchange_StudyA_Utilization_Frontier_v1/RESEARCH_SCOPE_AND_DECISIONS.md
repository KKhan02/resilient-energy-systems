# SEEDExchange 17 November 2026: Study A completion and transition to sizing and Study B

## A. Correct interpretation of completed network work

The original 432 annual PV+BESS AC sensitivity runs produced 376 passing and 56 failing scenario runs **after the verified SOC-aware corrections**. The new, separately labelled A0 94022 five-edge R×0.5 research network passed all 36 annual conditions, creating a **conditional mixed-network overlay of 408 passing and 24 failing cases**. Neither the physical H01/H06 service conductors nor real retrofit costs are known. The new AC results are not replacements for the signed original network.

The 24 remaining failures correspond to proposed **A0 92395 MST** geometry, not measured EPM LV lines. Its four-house energy cohort is the same under A0 and A1. The alternative STAR routing passes the 36 existing PV/BESS annual AC conditions for that cohort.

## B. Like-for-like energy economics, corrected four-house selection

The reconciled table uses 34 unique houses, annual gross demand 64,532 kWh for both assignments, and the newer four-house optimization records for A0 113699 and A0 85398 where they exist. All figures are 2025 modelled USD/year, historical equipment and import price, before actual LV network investment and loss charges.

| Assignment | Equipment selection | Annual equipment plus grid cost | Grid imports | PV curtailment |
|---|---|---:|---:|---:|
| A0 | minimum-cost | USD 13,783.15 | 11,039.93 kWh | see accompanying CSV |
| A1 | minimum-cost | USD 13,750.91 | 11,665.83 kWh | see accompanying CSV |
| A0 | higher-SS | USD 14,529.81 | 5,394.20 kWh | see accompanying CSV |
| A1 | higher-SS | USD 14,647.02 | 5,821.75 kWh | see accompanying CSV |

The earlier A0 higher-SS figure approximately **USD 14,953/year** used two *borrowed archived five-home hardware references* instead of the newer four-home designs. Those two source families are distinct; the newer four-house choices lower the A0 higher-SS equipment-plus-grid annual estimate by roughly USD 423. We must label which is being compared. A1 min-cost is approximately USD 32/year lower, but A0 higher-SS is approximately USD 117/year lower, before additional physical costs. No economically superior *buildable* assignment has been established.

At PF .98, length ×1, using **original, pre-correction AC dispatch**, energy-case feeder losses are about 1,753/1,716 kWh for A0/A1 minimum-cost and 1,707/1,679 kWh for A0/A1 higher-SS. Do not silently reuse these losses for post-correction schedules or the hypothetical five-edge A0 network. The illustrative `0.29 USD/kWh × network loss` column is a screening proxy and NOT an integrated loss-aware market settlement.

## C. A1 106039 PV/BESS frontier

Why this case first: the signed higher-SS reference curtailed 5,492.23 kWh of DC PV and imported 2,034.60 kWh over 2025, with eight battery modules. Larger storage may reduce midday spill *and* evening imports, but added modules cost money, while reducing panel count may improve equipment utilization with lower annual production. Different battery power, inverter sizes and annual cyclic SOC schedules may change these trade-offs.

The pilot is intentionally factorial in stages rather than another 6,840-run sweep: two signed reference configurations plus six new fixed-hardware 2025 PyPSA schedules. The second set of four alternatives is conditional on results. Annual cost, imports, curtailment, module cycles, SOC range and seasonal energy are reported. Network AC feasibility, actual conductor/transformer data, inverter hardware approvals, grid connection, protection and loss-aware network economics require follow-up. Explicit PV-curtailment penalties also require safeguards against pointless dissipative battery cycling. Reporting curtailment under a fixed-hardware minimum-import dispatch avoids claiming all curtailed DC power could be used.

## D. Study B 92395 topology and cost gate

The proposed STAR geometry has about **1,153.16 m** of direct feeder length; the proposed MST about **549.82 m**, a roughly 603.34 m cable-route difference under their respective assumptions. Both are hypothetical; no verified EPM LV backbone has been established. Across the completed annual PV/BESS AC portfolio, STAR passes 36/36 sensitivity runs and MST passes 12/36, failing 24. The annual-loss and voltage comparisons by tier and dispatch are in `STUDYB_92395_EXISTING_ANNUAL_SCREEN.csv`.

Next Study B comparison should vary **physical cable choices (R, X, ampacity and price), branching geometry, inverter connection position and installation costs**, with independent full-year AC checks. Do not add total Euclidean length times an invented rural Colombian €/m rate as a validated investment cost. Distribution losses, neutral/phase effects, easements, service/meters, protection, O&M and maintenance also matter. The cost decision should compare a feasible MST revision, STAR and an explicitly designed branched radial alternative, not assume the original MST geometry must be repaired.

## E. Next stages and general principles

- Verify local PV/BESS pilot before running secondary configurations. Pareto-rank designs by annualized equipment and import expense, curtailment, battery cycles and self-sufficiency, then AC-check only nondominated candidates. A different hardware solution cannot inherit earlier battery-shift AC results.
- After A1 106039, extend the same tested protocol to A1 94022 and A1 113699, then remaining groups if useful. Do not duplicate archived 6,840 optimizations.
- Complete a physically defensible 92395 Study B network comparison and document site-specific topology uncertainty, then advance to Site A Study C under the same evidence protocol.
- Define outage resilience separately. Proposed measures: critical-load service %, unserved critical energy and survival duration under specified outage start, BESS initial SOC, islanding hardware and solar conditions. Neither annual autarky nor no-export proves backup capability.
- Keep the curated research walkthrough chronological: historical cost frontier, geography and gross-load evidence, validated AC feedback, conditional A0 conductor study, then new hardware-utilization and Study B decisions. New physical/CAPEX conclusions stay provisional.
- Preserve original outputs and GitLab. Sync only reviewed research packages after explicit approval. No GitLab writes in this phase.
