# Run locally (Windows Miniforge, existing environment)

The new code reads existing saved CSV/JSON and reuses the existing v6 chronological PV-first function. No new optimization or AC calculation. The tests and full preflight are pending local execution. Use a fresh output folder, no overwrite. From repository root (CMD/Miniforge Prompt):

```bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24" -p "test_audit_battery_coverage.py" -v
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/audit_battery_coverage.py" --repo-root . --preflight-only
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/audit_battery_coverage.py" --repo-root . --out StudyA_Battery_Coverage_v1
python -c "import json; from pathlib import Path; p=Path('StudyA_Battery_Coverage_v1/RUN_MANIFEST.json'); m=json.loads(p.read_text()); assert m['status']=='COMPLETE_ENERGY_ONLY_BATTERY_COVERAGE_AC_PENDING' and m['rows']==44 and m['monthly_rows']==528; print(m['status'],m['causal_origin_counts'])"
git status --short
git add -- StudyA_Battery_Coverage_v1
git diff --cached --stat
git commit -m "Upload Study A battery dispatch coverage diagnostics"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin HEAD:sync/seedexchange-local-2026-11-17
```

Proceed after tests (4 expected), preflight status SIGNED_44_SOURCE_PREFLIGHT_NO_NEW_SOLVES, then successful receipt. Stop at any error and return full console output. Do not stage any other files. If untracked output folder already exists, use v2 consistently in all commands. No new code or result commits during local execution. Do not infer AC feasibility, hardware optimization or field certification.
