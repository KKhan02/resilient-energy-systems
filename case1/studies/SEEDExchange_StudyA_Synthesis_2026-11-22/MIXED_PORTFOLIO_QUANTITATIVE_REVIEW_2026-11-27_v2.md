# Study A loss-inclusive mixed portfolio pilot v2 | 27 November 2026

53 assignment-specific candidate records, 50 have both annual factor losses. Add verified reciprocal A1_113699_min_cost_to_A0; A0_113699_ss90_to_A1 excluded from stress-qualified pool due to one annual nighttime undervoltage. 16-case matrix v7 and 40-row territory/eight-portfolio v2: 6/8 composed reference pass, 3/8 severe pass. Remaining three quantitative loss gaps A0 native106039 SS90, A1 native106039 SS90 stress, A1 native113699 MC corrected. A0 106039 MC loss reconstruction: 39 original/corrected points per factor match source manifest candidate and annual AC SHA, delta -.2764262666909888/- .2793238754919155 kWh reference/stress, corrected losses 461.139264938709/503.981156319905; annual extrema still missing. No full annual replay. Same 34-house population and common hypothetical STAR, independent modeled LV territory sums only. Conditional geometry families separately enumerated; no comparison as if installation cost identical. Reference and stress loss costs separate, at .29 USD/kWh sensitivity, no billing or loss reoptimization. Pareto minimizes reference loss-inclusive cost, grid imports, DC curtailment (tolerance1e-6); only both-loss-complete subset eligible. All candidates retained, no claim of global optimum. Throughput is source annual discharge, or reconstruction from reported physical-window EFC, with equal energy quantities checked. Aggregate EFC = sum DC discharge / (sqrt(.95)*4.096*total modules), not sum of cycles or prediction of degradation. Exact validated schedule hashes for some older composed cases still incomplete; factor-specific correction evidence not single causal policy. No field certification or construction cost. 

| Assignment | Geometry | All | Both-loss complete | Pareto | Throughput complete | Stress margin complete |
|---|---|---:|---:|---:|---:|---:|
| A0 | MIDDLE_NO_R_CHANGE | 864 | 432 | 37 | 432 | 0 |
| A0 | R050_CONDITIONAL | 864 | 432 | 37 | 432 | 0 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | 576 | 288 | 42 | 288 | 0 |
| A1 | MAPPED_HEAD | 1008 | 432 | 61 | 432 | 432 |

| Assignment | Geometry | Selection | Ref cost incl losses USD/a | Stress cost USD/a | SS % | DC spill kWh/a | EFC |
|---|---|---|---:|---:|---:|---:|---:|
| A0 | MIDDLE_NO_R_CHANGE | MIN_REFERENCE_LOSS_COST | 14413.33 | 14501.74 | 79.351 | 7573.01 | 299.32 |
| A0 | MIDDLE_NO_R_CHANGE | MIN_IMPORTS | 15325.45 | 15415.14 | 82.865 | 11411.93 | 254.42 |
| A0 | MIDDLE_NO_R_CHANGE | MIN_DC_CURTAILMENT | 14980.36 | 15070.06 | 81.306 | 5645.49 | 247.31 |
| A0 | R050_CONDITIONAL | MIN_REFERENCE_LOSS_COST | 14399.58 | 14443.83 | 79.351 | 7573.01 | 299.32 |
| A0 | R050_CONDITIONAL | MIN_IMPORTS | 15311.58 | 15355.80 | 82.865 | 11411.93 | 254.42 |
| A0 | R050_CONDITIONAL | MIN_DC_CURTAILMENT | 14966.48 | 15010.72 | 81.306 | 5645.49 | 247.31 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_REFERENCE_LOSS_COST | 14273.37 | 14317.54 | 82.892 | 8756.69 | 308.78 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_IMPORTS | 15068.98 | 15113.08 | 89.123 | 14362.65 | 277.43 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_DC_CURTAILMENT | 14716.44 | 14760.60 | 83.949 | 7471.40 | 269.95 |
| A1 | MAPPED_HEAD | MIN_REFERENCE_LOSS_COST | 14284.08 | 14328.56 | 84.256 | 8841.65 | 304.86 |
| A1 | MAPPED_HEAD | MIN_IMPORTS | 15507.76 | 15552.14 | 94.206 | 14969.05 | 276.12 |
| A1 | MAPPED_HEAD | MIN_DC_CURTAILMENT | 14985.67 | 15030.11 | 88.336 | 7514.82 | 257.52 |
| A1 | MAPPED_HEAD | MIN_REFERENCE_LOSS_COST_SS90 | 14652.36 | 14696.76 | 90.590 | 13317.66 | 295.56 |

Next: bounded changed-hour loss/extrema reconciliation of three remaining candidates; A0 SS90 missing can change high-self-sufficiency frontier, A1 native MC 113699 missing can change cost optimum. No new isolated sizing, no new job in this turn. Then final common-evidence selection and B/C.
