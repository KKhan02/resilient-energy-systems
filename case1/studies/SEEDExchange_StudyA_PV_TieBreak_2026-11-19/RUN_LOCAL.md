# Study A1 106039 | two-stage PV charging timing experiment

This new isolated PyPSA/Linopy experiment compares the signed MC_REF (41 panels) and MC_P33 (33 panels) 2025 cases with identical 11-house demand, 8 battery modules, 12 kW battery power and 12 kVA inverter. Both share the assumed 5 kVA transformer. Original sources and historical results are not modified.

Stage 1 reproduces the fixed-hardware economic optimum; imports must match the signed case within 0.05 kWh. Stage 2 minimizes early-day PV curtailment using a weighted-hour objective, under annual imports <= Stage 1 + 0.01 kWh and battery DC throughput <= Stage 1 + 0.10 kWh. Preserve 20% manufacturer physical SOC, cyclic 8,760-hour SOC, all battery/inverter constraints, no export, no ENS and the original PF=.98 grid-import proxy. Perfect-foresight energy-only LP, **not** a rolling-horizon controller or pandapower AC certification.

## Windows Miniforge / Anaconda Prompt

Run from repository root. These files are committed to the sync GitLab branch; **no ZIP extraction or separate download is needed**.

```bat
cd /d "D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems"
git status --short
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PV_TieBreak_2026-11-19" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_2026-11-19\tiered_dispatch.py" --repo-root . --preflight-only
python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_2026-11-19\tiered_dispatch.py" --repo-root . --case both --out "StudyA_A1_106039_PV_TieBreak_Local_v1"
```

Read output RUN_MANIFEST.json. Only status COMPLETE_TWO_STAGE_ENERGY_ONLY_NOT_AC_VALIDATED with two cases and no errors is a successful numerical run. Solver errors are preserved for review. No AC pass is claimed even when energy-only validation succeeds.

After a successful local run, stage only the newly produced **result folder**, since the source code is already on GitLab:

```bat
git status --short
git add "StudyA_A1_106039_PV_TieBreak_Local_v1"
git diff --cached --stat
git commit -m "Validate A1 PV charging tie-break local 2025 results [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

After that compare hourly dispatch, weighted curtailment, annual imports, battery cycling and terminal SOC. Test changed hours in pandapower and check appropriate full-year PF/route sensitivities. Historical electrical reference results and all three new-hardware stress failures remain unchanged.
