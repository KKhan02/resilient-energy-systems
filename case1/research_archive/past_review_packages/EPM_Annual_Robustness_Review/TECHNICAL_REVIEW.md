# EPM GIS coordinated-Q: annual validation and uncertainty screening

## Study status
- **Annual:** 8,760 / 8,760 converged and passed the model screening limits for transformer **106039** (12 assumed houses, head-mounted inverter, load PF 0.98, service factor 1.0, Q ratio 0.25).
- **Robustness:** 32 configurations, 40 critical hours each, PF 0.90, service factors 1.3 and 1.6, two transformers and two inverter positions, four Q ratios.
- **Limits:** 0.97–1.03 pu bus voltages; transformer and LV line loading ≤100%.

## Annual metrics: transformer 106039
| Indicator | Result |
|---|---:|
| Feasible hours | 8,760 / 8,760 |
| Minimum LV voltage | 0.97000457 pu |
| Maximum LV voltage | 0.998119 pu |
| Maximum transformer loading | 97.185% |
| Maximum LV line loading | 8.808% |
| Mean hourly feeder loss | 0.05182 kW |
| Annual feeder energy losses | 453.92 kWh |
| Reactive-injection hours | 1,031 |
| Hours with altered HIL Q request | 108 |
| Hours with reactive support when inverter P≈0 | 645 |
| Max selected |Q| | 2.925 kvar |
| Hours voltage within 0.001 pu of lower limit | 133 |
| Peak AC PCC apparent power | 4.843 kVA |

### Annual interpretation
- Minimum voltage clearance is only 0.00000457 pu, so *no meaningful engineering safety margin* is demonstrated. The controller sometimes actively selects Q to keep voltage just above the threshold.
- Nonzero reactive support at almost-zero active power assumes the inverter remains energised and can supply Q at night or with no active injection. Device capability, SOC/auxiliary consumption and grid-code restrictions need verification.
- The coordinated Q controller optimizes using AC model feedback and more network information than a standalone local Volt–Var controller. Field implementation would require realistic sensing/communications and controller timing.
- Apparent connection power reaches 4.843 kVA, below the nominal 5 kVA transformer rating but higher than the 4.5 kVA proxy used in the energy-only screening. Conductor and transformer electrical parameters are model proxies.

## PF 0.90 / service-drop uncertainty results
| Transformer | Service factor | Siting | Best Q ratio tested | Passing hours / 40 |
|---|---:|---|---:|---:|
| 106039 | 1.3× | head | 0.35, 0.48 | **40/40** |
| 106039 | 1.3× | middle | 0.48 | **39/40** |
| 106039 | 1.6× | head | 0.48 | **37/40** |
| 106039 | 1.6× | middle | 0.35, 0.48 | **26/40** |
| 94022 | 1.3× | head | 0.48 | **32/40** |
| 94022 | 1.3× | middle | 0.48 | **36/40** |
| 94022 | 1.6× | head | 0.48 | **30/40** |
| 94022 | 1.6× | middle | 0.20, 0.25, 0.35, 0.48 | **30/40** |

Only 106039 with a 1.3× service multiplier and head-mounted injection passes all 40 selected stress hours, at Q ratios 0.35 or 0.48. No tested scenario passes all 40 hours at 1.6× service lengths. Transformer 94022 remains problematic across the stress sweep.

## Recommendations for next modelling phase
1. Run a full-year 106039 head-mounted Q=0.35 test at PF 0.90, service 1.3× to check the promising stress combination beyond 40 selected hours.
2. For 94022, investigate the non-feasible hours and constrained active-power battery dispatch. Reactive support alone has not been sufficient.
3. Test electrical-parameter and household-allocation uncertainty, since conductor impedances and service drops are not measured.
4. Reconcile the 4.5 kVA PyPSA PCC proxy with AC transformer loading and equipment constraints, including nighttime reactive capability.
5. Avoid treating annual PF 0.98 feasibility as confirmed EPM utility compliance; the electrical model remains a balanced equivalent with proxy conductor parameters and assumed household attachment.

## Files
- `figures/01_critical_hour_robustness_heatmap`: passing critical hours across Q, service factor and siting. No data-connecting lines.
- `figures/02_annual_106039_daily_voltage_loading`: daily worst-case annual voltage and transformer loading, with daily Q maximum as marker colour.
- `figures/03_Q_ratio_vs_min_voltage_robustness`: reactive-capability/voltage sensitivity.
- `robustness_all_32_scenarios.csv`: exact scenario data.
- `annual_106039_daily_metrics.csv`: daily summaries from 8,760 hourly records.
