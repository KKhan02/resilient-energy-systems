# Study A 92395: proposed STAR and MST, plus full-cohort PF and length sensitivities

## This addresses the requested correction

No actual LV sections in the **extracted** GIS does **not** imply that transformer 92395 has no physical LV service. The original 92395 houses **H30, H31, H32, H33** remain assigned to transformer **92395** under both A0 and A1. Their mapping to four separate annual stochastic household profiles remains unchanged.

The following networks are **proposed planning geometry**, not source EPM feeder sections:

- **STAR:** four direct connections from transformer 92395 to the four house positions.
- **MST:** the planar Euclidean minimum spanning tree connecting the transformer and four house positions. Each house has a separate 0.25 m numerical terminal stub to a co-located junction so the model does not treat customer load terminals as utility splice points. The stub is a numerical approximation, not a claimed service layout.

Both networks use the archived GIS transformer coordinate, its **5 kVA EPM source record**, the exact original source house positions, source PF assumptions, and the source model's illustrative AAC size 4 line parameters. Neither assumes a verified conductor/route/phase/protection design. **All** proposed edges scale with x1.0, x1.3, x1.6, because 92395 has no source-mapped LV segments to freeze.

The energy input is 2025 synthetic gross demand, **not PV+BESS**. The 92395 model deliberately reuses `run_epm_validation.build_net` and `seed_study_a_v6.solve_ac_hour` and **does not change** either original source file or the signed manifest. It records 0.95–1.05 pu, 0.97 pu sensitivity, <=100% loading, convergence and annual losses.

## Full cohort coverage

The previously supplied `SEEDExchange_StudyA_GrossAC_Sensitivity_v1/run_gross_sensitivity.py` already runs **all four GIS-modeled transformers under BOTH A0 and A1**, unless you expressly filter `--transformer`. There is no one-transformer restriction. The 113699 example was an optional pilot only.

| Territory | Population in A0 / A1 | Geometry | PF × assumed length combinations |
|---|---:|---|---:|
| 94022 | 10 / 8 | EPM LV + assumed services | 3 × 3 for each A0/A1 |
| 106039 | 12 / 11 | EPM LV + assumed services | 3 × 3 for each A0/A1 |
| 113699 | 4 / 6 | EPM LV + assumed services | 3 × 3 for each A0/A1 |
| 85398 | 4 / 5 | EPM LV + assumed services | 3 × 3 for each A0/A1 |
| **92395** | **4 / 4 (identical)** | **proposed STAR and MST** | **2 topologies × 3 × 3** |

The historical **eight** gross annual baselines PF0.98/length1.0 are preserved. For the four GIS modeled territories, **64 new** unique annual scenarios remain, making **72** total. For 92395, the 4-house A0 and A1 inputs are identical: rather than duplicating computation, each unique STAR/MST/PF/length solution is associated with **both** A0 and A1. This adds **18** distinct annual physical configurations. There are therefore **90 distinct annual numerical cases across all territories and both proposed 92395 topologies** when the full sweep finishes, of which 8 are already completed. Each new case is preceded by a separate 24-hour smoke test. This is not a claim that the simulations have already run.

PF settings: 0.95, 0.98, 1.00. Assumed service-length factors: 1.0, 1.3, 1.6. PF0.90 remains optional, not in this signed plan. One-house 98380 remains support-only, outside the approved >=4-house sweep.

## Windows instructions: Miniforge Prompt or Anaconda Prompt, from repository root

Extract this ZIP to your repository's `case1\studies\` directory. Keep the existing `SEEDExchange_StudyA_GrossAC_Sensitivity_v1` folder, `SEEDExchange_StudyA_v6_LocalRunner` (v6.2), `input_manifest_v6_2.json`, and all `outputs` exactly as they are.

### Step 1. Test the new proposed graph and sweep planning (no AC)

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\tests" -v
```

### Step 2. Inspect the run plan, no numerical execution

```bat
python "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\run_92395_star_mst.py" --repo-root . --phase all --dry-run
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase main --dry-run
```

### Step 3. Run the whole main sensitivity stage, ALL four GIS-backed transformers plus BOTH 92395 topologies

```bat
call "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\run_all_main.cmd"
```

This calls the existing GIS sensitivity runner **without a `--transformer` filter**, then the 92395 proposed STAR and MST baseline/main cases. Each produces 24-hour and 8,760-hour results in new output folders. It does not rerun/overwrite the eight existing annual GIS baselines.

### Step 4. Run all PF-by-length interactions

```bat
call "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\run_all_interactions.cmd"
```

You may also execute only the new 92395 study in one command:

```bat
python "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\run_92395_star_mst.py" --repo-root . --phase all --run
```

The 92395 runs are idempotent when files validate with checksum. A partial/mismatched existing folder blocks overwriting rather than silently replacing evidence.

## Source protections and provenance

- Requires exact signed `input_manifest_v6_2.json` SHA256 `2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69`.
- Revalidates unmodified original v6.2 runner, EPM GIS, all six electrical model module hashes, exact profile mapping and 35-house cohort source checks.
- Does not mutate the original v6 runner, source GIS, profiles, historical investment optimizations or prior outputs. No GitLab operations.
- Uses a balanced three-phase network proxy for source single-phase 240/120 V equipment. Never interpret these results as existing commissioned feeders, phase balance, known utility capacity or authorized household reconnection.
- `98380` remains one-house support-only. `113306` remains a separate optional transformer sensitivity, not part of this controlled six-transformer A0/A1 comparison.

## Next model phase, not yet executed

After reporting the gross AC PF-by-length matrix, evaluate both archived **minimum-cost** and **high-self-sufficiency** PV+BESS references for every >=4-house cohort, including dedicated four-house candidates. Separate 92395 STAR/MST topology choices must also be used in annual PV+BESS AC replay. Compare physical minimum SOC 20%, manufacturer battery continuous charge/discharge power, inverter kVA, annual PV available/generated/curtailed, charge/discharge/utilization/cycling, grid import, self-sufficiency, annual losses and AC thermal/voltage feasibility. Evaluate causal PV-first and perfect-foresight dispatch as distinct control strategies. Do not interpret the gross-load `inverter=0` results as PV+BESS configurations.

### Test coverage

Eight nonnumerical unit tests passed for planned 18 unique 92395 configurations, graph nodes/edges, the four fixed houses, MST sharing, x1.0 to x1.6 length scaling and rejected invalid scenarios. Full local EPM source loading and pandapower are **not installed in this analysis environment**, so the complete numerical AC integration is for your local machine. Results are not yet claimed.
