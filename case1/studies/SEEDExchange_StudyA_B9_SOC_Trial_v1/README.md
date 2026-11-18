# Study A1 106039: nine-battery SOC-neutral stress trial

**Scope:** SS_B9 and MC_B9, original signed 2025 energy and PF=0.95, line-length x1.6 AC results. No new optimization, equipment change or field-certification claim.

**Verified source facts:** SS_B9 has 1 AC-infeasible hour (27 Nov 20:00); MC_B9 has 2 (13 Oct 20:00 and 27 Nov 20:00). All are transformer loading only, with converged annual AC. A1 106039 is modelled at 5 kVA, not verified from EPM.

**Bounded trial values:** MC_B9 moves 0.60 kW DC of discharge from 13 Oct 17:00 to 20:00. Both B9 schedules move 0.80 kW DC from 27 Nov 18:00 to 20:00. Each move preserves exact DC discharge, 2025 aggregate imports, curtailment and manufacturer-SOC chronology. These are sensitivity setpoints, not operating-policy approval.

**Method:** Verify original source hashes, all 8,760 hours, exact cohort and AC result identity; independently replay both donor and target hours with the original pandapower solver; confirm the unchanged baseline reproduces; overlay the changed rows onto the signed stress AC year; accept a stress result only when all 8,760 hours are feasible. **All nine PF/length factors remain pending**, even if this narrow stress passes.

## Commands from Miniforge or Anaconda Prompt, in your existing synchronized checkout

```bat
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1\b9_soc_trial.py" --repo-root . --preflight
python "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1\b9_soc_trial.py" --repo-root . --out "StudyA_A1_106039_B9_SOC_Trial_v1"
git status --short
git add "StudyA_A1_106039_B9_SOC_Trial_v1"
git diff --cached --stat
git commit -m "Add signed B9 SOC-shift stress trial results [ci skip]"
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

If the output directory already exists, do not overwrite it. Use a fresh suffix after preserving the previous result. If preflight/source checks fail, do not run or stage a result. If stress fails, still preserve and commit the truthful failure evidence, but do not claim success. Later all-nine annual candidate AC validation is a separate study gate.

Source references: `StudyA_A1_106039_Utilization_v1/energy_{SS_B9,MC_B9}` and `StudyA_A1_106039_Frontier_AC_v1/{SS_B9,MC_B9}_pf095_l16` on the synchronized branch.

## 18 November 2026: pandas and timestamp-index regression fix

The original user-run AC trial reached `solve_changed` but raised `ValueError: Missing AC result columns`. Cause: the signed AC loader converts `timestamp_lst` to a DatetimeIndex, whereas `validate_frontier_ac.valid_ac` requires the same field as a column. The corrected trial supplies a temporary column without changing the DatetimeIndex, checks that computed feasibility equals stored corrected flags, and maintains the signed 8,760-hour alignment.

A separate `FutureWarning` occurred because the all-empty `error` column was inferred as float64 before receiving an empty string. The overlay now converts it to object dtype before changed-row assignment. These are **code-level corrections**, not a change in transformer assumptions, limits, profiles or setpoints.

The script creates its output directory only after successful AC processing, so the reported exception should not itself have written partial trial output. Inspect the result path before rerunning. The actual corrected 2025 stress outcome is still pending user execution.
