# 20 November 2026 | Independent GitLab audit of annual AC source-stitch pilot

**Verdict:** PASS for MC_B10, A1 106039, PF = 0.95, line-length multiplier = 1.0 under the provisional balanced EPM network and assumed 5 kVA transformer. A *single* annual source-stitched AC case is validated. The remaining 26 hardware-factor cases are not validated by this pilot.

## Signed user result retrieved from GitLab

Commit `cffa9e6d8fc099a900dc6345dae0968e942c7bae` uploaded `StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Pilot_v1/`. Independently retrieved `RUN_MANIFEST.json`, `ANNUAL_AC_PAIRED_SUMMARY.csv`, `MC_B10_pf095_l10/CASE_RECEIPT.json` and `MC_B10_pf095_l10/AC_NEW_SOLVED_HOURS.csv`. The pilot manifest reports `SOURCE_STITCHED_ANNUAL_AC_ALL_CASES_PASS`; one completed annual factor, 27 original annual factor source gates checked, 159 new unmatched original AC calls, 4 new reserve correction AC calls, source-stitch mode rather than 8,760 new annual AC solves.

The source schedule maps **8601/8760** exact original B9 same-input hours and independently runs the remaining **159** original MC_B10 inputs, with **three** independently solved equivalent-hour sampling checks. The source AC SHA-256 recorded for MC_B9 PF095 length 1.0 is `a209e6be7bc912dd16bfd255a0b7280e33c2bb7687573597f065f6e41159d70d`; MC_B10 own PF095 length 1.6 signed baseline SHA is `16069fb88b928b0ba6bd998670119d054a13065648543706be82f96d16afd180`. Exact original Windows/Git source hash modes are recorded in the manifest; no archived original AC source files are replaced.

Independent checks performed:
- Saved AC delta CSV contains **163 rows**, exactly **159** `original_different_from_B9` and **4** `candidate_reserve_correction`, with no duplicated timestamp/phase identity.
- All 163 saved AC rows have `CONVERGED` status, and the 159 newly computed original-source rows are AC feasible. The remaining two original annual violations arise in signed reused source hours and are corrected by the reserve overlay.
- The saved individual `CASE_RECEIPT.json` is identical in data to the same case entry inside `RUN_MANIFEST.json`.
- The four corrected timestamps are 2025-10-13 at 17:00 and 20:00 and 2025-11-27 at 18:00 and 20:00. Each of their solver fields `inverter_ac_kw`, `min_v_pu`, `max_v_pu`, `max_trafo_pct`, `max_line_pct`, `loss_kw`, `pcc_kva` matches the separately signed nine-factor changed-hour screen for the same PF/length exactly at saved numerical precision.
- Annual main-screen result: 8760 converged, original 2 AC failure hours -> corrected **0**, worst transformer 107.3136659% -> **99.3516178%**, minimum voltage 0.9565122 -> **0.9595084 pu**, annual AC losses 425.3863368 -> **425.3563849 kWh**. These losses are the full-year reconstructed sum, not just the four altered hours.
- Stricter **0.97 to 1.03 pu** sensitivity violations increase 48 -> **49 hours**; clearly distinguish this from the main 0.95 to 1.05 pu pass.
- The pilot's `no_new_full_8760h_AC_solve=True` is correct provenance: 8760-hour accounting is built from verified signed original source hours plus newly solved nonidentical hours and original-solver correction replay.

## Next approved run

The existing `new_hardware_annual_ac_stitch.py` source was already committed and locally proven by the pilot. Do not modify its solver algorithm before running the full campaign, because the `runner_sha256` is a provenance and safe-resume gate.

Use:

~~~bat
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_annual_ac_stitch.py" --repo-root . --scope full --preflight-only
python "case1\studies\SEEDExchange_StudyA_NewHardware_Reserve_2026-11-19\new_hardware_annual_ac_stitch.py" --repo-root . --scope full
~~~

Full preflight must report `modelled_case_factors=27`, `source_all_nine_factor_case_factors_checked=27`, `expected_new_original_hour_solves=9256` and `expected_candidate_overlay_hours=72`, with status `SIGNED_2025_ANNUAL_SOURCE_EQUIVALENCE_PREFLIGHT_PASS_NO_AC`. The full run chooses an unused output folder `StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Full_vN`, preserves each factor's delta CSV and signed case receipt and can resume only an explicitly incomplete run with the same code/source signatures.

Full acceptance requires 27/27 reconstructed annual factor-case summaries, each 8760 converged hours and zero **main-screen** AC failure hours. Strict 0.97/1.03 pu sensitivity is separately reported and may fail. Full result should be pushed selectively only after verifying the manifest and summary. The assistant must independently inspect the pushed numerical receipt in GitLab before treating all 27 annual factor-cases as validated. Do not push historical modified files, unrelated ZIP archives, or preliminary failed outputs as passes.

Following full AC audit, prepare a coherent hardware decision report integrating annualized equipment-plus-import costs, curtailment, battery discharge/cycles, annual losses and their pricing assumptions. Then resume approved Study A geographic cohort comparisons and Studies B/C. Preserve 5 kVA provisional rating, service geometry uncertainties and unbalanced-network limitations.
