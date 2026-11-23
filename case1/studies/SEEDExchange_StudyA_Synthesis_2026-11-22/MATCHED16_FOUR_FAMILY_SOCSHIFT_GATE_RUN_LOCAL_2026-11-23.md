# Four original AC source families and saved SOC-shift schedules

**Date:** 23 November 2026. **Nature:** source-integrity audit only. **No PyPSA solve or pandapower solve.**

The first locally generated 16-case receipt is now committed as `StudyA_Matched16_OriginalAC_InputPreflight_v1/`, at GitLab commit `54b4f66d`. Independent GitLab inspection checked the 16 CSV records, both source-matching case records, 17,520 input-hour results, all zero mismatch counts, and local SHA receipt. GitLab normalizes the saved CSV to LF (SHA-256 `16b8f61f90818392aebd5af3cf49aa10edda2a0dfd6149007a68022049bbbb3d`); re-encoding those same bytes with CRLF reproduces the local manifest's SHA-256 `a1dd9f1dcd3780f1c02137fece3380ae4e7534249f2cf9d52db793f56955250b`. No actual alteration to the source was found. This is independently audited **source input receipt**, not an independently recomputed AC solver result.

## New source findings

Across the 22 archived equipment families, four reciprocal 2025 optimized-PV/BESS source combinations have exact household/cohort, equipment and energy source-signature matches, with original AC sources at PF 0.98 and length x1.0.

| Reciprocal input case | Source family | Archived original AC violations | Saved SOC shift and changed-hour AC checks |
|---|---|---:|---|
| A0 hardware to A1, 106039 minimum-cost | A1_106039_min_cost_ref | 1/8,760 | 4 P-changed hours, 36 changed-hour-factor AC records |
| A1 hardware to A0, 106039 minimum-cost | A0_106039_min_cost_ref | 10/8,760 | 39 P-changed hours, 351 changed-hour-factor AC records |
| A1 hardware to A0, 85398 minimum-cost | A0_85398_min_cost_ref | 0/8,760 | No separate saved shift |
| A1 hardware to A0, 85398 SS90 | A0_85398_ss90_ref | 0/8,760 | No separate saved shift |

The A0 106039 optimized shift saves **8,721 original AC input hours** and changes 39, with 351 saved changed-hour AC checks over nine factors. Of those 39 changed hours, 37 have the original night's Q-disabled flag and two still have PV daylight; the original AC controller selected zero Q at all 39 source hours. The saved compact changed-hour report does **not** contain actual inverter P or selected Q, so its changed-hour P/Q response provenance cannot be fully reconstructed from that CSV. The trial recorded zero residual main-band AC violations at nine factors after its solver check.

The A1 106039 optimized shift saves **8,756 original AC input hours** and changes four, with 36 saved changed-hour AC rows over nine factors. All 36 report converged AC and zero chosen Q, and their inverter P, gross demand and PV-night flag match the corrected candidate schedule. Its nine saved annual checks report no main-band infeasibility. **These are archived fixed-schedule changed-hour reports**, not an independently executed or certified new 8,760-hour AC solve.

The two 85398 cases have unchanged original energy schedules, each original matched AC source has 8,760 converged hours and zero principal AC violations at PF .98 and length x1.0. This does not assert all nine uncertain settings, nor prove new utility wiring.

**Counts:** 4 original AC-input matches among 16; 35,040 original source AC hour records correspond to the four source families. Of these, two saved shifted schedules are documented. **Zero newly certified corrected AC reuse hours** and **zero field EPM-certified network cases**. Avoid interpreting 35,040 as one single cohort's unique hours or as a set of corrected AC solver outputs.

## Windows Miniforge commands

Run from the sync-branch repository root, after pulling the latest commit:

```bat
git status --short
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_four_family_input_gate.py" -v

python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_four_family_input_gate.py" --repo-root . --dry-run

python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_four_family_input_gate.py" --repo-root .
```

Expected successful report: 4 original source matches, 35,040 original AC hours, 39 + 4 changed P hours, 351 + 36 changed-hour-factor records in the two prior correction archives, zero certified corrected AC hours, and no new AC solve. If exact source signatures or archive status differ, the script fails before producing a new versioned receipt.

The full run writes `StudyA_Matched16_FourFamily_InputGate_v1/` or the next unused version, with `RUN_MANIFEST.json` and `FOUR_FAMILY_GATES.csv`. Confirm output values before staging **only that folder**:

```bat
git add -- "StudyA_Matched16_FourFamily_InputGate_v1"
git diff --cached --stat
git commit -m "Audit four reciprocal original AC source families and saved SOC shifts [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
```

Do not commit if any test or source check fails; report the traceback instead. A0 changed-hour P/Q detail is still an independent evidence gap and must not be bypassed. No new scientific graphic is warranted for a source-integrity audit.
