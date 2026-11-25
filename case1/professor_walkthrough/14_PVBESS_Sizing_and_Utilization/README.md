# Stage 14. PV/BESS sizing and utilization (historical and later validated results)

## 34-house A0/A1 community energy frontier

[01_34house_architecture_cost_import_curtailment.svg](01_34house_architecture_cost_import_curtailment.svg) is a new vector figure from the source-matched 34-house, architecture-specific annual energy totals. It compares A0/A1 minimum-cost and higher-self-sufficiency tiers with **unchanged household population (64,532 kWh/year)** but different PV/BESS/inverter hardware. In both assignments, the higher-SS tier reduces imported energy but has higher modelled annual equipment+grid expense and more DC PV curtailment. This is a planning-model trade-off, not evidence that adding batteries causes more curtailment. No identical-hardware attribution, full population AC certification, field-installed cable costs or loss-aware objective is claimed.

Source: `case1/studies/SEEDExchange_StudyA_Matched_Cohort_2026-11-21/A0_A1_34H_MATCHED_SOURCE_ENERGY.csv`, independently cross-checked against the eight signed original-origin reciprocal portfolios. Pair this with Stage 15 for the separate fixed-hardware causal control.


**Research question:** Can equipment sizing reduce curtailed solar energy, imported electricity and annualized cost simultaneously, while respecting battery physics and household AC limits?

A1 transformer 106039 provides an 11-household example with **20,878 kWh/year** demand. The archived minimum-cost reference uses 41 panels and eight battery modules; the higher-self-sufficiency reference uses 49 panels and eight modules. Six new complete 8,760-hour fixed-hardware PyPSA solutions have been audited.

- **Minimum-cost reference:** 3,107 kWh/a grid imports, 2,444 kWh/a DC PV curtailment, USD 4,416/a modelled cost.
- **Minimum-cost plus ninth module:** 2,793 kWh/a imports, 2,095 kWh/a curtailment, USD 4,472/a. Energy improves, cost rises.
- **Higher-SS reference:** 2,035 kWh/a imports, 5,492 kWh/a curtailment, USD 5,057/a.
- **Higher-SS plus ninth module:** 1,478 kWh/a imports, 4,876 kWh/a curtailment, USD 5,042/a. Energy-only improvement and modest modelled cost saving.
- **Higher-SS plus tenth module:** 1,185 kWh/a imports, 4,550 kWh/a curtailment, USD 5,103/a. Further imports reduction at additional cost.

**Historical 17 November limitation and later resolution:** The first PF 0.95 x length 1.6 full-year replay found two MC_B9 and one SS_B9 transformer overload hours, so those *initial schedules* were not AC feasible. By 21 November, subsequent SOC-consistent redispatch and the 27-factor-case source-stitched annual review completed the six-design A1 106039 portfolio comparison. All six designs now have modelled 8,760-hour main-band AC passes under the nine reference PF/service combinations (the 27 new cases plus the independently archived original factors), but this does **not** establish field validity. The worst reviewed new-factor minimum voltage is 0.957239659 pu; worst assumed 5 kVA transformer loading 99.431814859%. The separate strict 0.97–1.03 pu band remains unmet. Source: `case1/studies/SEEDExchange_StudyA_Validated_Frontier_2026-11-21/NEW_HARDWARE_FULL_27_REMOTE_AUDIT.md`.

**Visual plan:** Add one uncluttered 8-design cost-versus-grid-import frontier, explicitly labelled `ENERGY-ONLY`, and one monthly energy/curtailment plot only after the underlying annual values and plot source are checked. Retain the historical Stage 02 and 03 figures rather than replacing them.

**Sources:** `case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17/`; new stress-run evidence `StudyA_A1_106039_Frontier_AC_v1/` on this sync branch. No installed site CAPEX, AC losses integrated into investment objective, Colombian approved export tariff or resilience claim.


## Source-verified figure generator, 17 November 2026

The three **new** Stage 14 PNGs are generated locally, not already committed as validated figures. The GitLab script `generate_stage14_figures.py` uses the original annual + monthly 2025 review CSVs, enforces source SHA-256, checks 8 cases and monthly reconciliation, then writes a non-overwriting `figures/` folder with a manifest. The user may review and push these results to the same synchronized branch. See `case1/studies/SEEDExchange_Continuation_2026-11-17/README.md` for full commands. Maintain ENERGY-ONLY and the known B9 AC-overload distinction.


## Next electrical gate, 17 November 2026

For changed nine-battery hardware (`SS_B9`, `MC_B9`), GitLab now contains a separate **exploratory SOC-neutral stress-case repair script** at `case1/studies/SEEDExchange_StudyA_B9_SOC_Trial_v1/b9_soc_trial.py`. It preserves signed 2025 energy and AC results and tests three proposed same-day discharge moves against the exact original AC solver at PF 0.95 and length x1.6. The script is not an optimized policy, and **no user-run physical AC correction result is yet available**. All-nine factors and any final hardware selection remain pending. Three pure synthetic tests passed locally, but do not substitute for source AC replay.


## 24 November: charging priority and curtailment timing

[02_pv_first_curtailment_timing.svg](02_pv_first_curtailment_timing.svg) shows a source-matched 24-hour comparison on 13 January 2025, MC_P33, 11-house A1 106039, 33 panels and eight modules. The PV-first rule shifts charging and spill earlier/later while daily and annual curtailment are unchanged to numerical precision. The annual rule breaches the grid-import proxy twice, so this is a diagnostic rather than an operational controller. Both complete archived 8,760-hour CSVs were reopened to check annual sums and timestamp parity; no new optimization. [Exact figure-day data](../../studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/FIGURE_MC_P33_2025_01_13.csv). The wider 18-case native causal archive already exists; the next local audit will extend coverage to exact reciprocal sources and additional fixed-hardware alternatives.


## 25 November: two targeted sizing decisions

[03_targeted_sizing_two_territories.svg](03_targeted_sizing_two_territories.svg) compares all seven new fixed hardware energy cases against their signed reciprocal references. At 113699, reducing PV and storage can lower cost and spill with higher imports; at 94022, adding modules lowers spill and imports at higher cost, without changing peak transformer proxy. New schedules await AC validation. Source: `StudyA_Battery_Sizing_Pilot_v1/SIZING_SUMMARY.csv` and [derived delta table](../../studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/SIZING_DELTA_FIGURE_SOURCE_2026-11-25.csv).

## 25 November: full-night reserve correction

[04_94022_full_night_reserve.svg](04_94022_full_night_reserve.svg) documents all three corrected 94022 A0 annual reference schedules, zero violations, 81 changed hours, unchanged model cost. Reference PF .98, length ×1.0 only. Source: [figure table](../../studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/FULL_NIGHT_FIGURE_SOURCE_2026-11-25.csv); audit in the same study folder. Prior energy-only Figure 34 retained.

## Python figure update, 25 November

Use the [walkthrough plotting generator](../generate_figures_30_36.py) to regenerate Figures 30–35 and create Figure 36 from the two annual AC summaries. Figure 36 compares the five 113699 alternatives and three corrected 94022 cases, separated by household count, including annual loss-cost sensitivity, DC spill and minimum voltage. All eight pass at PF 0.98 and service length x1.0 only; the nine-factor sizing screen remains pending. No generated figures are claimed until the local plotting run completes. Existing SVGs preserved for historical comparison, not accepted as Python-provenanced without reproducible generation.

Python-rendered [Figures 32–36](../python_figures_30_36_v1/) are now uploaded; use the active PNG paths in the figure index. The eight new designs pass the reference annual AC condition only.
