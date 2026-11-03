# Transformer-aware Volt–Var, feeder-end stress test

## What was tested

- 32 scenarios: 2 EPM candidate transformer territories (94022 / 10 houses; 106039 / 12 houses), PF 0.90 and 0.98, unity PF and Volt–Var Q ratios 0.25/0.48, transformer safeguard ON/OFF, feeder-end inverter, 1.0× assumed service-drop length, 40 selected critical hours per scenario.
- All 1,280 pandapower calculations converged. Scenarios using unity PF were duplicated across Q-ratio values; duplicates are excluded from the summary comparison CSV but retained in the original upload.
- This is a critical-hour *scenario sensitivity* study, not an annual compliance test.

## Findings

1. There were **82 overloaded Volt–Var scenario-hour observations with the guard OFF**, summed across the eight unique Volt–Var settings. With guard ON, the model reduced Q in 82 scenario-hours, and all transformer loadings fell to approximately 100% or below. A residual value of 100.000003% is numerical rounding rather than a meaningful thermal overload.
2. In the strongest stress case, transformer 106039, PF 0.90, Q ratio 0.48, peak transformer loading improved **181.84% to approximately 100%**. Minimum LV voltage improved 0.9381 → 0.9607 pu, but maximum LV voltage worsened 1.0390 → 1.0710 pu. The number of selected hours above 1.05 pu increased from 0 to 11. This is a physical trade-off of limiting reactive support, not a plotting error.
3. Transformer 94022, PF 0.90, Q ratio 0.48, peak loading improved **150.35% → 100%**, while maximum voltage increased **1.0384 → 1.0609 pu**.
4. **None of the 32 scenarios passed** the strict screen (voltage 0.97–1.03 pu, transformer ≤100%, LV conductor ≤100%) **or** the broader 0.95–1.05 pu and loading screen. This excludes the feeder-end location as a currently acceptable solution under this single dispatch and routing assumption.
5. At PF 0.90, unity-power-factor operation itself overloads the transformer for 106039 (10/40 sampled hours) and 94022 (1/40). A reactive safeguard that only clips Q cannot remove an overload already present at Q=0. These 11 observations are repeated in the Q-ratio-labelled unity rows, so the CSV total of 22 includes duplicates.
6. None of the assumed line ampacities was exceeded (highest line loading ~33%). Conductor ampacity and impedance are still proxies, not verified EPM measurements.

## What the controller does and does not prove

- The safeguard is a numerical reactive-power setpoint limiter: it keeps the active-power dispatch and household demand unchanged, searches between zero Q and requested Q, and flags unresolved overloads. It does **not** guarantee feasible voltage or remove overload caused by active power or fixed load Q.
- One guard-limited case evaluates to 100.000003%; use a small numerical tolerance when classifying compliance.
- 82 is a count of scenario-hour interventions, not 82 distinct dates/hours or annual hours.
- Detailed topology is built from EPM-mapped LV sections plus assumed customer service drops, with uncertain customer assignment and estimated conductor parameters.

## Next engineering step

Do not spend a full-year campaign on the feeder-end candidate yet. Prioritize transformer-head and midpoint placement, and coordinate Volt–Var with transformer kVA and both upper and lower voltage constraints. When Q alone cannot satisfy all constraints, add active-power curtailment or BESS redispatch as a separate explicitly costed corrective case. Then validate shortlisted feasible controls over 8,760 hours. Preserve the current PyPSA cost-optimal results as an energy-only reference; dispatch changes must be reflected in economics before claiming a final solution.
