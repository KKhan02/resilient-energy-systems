# A1 106039, Stage 2 PV priority plus grid-aware evening battery reserve

The signed Stage 2 early PV preference changed 68 MC_REF grid-import hours across the year, without changing annual imports. The user-run matched 9-factor AC delta comparison confirms those changed hours introduce zero new AC failures. However, **full-year** archived MC_REF remains AC-infeasible at two 2025 evening hours at PF .95.

The earlier signed `StudyA_A1_106039_Redispatch_Trial_v1/` already demonstrates that targeted battery energy conservation can eliminate those events for the **original** 41-panel reference. We must not simply copy its corrected schedule: Stage 2 uses a different battery chronology. This package tests a source-consistent **new Stage 2 correction**, transferring DC discharge from 17:00 to 20:00 on 2025-10-13 (0.60 kWh DC) and 2025-11-27 (0.80 kWh DC). Prior evidence supports the size of these shifts, but this new four-hour experiment must be simulated independently.

## Scientific evidence gate
- This test is for **MC_REF, 41 panels, 8 Deye battery modules, 12 kW DC, 12 kVA inverter and assumed 5 kVA A1 106039**. It does NOT directly prove MC_P33 correction.
- Exact signed v2 Stage 2 full-year 2025 CSVs, matched delta AC manifests, original 11-home 2025 load chronology and archived 9-factor annual reference AC are checked. Original inputs are read-only.
- For each factor, reuse only those 8,760 AC hours where the inverter injection remains identical. The source Stage 1 annual reference is matched to v2 Stage 1 over all hours; the Stage 2 changed-hour AC must match the archived baseline at all 68 hours before reuse. Re-evaluate the further four hours with original v6 pandapower Q/PCC solver.
- Validate physical 20% minimum SOC, battery 12kW power, inverter, DC and AC energy closures, annual cyclic SOC, 5kVA PF .98 import proxy and exactly unchanged annual purchases/throughput.
- **Do not equate this source-stitched annual AC result with a new 8,760-hour AC run or utility certification**. EPM connection geometry/phase and the transformer nameplate remain provisional.

## 19 Nov 2026: permanent Windows source-provenance fix

The original archived annual AC, energy manifest and Stage2 delta files have
Windows CRLF SHA-256 signatures, whereas Git stores LF versions. The runner
now accepts only the exact signed bytes or an LF-to-CRLF reconstruction that
matches the original signed SHA-256 precisely. All other changes fail. No
historical file content is rewritten.

The full nine-factor preflight now checks source hashes, 8,760-hour chronology,
and Stage1 demand/inverter identity **before** any new output folder is created.
An optional short archive path avoids Windows path-length problems. With R:
still mapped as shown by the user, use Miniforge Prompt commands:

~~~bat
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19\run_stage2_grid_reserve.py" --repo-root . --scope full --historical-root R:/ --preflight-only
python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19\run_stage2_grid_reserve.py" --repo-root . --scope full --historical-root R:/
~~~

The runner automatically selects a new unused output folder and prints its
path. The earlier stress result in the local folder
StudyA_A1_106039_PV_TieBreak_GridReserve_Stress_v3 was already validated
by the user and must not be overwritten. The v1 examples below predate the
permanent fix. Preserve only successful provenance-signed results for GitLab.

## Complete Miniforge workflow, GitLab-first

From your repository root:

```bat
cd /d "D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems"
git status --short
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
git log -1 --oneline

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19\run_stage2_grid_reserve.py" --repo-root . --preflight-only

python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19\run_stage2_grid_reserve.py" --repo-root . --scope stress --out "StudyA_A1_106039_PV_TieBreak_GridReserve_Stress_v1"
```

Read `RUN_MANIFEST.json`. The stress case must be complete, no errors, and show zero corrected infeasible hours under PF .95 length 1.6. Only then run:

```bat
python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_GridReserve_2026-11-19\run_stage2_grid_reserve.py" --repo-root . --scope full --out "StudyA_A1_106039_PV_TieBreak_GridReserve_Full_v1"
```

Verify completion, nine factors and physical feasibility:

```bat
python -c "import json; from pathlib import Path; paths=[('StudyA_A1_106039_PV_TieBreak_GridReserve_Stress_v1',1),('StudyA_A1_106039_PV_TieBreak_GridReserve_Full_v1',9)]; files=[(p,json.loads((Path(p)/'RUN_MANIFEST.json').read_text(encoding='utf8')),n) for p,n in paths]; assert all(m['status']=='COMPLETE_SOURCE_STITCHED_2025_AC' and not m['errors'] and len(m['cases'])==n for p,m,n in files), [(p,m['status'],m['errors']) for p,m,n in files]; print('SOURCE-STITCHED 2025 AC GATE PASSED')"
```

Finally, commit only successful new local output folders and rebase/push:

```bat
git status --short
git add "StudyA_A1_106039_PV_TieBreak_GridReserve_Stress_v1" "StudyA_A1_106039_PV_TieBreak_GridReserve_Full_v1"
git diff --cached --stat
git diff --cached --name-only
git commit -m "Validate A1 Stage2 PV priority plus evening grid reserve source-stitched AC [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
git log -1 --oneline
```

If a source hash, annual identity, SOC, or any solver check fails, preserve the exception/receipt, do not claim completion and return the traceback for diagnosis. No ZIP downloads are needed.
