# A1-origin SS90 portfolio annual gap: 113699 A0

From checkout root, separate commands, literal output paths. Same original v6 AC model, source-locked 8760h, 25 prior PF98 regression benchmarks. No new PyPSA run.

~~~bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_113699_a0_ss90_portfolio_annual.py" -v
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_113699_a0_ss90_portfolio_annual.py" --repo-root . --preflight-only
~~~

Expected four tests OK and SIGNED_113699_A0_SS90_PORTFOLIO_ANNUAL_PREFLIGHT_NO_AC, 8760 planned, 25 benchmarks, zero new AC. Stop on error.

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_113699_a0_ss90_portfolio_annual.py" --repo-root . --run-local
~~~

Use actual folder version if not v1.

~~~bat
python -c "import pathlib,json,csv,hashlib; p=pathlib.Path('StudyA_113699_A0_SS90_Reciprocal_AnnualAC_PF98_v1'); j=json.loads((p/'RUN_MANIFEST.json').read_text()); a=p/'ANNUAL_2025_8760_AC.csv'; assert j['status']=='113699_A0_SS90_RECIPROCAL_ANNUAL_PF98_RESULTS_RECORDED' and j['new_AC_case_hours']==8760 and j['benchmark_regressions_passed']==25; assert sum(1 for _ in csv.DictReader(a.open(newline='')))==8760; assert hashlib.sha256(a.read_bytes()).hexdigest()==j['outputs_sha256'][a.name]; print('RECEIPT PASS',j['annual_AC_verified']); print(j['annual_summary'])"
git status --short
git add -- "StudyA_113699_A0_SS90_Reciprocal_AnnualAC_PF98_v1"
git diff --cached --stat
git diff --cached --name-only
~~~

Only intended results staged:

~~~bat
git commit -m "Archive 113699 A0 SS90 portfolio annual PF98 AC evidence [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
git log -1 --oneline
~~~

Receipt completion is not necessarily annual feasibility. Stop on failures; no cleanup/reset/force push. No unrelated staging.
