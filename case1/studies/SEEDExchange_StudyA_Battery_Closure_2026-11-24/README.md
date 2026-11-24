# Study A battery closure: coverage and next evidence gate

Source-pinned branch 80d3c8ece47734da57cd915af9208adae20928ce, 24 November 2026. This is a repository summary reconciliation and new local audit preparation, not a new solver campaign. Read the approved 7 November scope and 24 November handover before proceeding.

## Native causal coverage

Reopened 18 native causal summary JSONs: 16 mapped A0/A1 tier combinations and the two common proposed 92395 four-house energy references. The six four-house summaries have a different schema (no nested reference metrics); reopened the six corresponding energy manifests. The other twelve have embedded reference metrics. All 18 report zero ENS, same annual import/curtail/discharge to within 1e-7 kWh and terminal Store differences below 1e-7 kWh. This is **summary-level evidence only**, 157,680 archived hourly observations represented, not independent re-reading of every row or proof of causal AC feasibility. Four older borrowed five-house reference variants for A0 113699/85398 exist and are excluded from current native population; retain them as historical evidence. Common 92395 energy is counted once per tier, STAR/MST AC evidence remains distinct. The full 432-case AC campaign includes causal source schedules; do not treat it as validation of reciprocal or newly sized schedules. Some causal metrics carry a stale copied perfect-foresight interpretation string; top-level status/controller and actual chronology govern interpretation.

The earlier A1 106039 MC_REF/MC_P33 greedy and two-stage pilots are separate. New Figure 33 uses both original archived hourly series (8,760 timestamp matches) and exact 24-hour data for 13 January. Day curtailment 9.037975/9.037975 DC kWh, annual curtailment 549.292446/549.292446, annual imports 5227.091894/5227.091894 AC kWh; no numerical dispatch run. At 09:00 source spill 4.6614 kW with Store at floor; greedy charge 4.6614 kW; at 14:00 greedy spill 5.0296 kW while source charges 5.0296 kW. Greedy hits upper Store at 13:00, economic at 16:00. Two annual proxy violations remain for greedy MC_P33; not an AC-feasible controller.

## Reciprocal priorities

All 16 have original optimized energy metrics and some AC evidence. Two min-cost 106039 reciprocal sources explicitly reuse exact opposite native CSVs in RUN_MANIFEST; 14 distinct reciprocal families require an exact-source causal coverage check. The wider A1 106039 hardware frontier includes ten new fixed-hardware variants and two signed native references. MC_P33 causal exists; other variants must be checked, not blindly reoptimized. Native, reciprocal, and extra frontier = 44 inventory rows before exact identity reuse. Not a final candidate count/cap or 44 new solves.

| Reciprocal case | Import AC kWh | Curtail DC kWh | Share of PV |
|---|---:|---:|---:|
| A0_106039_ss90_to_A1 | 1014.3 | 7008.4 | 24.57% |
| A1_113699_ss90_to_A0 | 11.0 | 5518.9 | 40.18% |
| A0_94022_ss90_to_A1 | 286.9 | 5512.7 | 25.45% |
| A1_106039_ss90_to_A0 | 3203.7 | 4723.0 | 18.25% |
| A0_94022_min_cost_to_A1 | 1519.8 | 3173.4 | 17.67% |

Largest import is A1_94022_min_cost_to_A0 (6481.61 kWh/a) with unresolved AC and only 824.31 DC kWh spill. A1_113699_ss90_to_A0 has 11.05 kWh imports but 5518.93 DC kWh spill: extra charging alone may have little economic value; test downsizing and physical limits. Compare isolated battery kWh/kW and PV size, retain useful annual import and SOC reserve. Do not rank by absolute curtailed kWh alone; zero export and no grid charging stay in force. Avoid assuming equivalent cost if terminal SOC differs.

## Next local gate

Use existing v6 causal rule for genuinely missing source identities; verify native archive CSV signatures, full chronology, energy/Store balance, continuous power and exact source reuse. Run 44-row preflight before diagnostics. Source and causal summary statistics include overlapping SOC/charge-cap flags, instantaneous extra-charge upper sum (not recoverable annual energy), all three scalar PF proxies, monthly energy, changed hours and cycle definition. Native/reciprocal/extra frontier original energy dispatch only; corrected AC-aware/Stage2 schedules stay separate. No rolling forecast, AC, actual equipment change, or new PyPSA optimization. P33 saved output has no independent hash in its diagnostic manifest, so label it and check signed input and conservation. Full local verification of source receipts/signatures/metrics and tests pending. Do not treat any preflight failure as infeasibility; preserve data, inspect exact mismatch. Next use returned coverage to choose priority tie-break/controlled reserve and targeted sizing experiments; extend to all promising groups without arbitrary case cap. Do not move to Study B execution prematurely; keep field cost, 94022 min-cost and remaining stress limits explicit.
