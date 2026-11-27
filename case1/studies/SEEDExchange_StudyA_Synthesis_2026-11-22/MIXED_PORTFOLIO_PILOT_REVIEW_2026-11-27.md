# Study A mixed-portfolio pilot, 27 November 2026

A source-constrained enumeration of already evaluated equipment alternatives, not another PyPSA/pandapower run. Both assignments cover the same 34 household traces and 64,532 kWh/year. Exactly one candidate per territory, common proposed 92395 STAR included once. No consumer regrouping, no inter-territory trading or MV/combined network power flow. Reference and severe stress evidence required at candidate level, either full annual replay or explicitly labeled composed/archived accounting. Composed evidence can use factor-specific schedule corrections, not proof of a single robust causal controller. A0 94022 physical classes kept separate: middle placement no R change, new R050 conditional, older conditional five-edge archive. No feasible original head-only A0 portfolio asserted. No installed infrastructure costs included. No ranking across conditional geometry classes as if all had equal construction costs. This is a pilot candidate set, not global optimum, and pending reciprocal 113699 cases and reference-only reciprocal cases excluded from severe-stress eligibility. All three native source energy metrics come from reopened manifests and previous AC72 reconciliation. Source 106039 six designs use annual composed evidence, no blanket field claim. Native A1 113699 min-cost uses AC72 corrected accounting, not original failing severe run. Blank losses/voltage/thermal columns denote incomplete matched quantitative evidence, never zero. Native A0 106039 and older 94022 conditional have incomplete loss/margin records. Source identity of all candidates to be finalized before a full loss-inclusive portfolio frontier. No battery-throughput or electrical margin objective where comparable complete evidence is absent.

Three-objective minimization: energy-only modeled annual cost, grid imports, DC curtailment. Exact Cartesian enumeration within each geometry class, no arbitrary cap; dominance tolerance 1e-6 in respective units. Equal objective points retained if different case identities. Source hardware tier is not actual SS. Minimum cost for SS>=90% included as decision example, not imposed research target. No new LP/AC. Running 113699 job not used.

| Assignment | Geometry | Combinations | Nondominated | Loss-complete |
|---|---|---:|---:|---:|
| A0 | MIDDLE_NO_R_CHANGE | 756 | 70 | 0 |
| A0 | R050_CONDITIONAL | 756 | 70 | 0 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | 504 | 69 | 0 |
| A1 | MAPPED_HEAD | 1008 | 118 | 432 |

| Assignment | Geometry | Selection | Energy cost USD/a | Imports kWh/a | DC spill kWh/a | SS % |
|---|---|---|---:|---:|---:|---:|
| A0 | MIDDLE_NO_R_CHANGE | MIN_ENERGY_COST | 13903.47 | 13324.94 | 7573.01 | 79.351 |
| A0 | MIDDLE_NO_R_CHANGE | MIN_IMPORTS | 15342.55 | 8535.17 | 15504.13 | 86.774 |
| A0 | MIDDLE_NO_R_CHANGE | MIN_DC_CURTAILMENT | 14472.01 | 12063.39 | 5645.49 | 81.306 |
| A0 | R050_CONDITIONAL | MIN_ENERGY_COST | 13903.47 | 13324.94 | 7573.01 | 79.351 |
| A0 | R050_CONDITIONAL | MIN_IMPORTS | 15342.55 | 8535.17 | 15504.13 | 86.774 |
| A0 | R050_CONDITIONAL | MIN_DC_CURTAILMENT | 14472.01 | 12063.39 | 5645.49 | 81.306 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_ENERGY_COST | 13783.15 | 11039.93 | 8756.69 | 82.892 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_IMPORTS | 15109.67 | 4496.93 | 18454.85 | 93.031 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_DC_CURTAILMENT | 14226.87 | 10357.99 | 7471.40 | 83.949 |
| A0 | OLDER_CONDITIONAL_FIVE_EDGE | MIN_COST_SS90 | 14319.66 | 6184.56 | 13973.70 | 90.416 |
| A1 | MAPPED_HEAD | MIN_ENERGY_COST | 13750.91 | 11665.83 | 7330.81 | 81.922 |
| A1 | MAPPED_HEAD | MIN_IMPORTS | 15024.64 | 3738.76 | 14969.05 | 94.206 |
| A1 | MAPPED_HEAD | MIN_DC_CURTAILMENT | 14456.57 | 9032.98 | 6003.98 | 86.002 |
| A1 | MAPPED_HEAD | MIN_COST_SS90 | 14164.40 | 6072.66 | 13317.66 | 90.590 |

The saved candidate and representative tables retain exact case IDs. Only the nondominated table is saved, plus all candidate combinations can be regenerated deterministically from the candidate ledger. Next: independently audit candidate source identity and missing corrected loss ledgers, integrate completed 113699 receipt, then recalculate common evidence-grade full portfolio frontiers including loss sensitivity, throughput, headroom and physical cost gap. Do not equate loss-only or energy-only cost with installed-system economics.
