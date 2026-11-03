# SEEDExchange | San Rafael PyPSA optimization: results interpretation

Source: user-provided `complete_study_results.csv`, `conditional_hosting_envelope.csv`, `study_manifest.json`, and infeasibility log. This report summarizes numerical energy-model outputs only, not AC validation.

## Campaign checks

- Total recorded tasks: **6840**. Optimal model solutions: **6820**. Infeasible: **20**.
- Twelve demand cases, including separate `8_homes_H01` and `8_homes_H02` profiles; five transformer proxy ratings 5/10/15/20/25 kVA.
- Tasks: 4,980 fixed-PV economic, 1,020 fixed-BESS economic, 480 target self-sufficiency, 360 budget-constrained self-sufficiency.
- All successful rows declare `pandapower_status=NOT_RUN`, `export_policy=zero`; all successful `grid_export_kwh` and `unserved_kwh` equal zero.
- The recorded transformer-loading-screen factor is 0.9; for 5 kVA the model PCC cap is 4.5 kVA. No per-branch thermal/voltage constraints are verified.

## Lowest annual-cost fixed-PV configurations at the assumed 5 kVA transformer rating

| Case | PV panels | PV kWp | BESS usable kWh | Inverter kVA | CAPEX USD | Annual total USD/yr | Self-suff. % | 25-year NPC USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5_homes | 17 | 7.39 | 12.98 | 5.0 | 12,390 | 1,992 | 79.0 | 25,462 |
| 6_homes | 20 | 8.70 | 17.30 | 6.0 | 15,217 | 2,406 | 79.9 | 30,752 |
| 7_homes | 26 | 11.31 | 21.62 | 7.6 | 19,409 | 2,773 | 85.6 | 35,447 |
| 8_homes_H01 | 27 | 11.74 | 21.62 | 8.0 | 19,998 | 3,184 | 79.6 | 40,708 |
| 8_homes_H02 | 27 | 11.74 | 21.62 | 8.0 | 19,998 | 3,187 | 79.5 | 40,735 |
| 9_homes | 34 | 14.79 | 25.95 | 10.0 | 24,779 | 3,571 | 85.0 | 45,649 |
| 10_homes | 34 | 14.79 | 25.95 | 10.0 | 24,779 | 3,978 | 79.1 | 50,856 |
| 11_homes | 41 | 17.84 | 34.60 | 12.0 | 30,755 | 4,363 | 86.0 | 55,768 |
| 12_homes | 41 | 17.84 | 34.60 | 12.0 | 30,755 | 4,768 | 81.0 | 60,949 |
| 13_homes | 41 | 17.84 | 34.60 | 12.0 | 30,755 | 5,210 | 76.3 | 66,601 |
| 14_homes | 41 | 17.84 | 34.60 | 12.0 | 30,755 | 5,684 | 71.9 | 72,666 |
| 15_homes | 67 | 29.14 | 47.58 | 20.0 | 48,042 | 6,133 | 92.0 | 78,403 |

The lowest annual costs for the fixed-PV economic sweep are numerically identical across all tested transformer proxy ratings for each demand case. This only shows unchanged optimum objective values under these **aggregate** constraints, not equivalent physical grid feasibility or no need for upgrading.

## 12-home, 5 kVA self-sufficiency cost sensitivity

| Minimum self-sufficiency target | PV panels | BESS modules | Usable kWh | Achieved self-suff. % | CAPEX USD | Annual cost USD/yr |
|---:|---:|---:|---:|---:|---:|---:|
| 70% | 41 | 8 | 34.60 | 81.0 | 30,755 | 4,768 |
| 80% | 41 | 8 | 34.60 | 81.0 | 30,755 | 4,768 |
| 90% | 54 | 9 | 38.93 | 92.6 | 41,470 | 5,259 |
| 95% | 56 | 10 | 43.25 | 95.2 | 43,308 | 5,297 |

## 12-home, 5 kVA budget-constrained self-sufficiency

| CAPEX budget USD | Actual CAPEX USD | PV panels | BESS modules | Achieved self-suff. % |
|---:|---:|---:|---:|---:|
| 12,000 | 11,633 | 20 | 1 | 38.8 |
| 20,000 | 19,998 | 27 | 5 | 57.0 |
| 30,000 | 29,561 | 41 | 7 | 78.7 |

## Why 20 scenarios are infeasible

- All 20 use the 5 kVA transformer proxy. All are fixed-PV or fixed-BESS configurations with very limited DER. No target self-sufficiency or CAPEX-budget optimization is reported infeasible.
- For nine to twelve homes, fixed PV=0 and fixed BESS=0 fail. For thirteen homes, fixed BESS=1 module also fails. For fourteen homes, fixed PV=1 and fixed BESS=1 also fail. For fifteen homes, fixed PV=1 and 2 and fixed BESS=1 also fail.
- The solver outputs do not contain explicit infeasibility certificates or IIS reports, so the exact binding contradictory constraints are not established. Low DER and the 4.5 kVA connection limit are a strong explanation to investigate, not a confirmed mathematical diagnosis.

## Hosting envelope

- All 25 table entries report 15 homes, the tested study upper bound, for each 5–25 kVA transformer case and thresholds 0/70/80/90/95%.
- Treat these as energy-model conditional screening results. They do not establish actual transformers can supply 15 houses, nor quantify an upper maximum beyond 15 houses.

## Validation priorities

1. Map specific household profiles to candidate EPM transformer assets, preserving uncertain associations.
2. Check each selected system in pandapower for transformer loading, voltage, line and neutral effects (where modelling supports them), losses, and dispatch-dependent extreme hours.
3. Repeat demand/solar profiles with additional stochastic realizations; this campaign contains one.
4. Review cost and technology assumptions, especially inverter grid-PCC control, zero exports, and higher DER sizes than transformer ratings.
5. Do not interpret identical optimum costs across transformer ratings as proof that rating upgrades are unnecessary.

## Scope of available plots

The user reported 240 PNG plots and three shortlisted hourly directories, named `seven_best_fixedPV_26panels`, `nine_best_fixedPV_34panels`, and `twelve_best_fixedPV_41panels`. These plot and hourly files were not uploaded for independent visual/time-series validation.

