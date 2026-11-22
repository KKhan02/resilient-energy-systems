# Local run | Study A reciprocal 16-case original AC input-equivalence preflight

**Source date:** 22 November 2026. **Scope:** same 34-house A0/A1 matched-hardware study. **Calculation:** file and hourly-input verification only; zero new PyPSA or pandapower power flows.

## What the tool checks

- Original 16-case signed `StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json` and the archived 2025 house assignment input manifest with its expected SHA.
- Every target annual energy CSV is signed (exact or known Git-LF representation of original Windows CRLF), has all 8,760 consecutive 2025 local hours and finite required numeric inputs, and retains target house membership and expected hardware.
- Checks all five target-native hardware specifications: PV panels, battery modules, continuous battery DC power, AC inverter kVA and assumed transformer kVA.
- For **only the two exact target-native 106039 minimum-cost hardware candidates**, validates original native 8,760-hour optimized AC archive at PF .98 and length x1.0: source signed energy manifest, AC CSV SHA, 2025 timestamp, household set, original manifest geometry/source identity and Q policy, hourly gross demand, inverter AC P, PV daylight flag, PF, convergence and zero nighttime selected Q.
- Reports original AC source violation-hour count and the first mismatch in each compared source field. This is **not** proof that a later corrected SOC schedule uses identical AC inputs. Keeps `reusable_SOC_corrected_AC_hours_CERTIFIED=0` and `field_AC_certified=false` by design.

## Run on Windows Miniforge Prompt at the GitLab repository root

```bat
git status --short
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_original_ac_input_preflight.py" -v

python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_original_ac_input_preflight.py" --repo-root . --preflight-only

python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_original_ac_input_preflight.py" --repo-root .
```

**Expected checks if current sources are unchanged:** eleven pure synthetic tests pass; source energy preflight verifies **16/16**, or **140,160 signed 2025 target hourly records** (16 x 8,760). Full read-only comparison checks **17,520 original AC input-hour pairs** from the two 106039 target-native candidates. Based on the already independently reviewed data, it should find both candidates' **8,760 matching source gross-P/daylight records each**. Source originally recorded **10 A0** and **1 A1** AC-infeasible hours before SOC-aware correction. Final `RUN_MANIFEST.json` must still say **0 certified SOC-corrected reuse hours**.

If source signatures fail, data differ, or a test fails: **do not stage the output as validated**. Report the first error. The solver is never invoked.

## Check and push a successful result

The program never overwrites a previous folder. It creates `StudyA_Matched16_OriginalAC_InputPreflight_v1` or the next unused number with `RUN_MANIFEST.json` and `CASE_INPUT_GATE.csv`. Inspect your actual version:

```bat
dir /b /ad "StudyA_Matched16_OriginalAC_InputPreflight_v*"
set "OUT=StudyA_Matched16_OriginalAC_InputPreflight_v1"

python -c "import json,os; from pathlib import Path; j=json.loads((Path(os.environ['OUT'])/'RUN_MANIFEST.json').read_text()); assert j['status']=='ORIGINAL_AC_INPUTS_CHECKED_NO_AC_SOLVES'; assert j['cases']==16; assert j['source_energy_hours_verified']==140160; assert j['original_AC_candidate_cases']==2; assert j['original_AC_checked_hours']==17520; assert j['SOC_corrected_AC_certified_reuse_hours']==0; assert j['field_AC_certified'] is False; print('READ-ONLY AC SOURCE INPUT GATE PASS')"

git add -- "%OUT%"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Validate 16-case matched hardware original AC source input preflight [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

Change the `OUT` number if another version was created. Stage only the successful result folder, not other unreviewed local artifacts. You do not need to run MATLAB, PyPSA, pandapower or CI for this gate.

## Scientific handover

This study is a **necessary original-AC input correspondence check**, not a verified physical design or a corrected AC feasibility result for all 16 hardware exchanges. Once its output is pushed, independently audit its 16 receipts and two 8,760-hour source comparisons. Then search alternate archived native equipment families for the other 14, and check the exact SOC-corrected P/Q source outputs for the two 106039 candidates before approving any AC reuse.

**Walkthrough:** No new figure is warranted for this source-integrity gate. Existing Stage 14 energy and Stage 15 uncertainty plots already cover the substantive research questions. Add a new poster figure only after a defensible whole-population AC/economic decision or actual Study B/C topology result.
