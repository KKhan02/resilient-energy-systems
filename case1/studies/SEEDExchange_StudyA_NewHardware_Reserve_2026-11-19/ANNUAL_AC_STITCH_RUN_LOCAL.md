# Study A1 106039 | Verified annual AC source-stitch pilot and 27-case run

**Status:** Source-signed annual reconstruction runner committed, numerical
pilot and full campaign **not yet executed**. All source and full-year
feasibility claims remain conditional until the corresponding local runs
pass and their outputs are independently audited after a GitLab push.

## Why this avoids unnecessary computation

The completed, pushed three-case reserve screen covers 144 AC evaluations
for changed timestamps across nine power-factor and service-length settings.
It reports no corrected changed-hour failures but zero complete annual AC
factor cases. Verified original source data show that new fixed-hardware
MC_B10, SS_B10, and SS_P45_B9 configurations share most hourly electrical
inputs with original MC_B9 or SS_B9 source dispatch.

For each hour with exactly identical recorded inverter AC kW, PV daylight
control activation, inverter rating, 11-house load trace, model version,
PF and service geometry, this original balanced pandapower model has the
same input. We still verify this source property and **recompute three
deterministic matching-hour controls** per case-factor before allowing reuse.
If any signature, control, input or result disagrees, the run fails closed.

| New hardware | Same-inverter reference | Signed matching hours/year | Distinct hours/year |
| --- | --- | ---: | ---: |
| MC_B10 | MC_B9 (12 kVA) | 8,601 | 159 |
| SS_B10 | SS_B9 (20 kVA) | 8,493 | 267 |
| SS_P45_B9 | SS_B9 (20 kVA) | 8,029 | 731 |

All 9 original B9 reference AC factor files are read and source checked.
Each new hardware's own original PF .95 x1.6 annual AC is retained. Only
the 8 other network factors require original AC mismatch solves, expected
**9,256**. Corrected reserves require **72** additional replays to record
the complete AC solver fields and verify equivalence to the pushed
nine-factor changed-hour screen, plus deterministic matching-source
spot checks. No old signed file is rewritten or silently replaced.

The runner emits an hourly *delta ledger*, factor-specific receipt, a
27-factor annual summary and an overall signed-input report. It does
**not** duplicate 27 original 8,760-hour AC CSV files, because those
unchanged rows already reside in signed B9 and own-stress archives. Its
receipt explains how to reconstruct every full-year row and records source
and new delta hashes. Annual feasibility and losses are computed from
the full reconstructed 8,760-hour DataFrames, not only the changed hours.

## Local Miniforge execution

From your SEEDExchange repository root:

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_annual_ac_stitch.py" --repo-root . --scope pilot --preflight-only
~~~

**The first run must be preflight-only.** It performs signed-source checks
for all 27 annual factor cases, verifies the saved 144 AC rows, and
reports the expected original mismatch and corrected overlay hour counts.
It creates no output.

Only after that succeeds, run the small **MC_B10, PF0.95, length x1.0**
annual pilot. It reconstructs all 8,760 hours using 8,601 exact B9 source
AC records, re-solves 159 unmatched original AC hours, replays 4 corrected
reserve hours and cross-checks selected identical-source samples.

~~~bat
python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_annual_ac_stitch.py" --repo-root . --scope pilot
~~~

Expected completion status: `SOURCE_STITCHED_ANNUAL_AC_ALL_CASES_PASS`
with `annual_cases=1`, `new_original_ac_calls=159` and
`new_corrected_hour_ac_calls=4`. If a numeric mismatch or failure is
reported, preserve its receipt and inspect it; do not claim a pass.

Review `RUN_MANIFEST.json`, `ANNUAL_AC_PAIRED_SUMMARY.csv`, and the
one pilot factor's `AC_NEW_SOLVED_HOURS.csv`. When validated, **selectively
stage only the successful auto-numbered pilot result folder**:

~~~bat
git add "StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Pilot_vN"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Verify A1 original annual AC source equivalence pilot [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
~~~

Replace `vN` with the actual output name printed by the runner. The
assistant independently audits the pushed pilot before authorizing the
full 27-case local run:

~~~bat
python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_annual_ac_stitch.py" --repo-root . --scope full
~~~

The full runner saves each case-factor's delta ledger and SHA-256 receipt
as soon as it finishes. If interrupted after a complete factor and before
all 27, it can resume without losing completed work:

~~~bat
python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_annual_ac_stitch.py" --repo-root . --scope full --resume --out "StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Full_vN"
~~~

Resume is permitted only when source and runner signatures match and the
existing manifest says `INCOMPLETE_SOURCE_STITCHED_AC`. It checks
all saved delta hashes and individual receipts. It never overwrites a
previously completed result, changed source or partial factor folder.

Full-run acceptance: 27 reconstructed annual factor cases, each 8,760
converged and zero main-limit AC failures, exact source-hour identity and
source-signature verification, no change in annual energy schedule,
separate strict 0.97/1.03 pu sensitivity, and a complete provenance ledger.
The 5 kVA EPM transformer, conductor/service assumptions, balanced phases,
real installed costs and protection are **not field certified**.

After the assistant audits a pushed full-run receipt, return to economics,
PV curtailment, battery cycle intensity and cost/AC tradeoffs, then resume
the wider Study A cohorts and approved Studies B/C.
