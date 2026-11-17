# Engineering assessment of 175 mapped-feeder SOC windows

This document interprets the signed local 2025 SOC-window archive uploaded on 16 November 2026. No new power-flow simulation or investment optimization was performed for these findings.

## 1. Evidence and denominators

The source has 175 event keys, each a (network assignment, transformer, hardware tier, dispatch policy, timestamp) observation. The previous 126 remaining failing PF×length sensitivity runs contain many repeated configurations. Here 175 does not mean 175 unique hours across a single physical community. There are 16 distinct annual schedules in the extract.

- A1: 19 design-dispatch events and 8 annual schedules. All 19 are at the operational end-of-hour SOC floor. An earlier same-day DC discharge >0.15 kW is present in the last 8 hours for each.
- A0: 156 design-dispatch events and 8 annual schedules; 133 of 156 are at the end-hour SOC floor. An earlier same-day DC discharge >0.15 kW is present in the last 8 hours for each.
- A0 94022: 112 events, 4 annual schedules. A0 106039: 44 events, 4 annual schedules.
- A1 94022: 12 events, 4 annual schedules, 5 distinct event dates. A1 113699: 4 events, 2 schedules, 2 distinct dates. A1 106039: 3 causal events, 2 schedules, 2 distinct dates. The previously validated A1 106039 optimized case has already been excluded.

## 2. What the SOC-window evidence supports

All 19 A1 evening events have a possible earlier-hour energy source, but no particular DC power or donor time is yet accepted. Some potential donors occur with positive PV and some with positive grid import. Holding back discharge creates increased net grid demand at the donor; it can cause a new voltage or loading failure there. Whole-day SOC can also exceed upper capacity limits if retained energy is not accounted for. Correct counterfactuals therefore require the full signed 8,760-hour trajectory plus AC re-simulation at source and sink.

The valid 106039 optimized proof of concept established a conservative method: shift discharge to a constrained hour, preserve energy and SOC, rerun changed AC hours, and reuse unchanged signed AC snapshots. The A1 trial script extends that **method**, not its success claim, to the remaining A1 sources. Its accepted moves must pass the nine approved PF/route scenarios; partial or unsuccessful trials remain explicit.

## 3. Why A0 needs its own multi-event optimization

A0 has 156 event observations over 8 source schedules, with multi-hour clusters. Independent greedy moves can fail by borrowing from another stressed hour or spending energy twice. It is not enough to know that each hour individually has a donor. Use a day-level or annual SOC-constrained dispatch optimization, with AC-safe source and target corridors and optional battery power/line current constraints. Retain no-export and no-unserved-load assumptions and separate achieved self-sufficiency, curtailment, network AC losses and equipment expense.

For A0 106039, the worst event reports transformer loading 119.38% (in one causal min-cost sensitivity) under the *modelled* 5 kVA transformer assumption. For A0 94022 the minimum household voltage reaches 0.93728 pu in the retained failures. It is premature to claim either is dispatch-correctable without source-hour AC feasibility.

## 4. PV utilisation, sizing, resilience

All selected remaining evening constraint hours occur without contemporaneous PV. Correcting them by reserving discharge will **not by itself reduce daytime curtailment**, increase available PV energy, or change annual grid purchases under the energy-neutral shifts. A separate battery/PV utilization frontier should treat actual avoided future imports (not merely captured curtailed kWh) as a benefit, test additional battery energy against independent DC battery power and inverter AC constraints, and include network compliance and additional cable or equipment costs. Future outage resilience needs a separately agreed critical-load definition and SOC reserve policy.

## 5. Research and repository boundaries

- The geographic A0/A1 service connections are scenario assumptions, not utility-certified household wiring.
- The proposed 92395 STAR/MST networks are not EPM-verified LV layouts; study them as network design options in Study B, not as validated utility topology.
- Keep local archived 432 AC replays, historical 6,840 investment tasks and all source manifests immutable. New fixed-schedule trials are overlays, not replacements.
- Use the project's research walkthrough to show progression from gross load to spatial assignment, physical feeder constraints, storage coordination, topology alternatives and only then resilience.
- Do not change GitLab without explicit approval and a prior local repository diff review.
