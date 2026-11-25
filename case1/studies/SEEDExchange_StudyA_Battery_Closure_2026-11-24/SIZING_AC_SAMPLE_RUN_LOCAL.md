# Local AC sample gate

From existing Windows Miniforge repository root:
```bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24" -p "test_sizing_ac_sample.py" -v
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_ac_sample.py" --repo-root . --preflight-only
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_ac_sample.py" --repo-root . --out StudyA_Battery_Sizing_AC_Sample_v1
python -c "import json; from pathlib import Path; m=json.loads(Path('StudyA_Battery_Sizing_AC_Sample_v1/RUN_MANIFEST.json').read_text()); assert m['status']=='COMPLETE_SIZING_AC_SAMPLE_NOT_ANNUAL' and m['new_AC_case_hours']==m['planned_AC_case_hours'] and m['archived_regressions_passed']==28; print(m['status'],m['new_AC_case_hours'])"
git status --short
git add -- StudyA_Battery_Sizing_AC_Sample_v1
git diff --cached --stat
git commit -m "Upload Study A sizing candidate paired AC sample"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin HEAD:sync/seedexchange-local-2026-11-17
```
Stop on test/preflight/receipt error, report console. Physical AC failures in completed receipt are valid research evidence, not runner failure. No annual inference.
