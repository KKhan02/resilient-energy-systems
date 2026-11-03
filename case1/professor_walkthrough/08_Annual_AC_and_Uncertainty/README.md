# Annual AC validation and fragility to uncertain inputs

For transformer 106039, head-mounted coordinated Q control with ratio 0.25, load PF 0.98 and 1.0 service-length multiplier passed 8,760/8,760 hourly AC checks. Yet minimum voltage was only 0.970005 pu, giving effectively no margin. A PF 0.90 and longer-service sensitivity loses feasibility in multiple cases. Nighttime Q operation and conductor parameters need hardware and field checks.

## Open the images in order

1. [01_annual_106039_voltage_loading.png](01_annual_106039_voltage_loading.png): 2025 full year 106039 voltage and transformer loading.
2. [02_Q_uncertainty_heatmap.png](02_Q_uncertainty_heatmap.png): Effect of power factor service length and Q setting.
3. [03_Q_ratio_vs_min_voltage_robustness.png](03_Q_ratio_vs_min_voltage_robustness.png): reactive capability and uncertain service length affect worst household voltage.

## Why the next stage followed

The remaining research is a chronological, SOC-consistent active-power redispatch or reinforcement step, followed by resilience and adaptability tests.

Original simulations, raw figures and manifests are retained outside this curated folder; see the [main walkthrough](../README.md) and its figure index.
