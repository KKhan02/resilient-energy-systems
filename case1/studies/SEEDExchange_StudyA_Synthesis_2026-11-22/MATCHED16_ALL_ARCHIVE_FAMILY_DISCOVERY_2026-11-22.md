# Study A | all original AC source families checked against 16 reciprocal equipment cases

**Date:** 22 November 2026. **Nature:** read-only remote source-manifest and saved 2025 hourly-input review. **Not an additional AC solver run.**

## Two separate stages must remain distinct

1. The user reported a **successful local run** of the first `matched16_original_ac_input_preflight.py` on the fixed sync branch. Console receipt: `ORIGINAL_AC_INPUTS_CHECKED_NO_AC_SOLVES`, 16 cases, 2 original AC input-match candidates, 17,520 compared original input hours, **0 certified corrected-AC reuse hours**, no new AC solves. The local resulting `StudyA_Matched16_OriginalAC_InputPreflight_v1/` has **not been pushed to GitLab** as of this audit. The assistant could not yet independently inspect or verify its saved machine-readable `RUN_MANIFEST.json` or `CASE_INPUT_GATE.csv`. Do not call the user console response a reviewed, committed source receipt.
2. An additional **GitLab-side read-only broader archive search** now screened all **22 distinct original equipment source families** implicated by the saved 432-case AC archive. Exact target-household membership, assignment, transformer, PV panel quantity, BESS module number, BESS DC continuous kW, inverter AC kVA and assumed transformer kVA were compared to every source `energy_manifest.json` in that target's territory. **Four**, not only two, reciprocal cases have a matching original source family.

## Four original-equipment family and schedule matches

| Reciprocal case | Source family | Hardware and source energy signature | Original PF .98/length1 AC source infeasible hours |
|---|---|---|---:|
| `A0_106039_min_cost_to_A1` | `A1_106039_min_cost_ref` | 41 PV, 8 batteries, 12 kW DC, 12 kVA inverter, assumed 5 kVA | 1 |
| `A1_106039_min_cost_to_A0` | `A0_106039_min_cost_ref` | 41 PV, 8 batteries, 12 kW DC, 12 kVA inverter, assumed 5 kVA | 10 |
| `A1_85398_min_cost_to_A0` | `A0_85398_min_cost_ref` | 17 PV, 3 batteries, 5.386094221 kW DC, 5 kVA inverter, assumed 5 kVA | 0 |
| `A1_85398_ss90_to_A0` | `A0_85398_ss90_ref` | 20 PV, 5 batteries, 6.096291873 kW DC, 6 kVA inverter, assumed 5 kVA | 0 |

The two 85398 matches were not counted by the earlier **target-native same-tier family-only** preflight because that preflight used the selected `A0_85398_*_four` hardware, while these additional matches refer to the distinct historical `A0_85398_*_ref` alternative family. Both source-family `energy_csv_sha256` values equal the reciprocal target's `target_energy_sha256` exactly. Their original 2025 PF .98, length 1.0, optimized-dispatch `ac_hourly.csv` files both contain 8,760 rows and identical timestamps, gross demand, inverter AC P, day/night Q policy and PF inputs as the signed source energy `energy_hourly_2025.csv`. Both source AC files have 8,760 converged rows, zero invalid-night-Q events and zero main research band infeasible hours. These hour-field comparisons were performed directly on the remotely stored CSV rows; hash receipts have not yet been regenerated user-locally for these two source pairs.

The two 106039 target-native comparisons were already independently checked against archived source data in the previous continuation and subsequently passed the user's local reference-only preflight, but full user-local result archive still needs to be uploaded and independently audited.

**Do not overclaim:** the two added 85398 original AC matches are not new corrected-SOC AC validation; even 8,760 exact original P/aggregate demand/Q flags per case do not prove equality to previously corrected 2025 inverter P/Q or the actual household phase/wiring, line impedance and transformer rating. Do not substitute these source AC feasible hours into a new whole-34-house AC certification.

## Coverage and next decision

- **4/16** reciprocal cases now have an **original source-family hardware and energy schedule match** within the 22 family 432-case archived AC roster. The original-source 8,760-hour input fields have been checked directly for both additional 85398 pairs. These 4 cases represent **35,040 original reference input-hours** across four independently modelled territory/source scenarios, not unique community hours and not annual corrected-AC reuse.
- **12/16** reciprocal cases have no corresponding **exact hardware/assignment/household combination** among these 22 source families. This is not proof of physical infeasibility or absence of other historical source archives.
- The user should upload the existing v1 local receipt before a new v2 screening package. The next strict test for all four cases is the **SOC-corrected hourly P and selected Q** source provenance and AC input identity, including per-house load mapping and network fingerprint, rather than reusing original AC response fields without proof.
- The later power-flow workload for the 12 others should be selected after source-equivalence and actual EPM network conditions. Avoid automatically running 12x9 full-year AC cases.

## Sources

- `StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json` (16 reciprocal cases)
- `case1/studies/SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17/PORTFOLIO_432_ORIGINAL_PLUS_CONDITIONAL_FIVE_EDGE_OVERLAY.csv` (432 annual original AC case records)
- The 22 `case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01/energy_<family>/energy_manifest.json` source metadata records
- `.../energy_A0_85398_min_cost_ref/energy_hourly_2025.csv` and `.../energy_A0_85398_ss90_ref/energy_hourly_2025.csv`
- `.../annual_ac_replays_v1/A0_85398_min_cost_ref_mapped_optimized_pf098_length10_annual8760/{ac_summary.json,ac_hourly.csv}`
- `.../annual_ac_replays_v1/A0_85398_ss90_ref_mapped_optimized_pf098_length10_annual8760/{ac_summary.json,ac_hourly.csv}`
- Previously reviewed exact 106039 source documents and source receipts. No original files changed.
