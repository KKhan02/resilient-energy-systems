# Upload audit: `pvbess_phase_01(1).7z`

The second user archive contains exactly:

- 2 annual 8,760-hour PyPSA fixed-hardware results, A0 106039 `min_cost` and `ss90`.
- 2 annual 8,760-hour causal PV-first dispatch sensitivity results, same two hardware cases.
- 2 **24-hour** pandapower AC results, A0 106039 `min_cost` and `ss90`.

All six CSV contents match SHA-256 values recorded in the corresponding JSON summaries. Each 24-hour AC sample converged in all 24 hours and had zero violations in that sample:

| 24-hour case | Minimum voltage (pu) | Maximum transformer loading | AC-infeasible hours |
|---|---:|---:|---:|
| A0 106039 min-cost | 0.970054 | 72.7718% | 0 / 24 |
| A0 106039 ss90 | 0.977880 | 25.2984% | 0 / 24 |

These 24-hour samples are **not** full-year AC results and cannot establish annual compliance. An earlier gross-demand year did violate transformer loading, so an annual PV+BESS replay is essential.

The optimized and causal cases agree within numerical tolerance on annual grid imports and annual PV curtailment for this pilot, **but their hourly grid import, battery SOC and curtailment trajectories are not identical**. Both causal results have approximately zero terminal-minus-initial SOC, and the metadata explicitly says terminal equality was not enforced. No equality is assumed for other cohorts.

The annual AC stage must now run across the **whole Study A portfolio**, not just 106039, as specified in the package README.
