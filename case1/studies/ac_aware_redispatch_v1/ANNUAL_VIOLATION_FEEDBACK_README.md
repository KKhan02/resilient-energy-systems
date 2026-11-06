# WP1 annual AC-violation feedback (additive patch, 4 November 2026)

This patch adds **only** `run_annual_feedback.py`, this README, and one test file. It does not edit the preexisting PyPSA, pandapower, old battery controller, annual validation scripts, or saved outputs.

## Why it is needed

The conservative seven-house, transformer 94022, 5 kVA assumed, nighttime-Q-off manufacturer-SOC baseline gives 8,756 feasible of 8,760 AC hours. All four violations are evening undervoltages, with zero PV and zero inverter P. Three of the four hours have the battery Store at its **manufacturer-SOC floor** (1.145 kWh in the old usable-energy coordinate). The 29 Nov 19:00 hour has stored energy, but the baseline solver allocates some to the following hour. One-hour independent P injections would fabricate battery energy or leave later hours unsolved.

## What the patch does

1. Checks the complete annual AC replay against the exact manufacturer-baseline trajectory and hashes recorded in its summary. Fails on mismatches or partial annual results.
2. Recreates precisely the same selected seven-house GIS network and assumptions as the prior pilot.
3. For **every failed hour**, evaluates 9 inverter P samples between zero and the demand/rating cap with the existing coordinated-Q pandapower logic. Nighttime Q stays disabled. No assumed PV production is inserted into those evening hours.
4. Constructs **sampled, provisional P bands**. They are not guaranteed feasible between samples. If a failed hour lacks any feasible sample, the pilot halts rather than inventing an electrical solution.
5. Re-solves the **same fixed equipment** over all 8,760 hours with the existing PyPSA Store `e_cyclic`, real charging/discharging losses, manufacturer minimum SOC, zero export and zero ENS. Fixed equipment is unchanged: 26 panels, 5 Deye SE-G5.1 modules, 8.499 kW battery DC power, 7.6 kVA inverter.
6. Rechecks the original four failed hours in pandapower, records annual cost and energy differences relative to the identical manufacturer-SOC baseline.
7. Requires **another full-year independent pandapower validation** of the new trajectory before any annual feasibility claim. Savings or improvements from an arbitrary single-hour adjustment are never asserted.

This is a *conditional engineering research model*: balanced GIS feeder; unverified house connections, phases and conductor impedances; 0.97 to 1.03 pu, 100% thermal study screening; no official EPM approval. AC losses, inverter nighttime/standby losses and full AC energy balance remain outside PyPSA's objective. Nighttime inverter Q is not enabled.

## Run in Windows CMD from the repository root

Extract the patch ZIP into `D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems`. It adds three files under `case1/studies/ac_aware_redispatch_v1/`.

Run tests first:

```cmd
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests
```

Then the first feedback run. Paths assume the exact output names from the previous steps:

```cmd
python case1/studies/ac_aware_redispatch_v1/run_annual_feedback.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_pilot_02 --annual-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_manufacturer_annual_ac_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_01 --p-grid-points 9 --q-grid-points 9 --q-refine 0
```

If the 8,760-hour PyPSA re-solve succeeds, the next command independently replays the **new** schedule over the whole year:

```cmd
python case1/studies/ac_aware_redispatch_v1/validate_annual_ac.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_01 --trajectory redispatched --outdir case1/studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_ac_check_01
```

Do not run this last command if `run_annual_feedback.py` reports unresolved P bands or an infeasible PyPSA reoptimization. Never call selected-hour success a full-year pass. If a later AC replay still fails, repeat from the latest annual evidence only after reviewing new failure hours and deciding whether another cutting/feedback iteration is justified.

## Output

- `ac_p_samples.csv`: AC results for all sampled P at originally violating hours.
- `sampled_corridors.csv`: provisional P bands with units and hour indices.
- `unresolved_hours.csv`: failures to locate any feasible P operating sample.
- `redispatched_hourly.csv`: 8,760-hour new PyPSA energy/Store SOC trajectory, if feasible.
- `formerly_failing_hours_rechecked.csv`: independent pointwise AC checks after redispatch.
- `feedback_manifest.json`: hashes, original fail count, fixed hardware, costs, outcomes, and explicit limitations.
- `pilot_manifest.json`: copy of the original pilot metadata plus an explicit feedback provenance chain, to allow use of the existing `validate_annual_ac.py` without changing it.

## Scientific interpretation

The originally failing hours had zero inverter P; the test asks whether reallocation of finite stored energy from other hours fixes the AC constraints. A feasible sampled corridor does **not** prove battery energy exists at that hour. The PyPSA solve decides that globally. It may return `infeasible`, or it may shift operations and create new AC violations elsewhere. Both are valuable research results and must be recorded without upgrading hardware automatically.

No arbitrary adaptive-reserve SOC heuristic is included. The manufacturer DoD floor is retained. This fixed-hardware pilot does not replace the planned PV, battery energy/power, inverter, siting and household sweeps.
