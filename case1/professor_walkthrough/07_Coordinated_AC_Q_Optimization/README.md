# Coordinated AC reactive-power selection and the Q-ratio trade-off

**Question:** Is there a network-aware reactive-power command that satisfies household-voltage and transformer/line-loading constraints, and what Q capability is actually needed?

The coordinated controller searches permitted Q values and checks AC load flow at every sampled operating point. This is different from autonomous local Volt-Var control.

## Figures

1. [01_Q_ratio_feasibility_sweep.png](01_Q_ratio_feasibility_sweep.png): Selected-hour AC feasibility versus Q ratio for inverter head and midpoint placements on transformers 94022 and 106039.
2. [02_midpoint_Q_voltage_transformer_tradeoff.png](02_midpoint_Q_voltage_transformer_tradeoff.png): Increasing Q capability raises the minimum voltage in some scenarios, but also changes the maximum transformer loading.

## Quantitative interpretation from the original 40-hour sweep

- **106039, head:** Q ratio 0.25 was the **lowest tested ratio** that passed all 40 selected hours under the historical 0.97–1.03 pu screen.
- **106039, midpoint:** ratio 0.20 was the lowest tested passing value. At 0.20, minimum voltage was 0.970037 pu, maximum transformer loading 93.525% and mean sampled losses 0.154164 kW. At ratio 0.60, the maximum loading increased to 98.56% and mean sampled losses to 0.1841 kW.
- **94022, midpoint:** even the best tested settings reached only 38/40 feasible sampled hours. Q alone did not solve all cases under the original fixed dispatch.

These values are specific to the original 40-hour search, assumed installed-P reference, PF 0.98 and modelled connections. They are **not full-year feasibility claims**. The older controller study may select Q at night; the newer manufacturer-SOC study disables nighttime Q until actual inverter documentation supports it.

The original evidence and figure source remain in the [coordinated-Q review](../../research_archive/past_review_packages/SEEDExchange_Coordinated_Q_Sweep_Review_2026-11-03/). The Q ratio is a model capability proxy, not a verified inverter specification.

## Next step

The 8,760-hour AC tests and SOC-consistent active-power redispatch are documented in [08](../08_Annual_AC_and_Uncertainty/) and [09](../09_AC_Aware_Redispatch/).
