# Study A | Reciprocal A0/A1 matched-hardware experiment
**21 November 2026. Both directions for 113699 have been audited. Full runner now reuses four signed cases and requires 12 additional annual fixed-hardware LP solves. AC pending.**

## Purpose
The signed 34-house A0/A1 comparison holds the population fixed but has different PV/BESS equipment choices. This controlled experiment keeps, at each named transformer, **all four equipment quantities fixed** (PV panels, battery modules, battery DC continuous power and inverter kVA) and changes A0/A1 household membership using the signed 2025 hourly demand. The same assumed transformer rating, source NASA solar, zero exports, zero ENS, cyclic Store SOC, and manufacturer 20% physical SOC floor remain in force. It recomputes an 8,760-hour **energy-only** dispatch. Network AC remains separate.

The initial signed A1-hardware-to-A0 113699 pilot is already pushed at `StudyA_A0_A1_MatchedHardware_113699_Pilot_v1/`: A0 four households, 20 PV panels, four battery modules, 6.439699033 DC kW and 6 kVA inverter (assumed transformer 3 kVA). It reports 208.529525 kWh imports, 2,563.116348 kWh DC curtailed, and $1,802.314331/year equipment+grid cost. The source A1 six-house hardware and inputs were signed. This pilot has **no AC certification**.

The new runner `reciprocal_hardware_energy.py` preflights all 16 donor source manifests, original 2025 energy CSVs, original GIS profile IDs, solar source, and the initial signed pilot. The 92395 four-house STAR source remains common and unchanged. Existing original A0/A1 minimum-cost 106039 hardware is exactly identical, so both existing annual source schedules can be reused, rather than running two more LPs. Full scope would require 13 new LP solves before reuse of the forthcoming reverse pilot.

## Next step: only one reverse pilot

Transfer **A0 113699** min-cost hardware to the **A1 113699** six-house cohort, without changing the equipment: 17 PV panels, three Deye battery modules, 4.700939451 kW battery DC limit, 5 kVA inverter, assumed 3 kVA transformer. The original A0 four-house set is H04/H05/H07/H10; the A1 six-house set adds H03/H06. This reverse test may be infeasible. Report solver infeasibility rather than increasing hardware.

From your original Miniforge repository checkout:

```bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\reciprocal_hardware_energy.py" --repo-root . --scope reverse --preflight-only
```

Preflight expected `SIGNED_MATCHED_HARDWARE_16_SOURCE_PREFLIGHT_NO_NEW_SOLVES`, `source_hardware_case_count=16`, `common_92395_STAR_reference_count=2`, `expected_new_2025_LP_solves=1`, with 2 existing exact-hardware source reuses. No output folder is created.

Only if preflight passes:

```bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\reciprocal_hardware_energy.py" --repo-root . --scope reverse
```

Expect `ENERGY_ONLY_REVERSE_MATCHED_HARDWARE_PASS_AC_PENDING`, `completed=1`, `new_LP_solves=1`, and `new_AC_cases=0`. The runner auto-selects an unused `StudyA_A0_A1_MatchedHardware_ReversePilot_vN` output folder.

Inspect the output receipt and its signed 8,760-hour CSV. Replace v1 with the actual output directory:

```bat
set "OUT=StudyA_A0_A1_MatchedHardware_ReversePilot_v1"
python -c "from pathlib import Path; import hashlib,json; p=Path(r'%OUT%'); m=json.loads((p/'RUN_MANIFEST.json').read_text()); assert m['status']=='ENERGY_ONLY_REVERSE_MATCHED_HARDWARE_PASS_AC_PENDING' and m['completed_case_count']==1 and m['new_AC_cases']==0 and not m['errors']; r=m['completed_cases']['A0_113699_min_cost_to_A1']; f=Path(r['target_energy_csv']); assert hashlib.sha256(f.read_bytes()).hexdigest()==r['target_energy_sha256']; print('SIGNED REVERSE ENERGY PILOT PASS, AC PENDING')"
git add "%OUT%"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Validate reciprocal A0 hardware on A1 113699 energy [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
```

Do not stage failed/incomplete output as a pass. Preserve untracked old archives and historical source modifications. `main` is unchanged.

## After the reverse pilot
The committed runner also supports `--scope full` and `--resume --out "StudyA_A0_A1_MatchedHardware_Full_vN"` with signed source and per-case ledger checks. The full roster has 16 cross-assignment experiments and produces **eight** matched 34-house portfolio totals plus **four** A1-minus-A0 same-hardware comparison rows, with the common 92395 source counted once per portfolio. First independently review and sign the reverse pilot in GitLab and incorporate it as an additional reuse before launching the full work. This will avoid rerunning that 8,760-hour LP.

Future gates: independently validate same-hardware AC stress and corrected annual AC per territory, calculate corrected network losses from same-hour signed records, and distinguish the provisional A0 94022 five-edge hypothesis and Study B 92395 STAR/MST from actual EPM topology. No new 6,840-job hardware investment sweep is authorized.


## Continuation after the signed reverse pilot, 21 November 2026

The A0-to-A1 reverse 113699 pilot was pushed at GitLab commit 4cffd500 and
independently read: 8,760 2025 hours, 17 panels, 3 batteries, 4.700939451 kW
DC power, 5 kVA inverter, six A1 houses, 11,388 kWh demand,
3,682.545919 kWh imports, 689.909034 kWh DC curtailment and
USD 2,481.192672 annual equipment-plus-import cost. Its signed CSV
SHA-256 is df1952e61da8404677cceed1c760c5be1a5c891855f6dd8968088136997112d8,
matched after GitLab LF to original CRLF restoration. No AC claim.

Do not repeat either 113699 pilot. In your existing Miniforge repository
checkout on the sync branch, first run:

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\reciprocal_hardware_energy.py" --repo-root . --scope full --preflight-only
~~~

Require status SIGNED_MATCHED_HARDWARE_16_SOURCE_PREFLIGHT_NO_NEW_SOLVES,
expected_case_count=16, expected_new_2025_LP_solves=12, and
verified_reverse_pilot with the pinned manifest/CSV checksums. There are
22 synthetic tests total in the study folder after this update, subject to
local execution. The preflight itself writes no output and does no solves.

Only after these gates pass, run locally:

~~~bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\reciprocal_hardware_energy.py" --repo-root . --scope full
~~~

The runner creates a new unused StudyA_A0_A1_MatchedHardware_Full_vN folder.
For an interrupted run, inspect the saved INCOMPLETE_MATCHED_HARDWARE_ENERGY
receipt and use --scope full --resume --out "StudyA_A0_A1_MatchedHardware_Full_vN".
Do not use --resume on a complete run and never delete partial diagnostics
without inspecting them.

The completed 16-case full result must have status
ENERGY_ONLY_ALL_16_MATCHED_HARDWARE_PASS_AC_PENDING, errors empty,
completed_case_count=16, matched_portfolio_count=8,
paired_comparison_count=4, new_AC_cases=0, and 12 new annual LPs.
Push only the new successful versioned output after checking its receipts.
I will then independently verify the eight 34-house totals and four paired
controlled A0/A1 comparisons. This remains energy-only until new AC checks.
