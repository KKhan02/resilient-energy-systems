# 20 November 2026 | Independent remote audit of new-hardware nine-factor changed-hour AC

## Source and status

Read directly from `StudyA_A1_106039_NewHardware_Reserve_NineFactor_v1/` on the GitLab sync branch: `SCREEN_MANIFEST.json`, `ALL_NINE_CHANGED_HOUR_AC.csv`, `NINE_FACTOR_CHANGED_HOUR_SUMMARY.csv`, and inspected the directory listing for the three audit PNGs. This is the user-pushed 2025 source-verified local pandapower result, **not** a newly run annual AC campaign by the assistant.

The saved manifest reports `NINE_FACTOR_CHANGED_HOURS_PASS_ONLY`, `AC_calls=144`, `factor_case_count=27`, `annual_ac_cases_completed_by_this_screen=0`, `may_claim_annual_ac_feasibility=False`, with an explicit upstream signed stress-manifest SHA-256 and case-specific source energy and AC hashes.

Read and counted the CSV records independently:
- 144 rows, 144 distinct `case_id, pf, length_factor, timestamp_lst, phase` identities; no duplicate.
- MC_B10: 72 old/corrected rows, four modified 2025 hours, nine factors.
- SS_B10: 36 rows, two modified 2025 hours, nine factors.
- SS_P45_B9: 36 rows, two modified 2025 hours, nine factors.
- 27 summary factor-case entries; all candidate changed hours converge and pass the main 0.95–1.05 pu, transformer 100%, line 100% screens.
- 30 original-case changed-hour AC failures over factor repetitions; zero corrected changed-hour failures.
- Worst corrected changed-hour minimum voltage 0.9572396590 pu. Highest corrected changed-hour transformer loading 92.5333651006%. This 92.53% covers changed hours only; the 2025 annual maximum may be higher.
- The strict 0.97 pu voltage sensitivity does NOT pass at least the worst changed hours. It is separate from main-screen compliance.

These checks verify records and identity as retrieved from GitLab. The signed stress inputs and source lineage are enforced by the runner; do not treat this limited changed-hour screen as 27 full-year AC passes.

## Next approved research gate

The original `StudyA_A1_106039_Frontier_AC_v1` B9 nine-factor annual AC replays are used only when the exact electrical inputs match. Directly compared recorded source `inverter_ac_kw`, 2025 timestamps and PV-Q daylight eligibility, with matching inverter kVA:

| New original schedule | Original AC source | Exact source-matched hours/year | New-source hours/year |
| --- | --- | ---: | ---: |
| MC_B10 | MC_B9, 12kVA | 8601 | 159 |
| SS_B10 | SS_B9, 20kVA | 8493 | 267 |
| SS_P45_B9 | SS_B9, 20kVA | 8029 | 731 |

For the eight original full-year AC factors not already independently archived per design, the proposed source-stitch approach re-solves only `(159+267+731)*8=9256` original-source hours. Another 72 corrected reserve hours are replayed across nine PF/length combinations and compared to the uploaded screen; deterministic matched-source reference samples are also recomputed as a numerical equivalence gate.

**Implementation**, currently unexecuted: `new_hardware_annual_ac_stitch.py`, nine synthetic tests in `test_new_hardware_annual_ac_stitch.py`, and `ANNUAL_AC_STITCH_RUN_LOCAL.md` on the sync branch. All old sources remain read-only. Preflight checks all 27 source signatures, each 8760 chronology, B9 annual per-factor AC and exact source match. `--scope pilot` reconstructs one 8760-hour **MC_B10 PF.95 x1.0** case by reuse of 8601 original AC hours and 159 new original AC solves plus four independently replayed reserve hours. This pilot is an experiment, not a result yet.

Output has per-factor immutable signed AC delta ledger, original source provenance, original and corrected complete annual summaries and hashes, with no duplication of unchanged signed B9 annual AC. `--scope full` only after the pilot is reviewed in GitLab, then 27 modelled annual factor cases. The `--resume --out <incomplete folder>` mode verifies source, runner, case receipts, and delta hashes before reusing any saved completed factor. Nonconvergence yields an explicit AC failure, never an assumed pass.

Successful outputs must be selectively staged and pushed to the SAME sync branch for remote audit. Keep the existing 5 kVA provisional transformer, balanced phases, approximated service topology, and strict-voltage sensitivity caveats. No field certification, physical installed CAPEX or utility protection study yet.
