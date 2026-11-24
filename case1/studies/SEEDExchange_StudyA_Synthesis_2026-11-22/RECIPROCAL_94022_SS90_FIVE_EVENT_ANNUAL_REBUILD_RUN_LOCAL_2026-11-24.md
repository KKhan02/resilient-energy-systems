# 94022 SS90 five-event annual PF98 reconstruction

Status: source and tests committed to the active sync branch, local execution pending. The earlier ten residual-pilot tests passed in the user environment. No new AC solver calls or new annual result claimed.

This runner replaces exactly six PF0.98 AC records in the signed March50/Nov27 98% corrected annual archive, retaining 8,754 prior records. The 50% joint candidate passed all 12 sampled additional PF0.98/PF0.95 checks. Reconstruct all ten changed P hours against the original energy frame, including complete annual SOC, P/load and grid-import parity, signatures and loss closure. The method does not validate annual PF0.95, field wiring, actual nameplates or loss-aware economics.

## Local commands (from checkout root)

~~~bat
git status --short
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_94022_ss90_remaining3_annual_rebuild.py" -v
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_ss90_remaining3_annual_rebuild.py" --repo-root . --preflight-only
~~~

Expected five tests, OK. Preflight must report SIGNED_94022_SS90_FIVE_EVENTS_ANNUAL_REUSE_PREFLIGHT_NO_NEW_AC. Stop at any failure. No ZIP or manual copy needed.

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_ss90_remaining3_annual_rebuild.py" --repo-root . --run-local
~~~

## Receipt and selective upload (Windows Miniforge Prompt)

Set OUT to the actual versioned folder printed by the runner. The example assumes v1. Run each stage only if the previous stage passed.

~~~bat
set "OUT=StudyA_94022_SS90_AllFiveEvents_AnnualAC_PF98_v1"
python -c "import os,pathlib,json,csv,hashlib; p=pathlib.Path(os.environ['OUT']); j=json.loads((p/'RUN_MANIFEST.json').read_text()); assert j['status'] in ('REUSED_ANNUAL_94022_SS90_PF98_MAIN_BAND_PASS_NOT_FIELD','REUSED_ANNUAL_94022_SS90_PF98_VIOLATIONS_RECORDED'); assert j['new_ac_solved_in_this_reconstruction']==0 and j['old_corrected_ac_reused_hours']==8754 and j['unique_changed_P_hours_vs_frozen_original']==10; assert sum(1 for _ in csv.DictReader((p/'CORRECTED_2025_8760_AC.csv').open(newline='')))==8760; assert sum(1 for _ in csv.DictReader((p/'SIX_NEW_CHANGED_AC_HOURS.csv').open(newline='')))==6; assert set(j['outputs_sha256'])=={'CORRECTED_2025_8760_AC.csv','SIX_NEW_CHANGED_AC_HOURS.csv'}; assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==v for n,v in j['outputs_sha256'].items()); print('RECEIPT PASS |',j['status']); print(j['new_five_event_corrected_annual_summary'])"
~~~

Receipt PASS verifies the recorded completed result, not necessarily a main-band pass. Check git status and make sure no unrelated files are already staged before adding only the actual output folder.

~~~bat
git status --short
git add -- "%OUT%"
git diff --cached --stat
git diff --cached --name-only
~~~

If only the intended result files are staged:

~~~bat
git commit -m "Archive 94022 SS90 five-event annual PF98 AC reconstruction [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
git log -1 --oneline
~~~

Stop on any test, preflight, reconstruction, receipt, Git or rebase error and preserve its output. Do not clean, reset, force push, merge main or stage unrelated archives. Return the status/commit so the assistant can independently audit the uploaded result. If annual main-band pass, return to wider Study A rather than tuning this candidate further.
