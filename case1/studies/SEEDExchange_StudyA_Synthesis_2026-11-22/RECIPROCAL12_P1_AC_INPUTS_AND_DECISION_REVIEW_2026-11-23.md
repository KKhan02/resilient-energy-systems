# Study A | reciprocal P1 bounded AC study, source-only planning audit

Date: 23 November 2026. Original 12-case materiality receipt is already present. No new AC power flow or optimization in this preparation.

## What was inspected

Reopened original frozen 16 reciprocal energy cases, source-tier list, signed source v6.2 model, P/Q solve function, provisionally attached EPM GIS case builder, original A0 106039 39-hour replay and A1 113699 annual corrected-source/nine-factor runner. Confirmed source-manifest ancestry and the user's nine-test A0 P/Q synthetic PASS. Separately, reciprocal12 source-only regression PASS remains unreported after the corrected fixture was committed. The earlier A1 113699 annual AC result is for SOC-corrected P, with 188 changed inverter power hours versus one original reciprocal min-cost target, so it cannot serve as exact unchanged-P source AC certification.

## A controlled pilot rather than broad reruns

Source archive covers 12 unmatched families (94022 four, 113699 four, 106039 two, 85398 two). Take the six highest-priority P1 families only: 94022 A0 target two, 113699 A1 target two and 106039 SS90 two. For each use the already-selected other-equipment evening stress timestamps and a maximum selected PV-availability daylight hour. Exact 18 source rows were independently extracted from the signed remote 300-row CSV, preserving grid import, gross load, inverter AC P, PV DC available, night-Q indicator, modelled assumed nameplate and target assignment. All six daylight picks are 2025-09-04 12:00 local standard time; 2025-11-27 20:00 is the 106039 PF .95 source apparent-power warning hour.

Simulating each event at PF .98 and .95 produces 36 bounded PF-case-hour tests with archived central-head inverter and Q ratio 0.25 daytime, Q-off at night, service x1. The AC runner is explicitly opt-in, uses the original signed frozen solver and does not silently edit or replace a dispatch, topology, SOC trajectory, hardware or source file. It saves separate diagnostic plots if executed. Internal pandapower Q search may make more than 36 actual Newton/power-flow evaluations. The output status distinguishes complete sample recording from physical/annual feasibility.

## Limits and next decisions

Use a passing preflight to verify exact source P and house-level load alignment, not electrical pass. A failing fixed-P hour can motivate AC-constrained Q/P redispatch and, if necessary, a changed architecture and complete 8,760-hour result. A passing sample cannot demonstrate annual feasibility, phase/neutral/thermal reality or EPM certified wiring, and the assumed 3/5 kVA transformer values are not actual nameplates. 85398 P2 remains unmatched and will need eventual validation for a full Study A decision. Study B/C and northern 25kVA exclusion remain locked as in the approved handover.

Guide: RECIPROCAL12_P1_AC_PILOT_RUN_LOCAL_2026-11-23.md. New test: test_matched16_reciprocal12_p1_ac_pilot.py. Pilot implementation: matched16_reciprocal12_p1_ac_pilot.py. Source event ledger: RECIPROCAL12_P1_18H_SOURCE_PLAN_2026-11-23.csv.
