# 106039 residual two-event local run and conditional annual reuse

Run each command separately. Use literal paths, no OUT environment variable or CMD continuation caret.

~~~bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_106039_a0_ss90_residual2.py" -v
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_106039_a0_ss90_residual2.py" --repo-root . --preflight-only
~~~

Expected 4 tests OK, SIGNED_106039_A0_RESIDUAL2_PREFLIGHT_NO_AC, 40 planned, 0 new AC. Stop on error.

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_106039_a0_ss90_residual2.py" --repo-root . --run-local
~~~

Use actual versioned output folder if not v1. Receipt allows completed sampled result with no combined pass, or complete annual reconstruction (which may still have failures).

~~~bat
python -c "import pathlib,json,csv,hashlib; p=pathlib.Path('StudyA_106039_A0_SS90_Residual2_AnnualAC_PF98_v1'); j=json.loads((p/'RUN_MANIFEST.json').read_text()); assert j['status'] in ('106039_RESIDUAL2_PILOT_COMPLETE_NO_COMBINED_PASS','106039_RESIDUAL2_ANNUAL_RECONSTRUCTION_COMPLETE') and j['new_AC_case_hours']==40; expected={'DONOR_TARGET_40_AC_CASEHOURS.csv':40,'PAIR_CANDIDATES_10.csv':10}; expected.update({'CORRECTED_2025_8760_AC.csv':8760,'FOUR_NEW_CHANGED_AC_HOURS.csv':4} if j['status']=='106039_RESIDUAL2_ANNUAL_RECONSTRUCTION_COMPLETE' else {}); assert set(j['outputs_sha256'])==set(expected); assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in j['outputs_sha256'].items()); assert all(sum(1 for _ in csv.DictReader((p/n).open(newline='')))==k for n,k in expected.items()); assert j['status']!='106039_RESIDUAL2_ANNUAL_RECONSTRUCTION_COMPLETE' or (j['reused_prior_AC_hours']==8756 and j['cached_new_AC_hours']==4 and j['changed_P_hours_vs_original']==6); print('RECEIPT PASS',j['status'],j['annual_AC_verified']); print(j.get('annual_summary'))"
git status --short
git add -- "StudyA_106039_A0_SS90_Residual2_AnnualAC_PF98_v1"
git diff --cached --stat
git diff --cached --name-only
~~~

Only intended result staged:

~~~bat
git commit -m "Archive 106039 residual two-event AC and conditional annual reconstruction [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
git log -1 --oneline
~~~

Stop at errors; no reset, force push, clean, staging unrelated files, or annual claim without annual receipt. No new 8760h AC sweep.
