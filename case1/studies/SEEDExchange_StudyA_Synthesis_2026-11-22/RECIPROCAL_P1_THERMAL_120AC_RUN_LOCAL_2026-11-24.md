# Thermal P1 six-event local run

Four frozen hardware cases, six events, 30 candidate pairs, 120 AC records. Same original network and Q controller, reference PF .98 and stress .95. No new hardware or LP. Test full-year source algebra; choose smallest passing sampled fraction for each nonoverlapping event, verify combined annual energy. No annual AC certification.

~~~bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_reciprocal_p1_thermal_ac.py" -v
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal_p1_thermal_ac.py" --repo-root . --preflight-only
~~~

Expected 4 tests OK, SIGNED_P1_THERMAL_SIX_EVENTS_PREFLIGHT_NO_AC, 4 cases, 6 events, 30 candidates, 120 planned, 0 new AC. Stop if any fails.

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal_p1_thermal_ac.py" --repo-root . --run-local
~~~

Use actual output version:

~~~bat
set "OUT=StudyA_Reciprocal_P1_Thermal_DonorTarget_v1"
python -c "import os,pathlib,json,csv,hashlib; p=pathlib.Path(os.environ['OUT']); j=json.loads((p/'RUN_MANIFEST.json').read_text()); assert j['status']=='P1_THERMAL_120_AC_COMPLETE_NOT_ANNUAL' and j['new_AC_case_hours']==120 and j['annual_AC_verified'] is False; assert len(j['combined_candidates'])==4; assert sum(1 for _ in csv.DictReader((p/'DONOR_TARGET_120_AC_CASEHOURS.csv').open(newline='')))==120 and sum(1 for _ in csv.DictReader((p/'PAIR_CANDIDATES_30.csv').open(newline='')))==30; assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in j['outputs_sha256'].items()); print('RECEIPT PASS',j['converged'],j['infeasible']); print([(c['case'],c['all_event_pairs_pass'],c['combined_annual_SOC_valid']) for c in j['combined_candidates']])"
git status --short
git add -- "%OUT%"
git diff --cached --stat
git diff --cached --name-only
~~~

Only intended result staged:

~~~bat
git commit -m "Archive six reciprocal P1 thermal event donor target screen [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
git log -1 --oneline
~~~

Stop on errors; do not force-push, reset, clean or upload incomplete runs as complete. Receipt verifies completeness not electrical pass. 
