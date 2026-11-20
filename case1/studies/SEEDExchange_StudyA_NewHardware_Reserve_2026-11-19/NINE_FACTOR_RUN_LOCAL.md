# New hardware reserve | nine-factor changed-hour AC screen

**State:** Code prepared for local Miniforge execution. **No new full-year
AC feasibility may be claimed from this screen.** This follows the signed
three-case stress result in `StudyA_A1_106039_NewHardware_Reserve_Stress_v1`
and uses the original provisional balanced A1 106039 / 5 kVA network.

## Cases and work

| Hardware | Altered hours per factor | Nine factors | AC calls including old/new |
| --- | ---: | ---: | ---: |
| MC_B10 | 4 | 9 | 72 |
| SS_B10 | 2 | 9 | 36 |
| SS_P45_B9 | 2 | 9 | 36 |
| **Total** | **8** | **27 case-factors** | **144** |

The new runner imports original `new_hardware_reserve.py` to recheck
all three annual source PyPSA energy schedules, the original signed
full-year *stress* AC files, and the exact signed/CRLF-equivalent saved
corrected candidate CSVs. It verifies every stress result's annual SOC,
DC energy, inverter and 5-kVA dispatch constraints and confirms the same
candidate cannot silently change between stages. At PF .95 and length x1.6
it recomputes baseline and corrected AC and requires agreement with the
pushed stress AC rows. For other eight factors it re-solves changed hours
only, **not the unchanged 8,760-hour original AC baseline**.

The summary records non-converged/missing metrics as JSON null, preserves failed case counts and never recasts a failed hour as feasible.

The preflight argument contract was corrected after a local `KeyError: 'candidate'`: the source gate now receives the full case dictionary, not its `original` DataFrame. Two regression tests cover this boundary and a synthetic signed 8,760-hour CSV source gate. The failed preflight created no output and executed no new AC solver.

## Windows Miniforge commands

From the same project checkout on
`sync/seedexchange-local-2026-11-17`:

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_nine_factor.py" --repo-root . --preflight-only
python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_nine_factor.py" --repo-root .
~~~

The output folder auto-selects
`StudyA_A1_106039_NewHardware_Reserve_NineFactor_vN`. It includes
`SCREEN_MANIFEST.json`, `ALL_NINE_CHANGED_HOUR_AC.csv`,
`NINE_FACTOR_CHANGED_HOUR_SUMMARY.csv` and optional
`figures/audit` plots. Expect `NINE_FACTOR_CHANGED_HOURS_PASS_ONLY`
only if **all 27 candidate factor-cases** pass their changed-hour checks.
A failure remains a source-preserving diagnostic outcome, never a pass.

If all pass, stage **only the successful result folder** (replace vN
with the exact printed suffix):

~~~bat
git add "StudyA_A1_106039_NewHardware_Reserve_NineFactor_vN"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Validate A1 reserve changed hours across nine network factors [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

After the user pushes the signed changed-hour screen, the assistant
independently audits the result in GitLab. **Only then** stage the
missing 24 original full-year 8,760-hour AC factor replays for these
hardware designs using the original
`validate_frontier_ac.py` model (the three original stress factors are
already saved). Finally overlay exact corrected changed hours
against same-factor original AC baseline and compare losses,
voltage, transformer margins and conditional annual economics.

Keep original 2025 energy and AC archives immutable. Do not copy
MC_REF or B9 corrected rows into new hardware. No real-network
nameplate, neutral/unbalance, protection, losses cost, or project CAPEX
has been certified.
