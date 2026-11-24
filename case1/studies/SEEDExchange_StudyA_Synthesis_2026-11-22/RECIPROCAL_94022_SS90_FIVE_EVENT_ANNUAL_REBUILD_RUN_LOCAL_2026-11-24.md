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

The next unused StudyA_94022_SS90_AllFiveEvents_AnnualAC_PF98_vN folder contains the corrected annual CSV, six-row change ledger, manifest and diagnostic plots. Verify the manifest hashes, count 8760 annual and six ledger rows, zero new AC solves and 8754 reused corrected rows. Report actual status (main-band pass or violations recorded), never infer success from completion. Stage only that versioned result folder, inspect staged diff, commit and push the same sync branch. No main merge, force push, git clean, or reset. If annual pass, return to wider Study A rather than tuning this candidate further.
