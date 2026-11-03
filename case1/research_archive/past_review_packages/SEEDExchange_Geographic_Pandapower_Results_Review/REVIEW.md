# El Arenal: geographic pandapower critical-hour review

## Evidence and coverage

- Source: uploaded `geographic_pandapower_results.zip`.
- 48 conditional scenarios, 1,776 scenario-hour AC power flows, all converged.
- Six occupied candidate transformer territories; the seventh northern 25 kVA transformer has no assigned houses in the base allocation.
- Only **base** candidate assignments, minimum spanning tree routing, 1.3x detour, equal demand allocation, and PF 0.98/0.90 were executed.
- This is a **selected-hour screen, not annual validation**. The 36 critical hours per gross baseline and 40 per optimized case were selected separately. Counts of violating observations cannot be interpreted as full-year violation hours.
- All six territories have gross-load (no inverter injection) screens. Only 94022 (10 homes) and 106039 (12 homes) have *generic-house-count* optimized PV/BESS schedules. The 1-/4-home optimized cases were skipped.
- The 25 kVA northern unit was not simulated, because no houses are assigned to it in this base layout.

## Findings

- Under gross demand, PF 0.98, candidate trafo 94022 reaches 0.9307 pu and 108.5% transformer loading, and 106039 reaches 0.9115 pu and 125.6%. The four smaller gross PF 0.98 territories stay above 0.97 pu and below 100% transformer loading **among tested critical hours**.
- Optimized midpoint PV/BESS and PF 0.98 improve 94022 to minimum 0.941 pu and peak transformer loading 92.6%. For 106039 the corresponding values are 0.933 pu and 95.1%. Both have voltages below 0.95 pu; they do not pass voltage screening.
- At PF 0.90 the optimized midpoint cases peak at 102.0% for 94022 and 105.7% for 106039, exceeding nominal transformer capacity.
- Placing optimized PV/BESS at the end raises the maximum voltage to 1.048 pu (94022, PF 0.98) or 1.092 pu (106039, PF 0.98). The latter breaches the 1.05 pu reference ceiling in 13 of its selected 40 hours. For 106039, midpoint PF 0.98 reaches 1.033 pu; head placement remains below 1.03 but suffers worse minimum voltage.
- The no-PV/BESS baseline produces **identical** electrical results for all three inverter placements. This is because the inverter injection is identically zero in that design, not because siting has no effect.
- No nominal LV thermal overload occurs in any tested scenario using the **assumed** 150 A conductor limit.

## Interpretation constraints

- House-to-transformer associations are provisional. All inter-house links are algorithmic radial candidates, not as-built cables. The longest 1.3x-MST candidate path is approximately 1,275 m for transformer 106039 and 876 m for transformer 94022.
- Impedances and transformer data are representative assumptions; source is an ideal MV supply without upstream voltage drops; LV single-phase service is represented using a balanced three-phase equivalent, not explicit phase imbalance or neutral effects.
- Optimized generic 10-/12-house dispatches are *not* house-specific measured or georeferenced injections. There is one combined inverter per territory; no voltage-reactive control.
- Single allocation (equal), one routing hypothesis (MST) and one distance factor (1.3) were evaluated. We cannot infer sensitivity to alternatives from this archive.
- A converged AC power flow confirms numerical convergence, not compliance with design limits.

## Figures

1. `01_territory_min_voltage`: Gross-demand PF 0.98 comparison across six candidate territories, with optimized midpoint results for the two larger territories.
2. `02_territory_transformer_loading`: Matching transformer-loading comparison.
3. `03_optimized_inverter_siting_voltage`: Head/midpoint/end location sensitivity for the two occupied PV/BESS cases at PF 0.98, with minimum and maximum house voltages; no connecting lines.
4. `04_power_factor_optimized_midpoint`: PF 0.98 versus PF 0.90 voltage range at midpoint injection.

## Proposed next runs

1. Run topological/route stress sensitivities with the existing code: star versus MST routing, distance factors 1.0/1.3/1.6, and far-end-heavy load allocation, while keeping gross and optimized cases separate. Prioritize 94022 and 106039. Run a small critical-hour screen first.
2. Evaluate the northern-transformer alternative and H10/H29 reassignment cases separately. They change which houses fall within a territory; not as-built validation.
3. Run selected **full-year** AC cases after scenario screening, starting with the two larger territories at PF 0.98 and 0.90 and the most informative inverter siting choices. Compare different site placements using the *same* hourly schedules.
4. Integrate AC limits and losses back into PV/BESS sizing or test a revised dispatch. A fixed energy-only schedule is not necessarily electrically feasible.
5. Resilience and adaptability modelling should build on configurations that pass the defined AC constraints.
