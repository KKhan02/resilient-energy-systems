# Study A: final annual evidence collection, v2

## Current status

User-provided `annual_AC_replay_receipt_20261116T025931489660Z.json` path and printed values:

```json
{
  "status": "ANNUAL_PORTFOLIO_RESULTS_WITH_EXPLICIT_FAILURES",
  "requested": 384,
  "completed_new": 349,
  "reused_verified": 35,
  "blocked_or_failed": 0
}
```

This accounts for the **384 sensitivity cases**. The status name is generic and does not mean failures when `blocked_or_failed` is zero. This receipt alone does **not** independently verify the 48 baseline AC results or prove the 432 case outputs are intact.

## Run locally

Extract the package folder into `case1\studies\` inside your Windows checkout. Run from your repository root in Miniforge / Anaconda Prompt:

```bat
python "case1\studies\SEEDExchange_StudyA_AnnualFinalAudit_v2\collect_studya_pvbess_results_v2.py" --repo-root . --out StudyA_PVBESS_Annual_Result_Summary_FINAL.zip
```

Upload the generated ZIP to the conversation. The ZIP should be small because raw hourly CSVs are excluded. Do **not** add `--include-hourly` on the first pass. If the final ZIP file already exists, choose a different filename with `--out`.

## Checks

- The exact **8,760-hour 2025 LST** sequence for all annual CSVs.
- SHA-256 of each hourly CSV against the corresponding result JSON.
- AC metadata including 8,760 converged hours, zero nonconverged hours, identity, PF and service-length values.
- Input manifest SHA-256 identity.
- 22 annual energy and 22 causal outputs.
- 48 baseline plus 384 sensitivity AC outputs, covering 48 hardware/feeder/dispatch combinations, each under nine PF/length conditions.
- Include saved JSON summaries, execution receipts and a per-case inventory.

`COLLECTION_REPORT.json` must show `all_expected_verified: true` for full integrity of this *file-based* verification. If it says false, upload the ZIP regardless. The report will contain the details.

## Included derived tables

- `AC_432_CASE_METRICS.csv`: voltage, overload, AC feasible/violating hours, losses, PF/length, provenance and hardware grouping.
- `AC_48_DESIGN_COVERAGE.csv`: checks all nine PF/length combinations are present for every network/hardware/dispatch pairing.
- `ENERGY_22_CASE_METRICS.csv`: hardware, import, self-sufficiency, curtailment, cycles, and modelled annual cost.
- `CAUSAL_22_CASE_METRICS.csv`: analogous causal energy metrics plus initial/terminal SOC difference.
- `CASE_INVENTORY.csv`: hashes, timestamps and missing or mismatched data.

This collector is read-only; it does not rerun solvers, repair missing summaries, rename case folders or modify GitLab. Windows extended-length path handling is for file I/O only.

## Important interpretation

All 432 are **balanced-model annual AC replays with provisional LV/house attachment evidence**, not verified real-world regulatory compliance. Eight nonbaseline PF/length cases per design use the **same equipment and stored dispatch**, not independent re-optimizations. The historical 90-case gross-demand AC portfolio remains the primary no-DER comparator. Subsequent discussion should distinguish transformer-hours, distinct violating calendar hours and summed case-hours.

Only after full integrity checks should we make the matched gross-versus-PV+BESS feasibility claims, shortlist configurations for Studies B/C, and build approved walkthrough figures.
