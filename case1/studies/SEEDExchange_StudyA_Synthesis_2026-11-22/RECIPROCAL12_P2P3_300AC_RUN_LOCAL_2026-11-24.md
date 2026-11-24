# Reciprocal P2/P3 source-locked screen, local run

The existing source materiality register selects 25 hours per case. This screen covers the six untouched reciprocal families (four P2 and two P3), 150 signed source case-hours at PF .98 and .95, length factor 1.0, existing Q rule. 300 AC case-hour records, not annual or field verification. No new LP. User-local execution only.

~~~bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_reciprocal12_p2p3_ac_screen.py" -v
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal12_p2p3_ac_screen.py" --repo-root . --preflight-only
~~~

Expected five tests, OK. Preflight P2P3_RECIPROCAL12_SIGNED_GIS_PQ_PREFLIGHT_NO_AC, six cases, 150 selected hours, 300 planned and zero new AC. Stop if any check fails.

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal12_p2p3_ac_screen.py" --repo-root . --run-pilot
~~~

Use actual output version in OUT.

~~~bat
set "OUT=StudyA_Reciprocal12_P2P3_AC_Screen_v1"
python -c "import os,pathlib,json,csv,hashlib; p=pathlib.Path(os.environ['OUT']); j=json.loads((p/'RUN_MANIFEST.json').read_text()); a=p/'TARGETED_300_AC_CASEHOURS.csv'; b=p/'CASE_PF_SUMMARY_12.csv'; assert j['status']=='P2P3_TARGETED_300_AC_CASEHOURS_RECORDED_NOT_ANNUAL' and j['new_AC_case_hour_evaluations']==300 and j['annual_AC_verified'] is False; assert sum(1 for _ in csv.DictReader(a.open(newline='')))==300 and sum(1 for _ in csv.DictReader(b.open(newline='')))==12; assert hashlib.sha256(a.read_bytes()).hexdigest()==j['targeted_ac_csv_sha256'] and hashlib.sha256(b.read_bytes()).hexdigest()==j['case_pf_summary_sha256']; print('RECEIPT PASS | converged:',j['converged'],'| infeasible:',j['infeasible'],'| nonconverged:',j['nonconverged'])"
git status --short
git add -- "%OUT%"
git diff --cached --stat
git diff --cached --name-only
~~~

Only intended output staged, then:

~~~bat
git commit -m "Archive reciprocal P2 P3 300AC coverage screen [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
git log -1 --oneline
~~~

Stop on failure, preserve output, never force-push/reset/clean. Receipt is completeness, not all feasibility. Inspect nonconvergence and failure rows. No new annual claim.
