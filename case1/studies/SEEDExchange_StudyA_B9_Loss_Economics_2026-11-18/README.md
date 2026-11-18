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
