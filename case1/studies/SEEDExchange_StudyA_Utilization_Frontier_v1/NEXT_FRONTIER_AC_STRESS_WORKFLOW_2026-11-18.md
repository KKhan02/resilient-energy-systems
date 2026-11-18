# New hardware AC stress gate | 18 November 2026

The verified full 2025 energy-only frontier is complete. The original independent AC validator now supports all ten candidate names, including the four new fixed-hardware cases. It accepts LF-normalized Git checkout energy CSVs only if restoring CRLF matches the source manifest's Windows SHA-256 exactly. It does not rewrite sources. Saved AC result CSVs are also only reusable with exact SHA-compatible Git newline normalization.

**Initial targets:** `SS_P45_B9,MC_B10,SS_B10` under PF 0.95 and line factor 1.6, three independent 8,760-hour AC replays, **26,280** hourly AC calculations. They are energy-only until these runs complete and all converged AC hours meet voltage/transformer/line limits. Source PV battery capacity, SOC, hardware ratings and fixed 2025 demand remain unchanged.

### Complete commands in Windows Miniforge / Anaconda Prompt

```bat
cd /d "D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems"
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --rebase origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17\tests" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17\validate_frontier_ac.py" --repo-root . --energy-root "StudyA_A1_106039_Utilization_v1" --cases SS_P45_B9,MC_B10,SS_B10 --mode stress --preflight
python "case1\studies\SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17\validate_frontier_ac.py" --repo-root . --energy-root "StudyA_A1_106039_Utilization_v1" --cases SS_P45_B9,MC_B10,SS_B10 --mode stress --out "StudyA_A1_106039_NewHardware_AC_Stress_v1" --zip-out "StudyA_A1_106039_NewHardware_AC_Stress_20261118.zip" --receipt-stem PORTFOLIO_AC_NEW_HARDWARE_STRESS
git status --short
git add "StudyA_A1_106039_NewHardware_AC_Stress_v1"
git diff --cached --stat
git commit -m "Add original-solver AC stress replays for three frontier hardware designs [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

The ZIP is a redundant local archive, not required in Git. If source preflight fails, don't start the numerical AC run. If any design fails AC, **still preserve and push the failure evidence**. Check the source-verified hourly violations before altering dispatch or equipment. Do not treat a successful preflight as AC certification. If an output folder/ZIP already exists, retain it and choose a new uniquely named path.
