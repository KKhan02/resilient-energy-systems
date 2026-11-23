# Local run | remaining 12 reciprocal Study A cases, source-only materiality gate

> **POST-RUN CORRECTION | 23 NOV 2026:** The user has already uploaded `StudyA_Reciprocal12_Source_Materiality_v1` in commit `023f2b72`. Its manifest and both CSVs are present on the sync branch. The first nine-test materiality suite was reported to have ONE failure: `test_night_pf_095_proxy` supplied annual maximum gross demand 5.7703076217 kW instead of the simultaneous 2025-11-27 20:00 demand 5.186888959 kW. This was a **test fixture** error. The source formula and archived results are unchanged. The fixture is fixed on the sync branch; user must pull and rerun the nine tests before claiming 9/9. **Do not rerun the 12-case source producer or push another versioned receipt solely to fix this test.** The original steps 3 and 4 below describe first-time execution only and are superseded for the already-archived v1. See `RECIPROCAL12_LOCAL_TEST_FIX_AND_REMOTE_RECEIPT_AUDIT_2026-11-23.md`.


**Commit preparation:** 23 November 2026. Read-only source audit, no solver. Must run on the real synced GitLab branch in Miniforge Prompt at the repo root.

## Step 1: fetch and pull before any Python invocation

```bat
git status --short
git branch --show-current
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17

git ls-files -- "case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22/matched16_reciprocal12_materiality.py"
dir "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal12_materiality.py"
```

If the pull reports conflicts or the file is missing, stop and report the exact message. Do not reset, clean or overwrite local data. The output folders of previous studies must remain intact.

## Step 2: regression tests, including the previously repaired A0 P/Q test

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_a0_106039_changed_pq_replay.py" -v

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_reciprocal12_materiality.py" -v
```

Both test files contain **nine synthetic tests each**. The prior A0 P/Q fixture has been repaired but no subsequent successful local nine-test receipt has been reported. If either command says `Ran 0 tests`, stop. Do not treat that as a pass. No AC solver is invoked by the tests.

## Step 3: run the source-only 12-case screen

```bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal12_materiality.py" --repo-root . --dry-run

python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal12_materiality.py" --repo-root .
```

The dry-run hashes and reads the signed 12 original annual sources and prints only coverage; it writes nothing and solves no equations. A successful full run writes `StudyA_Reciprocal12_Source_Materiality_v1/`, or the next unused version, containing `RUN_MANIFEST.json`, `UNMATCHED12_SOURCE_MATERIALITY.csv` and `TARGETED_25H_HOUR_SELECTION.csv`.

Expected: **12 annual cases, 105,120 signed hourly energy records, 300 uniquely selected case-hour targets (25 per case), 0 new AC solves and 0 corrected AC reuse certified**. The source-only proxy should find **two** PF .95 nighttime hours above the assumed transformer nameplate screen, both at `2025-11-27 20:00:00` for separate 106039 SS90 cases. All results remain assumed-model screens, not evidence of actual EPM wiring.

## Step 4: inspect, then push only the new versioned results

If the full output is v1, check its values first:

```bat
python -c "import json; from pathlib import Path; p=Path('StudyA_Reciprocal12_Source_Materiality_v1'); j=json.loads((p/'RUN_MANIFEST.json').read_text()); assert j['status']=='RECIPROCAL12_SOURCE_ONLY_MATERIALITY_AND_25H_PRIORITIZATION'; assert (j['unmatched_2025_energy_cases'],j['signed_2025_hours_checked'],j['prioritized_target_hours'],j['AC_solver_calls'])==(12,105120,300,0); assert j['priority_counts']=={'P1':6,'P2':4,'P3':2}; print('12-CASE SOURCE RECEIPT PASS')"

git status --short
git add -- "StudyA_Reciprocal12_Source_Materiality_v1"
git diff --cached --stat
git commit -m "Archive signed 12-case source materiality and 300 target hours [ci skip]"
git push origin sync/seedexchange-local-2026-11-17
```

Use the actual output vN if a prior version exists. Never stage older trials or the whole repository by accident. Share the printed output status and test results; the signed CSV receipts will then be independently checked on GitLab. If a source SHA or other gate fails, preserve the traceback instead of changing tolerances or originals.

## What happens next

After reviewing the uploaded receipt and the physical source register, select a small targeted `2025-11-27 20:00` 106039 SS90 PF .95 AC replay on each of the two *actual signed reciprocal schedules*. For 113699 compare the already archived A1 six-house PF .95 stress-hour sample with signed reciprocal target P before deciding any extra solve. For 94022 assess original A0-voltage and real H01/H06 route evidence before investigating alternatives. Do not launch 12 × 9 × 8760 new AC solves automatically; those scenario conditions have not been approved or physically established.

No new user equipment price assumptions, installation costs, outage-resilience claims or EPM field-certificate labels are introduced by this gate.
