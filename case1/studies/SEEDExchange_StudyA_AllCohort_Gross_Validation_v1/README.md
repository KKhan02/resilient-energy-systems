# Study A v6.2, complete A0/A1 cohort follow-through

**Date:** 8 November 2026. **Mode:** local-only, no GitLab writes and no modification of the frozen v6.2 runner or `input_manifest_v6_2.json`.

## Results already supplied

Transformer **106039**, 5 kVA assumed, A0 12 homes and A1 11 homes, 8,760 hours each, PF 0.98, service factor 1.0, provisional balanced EPM network. Both annual gross AC runs converged 8,760/8,760 hours.

| Metric | A0 | A1 |
|---|---:|---:|
| Gross demand, kWh | 22,776 | 20,878 |
| Minimum voltage, pu | 0.944490 | 0.955327 |
| Max transformer loading, % | 123.8701 | 113.8769 |
| Transformer overload hours | 72 | 16 |
| Hours voltage below 0.95 pu | 5 | 0 |
| Hours voltage below 0.97 pu | 1,441 | 459 |
| Max line loading, % | 10.0079 | 7.7810 |
| Model AC losses, kWh | 665.530 | 586.125 |
| AC-infeasible hours | 72 | 16 |

This is neither a passed annual design nor an optimal assignment. H13 moved from 106039 to 85398, so the complete community-level comparison requires all the other cohorts.

## Required cohort coverage

| Transformer | A0 homes | A1 homes | AC GIS graph | Current status |
|---|---:|---:|---|---|
| 94022 | 10 | 8 | Yes | Run 24h then annual both |
| 106039 | 12 | 11 | Yes | Full-year gross AC complete both |
| 113699 | 4 | 6 | Yes | Run 24h then annual both. 3-kVA source rating |
| 85398 | 4 | 5 | Yes | Run 24h then annual both |
| 92395 | 4 | 4 | Extracted LV GIS sections missing | Keep both cohorts. Run **transformer-only load envelope** but mark AC pending alternative topology model or new GIS service evidence |
| 98380 | 1 | 1 | Support-only | Not a >=4-house Study A cohort |

The four-house cohorts are included because the approved scope calls for **N>=4**, even though one user paraphrase says 'more than four'. The table contains ten A0/A1 groups requiring analysis: eight with usable extracted GIS LV graphs and two at 92395 that need explicit LV assumptions for pandapower AC.

## Run instructions on Windows

1. Extract this folder into your repo at `case1\studies\SEEDExchange_StudyA_AllCohort_Gross_Validation_v1\`.
2. Open **Miniforge Prompt or Anaconda Prompt**. Change into the `resilient-energy-systems` repository root.
3. Do **not** rerun the two 106039 annual AC cases or change their result folders. Do **not** edit signed v6.2 files.
4. Run all other six source-GIS-backed paired cases, with 24h smoke checks before each annual pass:

```bat
call "case1\studies\SEEDExchange_StudyA_AllCohort_Gross_Validation_v1\run_remaining_gross_AC.cmd"
```

This creates a **new**, unused `outputs\run_01\batch_remaining_gross_v1\` folder under the original v6 runner with 12 children: six 24h tests, then six 8,760h tests. If it already exists, the batch fails rather than overwriting. Each case must converge for its full window. AC-infeasible hours are *expected and reported*, not hidden or treated as a numerical failure.

**92395, both A0 and A1:** No supported LV section in the extracted graph, but the transformer can physically have service. Run a source-signed transformer-only load/kVA screen, **not a pandapower AC run**:

```bat
python "case1\studies\SEEDExchange_StudyA_AllCohort_Gross_Validation_v1\screen_92395_transformer_only.py" --manifest "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json" --pf 0.98 --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\screen_92395_transformer_only_v1"
```

This screens 4 distinct mapped household demand profiles for 8,760 hours at PF 0.98 against the 5 kVA recorded transformer rating, ignoring line losses, voltage and other consumers. The A0 and A1 populations are identical, so one output series serves both scenarios. The missing GIS prevents a *source-backed* feeder power-flow model, not proof that H30–H33 have no LV connections.

### Engineering decision needed for full 92395 AC

To test both 92395 four-house cohorts in pandapower without inventing existing EPM conductors, one option is an explicitly **hypothetical transformer-centred STAR connection**, with independent straight-line drops from mapped transformer to each house, assumed conductor parameters and x1.0/1.3/1.6 sensitivity. A separate branched option could be modelled, but is a new layout hypothesis, not evidence of the current electrical network. This topology choice must be approved before new code is written. The house-to-transformer straight-line distances are approximately H30 15.8 m, H31 280.7 m, H32 331.4 m and H33 525.3 m. All actual service routes, impedances, phase allocations and utility approval remain unverified.

### Subsequent approved PV+BESS study

For every geography/source-eligible cohort, test minimum-cost archived-hardware references and a meaningful 90%-self-sufficiency reference against the **new physical household membership**. Include 20% physical-SOC floor, battery charge-power limitations, AC inverter limits, no grid battery charging/export, hours and magnitude of PV curtailment, battery equivalent cycles, self-sufficiency, and causal PV-first charging sensitivity. Prior hardware costs/90% self-sufficiency are **selection provenance**, not claims for the new 35-house groupings. The historical 6,840 optimizations remain untouched.

### Upload results

For each of the six newly completed AC cases, upload `ac_summary.json` and `ac_hourly.csv` or one ZIP containing their six output folders. Also upload `92395_gross_transformer_only_summary.json` and optionally its hourly CSV. Report any script errors and stop at the failed gate. We will make a full A0/A1 balance-of-system comparison, then proceed to new PV+BESS energy dispatches and annual AC replays.
