# Coordinated AC Q-sweep: numerical review

**Source:** user-uploaded `coordinated_q_results.zip`; 116 scenarios, 4,640 converged recorded scenario-hour results, 40 selected critical hours per scenario. Transformer 94022 has 10 candidate households; transformer 106039 has 12. EPM LV node topology plus assumed house service connections; nominal ratings 5 kVA. Load PF 0.98, service factor 1.0, equal allocation, optimized active-power dispatch held fixed.

## Key findings

- **106039, inverter head:** coordinated Q ratio 0.25 is the lowest *tested* value meeting 0.97–1.03 pu voltage, <=100% transformer and line loading in all 40 critical hours (9 of 14 coordinated ratios pass).
- **106039, inverter midpoint:** coordinated Q ratio 0.20 is the lowest *tested* ratio meeting all four AC checks in all 40 hours (10 of 14 ratios pass). At ratio 0.20: min V 0.970037 pu, max V 1.023206 pu, peak transformer 93.525%, mean sampled loss 0.154164 kW.
- **94022, inverter head:** 36/40 is the maximum achieved, at ratios 0.35–0.60. The source of violations remains low voltage with some transformer limits at the more aggressive settings.
- **94022, inverter midpoint:** best 38/40 at ratios 0.48 and 0.60. At ratio 0.48, two sampled hours are not AC-feasible within the Q search and fixed active dispatch: 2025-10-28 20:00 and 2025-11-27 20:00. Both exceed 100% transformer loading in the closest found solution, and the latter also has voltage below 0.97 pu. At these two hours the recorded combined inverter active injection is 0 kW, while gross load is 4.151 and 4.250 kW respectively. This is a good target for checking battery SOC and possible active-power redispatch, rather than further increasing Q.
- **HIL-only Volt–Var** never achieves 40/40 in any location or transformer group. Coordinated Q performs better within the searched grid, at the expense of supervisory AC measurements/modeling and potential network losses.
- For 106039, head at Q=0.25 and middle at Q=0.20 are both 40/40 feasible. Their mean critical-hour losses differ: approximately 0.0897 kW at the head versus 0.1542 kW at the midpoint, so the lower Q ratio is not necessarily the most economical siting.
- More Q capability is not automatically better: for 106039 middle, ratio 0.20 already passes all 40; at 0.60 peak loading rises to 98.56% and mean sampled losses 0.1841 kW. At 0.20 they are 93.53% and 0.1542 kW, respectively.

## Interpretation constraints

- All 40 selected hours are feasible in a case does **not** imply 8,760-hour network compliance. The selected 106039 minima approach 0.9700 pu, leaving essentially zero design margin. A robust target such as 0.975 pu, plus test of PF 0.90 and service factors 1.3/1.6, may change the result.
- By default, with no `--p-installed` override, the driver sets its installed-active-power reference equal to the inverter kVA numerical rating (10 and 12). Thus Q ratio 0.20 for 106039 implies a 2.4 kvar Q ceiling; this proxy must be checked against actual inverter active nameplate before treating the ratio as a device specification.
- Coordinated Q searches an AC-feasible Q **for each hour** with network-wide voltage and loading awareness. It is not equivalent to a locally autonomous HIL Q(U) curve. Control actuation/delay, communications, measurement accuracy and discrete sampling are not yet established.
- Active-power dispatch remains fixed; no battery SOC-aware re-dispatch or P curtailment is incorporated. A failed Q search does not mean a feeder is impossible to improve by redesign, active-power adjustment or reinforcement.
- Feeder impedance/ampacity are screening proxies, and house-to-line connections are assumed. The model is a balanced three-phase equivalent of 1-phase infrastructure. These sensitivities must be reported before making deployment claims.

## Recommended actions

1. Run full-year **106039 head Q=0.25 and/or midpoint Q=0.20** with coordinated control at load PF 0.98, using exact same input year. Compare unity PF for context and count annual violations rather than only extremes.
2. Repeat the 40 critical-hour sweep at PF 0.90 and service factors 1.3, 1.6 for the shortlisted ratios, with other uncertainties held constant.
3. For 94022, investigate the two identified infeasible autumn evening hours at Q=0.48 middle. Consider a modest voltage-aware P/SOC redispatch, inverter relocation or line/transformer reinforcement. Do not simply increase Q ceiling.
4. Only after checking full-year AC feasibility and robustness should the candidate design proceed to resilience and adaptability studies.
