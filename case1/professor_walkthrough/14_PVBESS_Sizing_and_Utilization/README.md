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
