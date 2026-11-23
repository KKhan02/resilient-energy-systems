# Matched 16, original AC source versus saved SOC correction audit

**Review date:** 23 November 2026. **Object:** 34 distinct modeled houses assigned A0/A1 to original mapped LV territories. **Method:** GitLab independent source file read and cross-check only, no new AC or energy optimization.

## Uploaded v1 receipt independently reviewed

GitLab sync commit `54b4f66d` contains the two locally generated signed files under `StudyA_Matched16_OriginalAC_InputPreflight_v1/`. I independently reviewed all **16** `CASE_INPUT_GATE.csv` rows, the `RUN_MANIFEST.json`, and both zero-mismatch source matching cases. Manifest counts: **140,160** signed annual energy source rows, **17,520** original PF .98/length1 AC source-hour comparisons, two source candidates, zero corrected-hour reuse certified. I also independently reconciled the actual repository file's Git-normalized LF SHA-256 (`16b8f61f90818392aebd5af3cf49aa10edda2a0dfd6149007a68022049bbbb3d`) to the local Windows CRLF SHA-256 in its uploaded manifest (`a1dd9f1dcd3780f1c02137fece3380ae4e7534249f2cf9d52db793f56955250b`). The Git checkout changed text line endings only; the receipt's original bytes can be reconstructed. This is **not** an independent re-execution of the archived AC model.

## Extended four-family evidence and SOC-aware operating changes

The 22-family archived-original equipment review adds two distinct 85398 `*_ref` target-native schedule signatures that were excluded from the v1 same-tier `*_four` comparison. The resulting original-source candidate coverage is **4/16**, with **12/16** no original archived family match. The 4 original PF .98/length1 reference AC streams each contain 8,760 matched source input hours. Distinguish **35,040 source-case hours**, which are not 35,040 unique community hours, from corrected AC approvals, of which there are **zero**.

| Reciprocal case | Original model AC failures at PF .98/length1 | Corrected inverter-P changed/unchanged hours | Saved nine-factor changed-hour AC rows | Scope |
|---|---:|---:|---:|---|
| A0 equipment to A1, 106039 min-cost | 1 | 4 / 8,756 | 36 | Original and A1 manual SOC shift archived |
| A1 equipment to A0, 106039 min-cost | 10 | 39 / 8,721 | 351 | Original and A0 sequenced SOC shift archived |
| A1 equipment to A0, 85398 min-cost | 0 | 0 / 8,760 | None | Exact original 2025 schedule, no saved shift |
| A1 equipment to A0, 85398 SS90 | 0 | 0 / 8,760 | None | Exact original 2025 schedule, no saved shift |

The A0 106039 min-cost corrected 2025 full schedule differs from its original at **39 inverter active-power hourly setpoints** while all gross household demand and PV-availability inputs agree. Original source AC records at these 39 hours have Q selected zero, but **2 of the 39** have the AC solver's daytime reactive-power path enabled. The changed-hour `CHANGED_HOURS_FINAL_AC.csv` has **351** factor-hour combinations and all `ac_feasible=True`, but its saved columns contain **no inverter_ac_kw or q_selected_kvar**. This prevents independent direct changed-input P/Q proof from that compact CSV. The nine modelled annual factor summaries all show zero remaining research-band violations, but the saved report is a historical solver claim and not a new independent AC result.

The A1 106039 min-cost corrected schedule differs at **4 active-power hours**, with **36** saved changed-factor-hour records. All are converged and AC feasible, and all **36 recorded q_selected_kvar are zero**; the saved changed-hour `inverter_ac_kw`, `gross_demand_kw` and night flag match corresponding corrected annual source values. The nine archived correction summaries say zero residual violations for original mapped balanced AC. At the strongest PF .95/length1.6 case, reported minimum model voltage is approximately 0.95724 pu and peak modeled transformer loading **99.4318%**, leaving **0.5682 percentage points** under the hypothetical 100% nameplate screen. It is **not actual utility headroom**.

The original 85398 two `A0_85398_*_ref` equipment and optimized energy archives match reciprocal target hardware and target signed energy SHA exactly. Their original reference optimized AC archives at PF .98/length1 have no research-band infeasible hours. No separate SOC-shift experiment is recorded or asserted for these two reference schedules. Do not transpose their original results to selected A0 `*_four` cohorts or to rewired EPM networks.

## Next reproducible gate

The local-only `matched16_four_family_input_gate.py`, with eight focused synthetic tests, independently checks the v1 receipt, source signatures for all four archive matches, annual P differences for the two corrected 106039 schedules, the 9-factor changed-hour coverage, and available P/Q columns and inputs. No powerflow is run. The exact Miniforge commands are in `MATCHED16_FOUR_FAMILY_SOCSHIFT_GATE_RUN_LOCAL_2026-11-23.md`. Source-archive validation still requires user local run and a new versioned signed receipt.

After that run, the key remaining scientific obstacle is **strict changed-hour A0 P/Q replay provenance at the two daytime-capable hours and the remaining 37 night-Q-off changed hours**. Where the archived compact AC row lacks the inputs, rerun only the bounded changed-hour solver validation or expose the original logged invocation inputs, preserving source hashes. The 12 original-family nonmatches should first be prioritized by materiality and conditional topology validity, not automatically simulated 12 × 9 × 8,760 hours.

No physical EPM household service wiring, phase allocation, actual transformer/nameplate, field economics, backup resilience or 2025 actual consumption is certified in this study.
