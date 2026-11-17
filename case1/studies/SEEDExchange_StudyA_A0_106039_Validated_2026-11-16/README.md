# SEEDExchange Study A | A0 106039 trial validation | 16 November 2026

**Status:** local experimental sequential SOC shift trial successfully removes every modelled AC violation in all 36 A0 106039 full-year PF/length cases for four archived reference hardware+dispatch combinations. Four 8760-hour candidate schedules and 720 changed-hour AC rows were independently audited from uploaded bytes. The local user-run numerical solver results were checked, not independently recomputed on this host.

## Scope and research boundary

- Study A, original assignment A0, existing mapped LV transformer 106039, 12 provisional households.
- Minimum-cost and SS90 equipment references, each under optimized and causal dispatch, nine PF/length scenarios.
- 44 sequenced same-day donor-to-target battery discharge shifts, including overlapping evening events. They preserve the full battery SOC history under the modelled efficiencies.
- Changed AC hours are newly solved by the user's local solver, and all unmodified hours are reused from signed 2025 annual AC results. This is *not* a new complete PyPSA optimization, new standalone 8760-hour pandapower run, grid-code certification, or forecast-based controller.
- Original annual sources, 432 source AC runs and GitLab have not been changed.

## Evidence and outcomes

| Design and schedule | Original violation-case-hours across 9 sensitivities | After | Adopted shifts |
|---|---:|---:|---:|
| A0 106039 min-cost causal | 113 | 0 | 21 |
| A0 106039 min-cost optimized | 103 | 0 | 21 |
| A0 106039 SS90 causal | 9 | 0 | 1 |
| A0 106039 SS90 optimized | 9 | 0 | 1 |
| **Total** | **234** | **0** | **44** |

- 36/36 PF/route sensitivity cases pass (8760 modelled annual hours accounted for in each).
- 720/720 uploaded final changed-hour AC evaluations are feasible.
- Minimum voltage **0.950004972 pu** among changed-hour records, margin **0.000004972 pu**. Peak transformer loading **99.94439%** among changed hours, headroom **0.05561 percentage points**. These near-threshold outcomes are conditional and **not robust margin proof**.
- Zero export and unserved load; 2025 energy/SOC balances are consistent, battery floor respected and no annual import/curtailment/end-SOC changes.
- Baseline A1-corrected 432-case portfolio has **340 passes, 92 failures**. Applying the A0 106039 **non-destructive overlay** gives **376 passes, 56 failures**: A0 94022 mapped 32 and A0 92395 proposed MST 24.
- Annual PV curtailment remains unchanged: 1,925.45 kWh DC (A0 106039 minimum-cost), 6,017.65 kWh DC (A0 106039 SS90). This trial does not improve PV utilization or establish optimal hardware sizes.

## Files

- `INDEPENDENT_QA.json`: explicit assurance checks, source hashes, margin and portfolio counts.
- `A0_106039_ALL_36_FACTOR_RESULTS.csv`: 36 before/after annual violation totals.
- `A0_106039_FOUR_DISPATCH_GROUP_SUMMARY.csv`: results aggregated by dispatch and hardware tier.
- `A0_106039_FOUR_ANNUAL_ENERGY_QA.csv`: SHA, full-year SOC, AC/DC balance checks.
- `A0_106039_44_ADOPTED_SHIFTS.csv`: every accepted energy transfer.
- `PORTFOLIO_432_POST_A0_106039_OVERLAY.csv`: source-preserving corrected status overlay. Original `infeasible_hours` field retained; updated results in `adjusted_bad_hours` and `corrected_by`.
- `SOURCE_StudyA_A0_106039_Sequenced_Trial_v1.zip`: byte-identical user-uploaded local trial output, included for reproducibility.
- `SOURCE_PORTFOLIO_432_POST_A1_CORRECTIONS.csv`: byte-identical portfolio status before this trial.
- `independent_a0_106039_audit.py`: reruns independent file-level checks and overlay derivation. No solver required.
- `NEXT_A0_94022_PILOT.md`: local run commands and interpretation gates.

## Reproduce independent audit

Run from this folder with Python, pandas, numpy installed:

```bat
python independent_a0_106039_audit.py "SOURCE_StudyA_A0_106039_Sequenced_Trial_v1.zip" "SOURCE_PORTFOLIO_432_POST_A1_CORRECTIONS.csv" "recomputed_audit"
```

This package is separate from the signed study model and does not modify the local results tree.
