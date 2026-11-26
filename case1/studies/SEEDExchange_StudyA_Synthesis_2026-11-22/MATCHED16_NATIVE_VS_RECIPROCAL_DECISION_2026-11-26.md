# Study A | reciprocal-to-native energy decision register, 26 November 2026

This is a read-only source reconciliation, not a new investment optimization, AC campaign or final architecture selection. The 16 reciprocal records in the matched hardware manifest were joined to the exact target-native same-territory and same-household source family. All 16 target household lists match the native donor list; both source SHA identities match the 44-row battery coverage ledger. Annual import, DC spill, demand and reciprocal energy cost checks pass at 1e-5. Costs are historical model equipment plus grid imports, not loss-inclusive or installed infrastructure costs. Dominance compares annual modeled cost, AC grid imports and DC PV curtailment only; equipment, SOC trajectories, losses and AC margins remain separate. Equal tier names do not guarantee equal achieved self-sufficiency.

| Reciprocal case | Native Δ cost (USD/a) | Native Δ imports (kWh/a) | Native Δ DC spill (kWh/a) | Energy-only relationship |
|---|---:|---:|---:|---|
| A0_106039_ss90_to_A1 | -8.62 | 1020.34 | -1516.20 | TRADEOFF |
| A1_113699_ss90_to_A0 | -507.01 | 520.46 | -4186.26 | TRADEOFF |
| A0_94022_ss90_to_A1 | -331.24 | 1232.90 | -2339.25 | TRADEOFF |
| A1_106039_ss90_to_A0 | -49.62 | -1221.15 | 1294.65 | TRADEOFF |
| A0_94022_min_cost_to_A1 | -33.28 | 1755.35 | -1764.38 | TRADEOFF |
| A1_113699_min_cost_to_A0 | -157.86 | 588.73 | -935.99 | TRADEOFF |
| A0_106039_min_cost_to_A1 | 0.00 | 0.00 | 0.00 | ENERGY_EQUIVALENT |
| A1_85398_ss90_to_A0 | -212.06 | 401.82 | -1142.93 | TRADEOFF |
| A1_94022_ss90_to_A0 | 12.26 | -2332.84 | 1124.81 | TRADEOFF |
| A1_106039_min_cost_to_A0 | 0.00 | 0.00 | 0.00 | ENERGY_EQUIVALENT |
| A1_85398_min_cost_to_A0 | 0.00 | 0.00 | 0.00 | ENERGY_EQUIVALENT |
| A0_85398_min_cost_to_A1 | 0.00 | -0.00 | 0.00 | ENERGY_EQUIVALENT |
| A1_94022_min_cost_to_A0 | -120.32 | -2285.01 | 1183.68 | TRADEOFF |
| A0_113699_min_cost_to_A1 | -45.17 | -1288.82 | 164.09 | TRADEOFF |
| A0_85398_ss90_to_A1 | 83.25 | -845.99 | 652.67 | TRADEOFF |
| A0_113699_ss90_to_A1 | -39.32 | -2404.33 | 2107.59 | TRADEOFF |

**94022 update.** Job18399135344 pipeline3119130737, exact reserve schedule hashes reproduced, 315 common hours, 8505/8505 converged, 1809 signed original regressions, 27/27 groups pass main limits, no new annual solve. Optional .97–1.03 diagnostic: 2686 below .97 and 33 above 1.03 sampled case-hours, not unique hours. Actual worst annual stress Vmin remains .950000103521, not the sampled .950092127776. Retain two-factor annual proof and nine-factor sample only. Do not repeat R050 or middle annual sweeps unless a new decision requires it.

**Next sizing decisions.** Highest absolute reciprocal spill is 106039 A0 SS90→A1 (7008 DC kWh/a). Reuse its six already-validated A1 frontier comparators before new LPs; same load territory but distinguish battery power and equipment. 94022 A0 SS90→A1 (5513 DC kWh/a, 98.11% energy self-sufficiency) has only sampled reciprocal AC evidence; native and reciprocal min-cost/SS90 points already bound a substantial part of its trade-off. Prioritize a matched fixed-inverter/battery-power PV-sizing sensitivity for this eight-house high-spill case only after user agrees exact candidate panel/module choices; then AC sample and targeted annual validation of promising designs. 113699 four-house high-spill case already received five sizing alternatives, so do not rerun them; 85398 remains a distinct candidate for later sizing and evidence completion. Do not conflate an energy-only dominant point with a network-feasible one. The 16-case matrix remains immutable; this additive decision register explicitly overrides the outdated min-cost 94022 failure status for the middle reserve option, not the original head configuration. Native evidence and cross-territory cost reconciliation remain separate. No B/C execution or unapproved physical/operational assumptions.
