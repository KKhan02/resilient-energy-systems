# Study A completed quantitative mixed-portfolio candidate-set comparison | 27 November 2026

All 53 selected candidate rows now have reference and severe-stress annual losses, source annual battery throughput, stress minimum voltage and peak transformer loading. Overlay job18435232570 success, 8/8 annual groups, 70080 archived hours reconciled,32 new point AC solves,156 reused point records,12 signed inputs. Four exact corrected native schedule identities and two older conditional five-edge stress summaries attached to candidate ledger. Same 34 households,64532 kWh/year; common 92395 hypothetical STAR counted once per portfolio. Four physical classes kept separate. No newly optimized or combined MV AC; candidate set is selected research alternatives, not all possible designs. Some six-design historical annual overlays use factor-dependent lineage and consolidated candidate schedule hashes missing for eight records; no field or causal claims. Annual aggregate EFC=DC discharge/(sqrt(.95)*4.096*modules). Main band .95–1.05pu, thermal<=100%. Extra voltage/transformer screens are illustrative post-processing sensitivity, NOT new acceptance rules or probability/future growth models. Loss cost .29 USD/kWh on all modeled losses, energy LP not reoptimized, construction and installation costs excluded and unknown. Three-objective Pareto cost including reference losses/import/DC spill, tolerance1e-6. Preserve geometry-specific alternatives, no global cross-geometry dominance claim.

| Assignment | Geometry | Evaluated | Nondominated | Best achievable stress Vmin | Best achievable peak transformer % |
|---|---|---:|---:|---:|---:|
| A0 | MIDDLE_NO_R_CHANGE | 864 | 72 | 0.950000104 | 99.571227 |
| A0 | R050_CONDITIONAL | 864 | 72 | 0.950316313 | 99.571227 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | 576 | 70 | 0.950316313 | 99.571227 |
| A1 | MAPPED_HEAD | 1008 | 93 | 0.950952895 | 99.431815 |

| Assignment | Geometry | Objective | Reference cost USD/a | Stress cost USD/a | SS % | Spill kWh/a | Vmin stress | Peak trafo stress % |
|---|---|---|---:|---:|---:|---:|---:|---:|
| A0 | MIDDLE_NO_R_CHANGE | MIN_REFERENCE_LOSS_COST | 14413.33 | 14501.74 | 79.351 | 7573.01 | 0.950000104 | 99.8710 |
| A0 | MIDDLE_NO_R_CHANGE | MIN_IMPORTS | 15843.08 | 15932.71 | 86.774 | 15504.13 | 0.950000104 | 99.5712 |
| A0 | MIDDLE_NO_R_CHANGE | MIN_DC_CURTAILMENT | 14980.36 | 15070.06 | 81.306 | 5645.49 | 0.950000104 | 99.8710 |
| A0 | MIDDLE_NO_R_CHANGE | MAX_VOLTAGE_HEADROOM | 14413.33 | 14501.74 | 79.351 | 7573.01 | 0.950000104 | 99.8710 |
| A0 | MIDDLE_NO_R_CHANGE | MAX_TRANSFORMER_HEADROOM | 14930.96 | 15019.31 | 83.260 | 11665.21 | 0.950000104 | 99.5712 |
| A0 | R050_CONDITIONAL | MIN_REFERENCE_LOSS_COST | 14399.58 | 14443.83 | 79.351 | 7573.01 | 0.950007790 | 99.8710 |
| A0 | R050_CONDITIONAL | MIN_IMPORTS | 15829.21 | 15873.37 | 86.774 | 15504.13 | 0.950316313 | 99.5712 |
| A0 | R050_CONDITIONAL | MIN_DC_CURTAILMENT | 14966.48 | 15010.72 | 81.306 | 5645.49 | 0.950007790 | 99.8710 |
| A0 | R050_CONDITIONAL | MAX_VOLTAGE_HEADROOM | 14917.21 | 14961.41 | 83.260 | 11665.21 | 0.950316313 | 99.5712 |
| A0 | R050_CONDITIONAL | MAX_TRANSFORMER_HEADROOM | 14917.21 | 14961.41 | 83.260 | 11665.21 | 0.950316313 | 99.5712 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_REFERENCE_LOSS_COST | 14273.37 | 14317.54 | 82.892 | 8756.69 | 0.950007790 | 99.8710 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_IMPORTS | 15586.61 | 15630.65 | 93.031 | 18454.85 | 0.950316313 | 99.5712 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_DC_CURTAILMENT | 14716.44 | 14760.60 | 83.949 | 7471.40 | 0.950007790 | 99.8710 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_REFERENCE_LOSS_COST_SS90 | 14798.45 | 14842.52 | 90.416 | 13973.70 | 0.950316313 | 99.5712 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MAX_VOLTAGE_HEADROOM | 14791.00 | 14835.12 | 86.801 | 12848.89 | 0.950316313 | 99.5712 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MAX_TRANSFORMER_HEADROOM | 14791.00 | 14835.12 | 86.801 | 12848.89 | 0.950316313 | 99.5712 |
| A1 | MAPPED_HEAD | MIN_REFERENCE_LOSS_COST | 14248.42 | 14292.93 | 81.922 | 7330.81 | 0.950039162 | 99.4318 |
| A1 | MAPPED_HEAD | MIN_IMPORTS | 15507.76 | 15552.14 | 94.206 | 14969.05 | 0.950952895 | 99.4318 |
| A1 | MAPPED_HEAD | MIN_DC_CURTAILMENT | 14950.01 | 14994.49 | 86.002 | 6003.98 | 0.950039667 | 99.4318 |
| A1 | MAPPED_HEAD | MIN_REFERENCE_LOSS_COST_SS90 | 14652.36 | 14696.76 | 90.590 | 13317.66 | 0.950952895 | 99.4318 |
| A1 | MAPPED_HEAD | MAX_VOLTAGE_HEADROOM | 14543.12 | 14587.54 | 88.642 | 13120.15 | 0.950952895 | 99.4318 |
| A1 | MAPPED_HEAD | MAX_TRANSFORMER_HEADROOM | 14248.42 | 14292.93 | 81.922 | 7330.81 | 0.950039162 | 99.4318 |

Full candidate population, 3312 combination ledger, Pareto subsets, decision representatives and illustrative headroom sensitivity saved. Weak 106039 transformer margin and 94022 voltage margin must remain explicit. No more isolated tuning merely to improve margins; a new electrical reliability target requires a specific decision. The remaining project-wide work is physical evidence/cost gap, research narrative and Study B geography/topology, then Study C. Distinguish reference-qualified reciprocal options from stress-qualified pool: 113699 six-house retains one severe night failure and is not included. No claim that all historical reciprocal portfolios pass. No new solve in this synthesis turn.
