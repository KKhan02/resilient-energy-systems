# PV-first diagnostic, no source modification

Complete Windows Miniforge/Anaconda Prompt commands:

```bat
cd /d "D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems"
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --rebase origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PV_Priority_Audit_2026-11-19" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_PV_Priority_Audit_2026-11-19\audit_pv_first_priority.py" --repo-root . --out "StudyA_A1_106039_PV_Priority_Audit_Local_v1"
git status --short
git add "StudyA_A1_106039_PV_Priority_Audit_Local_v1"
git diff --cached --stat
git commit -m "Reproduce MC_REF vs MC_P33 signed PV-first temporal priority diagnostics [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

The local replay is a **diagnostic only**. If it records `grid_proxy_failure_hours=2` for MC_P33, do not use it as a feasible dispatch. The original Linopy grid-import constraints and subsequent pandapower AC tests still govern electrical feasibility.

Output files: `DIAGNOSTIC_MANIFEST.json`, `MONTHLY_ORIGINAL_VS_PV_FIRST.csv`, `MC_REF_CAUSAL_PV_FIRST_8760.csv`, `MC_P33_CAUSAL_PV_FIRST_8760.csv`. Existing output directories refuse overwrite. No new investment MILP and no historic AC case overwritten.
