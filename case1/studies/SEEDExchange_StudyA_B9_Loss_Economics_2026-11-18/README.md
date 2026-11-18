# B9 source-audited AC-loss economic sensitivity

This folder holds an independent source-derived review of **four** validated fixed-hardware designs across **nine** network factors. It is a conditional cost sensitivity, not a retail tariff study or an investment optimum. The historical source files are never overwritten.

## Windows Miniforge/Anaconda Prompt

From your GitLab checkout root, after `git pull --ff-only`:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_B9_Loss_Economics_2026-11-18" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_B9_Loss_Economics_2026-11-18\audit_b9_loss_economics.py" --repo-root .
python "case1\studies\SEEDExchange_StudyA_B9_Loss_Economics_2026-11-18\audit_b9_loss_economics.py" --repo-root . --out "StudyA_A1_106039_B9_Loss_Audit_Local_v1"
git status --short
git add "StudyA_A1_106039_B9_Loss_Audit_Local_v1"
git diff --cached --stat
git commit -m "Verify B9 vs reference annual AC-loss cost sensitivity [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
```

The audit reads local source files only. It refuses existing output directories and mismatched signed source hashes. The already-derived `PAIRWISE_BATTERY_LOSS_ECONOMICS_18.csv` and `FOUR_DESIGN_BY_FACTOR_36.csv` in this folder were computed from the same sources and will be independently reproduced by the audit. All 18 pair rows and 36 design-factor rows were present and cross-checked. The audit contains no optimization or AC run.


## 18 November 2026: historical AC summary absent in local checkout

The user's execution raised `FileNotFoundError` at the first eight-battery historical `ac_summary.json`. Independent live GitLab inspection confirmed that **all 18 exact original source summaries exist** in the active synced branch, including the first missing file. This may indicate an incomplete or partially materialized local checkout, not a missing upstream result.

The audit now uses a **pinned, source-verified GitLab index** `SIGNED_REFERENCE_AC_LOSS_INDEX_18.json` (18 source summaries, exact source GitLab blob SHA-256 and original `ac_hourly.csv` SHA-256). If a local historical summary exists, it is checked against the pinned index; conflicting local files STOP the audit. If it is absent, the script recovers only the verified scalar annual loss from the source index and records `GITLAB_INDEX_FALLBACK` in the output manifest. It does not fabricate an AC simulation, replace signed files or silently claim to have inspected absent local hourly files.

The numeric 18 matched battery comparisons and 36 design-factor economics remain unchanged.

For a full rerun from Miniforge/Anaconda Prompt in your repo root:

```bat
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_B9_Loss_Economics_2026-11-18" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_B9_Loss_Economics_2026-11-18\audit_b9_loss_economics.py" --repo-root . --out "StudyA_A1_106039_B9_Loss_Audit_Local_v2"
git status --short
git add "StudyA_A1_106039_B9_Loss_Audit_Local_v2"
git diff --cached --stat
git commit -m "Add locally reproduced source-indexed B9 loss audit [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

Use a fresh output folder if `v2` exists. The local historical tree can be restored from GitLab separately without rerunning pandapower. No new numerical model run is needed for this economic audit.
