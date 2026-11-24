# 106039 reciprocal SS90 annual PF98 local run

Two frozen target cases. Each runs an original 8760-hour reference annual AC; substitute two signed 25% corrected records per case. No new optimization. No automatic annual pass claim, no new PF95 annual claim.

~~~bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_106039_ss90_reciprocal_annual.py" -v
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_106039_ss90_reciprocal_annual.py" --repo-root . --preflight-only
~~~

Expected 4 tests, OK; SIGNED_106039_RECIPROCAL_SS90_ANNUAL_PREFLIGHT_NO_AC, 17520 planned new AC, four cached corrected hours, zero new AC. Stop if failed.

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_106039_ss90_reciprocal_annual.py" --repo-root . --run-local
~~~

Use actual output version:

~~~bat
set "OUT=StudyA_106039_Reciprocal_SS90_AnnualAC_PF98_v1"
python -c "import os,pathlib,json,csv,hashlib; p=pathlib.Path(os.environ['OUT']); j=json.loads((p/'RUN_MANIFEST.json').read_text()); assert j['status']=='106039_RECIPROCAL_SS90_ANNUAL_PF98_COMPLETE_RESULTS_RECORDED' and j['new_AC_case_hours']==17520 and j['cached_corrected_AC_hours']==4; assert len(j['completed_cases'])==2 and len(j['outputs_sha256'])==5; assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in j['outputs_sha256'].items()); assert all(sum(1 for _ in csv.DictReader((p/n).open(newline='')))==(4 if n=='FOUR_CHANGED_AC_HOURS.csv' else 8760) for n in j['outputs_sha256']); print('RECEIPT PASS'); print([(k,v['original']['main_band_infeasible_hours'],v['corrected']['main_band_infeasible_hours'],v['corrected']['nonconverged_hours']) for k,v in j['completed_cases'].items()])"
git status --short
git add -- "%OUT%"
git diff --cached --stat
git diff --cached --name-only
~~~

Only intended output staged:

~~~bat
git commit -m "Archive 106039 reciprocal SS90 annual PF98 AC results [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
git log -1 --oneline
~~~

Stop on error; receipt completion is not annual pass. No reset, clean, force push or unrelated staging.
