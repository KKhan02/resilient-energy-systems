# Study A1 106039 | Full-year AC across nine factor combinations

## Verified gate received 18 November 2026

User's GitLab commit `65f9e524` has the signed `StudyA_A1_106039_B9_NineFactor_ChangedHour_v1/` results:
- `NINE_FACTOR_CHANGED_HOURS_PASS_ONLY` for both fixed-hardware B9 designs.
- 108/108 original/candidate changed-hour pandapower AC evaluations converged.
- 18/18 design-factor combinations have no **changed-hour** violation.
- Conservative changed-hour minimum voltage 0.957239659 pu, maximum transformer loading 92.533365% on the changed hours of the highest-stress factor.
- Original verified **full annual stress factor** PF=.95, route length=1.6 passed both cases, max modelled transformer 99.431815%, min voltage .957239659 pu; margin 0.568185 percentage points of assumed 5 kVA transformer.

These tests alone are **not** full 8,760-hour annual validation for the eight untested factor combinations.

## Reuse the existing source AC validator, do not invent a second simulator

The original trusted `case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17/validate_frontier_ac.py` now accepts `--receipt-stem PORTFOLIO_AC_ALLNINE_RECEIPT`. This preserves the previously signed `PORTFOLIO_AC_RECEIPT.csv/json` when extending `StudyA_A1_106039_Frontier_AC_v1` from the original 2 stress runs to 18 signed original-schedule AC factor cases.

The original `SS_B9_pf095_l16` and `MC_B9_pf095_l16` are reused by signed SHA-256, with no resimulation; the other **16 original fixed-hardware AC cases × 8,760 hours = 140,160 new pandapower hour evaluations** are computed on the user's computer. This does not re-run any of the historical 6,840 investment MILPs.

The completed `b9_full_annual_ac_overlay.py` then checks:
1. The signed B9 stress pass and the actual nine-factor changed-hour pass.
2. The original 2025 signed energy, hardware, cohort/solar manifest and signed 8,760-hour original AC results for all 18 cases.
3. The six unique corrected case-hours (two SS_B9, four MC_B9) for each factor, independently replaying **108 hours** and checking each against the prior nine-factor changed-hour record and the original full-year case.
4. The remaining unchanged hours at each **same factor** are inherited from that factor's verified 8,760-hour original result, not from another PF/length factor.
5. Corrected annual voltage, transformer, line limits, convergence and 2025 AC network losses, with original/corrected losses and delta losses independently reported.

It writes `ANNUAL_NINE_FACTOR_B9_RESULTS.csv`, `CHANGED_HOUR_REPLAY_WITH_LOSSES.csv` and `ANNUAL_AC_MANIFEST.json` under a **new** result folder. No existing result is modified by this overlay. If any corrected factor fails, it is reported as `FULL_ANNUAL_AC_REMAINING_FAILURES`; passing all gives `FULL_ANNUAL_ALL_NINE_MODELLED_AC_PASS`, limited to the provisional **balanced 5 kVA A1 106039** network model.

## Complete Windows Miniforge / Anaconda Prompt commands

The user checkout currently resides at:

```bat
cd /d "D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems"
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
git log -1 --oneline
```

Run local tests and original AC source preflight:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17\validate_frontier_ac.py" --repo-root . --energy-root "StudyA_A1_106039_Utilization_v1" --cases SS_B9,MC_B9 --mode all-nine --preflight
```

Run the **16 uncompleted original annual AC factor cases**, reusing the original two stress cases. No signed stress file or receipt is overwritten:

```bat
python "case1\studies\SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17\validate_frontier_ac.py" --repo-root . --energy-root "StudyA_A1_106039_Utilization_v1" --cases SS_B9,MC_B9 --mode all-nine --out "StudyA_A1_106039_Frontier_AC_v1" --zip-out "StudyA_A1_106039_Frontier_AC_allnine_20261118.zip" --receipt-stem PORTFOLIO_AC_ALLNINE_RECEIPT
```

Validate all 18 annual source cases and synthesize the **corrected** AC annual outcomes:

```bat
python "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1\b9_full_annual_ac_overlay.py" --repo-root . --source-root "StudyA_A1_106039_Frontier_AC_v1" --stress-root "StudyA_A1_106039_B9_SOC_Trial_v2" --screen-root "StudyA_A1_106039_B9_NineFactor_ChangedHour_v1" --preflight
python "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1\b9_full_annual_ac_overlay.py" --repo-root . --source-root "StudyA_A1_106039_Frontier_AC_v1" --stress-root "StudyA_A1_106039_B9_SOC_Trial_v2" --screen-root "StudyA_A1_106039_B9_NineFactor_ChangedHour_v1" --out "StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1"
```

The `StudyA_A1_106039_Frontier_AC_allnine_20261118.zip` is a local transfer/archive duplicate, not necessary to Git-commit along with its complete tracked annual AC folder.

Commit the new annual AC source case folders and corrected result summary. Review the staged stat before pushing:

```bat
git status --short
git add "StudyA_A1_106039_Frontier_AC_v1"
git add "StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1"
git diff --cached --stat
git commit -m "Validate B9 annual AC across nine PF and length factors with corrected loss audit [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

If the ZIP path already exists, choose a new unique `--zip-out` value. If original full-year annual cases already exist with matching source hashes, the original validator verifies and reuses them; it never overwrites them. Use a distinct receipt name if you have already generated the all-nine receipt. If the corrected output folder exists, preserve it and choose a new output name.

The `git pull --rebase` before push is a safeguard for intervening remote commits and does not change source evidence. Never force-push. If a rebase conflict appears, preserve files and inspect `git status` before resolving.

## Research limitations after success

Annual network losses are physically calculated under the provisional balanced AC model, but their corresponding electricity cost depends on utility settlement, real tariff, technical losses billing and actual hardware cost. **Unchanged DC energy imports after redispatch do not imply unchanged AC losses.** The real transformer rating, conductor/connection geometry, per-service phases, and dynamic/causal inverter control remain open. The historical original Study A 376/432 and hypothetical five-edge modified 408/432 results and the 6,840 MILP archive remain immutable.
