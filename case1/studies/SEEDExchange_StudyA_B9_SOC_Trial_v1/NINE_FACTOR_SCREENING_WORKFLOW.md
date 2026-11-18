# B9 nine-factor changed-hour screening (conditional)

This is a **new, conditional follow-up** to the signed 2025 A1 106039 B9 stress trial. It is not an annual AC replay.

The script refuses to run unless the local `StudyA_A1_106039_B9_SOC_Trial_v2` manifest explicitly records `STRESS_PASS_ONLY_ALL_NINE_PENDING`. The candidate B9 energy schedules, original annual AC SHA values, donor/target changed-hour evidence and source identity must match exactly.

When admitted, the script replays six unique case-hours (SS_B9 two, MC_B9 four) as both original and candidate across PF 0.95/0.98/1.00 and line-length factors 1.0/1.3/1.6. Thus it runs 108 changed-hour pandapower evaluations. It matches the saved source AC results for the already tested stress factor.

**No full-year feasibility claim:** passing these 108 AC evaluations does not verify the other 8,758 (SS_B9) or 8,756 (MC_B9) hours at any new factor. Do not call it electrical certification, economic optimum, or a final selection of hardware.

## Complete commands from Windows Miniforge / Anaconda Prompt

In the existing repository checkout:

```bat
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1\b9_soc_trial.py" --repo-root . --preflight
python "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1\b9_soc_trial.py" --repo-root . --out "StudyA_A1_106039_B9_SOC_Trial_v2"
```

Only after B9 stress **PASS** and its `TRIAL_MANIFEST.json` exists:

```bat
python "case1\studies\SEEDExchange_StudyA_B9_SOC_Trial_v1\b9_nine_factor_changed_hours.py" --repo-root . --stress-root "StudyA_A1_106039_B9_SOC_Trial_v2" --out "StudyA_A1_106039_B9_NineFactor_ChangedHour_v1"
git status --short
git add "StudyA_A1_106039_B9_SOC_Trial_v2"
git add "StudyA_A1_106039_B9_NineFactor_ChangedHour_v1"
git diff --cached --stat
git commit -m "Add B9 stress and nine-factor changed-hour screening evidence [ci skip]"
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

If stress **FAILS**, do not run the nine-factor script. Still preserve and commit the accurate stress failure:

```bat
git add "StudyA_A1_106039_B9_SOC_Trial_v2"
git diff --cached --stat
git commit -m "Record B9 stress trial failures for adjustment [ci skip]"
git push origin sync/seedexchange-local-2026-11-17
```

Every output directory must be new. Never delete or overwrite signed historical data or output. This work does not modify the original 432 annual AC results and does not validate the hypothetical five-edge A0 network.

If a non-stress changed-hour AC calculation fails to converge, the new screening records it as a failure. Non-finite metrics remain explicit and do not prevent writing the failure report. Source-integrity failures still stop the script.
