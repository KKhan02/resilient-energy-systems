# Local sizing follow-up

```bat
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24" -p "test_sizing_ac_followup.py" -v
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_ac_followup.py" --repo-root . --scope reserve94022 --preflight-only
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_ac_followup.py" --repo-root . --scope reserve94022 --out StudyA_94022_Sizing_Reserve_v1
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_ac_followup.py" --repo-root . --scope annual113699 --preflight-only
python "case1/studies/SEEDExchange_StudyA_Battery_Closure_2026-11-24/sizing_ac_followup.py" --repo-root . --scope annual113699 --out StudyA_113699_Sizing_AnnualAC_v1
python -c "import json; from pathlib import Path; r=json.loads(Path('StudyA_94022_Sizing_Reserve_v1/RUN_MANIFEST.json').read_text()); a=json.loads(Path('StudyA_113699_Sizing_AnnualAC_v1/RUN_MANIFEST.json').read_text()); assert r['status']=='COMPLETE_94022_REFERENCE_RESERVE_PILOT_NOT_ANNUAL_AC' and r['new_LPs_completed']==3 and r['new_reserve_AC_case_hours']==102; assert a['status']=='COMPLETE_113699_SIZING_ANNUAL_AC_RESULTS' and a['new_AC_case_hours']==43800 and a['regressions_passed']==225; print(r['status'],a['annual_AC_verified_by_case'])"
git status --short
git add -- StudyA_94022_Sizing_Reserve_v1 StudyA_113699_Sizing_AnnualAC_v1
git diff --cached --stat
git commit -m "Upload Study A sizing annual AC and reserve results"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin HEAD:sync/seedexchange-local-2026-11-17
```

If reference P envelope incomplete, partial solver, or test/preflight errors, stop and return console/receipt. Completed physical AC violations are evidence, not failed execution. For smaller 113699 batches use --cases followed by exact IDs with a different fresh output folder; retain all five in eventual comparison. Do not overwrite.
