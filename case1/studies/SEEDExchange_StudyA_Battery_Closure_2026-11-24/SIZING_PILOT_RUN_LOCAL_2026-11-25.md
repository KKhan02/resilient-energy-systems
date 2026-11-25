# Windows Miniforge local gate

From existing repo root, stop if branch differs, staged unrelated changes or tests/preflight fail. Do not overwrite output.

```bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24" -p "test_sizing_priority_pilot.py" -v
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_priority_pilot.py" --repo-root . --scope both --preflight-only
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_priority_pilot.py" --repo-root . --scope both --out StudyA_Battery_Sizing_Pilot_v1
python -c "import json; from pathlib import Path; m=json.loads(Path('StudyA_Battery_Sizing_Pilot_v1/RUN_MANIFEST.json').read_text()); assert m['status']=='COMPLETE_ENERGY_ONLY_SIZING_PILOT' and m['completed_new']==7 and not m['errors']; print(m['status'],m['completed_new'])"
git status --short
git add -- StudyA_Battery_Sizing_Pilot_v1
git diff --cached --stat
git commit -m "Upload Study A targeted battery and PV sizing pilot"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin HEAD:sync/seedexchange-local-2026-11-17
```

Expected 4 synthetic tests, 7 planned LPs, 7 completed. Any partial failure: return receipt and console, do not label as infeasible without diagnostic. No AC validation claim.
