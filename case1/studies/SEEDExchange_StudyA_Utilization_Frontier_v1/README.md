# Study A, next phase: A1 106039 annual PV/BESS utilization frontier

**Status:** Ready for *local numerical execution*, not completed sizing evidence. Source-audited research package prepared 17 November 2026. No original model or signed output is overwritten. It does not modify GitLab.

## What it answers

A1 transformer 106039 has the strongest existing curtailment-sizing question. The approved 11-house, 2025 reference uses 49 × 435 Wp PV modules, 8 Deye battery modules, 14.1102 kW DC battery power and a 20 kVA inverter. Existing signed 2025 results: 5,492.23 kWh of DC PV curtailment, 2,034.60 kWh grid imports, 90.2548% self-sufficiency and approximately USD 5,056.59/year for PV+BESS equipment plus grid purchases (excluding feeder investment and real losses).

We **do not rerun either existing signed reference**. Six new full-year fixed-hardware PyPSA experiments vary storage capacity and PV panel count independently. A further four are reserved for the second phase, if the pilot justifies them. The complete plan is in `FRONTIER_HARDWARE_PLAN.csv`.

## Exact experiment design

- **Two read-only signed references:** `MC_REF` = 41 panels/8 batteries/12 kW battery/12 kVA inverter; `SS_REF` = 49/8/14.1102 kW/20 kVA.
- **Pilot, six new annual LP solves:** `SS_B9`, `SS_B10`, `SS_P45`, `SS_P41_KEEP20`, `MC_B9`, `MC_P37`.
- **Additional four only if justified:** `SS_B9_POWER16`, `SS_P45_B9`, `MC_B10`, `MC_P33`.
- **2025 energy input:** same signed 11-house individual demand profiles, hourly NASA PV availability, 8,760 consecutive hourly steps; same 5 kVA **research assumption**, PF .98 dispatch screen, zero export, zero unserved load.
- **Hardware:** original PV inverter input ratio <=1.5, Deye 50A/44.8V = 2.24 kW continuous per module, original inverter DC battery port limits, manufacturer physical SOC minimum 20%, original conversion efficiencies and **cyclic annual** battery SOC.
- **Method:** imports the original `fixed_hardware.solve_fixed` and existing model. Each candidate fixes equipment *before* the full annual dispatch solve. This is a fixed-hardware dispatch comparison, not a new global investment MILP and not a causal control simulation.
- **Economics:** original 25-year annuity/replacement and assumed USD 0.29/kWh import. Solar, battery and inverter annualized equipment costs change with hardware. Marginal battery DC power cost remains zero in the original model because no sourced quote exists. Taxes, site works, utility work, cable CAPEX, thermal-loss cost and inverter standby are not included.
- **Outputs:** full annual hourly CSV and SHA-256 signed JSON per solved candidate, plus 12-month energy and annual investment/cost comparison tables. No new AC feasibility is asserted. The later stage must replay selected portfolios through pandapower and check the complete annual PF/length set, with AC-aware correction as required.

## Local instructions, Miniforge or Anaconda Prompt

Extract **the inner `SEEDExchange_StudyA_Utilization_Frontier_v1` folder** from the ZIP under `case1\studies\`. The script expects the original signed checkout and all previously verified annual source outputs under their established locations.

From your repository root:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Utilization_Frontier_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_Utilization_Frontier_v1\run_a1_106039_frontier.py" --plan --profile pilot
python "case1\studies\SEEDExchange_StudyA_Utilization_Frontier_v1\run_a1_106039_frontier.py" --repo-root . --preflight --profile pilot
python "case1\studies\SEEDExchange_StudyA_Utilization_Frontier_v1\run_a1_106039_frontier.py" --repo-root . --run --profile pilot --out "StudyA_A1_106039_Utilization_v1" --zip-out "StudyA_A1_106039_Utilization_Pilot_v1.zip"
```

Upload `StudyA_A1_106039_Utilization_Pilot_v1.zip` even if some variants are infeasible. All successful results are preserved and individually verified. Infeasible cases remain explicitly unresolved, not converted into false successes. Run `--profile full` only after reviewing the pilot, using the **same** `--out` for signed case-level reuse and a distinct `--zip-out` such as `StudyA_A1_106039_Utilization_Full_v1.zip`.

### Important controls

- Source integrity: `secure_context` checks original v6.2 and all model/GIS input hashes. The two signed energy references are checked for source manifest, full annual chronology, exact cohort and hardware.
- On a completed local output directory, the runner checks the source, digest and 8,760 rows and reuses without rerunning. A partial or mismatched folder requires inspection and is never overwritten.
- A design is not accepted as an AC-feasible replacement merely because energy cost or curtailment improves. The previously validated A1 voltage correction does not transfer automatically to newly optimized equipment and schedules.
- The runner verifies a physical 20% SOC floor and original inverter/continuous-current rules. It does not certify product compatibility or protection arrangements.
- It does not invent resale tariffs, hydro resource, network CAPEX, resilience/autonomy results or Colombia emissions factors.

## Existing non-solver results in this package

`A0_A1_EQUAL_POPULATION_ENERGY_COST_SCREEN.csv` reconciles two assignments, two hardware-selection tiers and the **same 34 households**. `STUDYB_92395_EXISTING_ANNUAL_SCREEN.csv` isolates the conditional STAR versus MST network outcomes. These were produced by `build_existing_decision_tables.py` using signed, audited prior results, without new numerical models. See `RESEARCH_SCOPE_AND_DECISIONS.md` for interpretation and future actions.
