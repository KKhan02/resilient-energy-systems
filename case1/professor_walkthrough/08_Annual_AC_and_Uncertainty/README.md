# Full-year AC validation, voltage reference bands and network uncertainty

This stage distinguishes **archived Q-only AC screening** from the later **manufacturer-SOC, nighttime-Q-off annual AC results**. All operating points use provisional GIS household connections and a balanced LV equivalent. Full-year hourly voltage magnitude screens do not certify compliance with duration-based supply-voltage standards.

## Figures

1. [01_annual_106039_voltage_loading.png](01_annual_106039_voltage_loading.png): **Historical** annual 106039 head-inverter Q-control result, 8,760/8,760 under the **original 0.97–1.03 pu model screen**, minimum voltage 0.970005 pu. This predates the newer manufacturer's SOC and conservative nighttime-Q assumptions.
2. [02_Q_uncertainty_heatmap.png](02_Q_uncertainty_heatmap.png): Earlier critical-hour Q/uncertainty study. **Sampled-hour only**, with original thresholds and inverter Q assumptions.
3. [03_Q_ratio_vs_min_voltage_robustness.png](03_Q_ratio_vs_min_voltage_robustness.png): Earlier Q ratio versus voltage under selected uncertainty conditions.
4. [04_94022_seven_stress_full_year_voltage_duration.png](04_94022_seven_stress_full_year_voltage_duration.png): **New** full-year voltage-duration curve at PF 0.90 and service-length multiplier 1.6, with fixed SOC-corrected inverter dispatch.
5. [05_94022_seven_stress_voltage_band_comparison.png](05_94022_seven_stress_voltage_band_comparison.png): **New** comparison of failed hourly magnitude screens for four voltage bands. No AC simulation was rerun for these alternative thresholds.
6. [06_94022_seven_stress_strict_failures_by_month.png](06_94022_seven_stress_strict_failures_by_month.png): **New** monthly distribution of the strict research threshold failures in the complete stress-test year.

## Updated full-year reference results

| Configuration | Operating assumptions | Annual AC result | Minimum voltage | Maximum transformer loading |
|---|---|---|---:|---:|
| 94022, 7 homes, 26 panels, 5 battery modules, 7.6 kVA inverter | 20% physical min battery SOC, PF 0.98, service factor 1.0, nighttime Q off, original strict band 0.97–1.03 pu | Manufacturer baseline: **8,756/8,760** strict passes | 0.968184 pu | 62.29% |
| Same 94022 equipment, feedback-redispatched annual schedule | Same assumptions and original strict band | **8,760/8,760** strict passes | 0.970099 pu | 58.58% |
| 106039, 12 homes, 41 panels, 8 battery modules, 12 kVA inverter | 20% physical min SOC, PF 0.98, service 1.0, nighttime Q off, **engineering band 0.95–1.05 pu** | **8,760/8,760** engineering passes | 0.955651 pu | 94.44% |

The initial **seven-house** manufacturer baseline also passed all 8,760 hours under the proposed 0.95–1.05 pu engineering target. The annual feedback change addressed the more demanding **research** lower threshold rather than a documented Colombian regulatory violation.

The **12-house** manufacturer-SOC baseline costs approximately USD 4,820.76/year in the energy-only model, versus USD 4,767.83/year in the historical optimized baseline. The AC replay models approximately 456.31 kWh of annual network losses, **excluded** from that energy objective.

## Annual versus critical-hour uncertainty

- **94022, 7 homes, PF 0.90 and service factor 1.6:** all 8,760 hours converge, with **zero** violations at 0.95–1.05 pu, but **111** below the original 0.97 pu research floor. Minimum voltage 0.960979 pu; peak transformer loading 64.60%. This result covers the **full year**, with active dispatch unchanged under the altered PF/service-length assumptions.
- **106039, 12 homes, nine PF/length combinations:** the available selected-hour study evaluates **96 critical hours per case**. Five of nine pass the 0.95–1.05 pu and thermal screens; the PF 0.90/service 1.6 stress case has **32 distinct failed selected hours**, a 0.944110 pu minimum voltage and 106.86% peak transformer loading. The original sample has **zero daylight PV hours**, so it cannot certify daytime or full-year stress robustness. Annual campaign validation is the next evidence gate.

## Voltage-policy interpretation

The original model's 0.97–1.03 pu range is a **strict research sensitivity**, not an established EPM approval limit. Compare separately against the proposed engineering target 0.95–1.05 pu, the historical EPM NT-13 technical magnitude reference 0.90–1.05 pu (current project applicability not verified) and the Colombian national 0.90–1.10 pu steady-state magnitude reference. None of our hourly GIS proxies establishes formal regulatory compliance.

## Source evidence

- [Seven-house manufacturer annual AC summary](../../studies/ac_aware_redispatch_v1/outputs/seven_manufacturer_annual_ac_01/annual_ac_summary.json)
- [Seven-house feedback annual AC summary](../../studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_ac_check_01/annual_ac_summary.json)
- [Seven-house full-year stress summary](../../studies/ac_aware_redispatch_v1/outputs/seven_worst_full_corrected_figures_01/full_year_voltage_band_summary.csv)
- [Twelve-house manufacturer annual AC summary](../../studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02/annual_ac_summary.json)
- [Twelve-house selected-hour sensitivity summary](../../studies/ac_aware_redispatch_v1/outputs/twelve_robustness_critical_01/sensitivity_scenarios.csv)
- [Historic 106039 annual Q-only source figure](../../research_archive/past_review_packages/EPM_Annual_Robustness_Review/figures/02_annual_106039_daily_voltage_loading.png)
