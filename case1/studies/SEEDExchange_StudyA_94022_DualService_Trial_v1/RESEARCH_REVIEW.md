# SEEDExchange Study A: A0 94022 sparse network bundle audit and dual-service follow-up

**Evidence date:** 16 November 2026.  **Status:** modelled sensitivity only, not a retrofit design or annual validation.

## Source, provenance, and independent checks

The uploaded `StudyA_94022_Sparse_Bundle_Trial_v1_Results.zip` passed CRC validation. SHA-256: `7c6f9921b83060b83f564e654dbb7f5e381f71002a343f26d3b0f4cdbd9fb0f7`. The 15-option study has 1,080 unique, converged power-flow rows, corresponding to 15 branch-resistance options, nine 2025 critical timestamps, four A0 94022 reference/dispatch configurations, and two PF/length pairs: (0.98, 1.0) and (0.95, 1.6). All 1,080 AC feasibility flags were independently recomputed against 0.95–1.05 pu and 100% line/transformer loading.

I independently matched 288 re-solved control snapshots (`head_reference`, `GIS_only_R050`, `service_only_R050`, `all_LV_R050`) to the previous 2,160-row branch-isolation evidence. All keys and feasibility flags agree; maximum numerical difference in AC quantities was `3.55e-15`. The supplied manifest records checksums for the older branch source, original probe and redispatch trial. This is a source-chain reconciliation, **not a new independent electrical solver run in the assistant environment**.

## Results

| LV resistance option | Feasible / 72 selected snapshots | Worst Vmin (pu) | Affected model edges | Sum of affected model edge lengths |
| --- | ---: | ---: | ---: | ---: |
| Original head-located inverter | 28 | 0.937278 | 0 | 0 m |
| H01 assumed service only, model line 007 | 60 | 0.940557 | 1 | 326.55 m |
| Mapped LV 014 + 011 only | 60 | 0.943067 | 2 | 150.17 m |
| H01 service + mapped LV 014 + 011 | **70** | 0.946797 | 3 | 476.73 m |
| H01 service + nine mapped LV pieces | **70** | 0.948823 | 10 | 614.55 m |
| All EPM-mapped LV pieces | 66 | 0.948797 | 16 | 288.01 m |
| All assumed service drops | 60 | 0.945587 | 10 | 1740.96 m |
| All 26 modelled LV edges | **72** | **0.956955** | 26 | 2028.97 m |

The minimum-voltage values are minima **over different snapshots**. They cannot be interpreted as the response at one matched operating hour. None of the 15 sparse configurations passes all 72 checks. Only the blanket R×0.5 case passes all 72, and it is not a physically specified network upgrade. In these 1,080 calculations the peak modelled transformer loading is about 98.21% and peak line loading below 12%; the failing constraint in the best sparse configurations is undervoltage.

For both 70/72 sparse options, the **same two rows** fail: 29 November 2025 at 20:00, PF 0.95, length multiplier 1.6, minimum-cost causal and optimized schedules. Both have zero inverter output and limiting household **H06**. The more extensive 10-edge sparse configuration reaches Vmin **0.948823 pu**, peak transformer loading **97.39%**, and peak line loading **11.12%** at those rows. The three-edge sparse configuration has Vmin **0.946797 pu** there.

## Meaning of model branches

The electrical network export positively identifies:

- **line 007:** assumed service tap `T_47053144_0` to `HOUSE_H01`, **326.553 m**, R=3.300 Ω/km in the assumed electrical model.
- **line 004:** assumed service tap `T_47053100_0` to `HOUSE_H06`, **315.267 m**, R=3.300 Ω/km in the assumed electrical model.
- **line 014:** mapped LV split segment of EPM source FID 47053086, 83.173 m (modelled line R=1.312 Ω/km).
- **line 011:** mapped LV split segment of EPM source FID 47053070, 67.000 m (R=1.312 Ω/km).

H01 and H06 are **modelled service-drop points**, not meter-verified customer service connections. Their lengths, conductor properties, transformer associations, phases and routing must be confirmed. Some of the 26 graph edges are artificial 0.001 m pieces from splitting source GIS lines at assumed taps. Neither the number of model edges nor their summed affected lengths represents a verified number/cost of cable replacements.

## Next discriminating experiment

The residual switches from H01 to H06 once H01 and mapped-network impedance improves. The next small test adds **H06's service branch line 004** to the best sparse controls, and compares two-house and selected GIS combinations. It tests **16 resistance configurations × 72 operating snapshots = 1,152 local AC solves**, including six identical historical controls, with original battery schedules unchanged and no annual full-year rerun.

**Most useful candidate:** R×0.5 on `[7, 4, 14, 11]`: both assumed long service branches plus the two most influential mapped LV splits. This affects approximately **791.99 m of modelled edges**, compared with 2,028.97 m for the uniform all-26-edge sensitivity. This is *not an installation-cost estimate* and not an assertion that the four-edge case passes. The local solver must prove it.

If the candidate passes the 72 snapshots, do **not** immediately call A0 94022 solved. First verify actual services and realistic cable impedance, then test the remaining seven PF/length pairings and a full 8,760-hour AC replay for one defensible design. Compare the conditional A0 retrofit costs with the proven A1 operational reassignment as a separate Study B investment trade-off. For proposed 92395 MST, retain the independent topology study. PV curtailment/storage sizing and outage resilience remain separate research objectives.

**Portfolio status remains unchanged:** 376/432 original case/dispatch/factor annual AC scenarios pass after independently validated battery-shift overlays. The remaining 56 annual failures are A0 94022 (32) and proposed A0 92395 MST (24). These nine-hour conductor proxy results are **not applied** to the annual portfolio. No signed outputs, historical plots or GitLab repository files were changed.
