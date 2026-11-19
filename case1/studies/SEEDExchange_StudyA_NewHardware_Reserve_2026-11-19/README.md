# Study A1 106039 | New-hardware evening reserve AC pilot

**Status:** Source-verified code prepared, user-local stress simulation NOT YET RUN.
Research network: provisional balanced EPM, 11 A1 households, assumed 5 kVA,
not site certified. This stage does not change hardware sizing, economics or
signed historical output.

## What already exists

The signed full-year PyPSA frontier contains 12 choices. The stress annual
pandapower source in \`StudyA_A1_106039_NewHardware_AC_Stress_v1\` contains
three new candidates with original AC violations:

| Case | PV modules | Battery modules | Original PF .95, length 1.6 AC failures |
| --- | ---: | ---: | --- |
| MC_B10 | 41 | 10 | 2025-10-13 20:00, 2025-11-27 20:00 |
| SS_B10 | 49 | 10 | 2025-11-27 20:00 |
| SS_P45_B9 | 45 | 9 | 2025-11-27 20:00 |

The prospective transfers are **source-specific hypotheses** and have
not been certified by pandapower. Original battery discharge at the donor
timestamps and target grid imports have been inspected in GitLab.

| Case | Battery DC transfer proposed |
| --- | --- |
| MC_B10 | 0.60 kWh DC Oct 13 17:00 -> 20:00; 0.80 kWh DC Nov 27 18:00 -> 20:00 |
| SS_B10 | 0.80 kWh DC Nov 27 18:00 -> 20:00 |
| SS_P45_B9 | 0.80 kWh DC Nov 27 18:00 -> 20:00 |

## Validation gates

The runner checks all three original source energy manifests/CSV hashes and
three original 8,760-row pandapower stress manifest/CSV hashes using existing
verified Git-LF/Windows-CRLF logic. It matches household demand, exact inverter
injections and the original fail timestamps. It checks annual manufacturer SOC
20% floor, DC and AC bus balances, cyclic SOC, inverter and battery power,
5 kVA dispatch proxy, no simultaneous charge/discharge, no export/ENS,
unchanged imports, unchanged battery throughput, protected PV/charge trajectories
and end-of-year SOC.

Only then does it create a new output folder and re-solve 4, 2 and 2
modified hours respectively, with the existing v6.2 pandapower solver. It
checks original numerical reproducibility before replacing any original annual
AC records. It preserves a 2025 candidate hourly CSV, exact replay CSV, source
hashes, case results and audit PNGs. The output is **source-stitched stress
only**, NOT a full nine-factor annual AC conclusion.

## Miniforge Command Prompt, from repository root

\`\`\`bat
git status --short
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_reserve.py" --repo-root . --preflight-only

python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_reserve.py" --repo-root .
\`\`\`

Verify the output folder printed by the runner. Expect 3 case results and
status \`STRESS_PASS_ONLY_ALL_NINE_PENDING\` **only if** all corrected annual
source-stitched AC screens pass. Retain failed receipts as evidence; do not
claim a failed run passed. The runner never overwrites an existing folder.

Push the completed, successful **new output folder only**:

\`\`\`bat
git status --short
git add "StudyA_A1_106039_NewHardware_Reserve_Stress_vN"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Validate source-matched A1 new-hardware reserve stress [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
\`\`\`

Replace \`vN\` with the ACTUAL folder printed by the runner. The assistant
will independently audit GitLab source and results. If any case fails, push
only when explicitly labelled diagnostic and plan another correction;
never recast failures as a pass.

## Later gates

A successful stress result is not enough for all-nine AC. Reuse the signed
one-factor original stress AC, run missing original 8,760-hour AC factors for
these hardware schedules, and overlay each case's exact modified hours using
the original solver. Do not multiply the stress result by nine or borrow
MC_REF or B9 corrected AC screens. Then update annual economics, curtailment
and battery utilization frontier, including strict 0.97 pu sensitivity separately.
