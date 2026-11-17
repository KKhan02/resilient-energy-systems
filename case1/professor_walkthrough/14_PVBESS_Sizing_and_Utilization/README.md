# Stage 14. PV/BESS sizing and utilization (under validation)

**Research question:** Can equipment sizing reduce curtailed solar energy, imported electricity and annualized cost simultaneously, while respecting battery physics and household AC limits?

A1 transformer 106039 provides an 11-household example with **20,878 kWh/year** demand. The archived minimum-cost reference uses 41 panels and eight battery modules; the higher-self-sufficiency reference uses 49 panels and eight modules. Six new complete 8,760-hour fixed-hardware PyPSA solutions have been audited.

- **Minimum-cost reference:** 3,107 kWh/a grid imports, 2,444 kWh/a DC PV curtailment, USD 4,416/a modelled cost.
- **Minimum-cost plus ninth module:** 2,793 kWh/a imports, 2,095 kWh/a curtailment, USD 4,472/a. Energy improves, cost rises.
- **Higher-SS reference:** 2,035 kWh/a imports, 5,492 kWh/a curtailment, USD 5,057/a.
- **Higher-SS plus ninth module:** 1,478 kWh/a imports, 4,876 kWh/a curtailment, USD 5,042/a. Energy-only improvement and modest modelled cost saving.
- **Higher-SS plus tenth module:** 1,185 kWh/a imports, 4,550 kWh/a curtailment, USD 5,103/a. Further imports reduction at additional cost.

**Critical limitation:** The new nine-module designs are not yet AC-feasible in the strongest initial PF 0.95 x length 1.6 full-year replay. MC_B9 has two transformer-overload hours; SS_B9 has one; voltage/line limits pass. Do not label them validated electrical designs. Follow-up requires SOC-consistent night-time redispatch, verified AC changed-hour tests and then all nine factors.

**Visual plan:** Add one uncluttered 8-design cost-versus-grid-import frontier, explicitly labelled `ENERGY-ONLY`, and one monthly energy/curtailment plot only after the underlying annual values and plot source are checked. Retain the historical Stage 02 and 03 figures rather than replacing them.

**Sources:** `case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17/`; new stress-run evidence `StudyA_A1_106039_Frontier_AC_v1/` on this sync branch. No installed site CAPEX, AC losses integrated into investment objective, Colombian approved export tariff or resilience claim.


## Source-verified figure generator, 17 November 2026

The three **new** Stage 14 PNGs are generated locally, not already committed as validated figures. The GitLab script `generate_stage14_figures.py` uses the original annual + monthly 2025 review CSVs, enforces source SHA-256, checks 8 cases and monthly reconciliation, then writes a non-overwriting `figures/` folder with a manifest. The user may review and push these results to the same synchronized branch. See `case1/studies/SEEDExchange_Continuation_2026-11-17/README.md` for full commands. Maintain ENERGY-ONLY and the known B9 AC-overload distinction.


## Next electrical gate, 17 November 2026

For changed nine-battery hardware (`SS_B9`, `MC_B9`), GitLab now contains a separate **exploratory SOC-neutral stress-case repair script** at `case1/studies/SEEDExchange_StudyA_B9_SOC_Trial_v1/b9_soc_trial.py`. It preserves signed 2025 energy and AC results and tests three proposed same-day discharge moves against the exact original AC solver at PF 0.95 and length x1.6. The script is not an optimized policy, and **no user-run physical AC correction result is yet available**. All-nine factors and any final hardware selection remain pending. Three pure synthetic tests passed locally, but do not substitute for source AC replay.
