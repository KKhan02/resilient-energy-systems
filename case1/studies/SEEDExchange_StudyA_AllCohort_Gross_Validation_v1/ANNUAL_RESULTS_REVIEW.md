# Study A: full-year gross AC results and paired-cohort completion plan

**Reviewed:** 8 November 2026. **Scope:** the user-executed 8,760-hour, year-2025 gross-load pandapower runs for transformer `106039`, under fixed A0 and A1 cohort membership. No new physical or economic simulation was performed in this review. Files analysed: uploaded `ac_hourly(1).csv` and `ac_summary(1).json` (A0); `ac_hourly_A1(1).csv` and `ac_summary_A1(1).json` (A1).

## Independent file consistency audit

- A0 and A1 each include **8,760 distinct consecutive hourly timestamps**, from 2025-01-01 00:00 through 2025-12-31 23:00 local-standard-time, no missing rows.
- Both have **8,760 converged hourly AC cases** and no other statuses. Summary convergence and AC-feasibility totals match individual CSV rows. All reported summary voltage/transformer extrema and loss totals agree with the CSV aggregation, within serialization tolerance.
- Source provenance: both summaries refer to exactly the same immutable input manifest SHA-256, `2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69`.
- File hashes recomputed from actual uploaded CSVs match metadata: A0 `5f430509e636ca426f9bcf1715a7a2f62a1c9b27fd025459c1fd9061ade582a6`; A1 `7fb37893a0547eac22ff065cfc836336a64adff97f0bb1e039da41aeaec2dca6`.
- Inverter injection is zero in all hours, consistent with gross-load analysis. This does **not** measure or certify shared PV+BESS feasibility.

## Gross AC outcomes, reference PF 0.98, service-length factor 1.0

| Metric | A0, 12 homes | A1, 11 homes |
|---|---:|---:|
| Annual source household gross load, kWh | 22,776 | 20,878 |
| Minimum house voltage, pu | 0.944490 | 0.955327 |
| Maximum house voltage, pu | 0.994383 | 0.994761 |
| Maximum transformer loading, % | 123.8701 | 113.8769 |
| Transformer loading >100% hours | 72 | 16 |
| House voltage <0.95 pu hours | 5 | 0 |
| House voltage <0.97 pu hours, stricter sensitivity | 1,441 | 459 |
| Line loading >100% hours | 0 | 0 |
| Maximum line loading, % | 10.0079 | 7.7810 |
| Gross AC infeasible hours, union of thresholds | 72 | 16 |
| Modelled line+transformer losses, kWh | 665.5303 | 586.1252 |
| Losses relative to annual gross demand | 2.9221% | 2.8074% |

A0 worst transformer-loading hour: **2025-10-13 19:00**, gross load 5.770308 kW, transformer loading 123.8701%, min house voltage 0.945895 pu. A0 minimum-voltage hour: **2025-11-25 19:00**, 0.944490 pu with 115.8879% transformer loading. A1 worst transformer-loading and voltage hour: **2025-10-13 19:00**, gross load 5.326677 kW, loading 113.8769%, minimum voltage 0.955327 pu. All five A0 low-voltage hours coincide with transformer overload. An additional strict 0.97 pu limit is a sensitivity, not the primary 0.95 pu failure criterion.

A1 reduced 106039 transformer-overload hours from 72 to 16 (56 hours, 77.8%), and losses from 665.53 to 586.13 kWh (79.41 kWh), but it also **removed one complete 1,898-kWh/year household from this transformer**, moving it to 85398. Therefore the improvement is *not* a controlled equal-demand design-efficiency improvement and cannot be interpreted as an overall community improvement before all cohorts are examined.

## Corrected minimum full population scope

| Transformer | A0 homes | A1 homes | Annual gross AC status |
|---|---:|---:|---|
| 94022 | 10 | 8 | Still needed, both |
| 106039 | 12 | 11 | Complete, both |
| 113699 | 4 | 6 | Still needed, both |
| 85398 | 4 | 5 | Still needed, both |
| 92395 | 4 | 4 | Still needed, but the *current GIS-based pandapower graph* lacks extracted LV line sections. Physical service is not disproven. Separate idealized transformer-only full-year gross kVA screen is provided; **not AC validation** |
| 98380 | 1 | 1 | Support-only, outside N>=4 main experiment |

There are ten A0/A1 transformer cohorts at N>=4. Eight have extracted GIS LV geometry and are eligible for the frozen v6.2 pandapower runner; two are 92395 and require extra modeling/source evidence. Retain 92395 houses H30–H33 in both populations. Do not use raw nearest-LV reassignment. The nearby 113306 is a separately proposed new transformer-assignment sensitivity, not a substitution in the controlled original six-transformer study.

## Proceed with two local-only actions

1. Run `run_remaining_gross_AC.cmd` from the repository root, via **Miniforge Prompt or Anaconda Prompt**. It executes six distinct 24-hour smoke validations followed by six 8,760-hour gross AC runs for 94022, 113699 and 85398, both A0 and A1. It uses the original signed v6.2 manifest, the existing unchanged runner, and new non-overwriting output directories. Review any errors; do not ignore AC nonconvergence.
2. Run the optional 92395 transformer-only 8,760-hour source-profile screen to quantify ideal kVA loading under existing four-house membership without constructing a fictitious feeder. This cannot establish voltage drop, line loading or losses. Before implementing *full* 92395 AC, get approval to use a clearly hypothetical LV star topology (or obtain additional GIS/current electrical evidence). Straight-line geometric service drops are uncertainty cases, never as-built connections.

After all gross screens, proceed to user-approved source-selected minimum-cost vs archived ≥90%-self-sufficiency equipment references across each identified cohort, with manufacturer physical SOC minimum20%, continuous charge/discharge limits, PV curtailment, BESS cycling and utilization, causal PV-first control, no grid-to-battery charging and zero grid export. Run 8,760-hour fixed-hardware energy dispatch followed by AC replay; any AC-infeasible results need explicit control/resizing assessment. Preserve historical archive and existing signed manifest. No GitLab writes were made.
