# A0 106039 | targeted corrected-hour AC P/Q provenance

Prepared 23 November 2026. Source-verified 2025 A0 106039 min-cost optimized SOC shift; proposed mapped GIS, assumed 5 kVA, not field-certified.

## Evidence and boundaries

The user reported FOUR_FAMILY_SOURCE_AND_SAVED_SHIFT_INPUT_AUDIT, four source cases and 35,040 original AC input hours, with zero new AC solves or certified corrected AC reuse. The versioned result folder has not yet been pushed to GitLab. The independently source-derived 39-hour ledger shows 39 changed inverter P setpoints; original total annual P is preserved; 37 hours have nighttime Q off, and exactly two contain positive PV, on 15 Nov 2025 17:00 and 27 Nov 2025 16:00. All 10 original PF.98 length1 A0 106039 AC failure hours were among the changed 39.

The A0 trial saved 351 changed-hour AC results across nine settings, but did not save the corresponding inverter P, selected Q or requested Q. The new bounded runner uses the signed frozen v6.2 source, signed household-specific traces, original proposed GIS feeder and original AC model. It rebuilds original and corrected hourly solutions, verifies each against original annual source and compact corrected result (absolute comparison tolerance 2e-4), and records actual P/Q and network metrics. It never changes historical outputs or computes another annual 8,760-hour AC profile.

## Step 1. Pull, verify and publish the successful four-family source receipt

Run these Miniforge Prompt commands from the repository root:

    git status --short
    git switch sync/seedexchange-local-2026-11-17
    git pull --ff-only origin sync/seedexchange-local-2026-11-17
    python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_four_family_input_gate.py" -v
    python -c "import json; from pathlib import Path; j=json.loads(Path('StudyA_Matched16_FourFamily_InputGate_v1/RUN_MANIFEST.json').read_text()); assert j['status']=='FOUR_FAMILY_SOURCE_AND_SAVED_SHIFT_INPUT_AUDIT'; assert j['source_verified_original_cases']==4; assert j['original_AC_input_hours_checked']==35040; assert j['source_SOC_shifted_cases']==2; assert j['certified_corrected_AC_reuse_hours']==0; assert j['new_AC_solves']==0; print('SOURCE ONLY GATE PASS')"
    git add -- "StudyA_Matched16_FourFamily_InputGate_v1"
    git diff --cached --stat
    git commit -m "Archive successful four-family source-input audit [ci skip]"
    git push origin sync/seedexchange-local-2026-11-17

Only stage the actual successful versioned output directory. If your saved output uses another vN name, adjust both the validation path and git add path. Do not mark this source-input receipt as a corrected-AC certificate.

## Step 2. Local two-daylight-hour P/Q pilot

    python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_a0_106039_changed_pq_replay.py" -v
    python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_a0_106039_changed_pq_replay.py" --repo-root . --scope daylight --preflight
    python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_a0_106039_changed_pq_replay.py" --repo-root . --scope daylight

The daylight preflight should select exactly 2025-11-15 17:00:00 with available PV DC 0.1859094887 kW, and 2025-11-27 16:00:00 with available PV DC 1.3652522556 kW. Pilot workload is 2 changed hours x nine PF/length factors x original/corrected = 36 targeted AC solver calls. These are not annual AC replays.

Success status A0_CHANGED_HOUR_PQ_REPLAY_PASS requires source baseline reproduction and saved changed-hour voltage/loading parity. A0_CHANGED_HOUR_PQ_REPLAY_CONFLICT means differences exist; preserve the saved files and do not continue until examined. The tool retains a detailed CSV and JSON failure receipt after a numerical discrepancy and exits nonzero. It never relaxes the original source signature, tolerance or physical-band criteria.

## Step 3. Only if daylight passes, extend to all 39 changed hours

    python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_a0_106039_changed_pq_replay.py" --repo-root . --scope all

Full bounded workload: 39 hours x nine PF/length settings x original/corrected = 702 targeted AC calls. The program saves versioned StudyA_A0_106039_ChangedHour_PQ_Audit_vN with REPLAY_PQ_AUDIT.csv and RUN_MANIFEST.json; v1 may be the daylight pilot and v2 the all-hours result. Check the actual numbers:

    dir /b /ad "StudyA_A0_106039_ChangedHour_PQ_Audit_v*"
    git status --short

Inspect exact output status and failed_comparisons before staging only those folders. Do not stage unrelated files or overwrite signed originals. A successful fixed-schedule AC response in the model does not certify the real EPM service wiring, transformer rating, Q-control permission, inverter dynamics, or loss-aware economics.
