# El Arenal | Geographic AC sensitivity review

**Scope:** 144 conditional pandapower scenarios, 40 selected hours each (5,760 converged AC calculations). Transformer 94022 serves 10 candidate houses; transformer 106039 serves 12 candidate houses. These are model allocations, not verified meter connections.

## Screening results

- All 144 scenarios converged for their selected 40 hours. Convergence is not proof of engineering compliance.
- 12/144 scenarios passed the joint project screen: all tested house voltages in 0.97–1.03 pu and peak transformer/line loading no greater than 100%.
- 47/144 scenarios passed the wider 0.95–1.05 pu screen with no transformer/line overloading.
- All 12 strict-screen passes occur in star-feeder configurations with assumed PF 0.98. The MST hypotheses have no strict passes across the 72 MST cases; none of the 72 PF 0.90 cases pass.
- Across all scenarios, the worst calculated voltage is 0.8437 pu and the greatest maximum voltage is 1.1121 pu. They occur in different scenarios and should not be combined as one network condition.
- The highest transformer loading is 112.2%. No modelled LV conductor exceeds its synthetic 0.15 kA limit (highest loading about 18.3%).

## Controlled comparison (PF 0.98, equal allocation, 1.3 route factor)

| Transformer | Feeder | Inverter | Min V (pu) | Max V (pu) | Peak transformer (%) | Strict screen |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 94022 | MST | end | 0.9409 | 1.0477 | 92.6 | Fail |
| 94022 | MST | head | 0.9409 | 0.9945 | 92.6 | Fail |
| 94022 | MST | middle | 0.9409 | 1.0107 | 92.6 | Fail |
| 94022 | STAR | end | 0.9725 | 1.0594 | 90.0 | Fail |
| 94022 | STAR | head | 0.9725 | 0.9984 | 90.0 | Pass |
| 94022 | STAR | middle | 0.9725 | 1.0241 | 90.0 | Pass |
| 106039 | MST | end | 0.9334 | 1.0921 | 95.1 | Fail |
| 106039 | MST | head | 0.9303 | 0.9985 | 95.5 | Fail |
| 106039 | MST | middle | 0.9334 | 1.0326 | 95.1 | Fail |
| 106039 | STAR | end | 0.9743 | 1.0512 | 93.3 | Fail |
| 106039 | STAR | head | 0.9738 | 0.9985 | 93.3 | Pass |
| 106039 | STAR | middle | 0.9743 | 1.0205 | 93.3 | Pass |

## Main interpretation

1. **Routing dominates some voltage outcomes.** At midpoint inverter placement, PF 0.98, equal load distribution and factor 1.3, the minimum voltage for 94022 is 0.9409 pu (MST) versus 0.9725 pu (star). For 106039 it is 0.9334 (MST) versus 0.9743 (star). These comparisons reflect *alternative hypothetical radial topologies*, not a choice that has already been surveyed or built.
2. **End-of-feeder injection risks overvoltage.** Under the same reference case, maxima for the far-end inverter are 1.0477 (MST) and 1.0594 (star) for 94022; 1.0921 (MST) and 1.0512 (star) for 106039. No far-end-siting scenario satisfies the strict full screen over all tested hours.
3. **Lower power factor matters.** None of the 72 PF 0.90 scenarios meets all joint strict criteria. At the 1.3 factor with far-end-heavy allocation and a midpoint inverter, 106039 transformer peak loading is 109.5% (MST) and 104.1% (star), despite voltage improvements in the star design.
4. **Star routings use more installed conductor length in the hypotheses.** At multiplier 1.3, 94022 has 2.00 km MST versus 3.77 km star; 106039 has 1.64 km MST versus 2.82 km star. This additional line cost has not been included in the PyPSA economic optimum; therefore a passing star layout should not be called economically preferable without reinforcement costing.
5. **Shorter feeder paths help voltage.** As the assumed detour factor increases from 1.0 to 1.6, the modeled MST midpoint minimum voltage for 106039 falls from 0.9442 to 0.9223 pu in the PF 0.98/equal case.

## Important limitations and next decision

- Only 40 critical hours per scenario were evaluated; do not interpret the counts as full-year violation hours or annual loss figures.
- The routing is MST or star with geometric detour factors of 1.0/1.3/1.6, not verified cable geography. The terminal voltage findings are sensitive to this distinction.
- The electrical model uses a balanced three-phase equivalent of a 240 V single-phase feeder, fixed loop resistance/reactance assumptions, an ideal upstream MV source, and unverified conductor ratings and transformer impedance. Phase/neutral effects, real conductor layout and actual voltage regulator settings remain outside scope.
- The inverter is a combined PV+BESS AC injector at unity power factor using fixed prior PyPSA active-power dispatch. The model does not AC-optimize inverter reactive support or resolve PV/BESS sizes after line losses and voltage constraints.
- Association alternatives H01/H02, H10 and H29 were not swept in this run. Transformer-to-house assignments remain provisional.
- **Recommended next work:** targeted annual AC simulation for a small matched subset of contrasting MST and star cases, followed by an explicitly costed and AC-feasible redesign. Prioritize obtaining conductor and route evidence before selecting star as an engineering solution. Then proceed to resilience/adaptability on accepted configurations.

## Figures

- `01_min_voltage_by_inverter_position`: reference minimum voltage, two transformer groups, both routing hypotheses.
- `02_max_voltage_by_inverter_position`: remote inverter voltage rise.
- `03_feeder_path_length_vs_minimum_voltage`: longest assumed electrical path versus worst voltage for midpoint inverter, three distance factors.
- `04_transformer_loading_vs_power_factor`: reactive demand impacts under far-end-heavy loading.
- `05_assumed_lv_route_length`: cost-relevant total routed length comparison.

All optimization and electrical comparisons are conditional simulations. They do not verify the EPM as-built supply network or utility permissible voltage range.
